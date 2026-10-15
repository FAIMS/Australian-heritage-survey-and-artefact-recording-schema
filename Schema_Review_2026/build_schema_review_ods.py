#!/usr/bin/env python3
"""
build_schema_review_ods.py

Generates a comprehensive OpenDocument Spreadsheet (.ods) and matching CSV files
for reviewing the Australian Heritage Survey and Artefact Recording schema (v2026).

Sheets generated:
1. Instructions_and_Legend: Guide for the reviewer, action codes, and data types
2. Forms_Overview: Review of all 18 primary and child forms / entities
3. Fields_Review: Comprehensive audit of all 668 fields across all forms and tabs
4. Value_Lists_Vocabularies: Full catalog of all 111 controlled vocabularies and 1,060 terms
5. Logic_and_Workflows: Business rules, autonumbering, GPS validation, and relationships

Zero third-party package dependencies (uses Python standard library only).
"""

import os
import csv
import json
import zipfile
import xml.sax.saxutils

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
SCHEMA_DIR = os.path.join(BASE_DIR, 'GeopackageV1', 'schema')
CSV_DIR = os.path.join(SCRIPT_DIR, 'csv')
ODS_OUTPUT_PATH = os.path.join(SCRIPT_DIR, 'Australian_Heritage_Schema_Review_2026.ods')

def escape_xml(text):
    if text is None:
        return ""
    return xml.sax.saxutils.escape(str(text))

def load_data():
    schema_path = os.path.join(SCHEMA_DIR, 'faims_extracted_schema.json')
    vocab_path = os.path.join(SCHEMA_DIR, 'vocabularies.json')

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocabularies = json.load(f)

    # Build reverse mapping: which vocab is used by which entity.field
    vocab_usage = {}
    for ent_name, ent_info in schema['entities'].items():
        for tab_name, fields in ent_info['tabs'].items():
            for fld in fields:
                v_ref = fld.get('vocab_ref')
                if v_ref:
                    if v_ref not in vocab_usage:
                        vocab_usage[v_ref] = []
                    vocab_usage[v_ref].append(f"{ent_info['label']} ({tab_name}.{fld['name']})")

    return schema, vocabularies, vocab_usage

