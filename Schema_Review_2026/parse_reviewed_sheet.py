#!/usr/bin/env python3
"""
parse_reviewed_sheet.py

Ingests the reviewed Australian Heritage Schema spreadsheet (.ods or .csv)
populated by Mick Morrison, validates the review actions (RETAIN, MODIFY, DELETE, NEW_FIELD),
and produces:
1. schema_review_audit_diff.md (Human-readable change log and diff summary)
2. revised_schema_2026.json (Structured machine-readable schema for GeoPackage / Fieldmark)
"""

import os
import sys
import csv
import json
import zipfile
import argparse
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ODS = os.path.join(SCRIPT_DIR, 'Australian_Heritage_Schema_Review_2026.ods')
CSV_DIR = os.path.join(SCRIPT_DIR, 'csv')
OUTPUT_DIFF_MD = os.path.join(SCRIPT_DIR, 'schema_review_audit_diff.md')
OUTPUT_REVISED_JSON = os.path.join(SCRIPT_DIR, 'revised_schema_2026.json')

NS = {
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
}

def read_ods_sheets(ods_path):
    """Extracts tables and rows directly from ODS content.xml without external dependencies"""
    with zipfile.ZipFile(ods_path, 'r') as zf:
        content_xml = zf.read('content.xml')

    root = ET.fromstring(content_xml)
    sheets = {}

    for t in root.findall('.//table:table', NS):
        sheet_name = t.attrib.get(f"{{{NS['table']}}}name", "")
        rows_data = []

        for r in t.findall('table:table-row', NS):
            row_cells = []
            for c in r.findall('table:table-cell', NS):
                # Check for repeated cells
                repeat = int(c.attrib.get(f"{{{NS['table']}}}number-columns-repeated", "1"))
                
                # Extract text
                texts = []
                for p in c.findall('text:p', NS):
                    texts.append("".join(p.itertext()))
                cell_text = "\n".join(texts).strip()

                for _ in range(min(repeat, 30)): # Guard against large empty repeats
                    row_cells.append(cell_text)

            # Strip trailing blank cells
            while row_cells and not row_cells[-1]:
                row_cells.pop()

            if any(row_cells):
                rows_data.append(row_cells)

        sheets[sheet_name] = rows_data

    return sheets

def read_csv_sheets(csv_dir):
    """Fallback reader from CSV files in csv/"""
    sheets = {}
    csv_files = {
        "01_Instructions_and_Legend": "01_Instructions_and_Legend.csv",
        "02_Forms_Overview": "02_Forms_Overview.csv",
        "03_Fields_Review": "03_Fields_Review.csv",
        "04_Value_Lists_Vocabularies": "04_Value_Lists_Vocabularies.csv",
        "05_Logic_and_Workflows": "05_Logic_and_Workflows.csv"
    }
    for s_name, fname in csv_files.items():
        p = os.path.join(csv_dir, fname)
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                sheets[s_name] = list(reader)
    return sheets

