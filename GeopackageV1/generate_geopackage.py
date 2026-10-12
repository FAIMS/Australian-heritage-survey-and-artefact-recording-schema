#!/usr/bin/env python3
"""
generate_geopackage.py

Builds a fully standards-compliant OGC GeoPackage (heritage_survey.gpkg)
for Australian Heritage Landscape Survey & Artefact Recording.

Key Specifications (v0.2):
- CRS: GDA2020 national standard (EPSG:7844 Geographic, and MGA2020 Zones 49-56, EPSG:7849-7856)
- Configurable MGA Zone selection (interactive or via --zone CLI argument)
- Generic Australian heritage survey terminology (no regional lock-in)
- Direct Polygon (feature_boundaries) and Line (feature_lines) layers for native QGIS digitizing
- 17 Feature point layers + Tree Scars child layer + Media attachments table
- 111 controlled vocabulary lookup tables
- Single surveyor configuration (Mick Morrison)
"""

import os
import sys
import json
import sqlite3
import struct
import math
import argparse
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.join(SCRIPT_DIR, 'schema')
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
GPKG_PATH = os.path.join(DATA_DIR, 'heritage_survey.gpkg')

# GDA2020 CRS Definitions
GDA2020_GEOGRAPHIC_EPSG = 7844
GDA2020_GEOGRAPHIC_WKT = (
    'GEOGCRS["GDA2020",DATUM["Geocentric Datum of Australia 2020",ELLIPSOID["GRS 1980",6378137,298.257222101,'
    'LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],'
    'CS[ellipsoidal,2],AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],'
    'AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],'
    'USAGE[SCOPE["Geodesy, cadastre, engineering survey, topographic mapping."],AREA["Australia."],'
    'BBOX[-60.55,93.41,-8.47,173.34]],ID["EPSG",7844]]'
)

def get_mga_wkt(zone):
    cm = zone * 6 - 183
    epsg = 7800 + zone
    return (
        f'PROJCRS["GDA2020 / MGA zone {zone}",BASEGEOGCRS["GDA2020",DATUM["Geocentric Datum of Australia 2020",'
        f'ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,'
        f'ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",7844]],CONVERSION["Map Grid of Australia zone {zone}",'
        f'METHOD["Transverse Mercator",ID["EPSG",9807]],PARAMETER["Latitude of natural origin",0,'
        f'ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",{cm},'
        f'ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.9996,'
        f'SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],'
        f'PARAMETER["False northing",10000000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],'
        f'AXIS["(E)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["(N)",north,ORDER[2],LENGTHUNIT["metre",1]],'
        f'USAGE[SCOPE["Engineering survey, topographic mapping."],AREA["Australia."],BBOX[-45,110,-10,155]],'
        f'ID["EPSG",{epsg}]]'
    )

def latlon_to_mga(lat, lon, zone):
    """Accurate GDA2020 / MGA Transverse Mercator conversion for any zone (49-56)"""
    a = 6378137.0
    f = 1 / 298.257222101
    b = a * (1 - f)
    e2 = (a**2 - b**2) / (a**2)
    e_prime2 = (a**2 - b**2) / (b**2)
    
    cm = zone * 6 - 183
    k0 = 0.9996
    false_e = 500000.0
    false_n = 10000000.0
    
    phi = math.radians(lat)
    lam = math.radians(lon)
    lam0 = math.radians(cm)
    
    delta_lam = lam - lam0
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)
    
    N = a / math.sqrt(1 - e2 * sin_phi**2)
    T = tan_phi**2
    C = e_prime2 * cos_phi**2
    A = cos_phi * delta_lam
    
    M = a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * phi
             - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*phi)
             + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*phi)
             - (35*e2**3/3072) * math.sin(6*phi))
             
    easting = false_e + k0 * N * (A + (1 - T + C) * A**3 / 6 + (5 - 18*T + T**2 + 72*C - 58*e_prime2) * A**5 / 120)
    northing = false_n + k0 * (M + N * tan_phi * (A**2 / 2 + (5 - T + 9*C + 4*C**2) * A**4 / 24 + (61 - 58*T + T**2 + 600*C - 330*e_prime2) * A**6 / 720))
    return round(easting, 2), round(northing, 2)

def create_gpkg_point_blob(x, y, srs_id):
    """OGC GeoPackage binary header + WKB Point"""
    header = struct.pack('<2sBB', b'GP', 0, 1) + struct.pack('<i', srs_id)
    wkb = struct.pack('<BIdd', 1, 1, float(x), float(y))
    return header + wkb