def build_instructions_data():
    rows = [
        ["AUSTRALIAN HERITAGE SURVEY & ARTEFACT RECORDING — SCHEMA REVIEW (2026)", "", "", ""],
        ["Review Workbook for Contemporary Archaeological Recording & Next-Gen Implementation", "", "", ""],
        ["Author: Mick Morrison (Flinders University Archaeology) | Schema Version: 2026 Review Draft", "", "", ""],
        ["", "", "", ""],
        ["1. PURPOSE OF THIS REVIEW WORKBOOK", "", "", ""],
        ["The digital recording schema was originally created in 2018 under FAIMS 2. Fieldwork practices, archaeological concepts, tablet technologies, and data standards have significantly evolved.", "", "", ""],
        ["The goal of this workbook is to enable you to systematically review every form, field, vocabulary term, and logic rule, and indicate what should be RETAINED, MODIFIED, or DELETED.", "", "", ""],
        ["Once completed, this spreadsheet will be parsed by the automated assistant to build the updated schema in GeoPackage and/or Fieldmark.", "", "", ""],
        ["", "", "", ""],
        ["2. WORKBOOK STRUCTURE", "", "", ""],
        ["Sheet Name", "Description", "Number of Items", "Your Task"],
        ["01_Instructions_and_Legend", "This guide and reference glossary", "Reference", "Read workflow instructions and code definitions"],
        ["02_Forms_Overview", "All 18 survey modules and primary/child feature types", "18 Forms + 2 Boundary layers", "Review form titles, ID prefixes, geometry types, and retain/modify status"],
        ["03_Fields_Review", "Detailed field-by-field audit across every form and tab", "668 Fields", "Mark ACTION (Retain, Modify, Delete, Add), new labels, widget types, and notes"],
        ["04_Value_Lists_Vocabularies", "All 111 controlled vocabularies and their option terms", "1,060 Terms", "Review terms, add new contemporary terms, refine definitions, or prune obsolete codes"],
        ["05_Logic_and_Workflows", "Underlying business logic, autonumbering, GPS rules, relations", "8 Core Logic Components", "Decide how field behaviors (IDs, GPS constraints, child records) should function in 2026"],
        ["", "", "", ""],
        ["3. HOW TO COMPLETE YOUR REVIEW", "", "", ""],
        ["Action Code", "Meaning", "When to Use", "How to Fill in the Review Columns"],
        ["RETAIN", "Keep as-is (Default)", "Field/form is still relevant and accurately defined.", "Leave pre-filled RETAIN. No extra typing needed."],
        ["MODIFY", "Change or Update", "Field needs a new label, different type, new vocabulary, or clearer help text.", "Set ACTION to MODIFY. Fill in NEW_FIELD_LABEL, NEW_FIELD_TYPE, or notes."],
        ["DELETE", "Remove from Schema", "Field/form is obsolete, unhelpful in the field, or redundant with modern GIS.", "Set ACTION to DELETE. Explain brief rationale in ARCHAEOLOGICAL_NOTES."],
        ["NEW_FIELD", "Add New Field", "A new field is needed in 2026 practice (e.g. cultural authority, drone photo ID).", "Add a row (or write in notes) with ACTION=NEW_FIELD and desired prompt/type."],
        ["ADD_TERM", "Add Vocab Option", "A controlled vocabulary is missing key terms for your current region.", "On the Vocabularies sheet, add a row with ACTION=ADD_TERM."],
        ["", "", "", ""],
        ["4. RECOMMENDED WIDGET TYPES FOR 2026", "", "", ""],
        ["Widget Type", "Usage", "Examples"],
        ["text", "Short single-line text (names, site IDs, brief labels)", "Site name, Landholder name, Tag ID"],
        ["multiline_text", "Free-text narrative notes, descriptions, observations", "Additional notes, Excavation summary, Context description"],
        ["integer", "Whole counts or positive integers", "Artefact count, Hearth count, Scar count, Axe mark count"],
        ["decimal", "Accurate numeric measurements with decimals (mm, m, g, kg)", "Maximum length (mm), Weight (g), Mound height (m), Girth (mm)"],
        ["dropdown", "Single-choice selection from controlled vocabulary", "Mound matrix, Flake completeness, Raw material, Landform element"],
        ["multiselect", "Multiple-choice checkboxes from controlled vocabulary", "Stone raw materials present, Faunal elements observed, Surface vegetation"],
        ["photo", "Camera capture or photo attachment with caption", "Overview site photo, Detail macro photo, Scar face closeup"],
        ["audio", "In-field audio voice note recorded directly on tablet", "Field recorder voice memos, Oral histories, Audio descriptions"],
        ["file", "PDF document, historical map, or field sketch attachment", "PDF site plan, Section drawing scan, Aerial photo overlay"],
        ["date", "Date or timestamp picker", "Survey date, Feature discovery timestamp"]
    ]
    return rows

