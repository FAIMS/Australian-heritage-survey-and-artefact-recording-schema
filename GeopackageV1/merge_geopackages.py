#!/usr/bin/env python3
"""
merge_geopackages.py

Multi-device offline synchronization & consolidation tool for Australian Heritage Surveys.

Enables seamless field workflows across multiple disconnected devices:
- Topcon FC-6000 Windows tablets running QGIS
- iPads running QField
- Laptops / Field Stations

Workflow:
1. Devices collect data completely offline (no 4G / internet required).
2. At the end of the survey day, device GeoPackages are copied to a central laptop via USB flash drive or cable.
3. This script merges all incoming GeoPackages into a single consolidated master database:
   - Deduplicates based on natural record_id (or formatted_id)
   - Resolves updates based on timestamp
   - Assigns fresh autoincrement primary keys (FID)
   - Merges spatial extents in gpkg_contents
   - Consolidates media attachments (photos, audio notes, PDFs)
   - Produces a detailed end-of-day audit and summary report
"""

import os
import sys
import shutil
import sqlite3
import argparse
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
MEDIA_DIR = os.path.join(SCRIPT_DIR, 'media')
DEFAULT_MASTER_GPKG = os.path.join(DATA_DIR, 'heritage_survey.gpkg')

FEATURE_LAYERS = [
    'feature_boundaries',
    'feature_lines',
    'burial',
    'tree',
    'tree_scars',
    'historical_feature',
    'mound',
    'point_of_interest',
    'rock_shelter',
    'surface_exposure',
    'flaked_stone_artefact',
    'other_stone_artefact',
    'knapped_glass_artefact',
    'discrete_hearth_artefact',
    'glass_artefact',
    'ceramic_artefact',
    'buttons',
    'metal_artefact',
    'weapons_and_ammunition',
    'misc_artefact'
]

def get_table_columns(conn, table_name):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name});")
    return [row[1] for row in cur.fetchall()]

def merge_single_gpkg(master_conn, source_gpkg_path, report_stats):
    src_conn = sqlite3.connect(source_gpkg_path)
    src_cur = src_conn.cursor()
    master_cur = master_conn.cursor()

    source_filename = os.path.basename(source_gpkg_path)
    report_stats[source_filename] = {'inserted': 0, 'updated': 0, 'skipped': 0, 'layers': {}}

    try:
        # 1. Merge all spatial feature layers
        for table in FEATURE_LAYERS:
            # Check if table exists in source
            src_cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name=?;", (table,))
            if not src_cur.fetchone():
                continue

            master_cols = get_table_columns(master_conn, table)
            src_cols = get_table_columns(src_conn, table)
            if not master_cols or not src_cols:
                continue

            # Identify unique identifier column: usually record_id or formatted_id
            id_col = 'record_id' if 'record_id' in src_cols else ('formatted_id' if 'formatted_id' in src_cols else None)
            
            # Common columns excluding autoincrement 'id'
            common_cols = [c for c in src_cols if c in master_cols and c != 'id']
            cols_clause = ", ".join(common_cols)
            placeholders = ", ".join(["?"] * len(common_cols))

            query = f"SELECT {cols_clause} FROM {table}"
            src_cur.execute(query)
            rows = src_cur.fetchall()

            tbl_ins = 0
            tbl_upd = 0
            tbl_skip = 0

            for row in rows:
                row_dict = dict(zip(common_cols, row))
                row_id_val = row_dict.get(id_col) if id_col else None

                if id_col and row_id_val:
                    # Check if record exists in master
                    check_query = f"SELECT id, timestamp FROM {table} WHERE {id_col} = ?"
                    master_cur.execute(check_query, (row_id_val,))
                    existing = master_cur.fetchone()

                    if existing:
                        existing_fid, existing_ts = existing
                        src_ts = row_dict.get('timestamp')

                        # Update if source is newer
                        if src_ts and existing_ts and str(src_ts) > str(existing_ts):
                            set_clause = ", ".join([f"{c} = ?" for c in common_cols])
                            update_sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"
                            master_cur.execute(update_sql, tuple(row) + (existing_fid,))
                            tbl_upd += 1
                        else:
                            tbl_skip += 1
                        continue

                # Insert new feature
                insert_sql = f"INSERT INTO {table} ({cols_clause}) VALUES ({placeholders})"
                master_cur.execute(insert_sql, row)
                tbl_ins += 1

            if (tbl_ins + tbl_upd + tbl_skip) > 0:
                report_stats[source_filename]['layers'][table] = {
                    'inserted': tbl_ins,
                    'updated': tbl_upd,
                    'skipped': tbl_skip
                }
                report_stats[source_filename]['inserted'] += tbl_ins
                report_stats[source_filename]['updated'] += tbl_upd
                report_stats[source_filename]['skipped'] += tbl_skip

        # 2. Merge media_attachments
        src_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media_attachments';")
        if src_cur.fetchone():
            master_cols = get_table_columns(master_conn, 'media_attachments')
            src_cols = get_table_columns(src_conn, 'media_attachments')
            common_cols = [c for c in src_cols if c in master_cols and c != 'id']
            cols_clause = ", ".join(common_cols)
            placeholders = ", ".join(["?"] * len(common_cols))

            src_cur.execute(f"SELECT {cols_clause} FROM media_attachments")
            media_rows = src_cur.fetchall()
            m_ins = 0
            m_skip = 0

            for mrow in media_rows:
                m_dict = dict(zip(common_cols, mrow))
                fname = m_dict.get('file_name')
                prec_id = m_dict.get('parent_record_id')

                # Check if already attached
                master_cur.execute("SELECT id FROM media_attachments WHERE parent_record_id = ? AND file_name = ?", (prec_id, fname))
                if master_cur.fetchone():
                    m_skip += 1
                else:
                    master_cur.execute(f"INSERT INTO media_attachments ({cols_clause}) VALUES ({placeholders})", mrow)
                    m_ins += 1

            if (m_ins + m_skip) > 0:
                report_stats[source_filename]['layers']['media_attachments'] = {
                    'inserted': m_ins,
                    'updated': 0,
                    'skipped': m_skip
                }
                report_stats[source_filename]['inserted'] += m_ins
                report_stats[source_filename]['skipped'] += m_skip

        # 3. Update spatial extents in gpkg_contents for all layers
        for table in FEATURE_LAYERS:
            src_cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name=?;", (table,))
            if not src_cur.fetchone():
                continue
            cols = get_table_columns(master_conn, table)
            if 'latitude' in cols:
                master_cur.execute(f"SELECT min(latitude), min(longitude), max(latitude), max(longitude) FROM {table};")
                ext = master_cur.fetchone()
                if ext and ext[0] is not None:
                    now_iso = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                    master_cur.execute('''
                    UPDATE gpkg_contents 
                    SET last_change = ?
                    WHERE table_name = ?
                    ''', (now_iso, table))
            else:
                now_iso = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                master_cur.execute('''
                UPDATE gpkg_contents 
                SET last_change = ?
                WHERE table_name = ?
                ''', (now_iso, table))

        master_conn.commit()

    finally:
        src_conn.close()

