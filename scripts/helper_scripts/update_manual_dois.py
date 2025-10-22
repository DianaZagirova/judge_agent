#!/usr/bin/env python3
"""
Script to update the evaluations database:
1. Add 'revision' column
2. Set result='valid' and revision='manual' for DOIs in dois_true_positives_manual.py
3. Set revision=None for all other records
"""

import sqlite3
import sys
from pathlib import Path

# Import the DOIs list
sys.path.insert(0, str(Path(__file__).parent / "data"))
from dois_true_positives_manual import dois

DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"

def update_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if revision column already exists
        cursor.execute("PRAGMA table_info(paper_evaluations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'revision' not in columns:
            print("Adding 'revision' column to paper_evaluations table...")
            cursor.execute("ALTER TABLE paper_evaluations ADD COLUMN revision TEXT")
            conn.commit()
            print("✓ Column added successfully")
        else:
            print("'revision' column already exists")
        
        # Update records for  DOIs
        print(f"\nUpdating {len(dois)} DOIs...")
        updated_count = 0
        not_found = []
        
        for doi in dois:
            cursor.execute(
                "UPDATE paper_evaluations SET result = ?, revision = ? WHERE doi = ?",
                ("valid", "manual", doi)
            )
            if cursor.rowcount > 0:
                updated_count += 1
            else:
                not_found.append(doi)
        
        conn.commit()
        print(f"✓ Updated {updated_count} records to result='valid' and revision='manual'")
        
        if not_found:
            print(f"\n⚠ Warning: {len(not_found)} DOIs not found in database:")
            for doi in not_found[:10]:  # Show first 10
                print(f"  - {doi}")
            if len(not_found) > 10:
                print(f"  ... and {len(not_found) - 10} more")
        
        # Verify the updates
        cursor.execute(
            "SELECT COUNT(*) FROM paper_evaluations WHERE revision = 'manual'"
        )
        manual_count = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM paper_evaluations WHERE revision IS NULL"
        )
        null_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM paper_evaluations")
        total_count = cursor.fetchone()[0]
        
        print(f"\n✓ Database summary:")
        print(f"  - Total records: {total_count}")
        print(f"  - Records with revision='manual': {manual_count}")
        print(f"  - Records with revision=NULL: {null_count}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    update_database()