def parse_review(sheets):
    forms_raw = sheets.get("02_Forms_Overview", [])
    fields_raw = sheets.get("03_Fields_Review", [])
    vocab_raw = sheets.get("04_Value_Lists_Vocabularies", [])
    logic_raw = sheets.get("05_Logic_and_Workflows", [])

    # 1. Parse Forms
    forms_dict = {}
    if forms_raw:
        headers = forms_raw[0]
        for row in forms_raw[1:]:
            if not row or len(row) < 3:
                continue
            r_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
            entity_code = r_dict.get("Entity_Code", "").strip()
            if entity_code:
                forms_dict[entity_code] = {
                    "module": r_dict.get("Module_Source", ""),
                    "label": r_dict.get("REVISED_FORM_LABEL") or r_dict.get("Form_Label", ""),
                    "original_label": r_dict.get("Form_Label", ""),
                    "level": r_dict.get("Entity_Level", ""),
                    "parent": r_dict.get("Parent_Entity", ""),
                    "prefix": r_dict.get("REVISED_ID_PREFIX") or r_dict.get("Current_ID_Prefix", ""),
                    "original_prefix": r_dict.get("Current_ID_Prefix", ""),
                    "geometry": r_dict.get("GEOMETRY_CHOICE") or r_dict.get("Spatial_Geometry", ""),
                    "action": (r_dict.get("ACTION") or "RETAIN").strip().upper(),
                    "notes": r_dict.get("ARCHAEOLOGICAL_NOTES_AND_RATIONALE", ""),
                    "fields": []
                }

    # 2. Parse Fields
    field_stats = {"RETAIN": 0, "MODIFY": 0, "DELETE": 0, "NEW_FIELD": 0, "UNKNOWN": 0}
    modified_fields = []
    deleted_fields = []
    new_fields = []

    if fields_raw:
        headers = fields_raw[0]
        for row in fields_raw[1:]:
            if not row or len(row) < 4:
                continue
            r_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
            form_ent = r_dict.get("Form_Entity", "").strip()
            fname = r_dict.get("Field_Name", "").strip()
            action = (r_dict.get("ACTION") or "RETAIN").strip().upper()

            if action not in field_stats:
                field_stats["UNKNOWN"] += 1
            else:
                field_stats[action] += 1

            field_entry = {
                "form_entity": form_ent,
                "tab": r_dict.get("Tab_Section", ""),
                "order": r_dict.get("Field_Order", ""),
                "name": fname,
                "label": r_dict.get("REVISED_FIELD_LABEL") or r_dict.get("Field_Label", ""),
                "original_label": r_dict.get("Field_Label", ""),
                "type": r_dict.get("REVISED_FIELD_TYPE") or r_dict.get("Field_Type", ""),
                "original_type": r_dict.get("Field_Type", ""),
                "vocab_name": r_dict.get("REVISED_VALUE_LIST") or r_dict.get("Value_List_Name", ""),
                "original_vocab_name": r_dict.get("Value_List_Name", ""),
                "required": r_dict.get("REQUIRED", "No").strip().lower() in ("yes", "true", "1"),
                "action": action,
                "notes": r_dict.get("ARCHAEOLOGICAL_NOTES_AND_CHANGES", "")
            }

            if action == "DELETE":
                deleted_fields.append(field_entry)
            elif action == "MODIFY":
                modified_fields.append(field_entry)
            elif action == "NEW_FIELD":
                new_fields.append(field_entry)

            # Match into form dict if exists
            for ent_code, ent_data in forms_dict.items():
                if ent_data["original_label"] == form_ent or ent_code == form_ent:
                    ent_data["fields"].append(field_entry)
                    break

    # 3. Parse Vocabularies
    vocab_stats = {"RETAIN": 0, "MODIFY": 0, "DELETE": 0, "ADD_TERM": 0}
    vocab_changes = []
    if vocab_raw:
        headers = vocab_raw[0]
        for row in vocab_raw[1:]:
            if not row or len(row) < 4:
                continue
            r_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
            v_act = (r_dict.get("ACTION") or "RETAIN").strip().upper()
            if v_act in vocab_stats:
                vocab_stats[v_act] += 1
            if v_act != "RETAIN":
                vocab_changes.append({
                    "vocab": r_dict.get("Vocab_Name", ""),
                    "term": r_dict.get("Term_Label", ""),
                    "action": v_act,
                    "revised_term": r_dict.get("REVISED_TERM_LABEL", ""),
                    "revised_def": r_dict.get("REVISED_DEFINITION", ""),
                    "notes": r_dict.get("NOTES", "")
                })

    # 4. Parse Logic
    logic_changes = []
    if logic_raw:
        headers = logic_raw[0]
        for row in logic_raw[1:]:
            if not row or len(row) < 3:
                continue
            r_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
            l_act = (r_dict.get("ACTION") or "RETAIN").strip().upper()
            if l_act != "RETAIN" or r_dict.get("REVISED_LOGIC_REQUIREMENTS"):
                logic_changes.append({
                    "rule_id": r_dict.get("Logic_Rule_ID", ""),
                    "name": r_dict.get("Rule_Name", ""),
                    "action": l_act,
                    "revised_requirements": r_dict.get("REVISED_LOGIC_REQUIREMENTS", ""),
                    "notes": r_dict.get("ARCHAEOLOGICAL_RATIONALE_AND_NOTES", "")
                })

    return forms_dict, field_stats, modified_fields, deleted_fields, new_fields, vocab_stats, vocab_changes, logic_changes