def create_gpkg_linestring_blob(coords, srs_id):
    """OGC GeoPackage binary header + WKB LineString"""
    header = struct.pack('<2sBB', b'GP', 0, 1) + struct.pack('<i', srs_id)
    wkb = bytearray(struct.pack('<BII', 1, 2, len(coords)))
    for x, y in coords:
        wkb.extend(struct.pack('<dd', float(x), float(y)))
    return bytes(header + wkb)

def create_gpkg_polygon_blob(coordinates_rings, srs_id):
    """OGC GeoPackage binary header + WKB Polygon"""
    header = struct.pack('<2sBB', b'GP', 0, 1) + struct.pack('<i', srs_id)
    wkb = bytearray(struct.pack('<BII', 1, 3, len(coordinates_rings)))
    for ring in coordinates_rings:
        if ring and (ring[0][0] != ring[-1][0] or ring[0][1] != ring[-1][1]):
            ring = list(ring) + [ring[0]]
        wkb.extend(struct.pack('<I', len(ring)))
        for x, y in ring:
            wkb.extend(struct.pack('<dd', float(x), float(y)))
    return bytes(header + wkb)

def clean_col_name(name):
    cleaned = name.strip()
    cleaned = cleaned.replace('--', '_').replace('-', '_').replace(' ', '_').replace('(', '').replace(')', '')
    cleaned = cleaned.replace('/', '_').replace('.', '').replace(',', '')
    while '__' in cleaned:
        cleaned = cleaned.replace('__', '_')
    return cleaned.lower().strip('_')

def map_field_to_sql_type(field):
    ftype = field.get('type', '')
    btype = field.get('base_type', '')
    name = field.get('name', '').lower()

    if 'autonum' in field.get('flags', []) or ftype == 'autonum':
        return 'INTEGER'
    if btype == 'integer' or 'number' in name or 'count' in name:
        return 'INTEGER'
    if btype == 'decimal' or 'weight' in name or 'length' in name or 'width' in name or 'degrees' in name or 'height' in name or 'girth' in name or 'thickness' in name:
        return 'REAL'
    return 'TEXT'

