# Australian Heritage Survey & Artefact Recording (GeoPackage V0.2)

> **Standardized Open OGC GeoPackage & QGIS/QField System for Australian Heritage Fieldwork**  
> Developed for robust, 100% disconnected offline field recording across Windows tablets (Topcon FC-6000) and iPads (QField).

---

## 1. Overview & Version 0.2 Highlights

This system provides a modern, standardized replacement for bespoke legacy recording tools (e.g. FAIMS 2). It packages an extensive Australian heritage schema (17 primary feature layers, child polygon boundaries, child linear features, tree scars, 111 controlled vocabularies, and media attachments) into a single, open **OGC GeoPackage (`heritage_survey.gpkg`)** accompanied by a synchronized **QGIS 3 project (`heritage_survey.qgs`)**.

### What's New in Version 0.2:
1. **GDA2020 National Standard**: Native support for **GDA2020** (EPSG:7844 Geographic 2D) and **MGA2020 Zones 49 to 56** (EPSG:7849–7856) with interactive or CLI zone selection.
2. **100% Disconnected Offline Recording**: Purpose-built for remote outback/bush locations with zero mobile reception (no 4G/5G, no internet). Designed for **Topcon FC-6000 Windows tablets** running QGIS and **Apple iPads** running QField.
3. **End-of-Day Multi-Device Consolidation (`merge_geopackages.py`)**: Automatic merging and deduplication of field data collected simultaneously across multiple tablets and iPads back at camp.
4. **Resolved QGIS Layer Missing Error**: Engineered with explicit `<provider encoding="UTF-8">ogr</provider>` definitions and relative project paths (`./heritage_survey.gpkg`) eliminating the previous `./heritage_survey.gpkg|layername=... missing` error.
5. **Integrated Basemaps**: Pre-configured with OpenTopoMap and OpenStreetMap XYZ tiles for connected prep work, alongside full support for offline `.mbtiles` packages in remote zones.
6. **Native Polygon & Line Digitizing**: Eliminated legacy point-by-point 'boundary coordinates' in favour of native QGIS polygon (`feature_boundaries`) and line (`feature_lines`) vector layers.
7. **Generic Australian Scope**: Fully generalized schema applicable across all Australian states and territories (author: Mick Morrison).

---

## 2. Quickstart: Generating the Survey Schema

### Option A: Double-Click Launcher (No Terminal Needed)
* **Windows**: Double-click `generate_project_windows.bat` in the `GeopackageV1` folder.
* **Mac**: Double-click `generate_project_mac.command` in the `GeopackageV1` folder.
A friendly menu will pop up asking for your zone number. Type `54` (or your zone) and press Enter.

### Option B: Terminal / Command-Line Launcher
Run the generator without flags to choose your working MGA zone interactively:
```bash
python3 GeopackageV1/generate_geopackage.py
```
```text
=================================================================
Select GDA2020 Coordinate Reference System for your survey area:
=================================================================
  [49] GDA2020 / MGA zone 49 (EPSG:7849 - WA West / Perth)
  [50] GDA2020 / MGA zone 50 (EPSG:7850 - WA Southwest & Mid)
  [51] GDA2020 / MGA zone 51 (EPSG:7851 - WA East / Pilbara)
  [52] GDA2020 / MGA zone 52 (EPSG:7852 - NT West / Kimberley)
  [53] GDA2020 / MGA zone 53 (EPSG:7853 - Adelaide / SA Central / NT)
  [54] GDA2020 / MGA zone 54 (EPSG:7854 - QLD West / NSW Far West / VIC West) [Default]
  [55] GDA2020 / MGA zone 55 (EPSG:7855 - Melbourne / Sydney West / ACT / QLD Central / TAS)
  [56] GDA2020 / MGA zone 56 (EPSG:7856 - Brisbane / Sydney East / Byron Bay / QLD Coast)
  [G]  GDA2020 Geographic 2D (EPSG:7844 - All Australia, Lat/Long degrees)
=================================================================
```

### Direct Command-Line Generation
Specify your zone directly using the `--zone` argument:
```bash
# Example: MGA Zone 54 (Far West NSW / QLD West)
python3 GeopackageV1/generate_geopackage.py --zone 54

# Example: MGA Zone 55 (VIC / Central NSW / TAS)
python3 GeopackageV1/generate_geopackage.py --zone 55

# Example: MGA Zone 56 (Eastern Seaboard / Brisbane / Sydney)
python3 GeopackageV1/generate_geopackage.py --zone 56

# Example: Geographic GDA2020 (Lat/Long degrees)
python3 GeopackageV1/generate_geopackage.py --zone geographic
```

Output files generated in `GeopackageV1/data/`:
* `heritage_survey.gpkg`: SQLite OGC GeoPackage containing all 20 spatial layers, 111 lookup tables, media attachments, and the embedded QGIS project.
* `heritage_survey.qgs`: QGIS 3 project configured with layer groups, symbology, 1:N relations, ValueMap dropdown widgets, and basemaps.

---

## 3. Supported Feature Layers & Structure

The schema organizes Australian heritage features into 4 functional groups:

| Group | Layers Included | Geometry | Key Attributes |
|---|---|---|---|
| **Boundaries & Linear Extents** | `feature_boundaries`<br>`feature_lines` | Polygon<br>LineString | Parent feature ID, boundary criterion, area ($m^2$), perimeter ($m$), length ($m$), notes |
| **Landscape Features** | `mound`<br>`surface_exposure`<br>`rock_shelter`<br>`discrete_hearth_artefact`<br>`burial`<br>`point_of_interest` | Point | Record ID, author, timestamp, coordinates, landform pattern/element, vegetation, matrix, dimensions, contents |
| **Trees & Cultural Scars** | `tree`<br>`tree_scars` (Child) | Point<br>Point | Species, condition, girth ($mm$), height, scar count. Scars: type, axe marks, orientation, dimensions ($mm$) |
| **Artefact Recordings** | `flaked_stone_artefact`<br>`other_stone_artefact`<br>`knapped_glass_artefact`<br>`glass_artefact`<br>`ceramic_artefact`<br>`buttons`<br>`metal_artefact`<br>`weapons_and_ammunition`<br>`historical_feature`<br>`misc_artefact` | Point | Raw material, flake completeness, platform surface, termination, cortex, weight ($g$), dimensions ($mm$), site association |
| **Media & Non-Spatial** | `media_attachments`<br>`survey_users`<br>`survey_metadata`<br>111 `vocab_*` tables | Attributes | Parent record ID, media type (photo, audio note, PDF, sketch), file path, caption, binary blob, timestamp |

---

## 4. Multi-Device Offline Fieldwork Workflow

For in-depth operating instructions, please see the complete [Offline Fieldwork Guide](file:///Users/mickmorrison/GitRepos/Australian-heritage-survey-and-artefact-recording-schema/GeopackageV1/OFFLINE_WORKFLOW_GUIDE.md).

```
   [Topcon FC-6000 Tablet A]            [iPad B (QField)]
   (Windows QGIS, offline GNSS)         (iOS QField, offline GNSS)
                │                                    │
                │ (Record features & boundaries)     │
                ▼                                    ▼
       survey_topcon_a.gpkg                 survey_ipad_b.gpkg
                │                                    │
                └───────────────┬────────────────────┘
                                │ End-of-Day USB Transfer
                                ▼
                       [Master Field Laptop]
                                │
                                ▼
             python3 merge_geopackages.py *.gpkg
                                │
                                ▼
                 [heritage_survey_MASTER.gpkg]
```

### Daily Routine
1. **Morning Prep**: Copy `heritage_survey.gpkg` and `heritage_survey.qgs` to each Topcon FC-6000 tablet (via USB) and iPad (via QField or iTunes/Finder).
2. **Field Recording**:
   * **Topcon FC-6000**: Open QGIS, activate GPS Information Panel, and record features and polygon boundaries with the built-in Topcon GNSS.
   * **iPad**: Open QField, use internal/external GPS, tap to record points and trace boundaries.
   * Dropdowns automatically populate from the 111 controlled vocabularies.
   * Mick Morrison is pre-filled as default surveyor; current timestamp is generated automatically.
3. **End-of-Day Consolidation**:
   * Copy the day's `.gpkg` files to the central laptop.
   * Run the multi-device consolidation script:
     ```bash
     python3 GeopackageV1/merge_geopackages.py incoming_tablets/*.gpkg
     ```
   * The tool automatically makes a safety backup, merges all records, deduplicates, and prints an audit report.

---

## 5. Repository Structure

```
GeopackageV1/
├── README.md                      # This user & quickstart guide
├── OFFLINE_WORKFLOW_GUIDE.md      # Field manual for Topcon FC-6000 & iPads
├── ARCHITECTURE.md                # System design & database specifications
├── FAIMS_TO_GEOPACKAGE_REVIEW.md  # Detailed transition review from FAIMS 2
├── generate_geopackage.py         # Main database generator (GDA2020 / MGA Zones 49-56)
├── export_qgis_project.py         # Synchronized QGIS .qgs project builder
├── merge_geopackages.py           # Offline multi-device synchronization & consolidation
├── parse_faims_schema.py          # Extractor utility for legacy FAIMS definitions
├── data/
│   ├── heritage_survey.gpkg       # Master OGC GeoPackage database
│   └── heritage_survey.qgs        # Synchronized QGIS 3 desktop/tablet project
├── schema/
│   ├── faims_extracted_schema.json# Normalized JSON schema (17 entities, 716 fields)
│   └── vocabularies.json          # 111 controlled vocabularies
└── media/                         # Field media repository
    ├── photos/                    # Site & artefact photographs
    ├── audio/                     # Voice notes & audio recordings
    └── documents/                 # PDF site plans & sketch diagrams
```

---

## 6. Authorship & Project Attribution
* **Original FAIMS 2 Modules**: Developed for the *Indigenous Foodways in Colonial Cape York Peninsula* ARC Linkage Project (LP170100050) by Mick Morrison, Shawn Ross, Brian Ballsun-Stanton, Ana Stevanovic, Christian Nassif-Haynes, and Petra Hermankova.
* **GeoPackage V0.2 Refactor**: Mick Morrison (Flinders University Archaeology). Designed for national Australian heritage survey standardisation (2026).
