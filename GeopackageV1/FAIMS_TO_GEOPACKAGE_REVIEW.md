# Comprehensive Review: Legacy FAIMS 2 Schema to Open GeoPackage V1

**Project**: Australian Heritage Survey & Artefact Recording Schema  
**Original System**: FAIMS Mobile v2.6 (Android 7+)  
**Target Architecture**: Open OGC GeoPackage Standard (GeoPackage V1) + Interactive Form Interface  
**Author**: Mick Morrison (Flinders University) & Research Team  
**Review Date**: October 2026

---

## 1. Executive Summary

The repository contains the digital recording schema originally developed for the ARC Linkage Project *Indigenous foodways in colonial Cape York Peninsula* (LP170100050). The system comprised 7 landscape feature modules ("Phase 1") and 1 complex artefact recording module ("Phase 2").

While groundbreaking in 2019–2020 for offline digital recording on Android tablets, the FAIMS 2 architecture has reached end-of-life:
1. **Device Lock-in**: FAIMS 2 only runs on specific Android tablets and cannot run natively on laptops (macOS, Windows, Linux) or iOS devices.
2. **Maintenance Fragility**: The build pipeline relied on BeanShell scripts, Perl string replacement scripts (`postproc.sh`), Google Sheets token authentication, and a heavily normalized Entity-Attribute-Value (EAV) database model.
3. **Student Accessibility**: Setting up FAIMS 2 for teaching required specialized server synchronization, ADB debugging, and complex APK installations.

By refactoring this entire schema into **1 standard OGC GeoPackage (`heritage_survey.gpkg`)** accompanied by an interactive, zero-dependency form application in `GeopackageV1`, we achieve:
* **Complete Platform Independence**: Students and instructors can run the web form on any computer with `python3 run_app.py` or `./start.sh` with zero external package installations.
* **Direct GIS Interoperability**: The exact same `.gpkg` file can be opened directly in **QGIS** or **QField** on field tablets.
* **Enhanced Capability**: Native polygon perimeter generation from boundary points, live microphone voice recordings, and PDF document support.

---

## 2. In-Depth Review of Existing Codebase & Architecture

### 2.1 Schema Definition Format (`module.xml`)
The source files (`Phase_1_modules/*/module.xml` and `Phase_2_modules/Phase-2-Object-Recording/module.xml`) use the concise FAIMS 2 XML markup:
* **Tab and Group Structure**: `<General>`, `<Geometry>`, `<Landscape_context>`, `<Feature_details>`, `<Supplementary>`.
* **Field Type Flags**:
  * `f="autonum nocertainty"`: Automatic sequential ID without certainty rating.
  * `f="nocertainty noannotation"`: Suppresses field-level notes and confidence sliders.
  * `f="notnull"`: Required field (primarily used on GPS coordinates).
  * `t="camera"`: Photo capture widget.
  * `t="file"`: External document attachment.
  * `t="dropdown"`, `t="checkbox"`, `t="radio"`: Controlled vocabulary selectors.
  * `b="decimal"`, `b="integer"`: Numeric data type validation.
* **Child Entity Creation**:
  * `<Record_coordinate t="button" lc="Coordinate"/>` & `<List_of_related_coordinates t="dropdown" ec="Coordinate"/>`: 1:N relationship linking parent feature to child GPS coordinates.
  * `<New_scar t="button" lc="Scar"/>` & `<List_of_related_scars t="list" ec="Scar"/>`: 1:N relationship linking parent tree to child scarred areas.

### 2.2 Logic Scripts (`logic/*.bsh`)
FAIMS 2 used BeanShell (Java-like scripting language interpreted at runtime on Android) for dynamic behavior:
1. `gis-shared.bsh`: Configured offline raster basemap (`Basemap.3857.tif`), geometry symbology, and map click callbacks.
2. `cascade-delete.bsh`: Executed cascading SQL queries to remove child entities from the `parentchild` table when a parent entity was deleted.
3. `leave-gps-verification.bsh`: Intercepted tab changes and warned the user if latitude/longitude had not been captured.
4. `autonumbering-validation.bsh`: Verified that identifier counters were positive integers.
5. `custom-search.bsh` & `recent-records.bsh`: Managed device-level recent records and multi-attribute search queries.

### 2.3 Post-Processing Pipeline (`postproc.sh` & `migrate_vocab.py`)
* `postproc.sh`: Executed Perl regular expressions (`perl -0777 -i.original -pe "s/.../.../igs" ui_schema.xml`) to inject multi-column grid layouts into generated UI schemas.
* `migrate_vocab.py`: Connected to Google Sheets via the Google Sheets API (`spreadsheets.readonly`) to download vocabulary terms into `vocab/*.xml`.

---

## 3. Comparative Analysis: FAIMS 2 vs. GeoPackage V1

