#!/usr/bin/env python3
"""Export all data from evaluations.db to JSON files."""

import sqlite3
import json
from pathlib import Path

DB_PATH = "data/evaluations.db"
OUTPUT_DIR = "data/json_export"

def export_table_to_json(cursor, table_name, output_path):
    """Export a single table to JSON."""
    # Get all rows
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Get column names
    column_names = [description[0] for description in cursor.description]
    
    # Convert to list of dictionaries
    data = []
    for row in rows:
        row_dict = dict(zip(column_names, row))
        data.append(row_dict)
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Exported {len(data)} rows from {table_name} to {output_path}")
    return len(data)

def main():
    # Create output directory
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} tables in database")
    print("="*80)
    
    total_rows = 0
    exported_files = []
    
    # Export each table
    for (table_name,) in tables:
        output_file = output_dir / f"{table_name}_1910.json"
        rows = export_table_to_json(cursor, table_name, output_file)
        total_rows += rows
        exported_files.append(str(output_file))
    
    # Also create a combined export with all tables
    combined_data = {}
    for (table_name,) in tables:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        data = [dict(zip(column_names, row)) for row in rows]
        combined_data[table_name] = data
    
    combined_file = output_dir / "all_data.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    exported_files.append(str(combined_file))
    
    # Close connection
    conn.close()
    
    print("="*80)
    print(f"\n✓ Export complete!")
    print(f"  Total rows exported: {total_rows}")
    print(f"\nExported files:")
    for file in exported_files:
        print(f"  - {file}")

if __name__ == "__main__":
    main()