def build_forms_overview_data(schema):
    headers = [
        "Module_Source",
        "Entity_Code",
        "Form_Label",
        "Entity_Level",
        "Parent_Entity",
        "Current_ID_Prefix",
        "Current_ID_Format",
        "Spatial_Geometry",
        "Total_Tabs",
        "Total_Fields",
        "Current_Logic_Summary",
        "ACTION",
        "REVISED_FORM_LABEL",
        "REVISED_ID_PREFIX",
        "GEOMETRY_CHOICE",
        "ARCHAEOLOGICAL_NOTES_AND_RATIONALE"
    ]

    rows = [headers]

    for ent_key, ent_info in schema['entities'].items():
        tabs = ent_info['tabs']
        total_fields = sum(len(flds) for flds in tabs.values())
        is_child = ent_info.get('is_child', False)
        level = "Child Entity" if is_child else "Primary Feature"
        parent = ent_info.get('parent_entity') or "None"
        
        geom = "Point"
        if ent_key in ('Mound', 'Surface_Exposure', 'Rock_Shelter', 'Historical_Feature'):
            geom = "Point + Polygon"

        logic_summary = "Autonumbered ID; GPS validation; Media attachments"
        if is_child:
            logic_summary = f"Linked to parent {parent}; Inherits coordinates"
        elif "Polygon" in geom:
            logic_summary += "; Linked child boundary polygons & lines"

        row = [
            ent_info.get('module', ''),
            ent_key,
            ent_info.get('label', ent_key),
            level,
            parent,
            ent_info.get('id_prefix', ''),
            ent_info.get('id_format', ''),
            geom,
            len(tabs),
            total_fields,
            logic_summary,
            "RETAIN",
            "",
            "",
            geom,
            ""
        ]
        rows.append(row)

    # Add the native boundary and line extents layers
    rows.append([
        "GeopackageV1 / Spatial Extents",
        "feature_boundaries",
        "Feature Boundary Polygons",
        "Child Spatial Layer",
        "Mound / Surface Exposure / Rock Shelter",
        "POLY",
        "N/A (Native Polygon)",
        "Polygon",
        1,
        8,
        "Native polygon boundary tracing; auto area (m²) and perimeter (m)",
        "RETAIN",
        "",
        "",
        "Polygon",
        "Replaces legacy point-by-point boundary coordinates with native QGIS digitizing"
    ])

    rows.append([
        "GeopackageV1 / Spatial Extents",
        "feature_lines",
        "Feature Line Extents",
        "Child Spatial Layer",
        "Any Feature",
        "LINE",
        "N/A (Native LineString)",
        "LineString",
        1,
        7,
        "Native linear feature digitizing; auto length (m) for transects, fences, walls",
        "RETAIN",
        "",
        "",
        "LineString",
        "Enables linear feature tracing in QGIS / QField"
    ])

    return rows

def build_fields_review_data(schema, vocabularies):
    headers = [
        "Form_Entity",
        "Tab_Section",
        "Field_Order",
        "Field_Name",
        "Field_Label",
        "Field_Type",
        "Current_Flags",
        "Value_List_Name",
        "Value_List_Options_Preview",
        "Form_Logic_Behavior",
        "Field_Description_Help",
        "ACTION",
        "REVISED_FIELD_LABEL",
        "REVISED_FIELD_TYPE",
        "REVISED_VALUE_LIST",
        "REQUIRED",
        "ARCHAEOLOGICAL_NOTES_AND_CHANGES"
    ]

    rows = [headers]

    for ent_key, ent_info in schema['entities'].items():
        ent_label = ent_info.get('label', ent_key)
        for tab_name, fields in ent_info['tabs'].items():
            for idx, f in enumerate(fields):
                fname = f.get('name', '')
                flabel = f.get('label', fname)
                ftype = f.get('type', 'text')
                flags = ", ".join(f.get('flags', []))
                desc = f.get('desc', '')
                v_ref = f.get('vocab_ref')

                # Vocab preview
                v_name = v_ref or "None"
                v_preview = "N/A"
                if v_ref and v_ref in vocabularies:
                    opts = vocabularies[v_ref].get('options', [])
                    sample_opts = [o['value'] for o in opts[:5]]
                    v_preview = " | ".join(sample_opts)
                    if len(opts) > 5:
                        v_preview += f" ... (+{len(opts)-5} more, total {len(opts)})"
                    else:
                        v_preview += f" (total {len(opts)})"
                elif f.get('options'):
                    opts = [o.get('value', '') for o in f['options']]
                    v_preview = " | ".join(opts[:5]) + f" (inline {len(opts)})"

                # Logic behavior explanation
                logic_behav = ""
                fname_lower = fname.lower()
                if "autonum" in flags or "id" in fname_lower:
                    logic_behav = f"Auto-sequences {ent_info['id_prefix']} identifier"
                elif "gps" in fname_lower:
                    logic_behav = "Captures GPS point coordinates & accuracy (m)"
                elif ftype in ('camera', 'photo') or 'photo' in fname_lower:
                    logic_behav = "Opens camera / photo picker; saves to media folder"
                elif ftype == 'button':
                    logic_behav = "UI navigation or action trigger button"
                elif "dropdown" in ftype or v_ref:
                    logic_behav = f"Restricted combobox from controlled vocab '{v_name}'"
                elif ftype in ('decimal', 'integer') or 'm' in fname_lower or 'mm' in fname_lower or 'g' in fname_lower:
                    logic_behav = "Numeric measurement input with validation"
                else:
                    logic_behav = "Standard user text input"

                required_val = "Yes" if "notnull" in f.get('flags', []) else "No"

                row = [
                    ent_label,
                    tab_name,
                    idx + 1,
                    fname,
                    flabel,
                    ftype,
                    flags,
                    v_name,
                    v_preview,
                    logic_behav,
                    desc,
                    "RETAIN",
                    "",
                    "",
                    "",
                    required_val,
                    ""
                ]
                rows.append(row)

    return rows