def init_gpkg_metadata_tables(conn, target_crs_id):
    cur = conn.cursor()
    cur.execute('PRAGMA application_id = 1196444487;')  # 'GPKG'
    cur.execute('PRAGMA user_version = 10200;')         # GPKG 1.2

    # 1. gpkg_spatial_ref_sys
    cur.execute('''
    CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
        srs_name TEXT NOT NULL,
        srs_id INTEGER NOT NULL PRIMARY KEY,
        organization TEXT NOT NULL,
        organization_coordsys_id INTEGER NOT NULL,
        definition TEXT NOT NULL,
        description TEXT
    );
    ''')

    # Register Undefined and GDA2020 Geographic
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_spatial_ref_sys VALUES 
    ('Undefined Cartesian', -1, 'NONE', -1, 'undefined', 'undefined cartesian coordinate reference system'),
    ('Undefined Geographic', 0, 'NONE', 0, 'undefined', 'undefined geographic coordinate reference system'),
    ('GDA2020', 7844, 'EPSG', 7844, ?, 'Geocentric Datum of Australia 2020 (Geographic 2D, degrees)'),
    ('WGS 84', 4326, 'EPSG', 4326, 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]', 'WGS 84 Geographic 2D (Lat/Lon)');
    ''', (GDA2020_GEOGRAPHIC_WKT,))

    # Register MGA2020 Zones 49 through 56
    for z in range(49, 57):
        epsg = 7800 + z
        wkt = get_mga_wkt(z)
        cur.execute('''
        INSERT OR REPLACE INTO gpkg_spatial_ref_sys VALUES 
        (?, ?, 'EPSG', ?, ?, ?);
        ''', (f'GDA2020 / MGA zone {z}', epsg, epsg, wkt, f'Map Grid of Australia 2020 Zone {z} (Projected, metres)'))

    # 2. gpkg_contents
    cur.execute('''
    CREATE TABLE IF NOT EXISTS gpkg_contents (
        table_name TEXT NOT NULL PRIMARY KEY,
        data_type TEXT NOT NULL,
        identifier TEXT UNIQUE,
        description TEXT DEFAULT '',
        last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE,
        srs_id INTEGER,
        CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
    );
    ''')

    # 3. gpkg_geometry_columns
    cur.execute('''
    CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
        table_name TEXT NOT NULL,
        column_name TEXT NOT NULL,
        geometry_type_name TEXT NOT NULL,
        srs_id INTEGER NOT NULL,
        z TINYINT NOT NULL,
        m TINYINT NOT NULL,
        CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
        CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
        CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
    );
    ''')

    # 4. layer_styles (QGIS standard embedded styles)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS layer_styles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        f_table_catalog TEXT,
        f_table_schema TEXT,
        f_table_name TEXT,
        f_geometry_column TEXT,
        styleName TEXT,
        styleQML TEXT,
        styleSLD TEXT,
        useAsDefault BOOLEAN,
        description TEXT,
        owner TEXT,
        ui TEXT,
        update_time DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    ''')

    # 5. Survey metadata
    cur.execute('''
    CREATE TABLE IF NOT EXISTS survey_metadata (
        key TEXT PRIMARY KEY,
        value TEXT,
        description TEXT
    );
    ''')
    cur.execute('''
    INSERT OR REPLACE INTO survey_metadata VALUES
    ('project_name', 'Australian Heritage Landscape Survey & Artefact Recording', 'Standard schema for Australian heritage recording'),
    ('author', 'Mick Morrison', 'Primary Investigator'),
    ('institution', 'Flinders University', 'Archaeology'),
    ('srid_storage', ?, 'Primary storage coordinate system for GeoPackage geometry'),
    ('datum', 'GDA2020', 'Geocentric Datum of Australia 2020'),
    ('version', 'GeoPackage-V0.2', 'Refactored open standard schema');
    ''', (str(target_crs_id),))

    # 6. Survey users: Only Mick Morrison as requested
    cur.execute('''
    CREATE TABLE IF NOT EXISTS survey_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'Lead Surveyor',
        active INTEGER DEFAULT 1
    );
    ''')
    cur.execute('''
    INSERT OR REPLACE INTO survey_users (username, full_name, role) VALUES
    ('mmorrison', 'Mick Morrison', 'Lead Surveyor');
    ''')

    conn.commit()

