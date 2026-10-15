# Australian Heritage Schema Review & Modernisation (v2026)

> **Schema Review Workbook & Automated Transition Pipeline**  
> Developed for Mick Morrison (Flinders University Archaeology).  
> Purpose: Audit, refine, and update the 2018 FAIMS recording schema for contemporary archaeological practice, and seamlessly instantiate the updated schema in GeoPackage and/or Fieldmark.

---

## 1. Quick Access to Review Files

| File | Format | Description |
|---|:---:|---|
| [**`Australian_Heritage_Schema_Review_2026.ods`**](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/Australian_Heritage_Schema_Review_2026.ods) | **ODF Spreadsheet** | **Primary Review File**. Multi-sheet OpenDocument Spreadsheet compatible with LibreOffice Calc, Excel, Google Sheets, and Numbers. (A copy is also located in `Schema_Review_2026/`). |
| [**`csv/02_Forms_Overview.csv`**](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/Schema_Review_2026/csv/02_Forms_Overview.csv) | CSV | Plain text audit of all 18 survey forms, ID prefixes, and geometry types. |
| [**`csv/03_Fields_Review.csv`**](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/Schema_Review_2026/csv/03_Fields_Review.csv) | CSV | Plain text audit of all 668 fields across all forms and tabs. |
| [**`csv/04_Value_Lists_Vocabularies.csv`**](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/Schema_Review_2026/csv/04_Value_Lists_Vocabularies.csv) | CSV | Plain text catalog of all 111 controlled vocabularies and 1,060 option terms. |
| [**`csv/05_Logic_and_Workflows.csv`**](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/Schema_Review_2026/csv/05_Logic_and_Workflows.csv) | CSV | Review of the 8 core business logic workflows (autonumbering, GPS checks, cascade deletes, relations). |

---

## 2. Spreadsheet Architecture & How to Review

The spreadsheet is designed with **soft-yellow review columns** (columns L through Q) where you can record your decisions without disrupting the existing schema definitions:

```
┌─────────────────────────────────┬──────────────────────────────────────────┐
│   Original 2018 Specification   │     Your 2026 Archaeological Review      │
│   (Navy Blue Headers)           │     (Gold Headers / Yellow Data Cells)   │
├─────────────────────────────────┼──────────────────────────────────────────┤
│ Form | Tab | Field Name | Label │ ACTION | REVISED_LABEL | TYPE | NOTES     │
│ Mound | Feature | mound_matrix  │ RETAIN │               │      │           │
│ Mound | Feature | shape         │ MODIFY │ Mound Profile │ drop │ New terms │
│ Tree  | General | camera_id     │ DELETE │               │      │ Obsolete  │
└─────────────────────────────────┴──────────────────────────────────────────┘
```

### Sheet 1: `01_Instructions_and_Legend`
Contains instructions, guidance, action codes, and recommended field widget types (`text`, `multiline_text`, `integer`, `decimal`, `dropdown`, `multiselect`, `photo`, `audio`, `file`, `date`).

### Sheet 2: `02_Forms_Overview` (18 Forms / Entities)
Review the high-level survey entities. You can decide whether to:
* **RETAIN**: Keep the form as a distinct recording entity (e.g. Mounds, Trees, Scars, Hearths, Flaked Stone Artefacts).
* **MODIFY**: Change the form title, ID prefix (e.g. `MD`, `FLSA`), or spatial geometry (`Point`, `Polygon`, `LineString`, `Both`).
* **DELETE** or **MERGE**: Remove obsolete forms or combine forms (e.g. merge `Buttons` or `Weapons` into `Historical_Feature` or `Misc_Artefact` if they are rarely recorded as standalone entities).

### Sheet 3: `03_Fields_Review` (The Core Detailed Form Review — 668 Fields)
Review every tab and field across all forms:
* **`ACTION`**:
  * `RETAIN`: Leave as default (pre-filled). Keep the field exactly as is.
  * `MODIFY`: Change the user prompt (`REVISED_FIELD_LABEL`), widget type (`REVISED_FIELD_TYPE`), or attached value list (`REVISED_VALUE_LIST`).
  * `DELETE`: Mark the field to be dropped from the modern schema.
  * `NEW_FIELD`: Insert a row to add a new contemporary recording field.
* **`REQUIRED`**: Change to `Yes` if the field should be mandatory before a record can be saved in the field.
* **`ARCHAEOLOGICAL_NOTES_AND_CHANGES`**: Explain your rationale or specific requirements for contemporary practice.

### Sheet 4: `04_Value_Lists_Vocabularies` (111 Vocabularies & 1,060 Terms)
Audit controlled vocabulary terms:
* Add missing contemporary terms (`ADD_TERM`).
* Refine terminology or glossary definitions (`MODIFY`).
* Prune obsolete or hyper-local terms (`DELETE`).

### Sheet 5: `05_Logic_and_Workflows` (8 Core Business Workflows)
Review how the software handles logic in the field:
1. **Auto-Numbering & Formatted Identifiers** (`LOGIC-01`)
2. **Mandatory GPS Check & Accuracy Threshold** (`LOGIC-02`)
3. **Native Boundary Polygon & Line Digitizing** (`LOGIC-03`)
4. **1:N Tree to Scars Parent-Child Relationship** (`LOGIC-04`)
5. **1:N Site to Boundary Polygons Relationship** (`LOGIC-05`)
6. **Foreign Key Cascade Deletion** (`LOGIC-06`)
7. **In-Field Record Search & Map Zooming** (`LOGIC-07`)
8. **Unified Media Attachment Pipeline (Photos, Voice Notes, PDFs)** (`LOGIC-08`)

---

## 3. Automated Ingestion & Instantiation Workflow

Once you have completed your review in the spreadsheet:

1. **Save your changes** to `Australian_Heritage_Schema_Review_2026.ods`.
2. **Run the automated parser** (or ask this assistant to run it):
   ```bash
   python3 Schema_Review_2026/parse_reviewed_sheet.py
   ```
3. **What happens automatically**:
   * Reads your `.ods` spreadsheet.
   * Generates [`schema_review_audit_diff.md`](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/Schema_Review_2026/schema_review_audit_diff.md) — a clean Markdown diff report showing every field kept, changed, or deleted.
   * Generates [`revised_schema_2026.json`](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/Schema_Review_2026/revised_schema_2026.json) — structured data for automated compiler scripts.
4. **Next-Step Instantiation**:
   * **For GeoPackage**: The bot can run an updated `generate_geopackage.py` targeting the revised schema, producing the new `.gpkg` and `.qgs` with your updated fields, forms, and dropdowns.
   * **For Fieldmark**: The bot can map `revised_schema_2026.json` into Fieldmark module definitions ready for deployment.