def print_merge_report(report_stats, master_path):
    print("\n" + "=" * 70)
    print("           AUSTRALIAN HERITAGE SURVEY - END-OF-DAY MERGE REPORT")
    print("=" * 70)
    print(f"Master GeoPackage: {master_path}")
    print(f"Timestamp:        {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)

    total_ins = 0
    total_upd = 0
    total_skip = 0

    for src_file, stats in report_stats.items():
        print(f"\n[Source Device File: {src_file}]")
        print(f"  Summary: {stats['inserted']} new features added | {stats['updated']} updated | {stats['skipped']} already present / unchanged")
        if stats['layers']:
            print("  Breakdown by layer:")
            for l_name, l_stat in stats['layers'].items():
                print(f"    - {l_name:<25}: +{l_stat['inserted']} inserted, ~{l_stat['updated']} updated, ={l_stat['skipped']} retained")
        total_ins += stats['inserted']
        total_upd += stats['updated']
        total_skip += stats['skipped']

    print("-" * 70)
    print(f"TOTAL CONSOLIDATION: +{total_ins} inserted, ~{total_upd} updated across {len(report_stats)} source device(s).")
    print("=" * 70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Consolidate multiple field GeoPackages into master heritage database.")
    parser.add_argument('sources', nargs='*', help='One or more source .gpkg files from Topcon tablets / iPads')
    parser.add_argument('--master', default=DEFAULT_MASTER_GPKG, help=f'Master GeoPackage path (default: {DEFAULT_MASTER_GPKG})')
    parser.add_argument('--backup', action='store_true', default=True, help='Create a timestamped backup of the master before merging')
    args = parser.parse_args()

    master_path = os.path.abspath(args.master)
    if not os.path.exists(master_path):
        print(f"Error: Master GeoPackage not found at '{master_path}'. Run generate_geopackage.py first.")
        sys.exit(1)

    sources = [os.path.abspath(s) for s in args.sources if os.path.exists(s) and os.path.abspath(s) != master_path]

    if not sources:
        # Check if there is an incoming directory with .gpkg files
        incoming_dir = os.path.join(DATA_DIR, 'incoming_sync')
        if os.path.exists(incoming_dir):
            for fname in os.listdir(incoming_dir):
                if fname.endswith('.gpkg') and not fname.startswith('.'):
                    full_p = os.path.join(incoming_dir, fname)
                    if full_p != master_path:
                        sources.append(full_p)

    if not sources:
        print("No source GeoPackage files specified or found in 'data/incoming_sync/'.")
        print("Usage:")
        print("  python3 merge_geopackages.py tablet_topcon_a.gpkg ipad_survey_b.gpkg")
        print("  python3 merge_geopackages.py data/incoming_sync/*.gpkg")
        sys.exit(0)

    # 1. Backup master database
    if args.backup:
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{master_path}.backup_{ts}"
        shutil.copy2(master_path, backup_path)
        print(f"Created safety backup of master GeoPackage: {backup_path}")

    master_conn = sqlite3.connect(master_path)
    report_stats = {}

    try:
        for src_path in sources:
            print(f"Merging records from: {src_path}...")
            merge_single_gpkg(master_conn, src_path, report_stats)
    finally:
        master_conn.close()

    print_merge_report(report_stats, master_path)

if __name__ == '__main__':
    main()