| Feature | Legacy FAIMS 2 (2019-2020) | New GeoPackage V1 (2026) | Rationale & Advantage |
| :--- | :--- | :--- | :--- |
| **Data Container** | Bespoke EAV SQLite database with FAIMS server sync | Single standard OGC GeoPackage (`.gpkg`) SQLite file | Open international standard (ISO/IEC 19566-2). Usable in QGIS, ArcGIS, Python, R, and web apps. |
| **Supported Devices** | Android tablets only (Android 7+) | Any device (macOS, Windows, Linux, Android, iOS) | Enables student use on personal laptops in labs and classrooms. |
| **Coordinate System** | WGS 84 (EPSG:4326) with manual easting/northing | WGS 84 (EPSG:4326) with automatic Australian MGA Zone 54 (EPSG:28354) calculations | Standardizes coordinate calculations and eliminates manual projection conversion errors. |
| **Boundary Recording** | Sequence of child point coordinates | Child point coordinates + **Generated Polygon Margins** | Allows immediate calculation of site area ($m^2$) and perimeter ($m$). |
| **Media Attachments** | Photos and camera images only | **Photos, Live Microphone Voice Notes, PDF Documents** | Voice notes allow rapid note-taking in the field; PDFs enable attaching sketches and archival maps. |
| **Controlled Vocabularies** | 111 XML files compiled into data schemas | 111 relational lookup tables in GPKG + interactive definition helpers | Provides instant dictionary definitions to students right in the form. |
| **Installation & Setup** | Server deployment + Android APK installation | **Zero external dependencies** (`python3 run_app.py`) | No virtual environments, no Docker, no compilation tools needed. |

---

## 4. Architectural Pathways & Decisions

### Pathway 1: Pure QGIS / QField Project (Without Custom App)
* **Description**: Create the GeoPackage and only provide a QGIS `.qgs` project file.
* **Pros**: Relies entirely on existing open-source GIS software.
* **Cons**: High learning curve for novice archaeology students who find QGIS desktop overwhelming; QGIS mobile setup requires cloud synchronization or file transfers.

### Pathway 2: Web-Only GIS Application (Non-Standard Database)
* **Description**: Build a standalone web application using PostgreSQL / PostGIS or a bespoke JSON store.
* **Pros**: Complete control over the user interface.
* **Cons**: Breaks the requirement for an openly accessible GeoPackage standard; cannot be opened directly in standard desktop GIS without export.

### Pathway 3: Hybrid Architecture (Selected & Implemented in `GeopackageV1`)
* **Description**:
  1. Build a **100% compliant OGC GeoPackage** (`heritage_survey.gpkg`) containing all 17 feature layers, child layers, vocabulary tables, and embedded QGIS project styles.
  2. Build a **lightweight, student-friendly interactive form interface** that directly reads and writes this GeoPackage file.
* **Why this is the best pathway**:
  * Students can use the web form interface for fast, guided recording with helpful tooltips and validation.
  * Advanced students and researchers can open the exact same `.gpkg` file in QGIS or QField for advanced geospatial analysis and map making.
  * Zero-dependency implementation guarantees it runs out of the box on any university or field laptop.

---

## 5. Summary of Built Features in `GeopackageV1`

1. **`parse_faims_schema.py`**:
   * Scans all 8 FAIMS modules and 111 vocabularies.
   * Compiles 23 entity definitions, 716 attributes, and glossary definitions into clean JSON.
2. **`generate_geopackage.py`**:
   * Generates `data/heritage_survey.gpkg` (OGC GeoPackage 1.2/1.3).
   * Creates 20 spatial feature layers (Points and Polygons) and 111 controlled vocabulary lookup tables.
   * Embeds baseline sample records from Cape York (Mound `MD001`, Tree `TR001`, Flaked Stone `FLSA001`).
   * Configures `layer_styles` with QML styling.
3. **`export_qgis_project.py`**:
   * Generates `data/heritage_survey.qgs` with 1:N relations and symbology.
   * Embeds the project into the GeoPackage's `qgis_projects` table.
4. **`app/db.py`**:
   * SQLite GeoPackage Data Access Layer with binary WKB Point and Polygon encoders/decoders.
   * Automatic MGA Zone 54 Easting and Northing calculations.
   * Cascade deletion and autonumbering logic.
5. **`app/server.py`**:
   * Zero-dependency Python HTTP server and REST API.
   * Full CRUD endpoints, media file upload, and GeoJSON export.
6. **`static/` Web Form & GIS Map Interface**:
   * Responsive single-page application with split-view form and map.
   * Dynamic field rendering based on active feature type.
   * Interactive boundary polygon drawer and *"Generate Polygon from Points"* tool.
   * Camera photo capture, Web Audio API microphone voice recorder, and PDF uploader.
   * Live search dialog and recent records drawer.

---

## 6. Recommendations & Open Questions for Mick Morrison

1. **Field Hardware & Tablets**:
   * For student laptop labs: The built-in web application (`python3 run_app.py`) is recommended because it runs locally without internet.
   * For mobile tablets in the field: Do you plan to use Android tablets or iPads? If tablets are used without laptops, **QField** opens `heritage_survey.gpkg` natively.
2. **Projected CRS in Other States**:
   * Currently, the system is calibrated to **MGA Zone 54** (Cape York / Northern Queensland). If you or your students conduct surveys elsewhere in Australia (e.g., South Australia in MGA Zone 53 or Victoria/NSW in MGA Zone 55/56), we can add a one-click dropdown to select the survey zone.
3. **Media Storage Mode**:
   * Media files are currently stored in `media/photos/`, `media/audio/`, and `media/documents/`, with file paths and metadata tracked in the database. An optional BLOB column is also available in `media_attachments` if you ever want fully embedded binary media inside the single `.gpkg` file.
4. **Additional Custom Features**:
   * Would you like automated PDF report generation (e.g., exporting a site recording summary sheet for each mound or scarred tree)? This can easily be integrated.