def generate_diff_report(forms_dict, field_stats, modified_fields, deleted_fields, new_fields, vocab_stats, vocab_changes, logic_changes):
    md_lines = [
        "# Australian Heritage Survey — Schema Review Audit & Diff Report",
        "",
        "> **Generated by parse_reviewed_sheet.py**  ",
        "> Captures all user-submitted review actions for contemporary archaeological practice.",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"* **Total Forms / Entities**: {len(forms_dict)}",
        f"* **Field Decisions**: {field_stats['RETAIN']} Retained | {field_stats['MODIFY']} Modified | {field_stats['DELETE']} Deleted | {field_stats['NEW_FIELD']} Added",
        f"* **Vocabulary Terms**: {vocab_stats['RETAIN']} Retained | {vocab_stats['MODIFY']} Modified | {vocab_stats['DELETE']} Deleted | {vocab_stats['ADD_TERM']} Added",
        f"* **Workflow / Logic Rules Updated**: {len(logic_changes)}",
        "",
        "---",
        "",
        "## 2. Forms Overview & Status",
        "",
        "| Entity Code | Current Label | Action | Revised Label | Geometry | Notes |",
        "|---|---|---|---|---|---|"
    ]

    for code, fdata in forms_dict.items():
        act_badge = f"**{fdata['action']}**"
        rev_lbl = fdata['label'] if fdata['label'] != fdata['original_label'] else "—"
        md_lines.append(f"| `{code}` | {fdata['original_label']} | {act_badge} | {rev_lbl} | {fdata['geometry']} | {fdata['notes'] or '—'} |")

    md_lines.extend([
        "",
        "---",
        "",
        "## 3. Field Modifications (Action = MODIFY)",
        ""
    ])

    if modified_fields:
        md_lines.append("| Form / Entity | Tab | Field Name | Original Label | Revised Label | Original Type | Revised Type | Notes |")
        md_lines.append("|---|---|---|---|---|---|---|---|")
        for mf in modified_fields:
            md_lines.append(f"| {mf['form_entity']} | {mf['tab']} | `{mf['name']}` | {mf['original_label']} | **{mf['label']}** | {mf['original_type']} | {mf['type']} | {mf['notes'] or '—'} |")
    else:
        md_lines.append("*No fields currently marked as MODIFY (all retained or deleted).*")

    md_lines.extend([
        "",
        "---",
        "",
        "## 4. Field Deletions (Action = DELETE)",
        ""
    ])

    if deleted_fields:
        md_lines.append("| Form / Entity | Tab | Field Name | Label | Original Type | Archaeological Rationale |")
        md_lines.append("|---|---|---|---|---|---|")
        for df in deleted_fields:
            md_lines.append(f"| {df['form_entity']} | {df['tab']} | `{df['name']}` | {df['original_label']} | {df['original_type']} | {df['notes'] or 'Marked for deletion'} |")
    else:
        md_lines.append("*No fields currently marked for DELETE.*")

    md_lines.extend([
        "",
        "---",
        "",
        "## 5. New Fields Added (Action = NEW_FIELD)",
        ""
    ])

    if new_fields:
        md_lines.append("| Form / Entity | Tab | Proposed Field Name | Proposed Label | Type | Vocab | Notes |")
        md_lines.append("|---|---|---|---|---|---|---|")
        for nf in new_fields:
            md_lines.append(f"| {nf['form_entity']} | {nf['tab']} | `{nf['name']}` | {nf['label']} | {nf['type']} | {nf['vocab_name']} | {nf['notes']} |")
    else:
        md_lines.append("*No new fields currently added.*")

    md_lines.extend([
        "",
        "---",
        "",
        "## 6. Controlled Vocabulary Changes",
        ""
    ])

    if vocab_changes:
        md_lines.append("| Vocabulary | Action | Original Term | Revised Term | Definition / Notes |")
        md_lines.append("|---|---|---|---|---|")
        for vc in vocab_changes:
            md_lines.append(f"| `{vc['vocab']}` | **{vc['action']}** | {vc['term']} | {vc['revised_term'] or '—'} | {vc['revised_def'] or vc['notes'] or '—'} |")
    else:
        md_lines.append("*All 111 controlled vocabularies and 1,060 terms currently retained as baseline.*")

    md_lines.extend([
        "",
        "---",
        "",
        "## 7. Business Logic & Workflow Adjustments",
        ""
    ])

    if logic_changes:
        md_lines.append("| Rule ID | Rule Name | Action | Revised Requirements | Notes |")
        md_lines.append("|---|---|---|---|---|")
        for lc in logic_changes:
            md_lines.append(f"| `{lc['rule_id']}` | {lc['name']} | **{lc['action']}** | {lc['revised_requirements']} | {lc['notes']} |")
    else:
        md_lines.append("*All core logic workflows (autonumbering, GPS validation, 1:N relations, cascade deletes) retained as baseline.*")

    return "\n".join(md_lines)