def build_vocabularies_data(vocabularies, vocab_usage):
    headers = [
        "Vocab_Name",
        "Vocab_Title",
        "Used_By_Forms_and_Fields",
        "Term_Label",
        "Term_Code",
        "Parent_Term",
        "Term_Definition_Description",
        "ACTION",
        "REVISED_TERM_LABEL",
        "REVISED_DEFINITION",
        "NOTES"
    ]

    rows = [headers]

    for vname, vdata in vocabularies.items():
        vtitle = vdata.get('title', vname.replace('_', ' ').title())
        used_by = "; ".join(vocab_usage.get(vname, ["Unused / Standalone"]))
        
        for opt in vdata.get('options', []):
            t_label = opt.get('value', '')
            t_code = t_label.lower().replace(' ', '_').replace('/', '_').replace('-', '_').strip('_')
            t_parent = opt.get('parent') or "None"
            t_desc = opt.get('desc', '')

            row = [
                vname,
                vtitle,
                used_by,
                t_label,
                t_code,
                t_parent,
                t_desc,
                "RETAIN",
                "",
                "",
                ""
            ]
            rows.append(row)

    return rows

def build_logic_and_workflows_data():
    headers = [
        "Logic_Rule_ID",
        "Rule_Name",
        "Rule_Category",
        "Original_2018_FAIMS_Behavior",
        "Target_2026_GeoPackage_Approach",
        "Target_2026_Fieldmark_Approach",
        "Applies_To_Forms",
        "ACTION",
        "REVISED_LOGIC_REQUIREMENTS",
        "ARCHAEOLOGICAL_RATIONALE_AND_NOTES"
    ]

    rules = [
        (
            "LOGIC-01",
            "Automatic ID Sequencing",
            "Identification",
            "Custom BeanShell script in autonumbering-validation.bsh read internal SQLite table, maintained per-device counter, formatted string as MD{{Mound_ID}}.",
            "QGIS Default Value expression or SQLite triggers auto-generate sequential identifier with operator prefix (e.g. MD-MM-001).",
            "Fieldmark built-in autonum schema rule increments sequence and locks field upon creation.",
            "All 18 Primary and Child Forms",
            "RETAIN",
            "",
            "Essential for unique site, tree, and artefact referencing across survey teams."
        ),
        (
            "LOGIC-02",
            "Mandatory GPS Location Check",
            "Spatial Validation",
            "leave-gps-verification.bsh validated coordinates before user was permitted to advance past Location tab, requiring accuracy <= 15m.",
            "Geometry column enforced as NOT NULL. QGIS/QField snaps feature to GPS crosshair and records accuracy in gps_accuracy attribute.",
            "Mandatory GPS Location field with configurable accuracy threshold in Fieldmark form.",
            "All Primary Feature Forms (Mounds, Shelters, Trees, Burials, Artefacts)",
            "RETAIN",
            "",
            "Prevents orphaned features recorded without spatial coordinates."
        ),
        (
            "LOGIC-03",
            "Boundary Extents & Polygon Digitizing",
            "Spatial Geometry",
            "gis-shared.bsh required fieldworkers to record discrete Boundary Points (MD001-BP1, BP2...) which were algorithmically joined into a polygon.",
            "Native Polygon (feature_boundaries) and Line (feature_lines) layers digitized directly on Topcon FC-6000 screen or iPad retina display. Area (m²) and perimeter (m) calculated automatically.",
            "Native Polygon geometry attribute with automatic area calculation in Fieldmark.",
            "Mounds, Surface Exposures, Rock Shelters, Historical Features",
            "MODIFY",
            "Replaced 2018 boundary points with native vector digitizing; retain 1:N link to parent feature.",
            "Eliminates clumsy point-by-point perimeter entry. QGIS digitizing tools allow accurate perimeter tracing."
        ),
        (
            "LOGIC-04",
            "1:N Tree to Cultural Scars Relation",
            "Parent-Child Hierarchy",
            "Historic-trees module allowed one Tree record to generate multiple child Scar records (TR001-SC1, TR001-SC2) with custom morphometrics.",
            "QGIS 1:N Composition Relation between tree (record_id) and tree_scars (parent_tree_id). Child tab displays embedded scar table.",
            "Fieldmark parent-child subrecord collection for Scar entities inside Tree form.",
            "Historic / Scarred Trees",
            "RETAIN",
            "",
            "Culturally scarred trees frequently exhibit multiple scar events on different trunk faces."
        ),
        (
            "LOGIC-05",
            "1:N Feature to Boundaries & Lines Relation",
            "Parent-Child Hierarchy",
            "Parent mounds and exposures linked to child boundary points.",
            "QGIS 1:N Relation between feature (record_id) and feature_boundaries / feature_lines (parent_feature_id).",
            "Fieldmark subrecord or related spatial collection.",
            "Mound, Surface Exposure, Rock Shelter, Historical Feature",
            "RETAIN",
            "",
            "Enables complex multi-part boundaries or separate core vs periphery extents for a single site."
        ),
        (
            "LOGIC-06",
            "Cascade Deletion of Child Entities",
            "Data Integrity",
            "cascade-delete.bsh manually traversed database and purged child boundary coordinates, scars, and file records when a parent record was deleted.",
            "SQLite FOREIGN KEY (parent_feature_id) REFERENCES parent(record_id) ON DELETE CASCADE, plus QGIS Composition Relation.",
            "Fieldmark automatic cascade delete on child collections.",
            "All Parent Forms with linked Scars, Boundaries, or Media",
            "RETAIN",
            "",
            "Prevents orphaned boundary polygons, scars, or media files remaining when a site is deleted."
        ),
        (
            "LOGIC-07",
            "In-Field Record Search & Map Zoom",
            "Field Navigation",
            "custom-search.bsh and find-in-map.bsh executed SQL text searches and commanded GIS map view to re-center on coordinates.",
            "Native QGIS Attribute Table filter, QGIS locator bar, and QField spatial search tool.",
            "Fieldmark native record search, sorting, and map clustering.",
            "All Forms",
            "RETAIN",
            "",
            "Surveyors need to quickly locate existing recorded sites on their map while walking transects."
        ),
        (
            "LOGIC-08",
            "Unified Media Attachment Pipeline",
            "Multimedia Management",
            "Android camera intent saved photos to internal directory; separate external camera ID field required manual cross-referencing.",
            "Unified media_attachments table supporting Photos, Audio Voice Notes, PDF site plans, and field sketches, with QGIS form attachment widgets.",
            "Fieldmark Photo, Audio Memo, and File attachment fields with native camera/mic integration.",
            "All Forms",
            "MODIFY",
            "Upgrade to multi-format media (Photos + Audio voice notes + PDF plans) linked by record_id.",
            "Modern field recording relies heavily on audio voice notes and digital PDF plans in addition to photos."
        )
    ]

    rows = [headers]
    for r in rules:
        rows.append(list(r))
    return rows

