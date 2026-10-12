# Offline Fieldwork Guide: Australian Heritage Recording

> **Field Manual for Disconnected Multi-Device Heritage Recording**  
> Designed for **Topcon FC-6000 Windows Tablets** running QGIS and **Apple iPads** running QField.  
> Tested for 100% disconnected environments with zero cellular (4G/5G) and zero internet connectivity.

---

## 1. Equipment & Software Stack

### Primary Devices
1. **Topcon FC-6000 Windows Rugged Tablet**:
   * **OS**: Windows 10 / 11 Pro 64-bit.
   * **Software**: QGIS Desktop 3.28 LTR or 3.34+ LTR.
   * **GNSS**: Internal multi-constellation u-blox receiver (GPS, GLONASS, Galileo, BeiDou, SBAS).
   * **Connectivity**: USB-A port for flash drives, MicroSD card slot.
2. **Apple iPad (Field Assistant / Student Units)**:
   * **OS**: iPadOS 16+.
   * **Software**: [QField for QGIS](https://qfield.org/) (installed via Apple App Store).
   * **GNSS**: Internal Apple GNSS (Wi-Fi+Cellular models) or external Bluetooth GNSS receiver (e.g., Bad Elf Surveyor, Garmin GLO 2, Trimble R1/DA2, Emlid Reach RX).
3. **Master Field Station (Camp Laptop)**:
   * Windows, macOS, or Linux laptop with Python 3 and QGIS installed.
   * Used for daily project staging, master consolidation (`merge_geopackages.py`), quality control, and hard-drive backups.

---

## 2. Pre-Survey Preparation (At Base Camp with Power / Wi-Fi)

Before heading into areas without mobile reception, prepare the survey project and offline basemaps.

### Step 1: Generate the Project for your MGA Zone

Before leaving base camp, you must generate the survey database (`heritage_survey.gpkg`) and QGIS project (`heritage_survey.qgs`) calibrated to the coordinate zone of your survey area.

---

#### 1.1 Understanding MGA Zones: Which Zone Do You Need?

Australia is mapped under **GDA2020** using the **Map Grid of Australia (MGA2020)**. The continent is divided into 6-degree longitudinal strips numbered **Zone 49 through Zone 56**. Using the correct zone ensures that distances (metres), artefact sizes, and polygon areas ($m^2$) are calculated with sub-centimetre metric precision.

Find your survey area in the table below:

| Zone | Primary Regions & Towns Covered | EPSG Code |
|:---:|---|:---:|
| **49** | WA West Coast, Perth outer west, Geraldton coast | `EPSG:7849` |
| **50** | Perth metropolitan, WA Southwest, Kalgoorlie, Pilbara West | `EPSG:7850` |
| **51** | WA East, Pilbara East (Newman), Kimberley West (Broome) | `EPSG:7851` |
| **52** | NT West (Victoria River, Tanami), Kimberley East (Kununurra) | `EPSG:7852` |
| **53** | SA Central, Adelaide metropolitan, Flinders Ranges, NT Central (Alice Springs, Darwin) | `EPSG:7853` |
| **54** | **Default**: Far West NSW (Broken Hill), Western QLD (Mount Isa, Channel Country), Western VIC (Mildura), SA East | `EPSG:7854` |
| **55** | Melbourne, Central VIC, ACT / Canberra, Sydney Western Plains, Central QLD (Rockhampton), TAS | `EPSG:7855` |
| **56** | Sydney East / Coast, Newcastle, Northern Rivers / Byron Bay, Brisbane, Gold Coast, Sunshine Coast, QLD Coast | `EPSG:7856` |
| **G** | **Geographic (All Australia)**: Unprojected Latitude/Longitude degrees (useful for continental-scale surveys) | `EPSG:7844` |

> [!TIP]
> **Not sure which zone?** If you are working in Western Queensland or Far West NSW, choose **Zone 54**. If you are on the Australian east coast (Sydney/Brisbane), choose **Zone 56**. If your survey spans multiple zones, choose **G** (Geographic).

---

#### 1.2 Method A: The Easiest Way (Double-Click Launcher — No Terminal Knowledge Required)

If you are unfamiliar with the terminal or command line, use the pre-built double-clickable launcher scripts included in the `GeopackageV1` folder:

##### On Windows:
1. Open File Explorer and navigate to the `GeopackageV1` folder.
2. Double-click the file named **`generate_project_windows.bat`**.
3. A black command window will open with an interactive menu:
   ```text
   =================================================================
   Select GDA2020 Coordinate Reference System for your survey area:
   =================================================================
     [49] GDA2020 / MGA zone 49 (EPSG:7849 - WA West / Perth)
     [50] GDA2020 / MGA zone 50 (EPSG:7850 - WA Southwest & Mid)
     ...
     [54] GDA2020 / MGA zone 54 (EPSG:7854 - QLD West / NSW Far West) [Default]
     [55] GDA2020 / MGA zone 55 (EPSG:7855 - Melbourne / Sydney West / ACT)
     [56] GDA2020 / MGA zone 56 (EPSG:7856 - Brisbane / Sydney East / QLD Coast)
     [G]  GDA2020 Geographic 2D (EPSG:7844 - All Australia, Lat/Long degrees)
   =================================================================
   Select MGA Zone (49-56 or G) [default: 54]:
   ```
4. Type your zone number (e.g. `54`) and press **Enter** (or simply press Enter to accept the default Zone 54).
5. The generator will build the files and display `Finished!`. Press any key to close the window.

##### On Mac:
1. Open Finder and navigate to the `GeopackageV1` folder.
2. Double-click the file named **`generate_project_mac.command`**.
3. A Terminal window will automatically open with the same interactive menu.
4. Type your zone number (e.g. `54`) and press **Return**.
5. Once complete, press any key to close the window.

---

#### 1.3 Method B: Step-by-Step for Windows Users (Using Command Prompt or PowerShell)

If you prefer to run it manually or need to run specific command flags:

##### Step B.1: Open Command Prompt
1. Press the Windows key + `R` on your keyboard to open the **Run** dialog.
2. Type `cmd` and press **Enter** (or search for **Command Prompt** in the Windows Start menu).

##### Step B.2: Navigate to the `GeopackageV1` Folder
In the black window, you need to tell the computer which folder you are working in using the `cd` (change directory) command:
1. Type `cd ` (type `cd` followed by a space — do not press Enter yet!).
2. Open Windows File Explorer and locate your `GeopackageV1` folder.
3. **Click and drag** the `GeopackageV1` folder from File Explorer directly into the Command Prompt window! Windows will automatically paste the full folder path (e.g. `cd "C:\Users\username\Documents\GeopackageV1"`).
4. Press **Enter**.
> [!NOTE]
> If your folder is on a secondary drive (e.g., `D:\` or a USB drive `E:\`), type `D:` or `E:` and press Enter after `cd` to switch to that drive.

##### Step B.3: Verify Python is Installed
1. In the Command Prompt, type:
   ```cmd
   python --version
   ```
   *(Or try `py --version`)*.
2. If you see something like `Python 3.10.x` (or any version 3.8+), you are ready to proceed!
3. **If you get an error** saying `'python' is not recognized`:
   * **If QGIS is installed on your computer**: Search your Windows Start menu for **OSGeo4W Shell** (this is installed with QGIS). Open it and run your commands there — it has Python completely pre-configured!
   * Otherwise, download Python from [python.org](https://www.python.org/downloads/) (make sure to check the box **"Add python.exe to PATH"** during installation).

##### Step B.4: Run the Generator
Now run the generation script:
* **Interactive mode** (prompts you for your zone):
  ```cmd
  python generate_geopackage.py
  ```
  *(Or `py generate_geopackage.py`)*
* **Direct mode** (specify your zone in one command, e.g. Zone 54):
  ```cmd
  python generate_geopackage.py --zone 54
  ```

---

#### 1.4 Method C: Step-by-Step for macOS Users (Using Terminal)

##### Step C.1: Open Terminal
1. Press `Cmd + Space` on your keyboard to open Spotlight Search.
2. Type `Terminal` and press **Return**.

##### Step C.2: Navigate to the `GeopackageV1` Folder
1. In the Terminal window, type `cd ` (type `cd` followed by a space — do not press Return yet!).
2. Open **Finder** and locate your `GeopackageV1` folder.
3. **Drag and drop** the `GeopackageV1` folder from Finder directly into your Terminal window! Terminal will fill in the complete path for you.
4. Press **Return**.

##### Step C.3: Run the Generator
1. In Terminal, run:
   * **Interactive mode**:
     ```bash
     python3 generate_geopackage.py
     ```
   * **Direct mode** (e.g. Zone 54):
     ```bash
     python3 generate_geopackage.py --zone 54
     ```
2. Press **Return**.

---

#### 1.5 What Success Looks Like (Expected Screen Output)

When the script runs, you will see output similar to this:

```text
Configuring GeoPackage with target CRS: GDA2020 / MGA zone 54 (EPSG:7854)
Replacing existing .../GeopackageV1/data/heritage_survey.gpkg...
Populating 111 controlled vocabulary lookup tables...
Inserting generic baseline survey records...
Created 17 feature point layers, 2 boundary layers, tree_scars, and media_attachments.
GeoPackage database created successfully!

Generating synchronized QGIS 3 project with native OGR connections & OSM basemap...
Configuring QGIS project with target CRS EPSG:7854...
Generated synchronized QGIS project: .../GeopackageV1/data/heritage_survey.qgs
Embedded QGIS project directly into heritage_survey.gpkg (qgis_projects table).

Finished! GeoPackage size: 1,339,392 bytes at .../GeopackageV1/data/heritage_survey.gpkg
```

---

#### 1.6 Verifying Your Output Files

After running the script, open your `GeopackageV1/data/` folder in File Explorer (Windows) or Finder (Mac). You should see:

1. **`heritage_survey.gpkg`** (~1.3 MB):
   The primary SQLite GeoPackage containing all 20 spatial layers, 111 controlled vocabularies, media tables, and embedded QGIS project metadata.
2. **`heritage_survey.qgs`** (~500 KB):
   The desktop/tablet QGIS project file with pre-configured symbology, layer groups, dropdown menus, and snapping rules.

> [!TIP]
> **Want to test opening it?** Double-click `heritage_survey.qgs` on your laptop. QGIS will launch immediately with all 20 layers color-coded and organized into clean collapsible groups, ready for field recording!

---

#### 1.7 Beginner Troubleshooting FAQ

* **Q: Windows says `python is not recognized as an internal or external command`.**
  * **Fix**: Try typing `py generate_geopackage.py`. If that also fails, open **OSGeo4W Shell** from your Windows Start Menu (included with QGIS), navigate to the folder with `cd`, and run `python generate_geopackage.py`.
* **Q: Mac says `zsh: command not found: python`.**
  * **Fix**: macOS uses `python3` instead of `python`. Ensure you type `python3 generate_geopackage.py`. If macOS prompts to install developer tools, click Install and let it finish.
* **Q: It says `FileNotFoundError: [Errno 2] No such file or directory: 'schema/faims_extracted_schema.json'`.**
  * **Fix**: Make sure you have navigated (`cd`) directly inside the `GeopackageV1` folder before running the command, so the script can find its `schema/` folder.
* **Q: I generated the project for Zone 54, but now my team is travelling to Zone 55. Do I have to start over?**
  * **Fix**: No! Simply run the generator again with `--zone 55` (or double-click the launcher and select `55`). The script will regenerate a clean project calibrated to Zone 55 in seconds.

---

### Step 2: Prepare Offline Basemap Packages (MBTiles)
Because web OpenTopoMap and OpenStreetMap require internet to stream live tiles, pre-cache an offline basemap for your specific survey area:

1. Open QGIS on your laptop while connected to Wi-Fi.
2. Pan and zoom to your survey area with the **OpenTopoMap** or **OpenStreetMap** layer visible.
3. Open the QGIS Processing Toolbox &rarr; search for **Generate XYZ tiles (MBTiles)**.
4. Set:
   * **Extent**: Select `Calculate from Layer` or draw a bounding box around your survey boundaries.
   * **Minimum Zoom**: `10` (regional context).
   * **Maximum Zoom**: `16` or `17` (detailed terrain and creek lines).
   * **Output file**: Save as `GeopackageV1/data/basemap_offline.mbtiles`.
5. Click **Run**.
6. In `heritage_survey.qgs`, drag `basemap_offline.mbtiles` into the **Basemaps** layer group. It will now display offline with zero internet!

*(Alternative: Download official state/national GeoTIFF topomaps from Geoscience Australia, QTopo, or NSW Spatial Services and place them in the project).*

### Step 3: Configure Device Prefixes to Prevent Record ID Collisions
When multiple devices record features simultaneously offline, prevent primary key and record ID conflicts by assigning each device a distinctive prefix:

| Device | Operator | ID Prefix Style | Example Feature ID |
|---|---|---|---|
| **Topcon Tablet A** | Mick Morrison | `MM` or `A` | `MD-MM-001`, `FLSA-MM-001` |
| **Topcon Tablet B** | Student 1 | `ST1` or `B` | `MD-B-001`, `FLSA-B-001` |
| **iPad C** | Student 2 | `ST2` or `C` | `MD-C-001`, `FLSA-C-001` |

---

## 3. Deployment to Field Devices

### Loading onto Topcon FC-6000 (Windows)
1. Copy the entire `GeopackageV1` folder onto a standard USB flash drive.
2. Plug the USB drive into the FC-6000's USB-A port.
3. Copy `GeopackageV1` to the tablet's local storage (e.g., `C:\FieldSurvey\GeopackageV1\`).
4. Double-click `C:\FieldSurvey\GeopackageV1\data\heritage_survey.qgs` to open directly in QGIS.

### Loading onto Apple iPad (QField)
* **Via USB Cable (Mac / Windows)**:
  1. Connect iPad to laptop with USB cable.
  2. On Mac (Finder) or Windows (iTunes / Apple Devices app), click on your iPad &rarr; **Files** &rarr; select **QField**.
  3. Drag the `GeopackageV1` folder into QField's documents.
* **Via USB-C Flash Drive (iPad Pro / iPad Air / iPad 10th gen)**:
  1. Plug USB-C drive into iPad.
  2. Open the iPad **Files** app &rarr; navigate to the USB drive &rarr; copy `GeopackageV1` to **On My iPad &rarr; QField**.
* **Opening in QField**:
  1. Open QField app on iPad.
  2. Tap **Open local project** &rarr; navigate to `GeopackageV1/data/` &rarr; select `heritage_survey.qgs`.

---

## 4. Field Recording Instructions

### Recording on Topcon FC-6000 (Windows QGIS)

#### 1. Connect Internal Topcon GNSS:
1. In QGIS, open **View &rarr; Panels &rarr; GPS Information Panel**.
2. Click the **Connect** button.
   * If not automatically recognized, open the GPS Panel settings (gear icon) and select **Serial Port** (typically `COM3` on Topcon FC-6000, baud `9600` or `115200`).
3. Once a satellite lock is acquired, the coordinates, elevation, and accuracy ($m$) will display in green.
4. Enable **Auto-center map on GPS location**.

#### 2. Recording Point Features (Mounds, Trees, Artefacts, Hearths):
1. Select the target layer in the Layers panel (e.g. `mound` or `flaked_stone_artefact`).
2. Toggle editing mode (pencil icon `Ctrl+E`).
3. Click the **Add Point Feature** tool.
4. To place the point exactly at your current GPS location, click the **Add Point at GPS Position** button on the GPS Toolbar (or press `Ctrl+.`).
5. The attribute form immediately appears:
   * **Record ID**: Enter your prefixed ID (e.g. `MD-MM-001`).
   * **Author**: Automatically defaults to `'Mick Morrison'` (or your configured name).
   * **Timestamp**: Automatically records current date and time.
   * **Dropdown fields**: Tap any field to reveal the controlled vocabulary choices.
6. Click **OK** and save layer edits.

#### 3. Digitizing Native Polygon Boundaries (`feature_boundaries`):
*(Legacy boundary points have been eliminated; you now digitize native polygons directly).*
1. Select the `feature_boundaries` layer in the **Boundaries & Linear Extents** group.
2. Toggle editing mode (`Ctrl+E`).
3. Select the **Add Polygon Feature** tool (`Ctrl+.`).
4. Walk the perimeter of the mound or surface exposure:
   * Tap points around the visible edge, or use the vertex tool.
   * Right-click to close the polygon.
5. In the pop-up form:
   * **parent_feature_type**: Choose `mound` (or relevant feature type).
   * **parent_feature_id**: Enter the parent feature ID (e.g. `MD-MM-001`).
   * **boundary_criterion**: Select from dropdown (e.g. *Mound margins*, *Artefact scatter extent*).
   * Area ($m^2$) and perimeter ($m$) are calculated automatically.
6. Save edits.

#### 4. Digitizing Linear Features (`feature_lines`):
1. Select `feature_lines` layer &rarr; toggle editing.
2. Select **Add Line Feature** &rarr; click vertices along fence lines, survey transects, or old trackways.
3. Link to parent feature ID and save.

---

### Recording on Apple iPad (QField)

1. Open `heritage_survey.qgs` in QField.
2. Tap the **Location** button (crosshair icon at bottom right) to center on your position.
3. Tap the **Layers** button (top left) and tap on the layer you wish to record (e.g., `flaked_stone_artefact`).
4. Tap the **Pencil** icon to enter digitizing mode.
5. Position the crosshair over your location (or tap the **GPS crosshair** button to snap directly to your GPS coordinates).
6. Tap the green **+** (Add Feature) button.
7. Fill in the form fields using the touch-friendly dropdown menus.
8. Tap the green checkmark to save the feature.

#### Digitizing Boundaries on iPad:
1. Select `feature_boundaries`.
2. Tap **Add Feature**.
3. Tap points around the boundary perimeter.
4. Enter parent feature ID (`MD-C-001`) and boundary criterion.
5. Tap checkmark to save.

---

## 5. End-of-Day Camp Consolidation Workflow

At the end of each survey day, consolidate data from all tablets and iPads onto the master field laptop.

```
       [Topcon Tablet A]                [iPad C]
       (survey_topcon_a.gpkg)      (survey_ipad_c.gpkg)
                 │                           │
                 │      USB Flash Drive      │
                 └─────────────┬─────────────┘
                               ▼
                    [Camp Field Laptop]
            GeopackageV1/data/incoming_sync/
                               │
                               ▼
           python3 GeopackageV1/merge_geopackages.py
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       [Safety Backup Created]    [Summary Audit Report]
       heritage_survey.backup     - MD: +3 inserted
                                  - FLSA: +18 inserted
                                  - Boundaries: +3 inserted
                                  - 0 conflicts
```

### Step-by-Step Merge Procedure

1. **Copy Files to Laptop**:
   * Insert USB drive into Topcon tablet &rarr; copy `heritage_survey.gpkg` &rarr; rename it `topcon_tablet_a.gpkg`.
   * Insert USB drive into iPad &rarr; copy `heritage_survey.gpkg` &rarr; rename it `ipad_survey_c.gpkg`.
   * Transfer both files to the field laptop into:
     ```
     GeopackageV1/data/incoming_sync/
     ```

2. **Execute Consolidation Script**:
   Open a terminal or command prompt on the laptop and run:
   ```bash
   cd GeopackageV1
   python3 merge_geopackages.py data/incoming_sync/*.gpkg
   ```

3. **What the Script Does Automatically**:
   * Creates an instant safety backup of the master GeoPackage (`heritage_survey.gpkg.backup_YYYYMMDD_HHMMSS`).
   * Iterates through all incoming device files.
   * Compares `record_id`:
     * If new: inserts feature into master table with a clean new database FID.
     * If existing: checks timestamp; updates only if the incoming record is newer.
     * Deduplicates baseline and unchanged records.
   * Consolidates all `media_attachments` records.
   * Updates spatial bounding boxes in `gpkg_contents`.
   * Prints a full audit report detailing newly inserted and updated features per layer.

4. **Prepare for the Next Day**:
   * Copy the newly consolidated `heritage_survey.gpkg` back onto each field tablet and iPad for the next morning.
   * All surveyors will now see all features recorded across the entire team on their maps!

---

## 6. Troubleshooting & Field FAQs

### Q: Why do web OpenTopoMap / OpenStreetMap tiles show blank / red X in the bush?
**A**: Because you are offline with no 4G service. This is expected. Turn off the online basemap layers in QGIS/QField and activate your pre-cached `basemap_offline.mbtiles` layer.

### Q: What if two surveyors accidentally used the same Record ID (e.g., both recorded `MD001`)?
**A**: `merge_geopackages.py` detects matching `record_id` entries. To prevent this, strictly follow the device prefix protocol (e.g. `MD-A-001` vs `MD-B-001`). If a duplicate does occur, the merge script preserves the master record and logs the collision in the merge audit report so you can inspect and rename it.

### Q: How do I export data for reporting or GIS spatial analysis?
**A**: In QGIS on your laptop:
* Right-click any layer (e.g. `mound` or `all_heritage_features`) &rarr; **Export &rarr; Save Features As...**
* Export to **ESRI Shapefile**, **GeoJSON**, **KML** (Google Earth), or **Spreadsheet (CSV/XLSX)**.
* Because your coordinates are in **GDA2020 / MGA**, all distances and areas are in true Australian ground metres.