def main():
    parser = argparse.ArgumentParser(description="Parse reviewed schema spreadsheet and output audit diff & revised JSON.")
    parser.add_argument('--input', default=DEFAULT_ODS, help=f"Path to reviewed .ods spreadsheet (default: {DEFAULT_ODS})")
    parser.add_argument('--use-csv', action='store_true', help="Read from CSV files in csv/ instead of ODS")
    args = parser.parse_args()

    if args.use_csv or not os.path.exists(args.input):
        print(f"Reading from CSV files in {CSV_DIR}...")
        sheets = read_csv_sheets(CSV_DIR)
    else:
        print(f"Reading from OpenDocument Spreadsheet: {args.input}...")
        sheets = read_ods_sheets(args.input)

    if not sheets:
        print("Error: No data sheets could be read.")
        sys.exit(1)

    print("Parsing review actions, field changes, and vocabularies...")
    forms_dict, field_stats, modified_fields, deleted_fields, new_fields, vocab_stats, vocab_changes, logic_changes = parse_review(sheets)

    # 1. Write Markdown diff report
    report_md = generate_diff_report(forms_dict, field_stats, modified_fields, deleted_fields, new_fields, vocab_stats, vocab_changes, logic_changes)
    with open(OUTPUT_DIFF_MD, 'w', encoding='utf-8') as f:
        f.write(report_md)
    print(f"\nGenerated Audit Diff Report: {OUTPUT_DIFF_MD}")

    # 2. Write Revised Schema JSON
    revised_data = {
        "metadata": {
            "title": "Australian Heritage Survey & Artefact Recording Schema",
            "author": "Mick Morrison",
            "version": "2026-Reviewed-Draft",
            "source_review_file": os.path.basename(args.input)
        },
        "entities": forms_dict
    }
    with open(OUTPUT_REVISED_JSON, 'w', encoding='utf-8') as f:
        json.dump(revised_data, f, indent=2, ensure_ascii=False)
    print(f"Generated Machine-Readable Schema: {OUTPUT_REVISED_JSON}")

    print("\n" + "=" * 65)
    print("                     SCHEMA REVIEW SUMMARY")
    print("=" * 65)
    print(f"Forms / Entities: {len(forms_dict)}")
    print(f"Field Decisions:  {field_stats['RETAIN']} Retained | {field_stats['MODIFY']} Modified | {field_stats['DELETE']} Deleted | {field_stats['NEW_FIELD']} Added")
    print(f"Vocabularies:     {vocab_stats['RETAIN']} Retained | {vocab_stats['MODIFY']} Modified | {vocab_stats['DELETE']} Deleted | {vocab_stats['ADD_TERM']} Added")
    print("=" * 65 + "\n")

if __name__ == '__main__':
    main()