def generate_csv_files(sheets_data):
    os.makedirs(CSV_DIR, exist_ok=True)
    for filename, rows in sheets_data.items():
        csv_path = os.path.join(CSV_DIR, f"{filename}.csv")
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"Generated CSV: {csv_path} ({len(rows):,} rows)")

def build_ods_xml(sheets_data):
    """
    Constructs the OpenDocument Spreadsheet XML with styles, headers, and formatted tables.
    """
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<office:document-content ',
        '  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" ',
        '  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" ',
        '  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" ',
        '  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" ',
        '  xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" ',
        '  office:version="1.2">',
        '  <office:automatic-styles>',
        '    <!-- Table Header Style: Dark Navy background, bold white text -->',
        '    <style:style style:name="Header_Navy" style:family="table-cell">',
        '      <style:table-cell-properties fo:background-color="#1F4E78" fo:padding="5pt" fo:border="0.5pt solid #000000"/>',
        '      <style:text-properties fo:color="#FFFFFF" fo:font-weight="bold" fo:font-size="10pt"/>',
        '    </style:style>',
        '    <!-- Review Action Header Style: Rich Gold background, bold white text -->',
        '    <style:style style:name="Header_Gold" style:family="table-cell">',
        '      <style:table-cell-properties fo:background-color="#C65911" fo:padding="5pt" fo:border="0.5pt solid #000000"/>',
        '      <style:text-properties fo:color="#FFFFFF" fo:font-weight="bold" fo:font-size="10pt"/>',
        '    </style:style>',
        '    <!-- Title Banner Style -->',
        '    <style:style style:name="Title_Banner" style:family="table-cell">',
        '      <style:table-cell-properties fo:background-color="#D9E1F2" fo:padding="6pt" fo:border="0.5pt solid #8EA9DB"/>',
        '      <style:text-properties fo:color="#1F4E78" fo:font-weight="bold" fo:font-size="12pt"/>',
        '    </style:style>',
        '    <!-- Section Subheading Style -->',
        '    <style:style style:name="Section_Sub" style:family="table-cell">',
        '      <style:table-cell-properties fo:background-color="#F2F2F2" fo:padding="5pt" fo:border="0.5pt solid #BFBFBF"/>',
        '      <style:text-properties fo:color="#333333" fo:font-weight="bold" fo:font-size="10pt"/>',
        '    </style:style>',
        '    <!-- Standard Data Cell -->',
        '    <style:style style:name="Data_Cell" style:family="table-cell">',
        '      <style:table-cell-properties fo:padding="4pt" fo:border="0.5pt solid #D9D9D9"/>',
        '      <style:text-properties fo:font-size="9pt" fo:color="#262626"/>',
        '    </style:style>',
        '    <!-- Entity / Group Bold Cell -->',
        '    <style:style style:name="Entity_Cell" style:family="table-cell">',
        '      <style:table-cell-properties fo:padding="4pt" fo:border="0.5pt solid #D9D9D9" fo:background-color="#F9FBFD"/>',
        '      <style:text-properties fo:font-size="9pt" fo:font-weight="bold" fo:color="#1F4E78"/>',
        '    </style:style>',
        '    <!-- Action Choice Cell (Warm Yellow Highlight) -->',
        '    <style:style style:name="Action_Cell" style:family="table-cell">',
        '      <style:table-cell-properties fo:background-color="#FFF2CC" fo:padding="4pt" fo:border="0.5pt solid #D6B656"/>',
        '      <style:text-properties fo:font-size="9pt" fo:font-weight="bold" fo:color="#7F6000"/>',
        '    </style:style>',
        '    <!-- Review Input Cell (Soft Yellow Tint for User Entry) -->',
        '    <style:style style:name="Input_Cell" style:family="table-cell">',
        '      <style:table-cell-properties fo:background-color="#FFFDF5" fo:padding="4pt" fo:border="0.5pt solid #EAD89C"/>',
        '      <style:text-properties fo:font-size="9pt" fo:color="#000000"/>',
        '    </style:style>',
        '  </office:automatic-styles>',
        '  <office:body>',
        '    <office:spreadsheet>'
    ]

    for sheet_name, rows in sheets_data.items():
        xml_parts.append(f'      <table:table table:name="{escape_xml(sheet_name)}">')

        is_instructions = ("Instructions" in sheet_name)

        for row_idx, row in enumerate(rows):
            xml_parts.append('        <table:table-row>')
            is_header_row = (row_idx == 0 and not is_instructions) or (is_instructions and row_idx in (10, 18, 26))
            is_title_row = is_instructions and row_idx in (0, 1, 2)
            is_section_row = is_instructions and row_idx in (4, 9, 16, 24)

            for col_idx, cell_value in enumerate(row):
                cell_str = str(cell_value) if cell_value is not None else ""
                escaped_val = escape_xml(cell_str)

                # Determine style
                if is_title_row:
                    style_name = "Title_Banner"
                elif is_section_row:
                    style_name = "Section_Sub"
                elif is_header_row:
                    # Check if this is a review column header
                    if "ACTION" in cell_str or "REVISED" in cell_str or "REQUIRED" in cell_str or "NOTES" in cell_str or "RATIONALE" in cell_str or "GEOMETRY_CHOICE" in cell_str:
                        style_name = "Header_Gold"
                    else:
                        style_name = "Header_Navy"
                else:
                    # Data row
                    if col_idx == 0:
                        style_name = "Entity_Cell"
                    elif cell_str in ("RETAIN", "MODIFY", "DELETE", "ADD_TERM", "NEW_FIELD"):
                        style_name = "Action_Cell"
                    elif col_idx >= 11 and not is_instructions:
                        # These are review columns
                        style_name = "Input_Cell"
                    else:
                        style_name = "Data_Cell"

                xml_parts.append(
                    f'          <table:table-cell table:style-name="{style_name}" office:value-type="string">'
                    f'<text:p>{escaped_val}</text:p></table:table-cell>'
                )

            xml_parts.append('        </table:table-row>')

        xml_parts.append('      </table:table>')

    xml_parts.append('    </office:spreadsheet>')
    xml_parts.append('  </office:body>')
    xml_parts.append('</office:document-content>')

    return "\n".join(xml_parts)