def populate_vocabularies_in_db(conn, vocabularies):
    cur = conn.cursor()
    print("Populating 111 controlled vocabulary lookup tables...")
    for vname, vdata in vocabularies.items():
        table_name = f"vocab_{vname}"
        cur.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            label TEXT NOT NULL,
            parent_term TEXT,
            description TEXT,
            display_order INTEGER
        );
        ''')
        cur.execute('''
        INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
        VALUES (?, 'attributes', ?, ?, 0);
        ''', (table_name, table_name, f"Controlled vocabulary: {vdata['title']}"))

        for idx, opt in enumerate(vdata['options']):
            val = opt['value']
            code = clean_col_name(val)
            desc = opt.get('desc', '')
            parent = opt.get('parent', None)
            cur.execute(f'''
            INSERT OR IGNORE INTO {table_name} (code, label, parent_term, description, display_order)
            VALUES (?, ?, ?, ?, ?);
            ''', (code, val, parent, desc, idx + 1))

    conn.commit()

def create_media_attachments_table(conn):
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS media_attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_feature_type TEXT NOT NULL,
        parent_record_id TEXT NOT NULL,
        media_type TEXT NOT NULL CHECK(media_type IN ('photo', 'audio_note', 'pdf_document', 'sketch', 'other')),
        field_name TEXT,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        mime_type TEXT,
        caption TEXT,
        author TEXT,
        timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        file_size_bytes INTEGER,
        blob_data BLOB
    );
    ''')
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
    VALUES ('media_attachments', 'attributes', 'media_attachments', 'Survey media attachments (Photos, Audio voice notes, PDF site plans, Sketches)', 0);
    ''')
    conn.commit()

def create_child_spatial_tables(conn, target_crs_id):
    cur = conn.cursor()

    # 1. feature_boundaries (Polygon layer for native QGIS digitizing)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS feature_boundaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        geom POLYGON,
        parent_feature_type TEXT NOT NULL,
        parent_feature_id TEXT NOT NULL,
        boundary_criterion TEXT,
        geometry_type TEXT DEFAULT 'Polygon',
        area_sqm REAL,
        perimeter_m REAL,
        notes TEXT,
        author TEXT,
        timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    ''')
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
    VALUES ('feature_boundaries', 'features', 'feature_boundaries', 'Child boundary polygons representing feature perimeters and site extents', ?);
    ''', (target_crs_id,))
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_geometry_columns VALUES ('feature_boundaries', 'geom', 'POLYGON', ?, 0, 0);
    ''', (target_crs_id,))

    # 2. feature_lines (LineString layer for native QGIS linear feature digitizing)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS feature_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        geom LINESTRING,
        parent_feature_type TEXT NOT NULL,
        parent_feature_id TEXT NOT NULL,
        line_type TEXT DEFAULT 'Linear Feature',
        description TEXT,
        length_m REAL,
        author TEXT,
        timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    ''')
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
    VALUES ('feature_lines', 'features', 'feature_lines', 'Child linear features (fence lines, transects, trench alignments, wall footings)', ?);
    ''', (target_crs_id,))
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_geometry_columns VALUES ('feature_lines', 'geom', 'LINESTRING', ?, 0, 0);
    ''', (target_crs_id,))

    # 3. tree_scars (Child entity for Historic Trees)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tree_scars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        geom POINT,
        parent_tree_id TEXT NOT NULL,
        scar_number INTEGER NOT NULL,
        formatted_id TEXT NOT NULL,
        author TEXT,
        timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        scar_type TEXT,
        axe_marks_present TEXT,
        axe_mark_count INTEGER,
        max_axe_mark_length_mm REAL,
        scar_height_above_ground_mm REAL,
        scar_orientation_degrees REAL,
        scar_length_mm REAL,
        scar_width_mm REAL,
        aperture_length_mm REAL,
        aperture_width_mm REAL,
        device_photos_of_scar TEXT,
        additional_notes TEXT,
        external_camera_id_scars TEXT,
        external_camera_file_names_and_attachment TEXT,
        external_camera_image_attachment TEXT,
        additional_edits_or_uploads_required TEXT,
        editing_notes TEXT
    );
    ''')
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
    VALUES ('tree_scars', 'features', 'tree_scars', 'Child scars associated with Historic Trees', ?);
    ''', (target_crs_id,))
    cur.execute('''
    INSERT OR REPLACE INTO gpkg_geometry_columns VALUES ('tree_scars', 'geom', 'POINT', ?, 0, 0);
    ''', (target_crs_id,))

    conn.commit()

def create_feature_layers(conn, schema, target_crs_id):
    cur = conn.cursor()
    entities = schema['entities']
    created_tables = []

    for ent_key, ent_info in entities.items():
        if ent_info.get('is_child', False):
            continue

        table_name = clean_col_name(ent_key)
        id_prefix = ent_info['id_prefix']
        
        cols = [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'geom POINT',
            'record_id TEXT UNIQUE NOT NULL',
            'author TEXT',
            'timestamp DATETIME DEFAULT (strftime(\'%Y-%m-%dT%H:%M:%fZ\',\'now\'))',
            'latitude REAL',
            'longitude REAL',
            'easting REAL',
            'northing REAL',
            'mga_zone INTEGER',
            'gps_accuracy REAL'
        ]

        seen_cols = {'id', 'geom', 'record_id', 'author', 'timestamp', 'latitude', 'longitude', 'easting', 'northing', 'mga_zone', 'gps_accuracy'}
        
        for tab_name, fields in ent_info['tabs'].items():
            for f in fields:
                fname = f['name']
                if f['type'] in ('button', 'webview', 'gpsdiag', 'list'):
                    continue
                if 'autonum' in f['flags'] or ('id' in fname.lower() and ('flaked' in fname.lower() or 'burial' in fname.lower() or 'tree' in fname.lower() or 'mound' in fname.lower())):
                    col_name = f"{table_name}_num"
                    if col_name not in seen_cols:
                        cols.append(f"{col_name} INTEGER")
                        seen_cols.add(col_name)
                    continue

                col_name = clean_col_name(fname)
                if col_name in seen_cols or col_name in ('gps', 'find_this_in_the_map', 'find_this_in_the_map...'):
                    continue

                sql_type = map_field_to_sql_type(f)
                cols.append(f"{col_name} {sql_type}")
                seen_cols.add(col_name)

        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n  " + ",\n  ".join(cols) + "\n);"
        cur.execute(create_sql)

        cur.execute('''
        INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
        VALUES (?, 'features', ?, ?, ?);
        ''', (table_name, table_name, f"Survey Layer: {ent_info['label']} (Prefix: {id_prefix})", target_crs_id))

        cur.execute('''
        INSERT OR REPLACE INTO gpkg_geometry_columns VALUES (?, 'geom', 'POINT', ?, 0, 0);
        ''', (table_name, target_crs_id))

        created_tables.append(table_name)

    # Master overview spatial view
    union_queries = []
    for tbl in created_tables:
        union_queries.append(f"""
        SELECT 
            '{tbl}' AS feature_type,
            record_id,
            author,
            timestamp,
            latitude,
            longitude,
            easting,
            northing,
            geom
        FROM {tbl}
        """)

    summary_view_sql = "CREATE VIEW IF NOT EXISTS all_heritage_features AS\n" + " UNION ALL\n".join(union_queries) + ";"
    cur.execute("DROP VIEW IF EXISTS all_heritage_features;")
    cur.execute(summary_view_sql)

    conn.commit()
    return created_tables

def insert_baseline_records(conn, target_crs_id, zone):
    cur = conn.cursor()
    print("Inserting generic baseline survey records...")

    # Calculate MGA coordinates for the chosen zone
    # Reference location (mid-latitude -25.0, center of zone)
    cm = zone * 6 - 183
    ref_lat = -25.5000
    ref_lon = cm + 0.1500
    e, n = latlon_to_mga(ref_lat, ref_lon, zone)

    # Point geometry in chosen CRS
    if target_crs_id == 7844:
        gx, gy = ref_lon, ref_lat
    else:
        gx, gy = e, n

    mound_geom = create_gpkg_point_blob(gx, gy, target_crs_id)
    cur.execute('''
    INSERT OR REPLACE INTO mound (
        geom, record_id, author, timestamp, latitude, longitude, easting, northing, mga_zone, gps_accuracy,
        mound_num, landform_pattern, landform_element, dominant_vegetation_type,
        dominant_vegetation_cover, site_boundary_criterion, geometry_type, mound_matrix,
        mound_shape, mound_length_m, mound_height_estimate_m, mound_surface_vegetation,
        stone_artefact_count, faunal_materials_present, additional_notes
    ) VALUES (
        ?, 'MD001', 'Mick Morrison', '2026-08-10T09:30:00Z', ?, ?, ?, ?, ?, 1.5,
        1, 'Alluvial plain', 'Levee', 'Eucalypt woodland',
        'Mid-dense', 'Mound margins', 'Polygon', 'Shell, bone and charcoal rich matrix',
        'Oval / circular', 32.5, 1.25, 'Sparse grasses on crest',
        14, 'Marine shell and bone fragments',
        'Prominent earthen and shell mound located on alluvial terrace. Native polygon boundary digitized in QGIS.'
    );
    ''', (mound_geom, ref_lat, ref_lon, e, n, zone))

    # Child Polygon Boundary in chosen CRS (drawn directly around mound)
    if target_crs_id == 7844:
        poly_ring = [
            (ref_lon - 0.0003, ref_lat + 0.0002),
            (ref_lon + 0.0003, ref_lat + 0.0002),
            (ref_lon + 0.0002, ref_lat - 0.0003),
            (ref_lon - 0.0003, ref_lat - 0.0002),
            (ref_lon - 0.0003, ref_lat + 0.0002)
        ]
    else:
        poly_ring = [
            (e - 30.0, n + 20.0),
            (e + 30.0, n + 20.0),
            (e + 20.0, n - 30.0),
            (e - 30.0, n - 20.0),
            (e - 30.0, n + 20.0)
        ]
    poly_geom = create_gpkg_polygon_blob([poly_ring], target_crs_id)
    cur.execute('''
    INSERT OR REPLACE INTO feature_boundaries (
        geom, parent_feature_type, parent_feature_id, boundary_criterion, geometry_type,
        area_sqm, perimeter_m, notes, author, timestamp
    ) VALUES (
        ?, 'mound', 'MD001', 'Mound margins', 'Polygon',
        615.0, 98.4, 'Digitized along visible slope break marking mound margin', 'Mick Morrison', '2026-08-10T09:45:00Z'
    );
    ''', (poly_geom,))

    # Sample Tree (TR001)
    tree_lat = ref_lat - 0.0040
    tree_lon = ref_lon + 0.0030
    te, tn = latlon_to_mga(tree_lat, tree_lon, zone)
    tgx, tgy = (tree_lon, tree_lat) if target_crs_id == 7844 else (te, tn)
    tree_geom = create_gpkg_point_blob(tgx, tgy, target_crs_id)

    cur.execute('''
    INSERT OR REPLACE INTO tree (
        geom, record_id, author, timestamp, latitude, longitude, easting, northing, mga_zone, gps_accuracy,
        tree_num, tree_type, species, girth_mm, tree_height, tree_condition, number_of_scars, additional_notes
    ) VALUES (
        ?, 'TR001', 'Mick Morrison', '2026-08-10T11:15:00Z', ?, ?, ?, ?, ?, 1.8,
        1, 'Living tree', 'Eucalyptus sp.', 1780.0, '10-20 m', 'Mature living', 1,
        'Mature box tree with intact cultural scar on south-western trunk face.'
    );
    ''', (tree_geom, tree_lat, tree_lon, te, tn, zone))

    # Tree Child Scar (TR001-SC1)
    cur.execute('''
    INSERT OR REPLACE INTO tree_scars (
        geom, parent_tree_id, scar_number, formatted_id, author, timestamp,
        scar_type, axe_marks_present, axe_mark_count, scar_height_above_ground_mm,
        scar_length_mm, scar_width_mm, additional_notes
    ) VALUES (
        ?, 'TR001', 1, 'TR001-SC1', 'Mick Morrison', '2026-08-10T11:20:00Z',
        'Bark removal - container/shield', 'Yes', 4, 820.0,
        1180.0, 360.0, 'Parallel cut marks visible at lower dry face'
    );
    ''', (tree_geom,))

    # Sample Flaked Stone Artefact (FLSA001) associated with Mound MD001
    flsa_lat = ref_lat + 0.0001
    flsa_lon = ref_lon + 0.0001
    fe, fn = latlon_to_mga(flsa_lat, flsa_lon, zone)
    fgx, fgy = (flsa_lon, flsa_lat) if target_crs_id == 7844 else (fe, fn)
    flsa_geom = create_gpkg_point_blob(fgx, fgy, target_crs_id)

    cur.execute('''
    INSERT OR REPLACE INTO flaked_stone_artefact (
        geom, record_id, author, timestamp, latitude, longitude, easting, northing, mga_zone, gps_accuracy,
        flaked_stone_artefact_num, raw_material_type, raw_material_colour, weight_g,
        flake_completeness, platform_surface, maximum_length_mm,
        maximum_width_mm, maximum_thickness_mm, related_site_name, additional_notes
    ) VALUES (
        ?, 'FLSA001', 'Mick Morrison', '2026-08-10T14:00:00Z', ?, ?, ?, ?, ?, 1.2,
        1, 'Silcrete', 'Reddish-brown', 21.4,
        'Complete flake', 'Focal', 38.5, 29.0, 11.2, 'MD001',
        'Complete silcrete flake with prominent bulb of percussion and feather termination.'
    );
    ''', (flsa_geom, flsa_lat, flsa_lon, fe, fn, zone))

    # Sample Media Attachments
    cur.execute('''
    INSERT OR REPLACE INTO media_attachments (
        parent_feature_type, parent_record_id, media_type, field_name, file_name, file_path,
        mime_type, caption, author, timestamp
    ) VALUES 
    ('mound', 'MD001', 'photo', 'Device_photos', 'MD001_overview.jpg', 'media/photos/sample_mound_overview.jpg', 'image/jpeg', 'Overview photograph of mound deposit', 'Mick Morrison', '2026-08-10T09:32:00Z'),
    ('mound', 'MD001', 'audio_note', 'Audio_field_notes', 'MD001_field_audio.wav', 'media/audio/MD001_field_audio.wav', 'audio/wav', 'Voice note describing surface visibility and geomorphic context', 'Mick Morrison', '2026-08-10T09:35:00Z'),
    ('mound', 'MD001', 'pdf_document', 'External_camera_image_attachment', 'MD001_site_sketch_plan.pdf', 'media/documents/MD001_site_sketch_plan.pdf', 'application/pdf', 'Site plan sketch with datum reference and scale', 'Mick Morrison', '2026-08-10T10:00:00Z'),
    ('tree', 'TR001', 'photo', 'Device_photos', 'TR001_scar_detail.jpg', 'media/photos/TR001_scar_detail.jpg', 'image/jpeg', 'Detail of scar dry face and axe cut marks', 'Mick Morrison', '2026-08-10T11:22:00Z');
    ''')

    conn.commit()

def choose_zone_interactive():
    print("=" * 65)
    print("  AUSTRALIAN HERITAGE SURVEY & ARTEFACT RECORDING (v0.2)")
    print("  Coordinate Reference System Selection (GDA2020 Standard)")
    print("=" * 65)
    print("  [49] GDA2020 / MGA zone 49 (EPSG:7849 - WA West)")
    print("  [50] GDA2020 / MGA zone 50 (EPSG:7850 - Perth / WA South-West)")
    print("  [51] GDA2020 / MGA zone 51 (EPSG:7851 - WA East)")
    print("  [52] GDA2020 / MGA zone 52 (EPSG:7852 - NT West / SA West)")
    print("  [53] GDA2020 / MGA zone 53 (EPSG:7853 - Adelaide / SA Central / NT)")
    print("  [54] GDA2020 / MGA zone 54 (EPSG:7854 - QLD West / NSW Far West / VIC West) [Default]")
    print("  [55] GDA2020 / MGA zone 55 (EPSG:7855 - Melbourne / Sydney West / ACT / QLD Central / TAS)")
    print("  [56] GDA2020 / MGA zone 56 (EPSG:7856 - Brisbane / Sydney East / Byron Bay / QLD Coast)")
    print("  [G]  GDA2020 Geographic 2D (EPSG:7844 - All Australia, Lat/Long degrees)")
    print("=" * 65)

    if not sys.stdin.isatty():
        print("Non-interactive session: defaulting to MGA Zone 54 (EPSG:7854)")
        return 54, 7854

    choice = input("Select MGA Zone (49-56 or G) [default: 54]: ").strip().upper()
    if choice == 'G':
        return 54, 7844
    if choice in [str(z) for z in range(49, 57)]:
        z = int(choice)
        return z, 7800 + z
    return 54, 7854

def main():
    parser = argparse.ArgumentParser(description="Generate Australian Heritage Survey GeoPackage (v0.2)")
    parser.add_argument("--zone", type=str, default=None, help="MGA Zone (49-56) or 'geographic' (GDA2020 EPSG:7844)")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    if args.zone:
        z_str = args.zone.strip().lower()
        if z_str in ('g', 'geographic', '7844'):
            zone, target_crs_id = 54, 7844
        elif z_str in [str(z) for z in range(49, 57)]:
            zone = int(z_str)
            target_crs_id = 7800 + zone
        else:
            print(f"Unknown zone '{args.zone}'. Defaulting to MGA Zone 54 (EPSG:7854).")
            zone, target_crs_id = 54, 7854
    else:
        zone, target_crs_id = choose_zone_interactive()

    crs_name = f"GDA2020 / MGA zone {zone} (EPSG:{target_crs_id})" if target_crs_id != 7844 else "GDA2020 Geographic 2D (EPSG:7844)"
    print(f"\nConfiguring GeoPackage with target CRS: {crs_name}")

    schema_path = os.path.join(SCHEMA_DIR, 'faims_extracted_schema.json')
    vocab_path = os.path.join(SCHEMA_DIR, 'vocabularies.json')

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocabularies = json.load(f)

    if os.path.exists(GPKG_PATH):
        print(f"Replacing existing {GPKG_PATH}...")
        os.remove(GPKG_PATH)

    conn = sqlite3.connect(GPKG_PATH)
    try:
        init_gpkg_metadata_tables(conn, target_crs_id)
        populate_vocabularies_in_db(conn, vocabularies)
        create_media_attachments_table(conn)
        create_child_spatial_tables(conn, target_crs_id)
        created_tables = create_feature_layers(conn, schema, target_crs_id)
        insert_baseline_records(conn, target_crs_id, zone)
        print(f"Created {len(created_tables)} feature point layers, 2 boundary layers, tree_scars, and media_attachments.")
        print("GeoPackage database created successfully!")
    finally:
        conn.close()

    # Automatically generate corresponding QGIS project
    print("\nGenerating synchronized QGIS 3 project with native OGR connections & OSM basemap...")
    from export_qgis_project import export_project
    export_project(target_crs_id, zone)

    print(f"\nFinished! GeoPackage size: {os.path.getsize(GPKG_PATH):,} bytes at {GPKG_PATH}")

if __name__ == '__main__':
    main()