def build_ods_file(content_xml, output_path):
    manifest_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>'''

    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # mimetype MUST be uncompressed and the first entry
        zf.writestr('mimetype', 'application/vnd.oasis.opendocument.spreadsheet', compress_type=zipfile.ZIP_STORED)
        zf.writestr('META-INF/manifest.xml', manifest_xml)
        zf.writestr('content.xml', content_xml)

    print(f"\nSuccessfully built ODS Spreadsheet: {output_path} ({os.path.getsize(output_path):,} bytes)")

def main():
    print("Loading schema and controlled vocabularies...")
    schema, vocabularies, vocab_usage = load_data()

    print("Assembling review sheets...")
    instructions_rows = build_instructions_data()
    forms_rows = build_forms_overview_data(schema)
    fields_rows = build_fields_review_data(schema, vocabularies)
    vocab_rows = build_vocabularies_data(vocabularies, vocab_usage)
    logic_rows = build_logic_and_workflows_data()

    sheets = {
        "01_Instructions_and_Legend": instructions_rows,
        "02_Forms_Overview": forms_rows,
        "03_Fields_Review": fields_rows,
        "04_Value_Lists_Vocabularies": vocab_rows,
        "05_Logic_and_Workflows": logic_rows
    }

    print("\nWriting individual CSV files for quick inspection/git diffing...")
    generate_csv_files(sheets)

    print("\nGenerating OpenDocument Spreadsheet XML...")
    content_xml = build_ods_xml(sheets)

    build_ods_file(content_xml, ODS_OUTPUT_PATH)

    # Also place a copy directly in the workspace root for one-click access
    root_ods = os.path.join(BASE_DIR, 'Australian_Heritage_Schema_Review_2026.ods')
    import shutil
    shutil.copy2(ODS_OUTPUT_PATH, root_ods)
    print(f"Placed copy at workspace root: {root_ods}")

if __name__ == '__main__':
    main()
