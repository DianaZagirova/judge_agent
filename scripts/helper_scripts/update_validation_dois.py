#!/usr/bin/env python3
"""
Analyze the evaluations database and update DOIs from validation list to mark them as 'valid'.
"""

import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Paths
DOIS_FILE = "/home/diana.z/hack/download_papers_pubmed/data/dois_validation/dois_validation3.txt"
EVALUATIONS_DB = Path(__file__).parent.parent.parent / "data" / "evaluations.db"

def load_validation_dois():
    """Load DOIs from validation file."""
    with open(DOIS_FILE, 'r') as f:
        dois = [line.strip() for line in f if line.strip()]
    # Remove duplicates while preserving order
    seen = set()
    unique_dois = []
    for doi in dois:
        if doi not in seen:
            seen.add(doi)
            unique_dois.append(doi)
    return unique_dois

def analyze_database():
    """Analyze the evaluations database."""
    if not EVALUATIONS_DB.exists():
        print(f"❌ Database not found: {EVALUATIONS_DB}")
        return None
    
    conn = sqlite3.connect(EVALUATIONS_DB)
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(paper_evaluations)")
    columns = {col[1] for col in cursor.fetchall()}
    
    print(f"📊 Database: {EVALUATIONS_DB}")
    print(f"📋 Columns: {', '.join(sorted(columns))}")
    print()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations")
    total = cursor.fetchone()[0]
    print(f"📈 Total records: {total:,}")
    
    # Get counts by result
    cursor.execute("SELECT result, COUNT(*) FROM paper_evaluations GROUP BY result ORDER BY COUNT(*) DESC")
    result_counts = cursor.fetchall()
    print(f"\n📊 Records by result:")
    for result, count in result_counts:
        print(f"  - {result}: {count:,} ({100*count/total:.1f}%)")
    
    # Get counts by success
    cursor.execute("SELECT success, COUNT(*) FROM paper_evaluations GROUP BY success")
    success_counts = cursor.fetchall()
    print(f"\n✅ Records by success status:")
    for success, count in success_counts:
        status = "Success" if success == 1 else "Failed"
        print(f"  - {status}: {count:,} ({100*count/total:.1f}%)")
    
    conn.close()
    return columns

def update_validation_dois(dois, dry_run=False):
    """Update DOIs from validation list to mark as 'valid'."""
    if not EVALUATIONS_DB.exists():
        print(f"❌ Database not found: {EVALUATIONS_DB}")
        return
    
    conn = sqlite3.connect(EVALUATIONS_DB)
    cursor = conn.cursor()
    
    print(f"\n🔍 Checking {len(dois)} validation DOIs...")
    
    # Check which DOIs exist in database
    found_dois = []
    not_found_dois = []
    already_valid = []
    to_update = []
    
    for doi in dois:
        cursor.execute("SELECT doi, result FROM paper_evaluations WHERE doi = ?", (doi,))
        row = cursor.fetchone()
        
        if row:
            found_dois.append(doi)
            current_result = row[1]
            if current_result == 'valid':
                already_valid.append(doi)
            else:
                to_update.append((doi, current_result))
        else:
            not_found_dois.append(doi)
    
    print(f"\n📊 Analysis:")
    print(f"  ✅ Found in database: {len(found_dois)}")
    print(f"  ✓  Already marked as 'valid': {len(already_valid)}")
    print(f"  🔄 Need to update: {len(to_update)}")
    print(f"  ❌ Not found in database: {len(not_found_dois)}")
    
    if to_update:
        print(f"\n🔄 DOIs to update from other results to 'valid':")
        result_changes = defaultdict(int)
        for doi, current_result in to_update[:10]:  # Show first 10
            print(f"  - {doi}: '{current_result}' → 'valid'")
            result_changes[current_result] += 1
        
        if len(to_update) > 10:
            print(f"  ... and {len(to_update) - 10} more")
        
        print(f"\n📊 Changes by current result:")
        for result, count in sorted(result_changes.items(), key=lambda x: x[1], reverse=True):
            print(f"  - '{result}' → 'valid': {count}")
    
    if not_found_dois:
        print(f"\n❌ DOIs not found in database (first 10):")
        for doi in not_found_dois[:10]:
            print(f"  - {doi}")
        if len(not_found_dois) > 10:
            print(f"  ... and {len(not_found_dois) - 10} more")
    
    # Perform update
    if to_update and not dry_run:
        print(f"\n🔄 Updating {len(to_update)} records...")
        updated_count = 0
        for doi, _ in to_update:
            cursor.execute(
                "UPDATE paper_evaluations SET result = ? WHERE doi = ?",
                ('valid', doi)
            )
            if cursor.rowcount > 0:
                updated_count += 1
        
        conn.commit()
        print(f"✅ Successfully updated {updated_count} records to 'valid'")
        
        # Verify updates
        cursor.execute(
            "SELECT COUNT(*) FROM paper_evaluations WHERE result = 'valid'"
        )
        valid_count = cursor.fetchone()[0]
        print(f"📊 Total 'valid' records now: {valid_count:,}")
    elif to_update and dry_run:
        print(f"\n🔍 DRY RUN: Would update {len(to_update)} records (use --apply to actually update)")
    
    conn.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze evaluations database and update validation DOIs to 'valid'",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true",
                        help="Actually apply the updates (default is dry-run)")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Only analyze the database, don't check/update DOIs")
    
    args = parser.parse_args()
    
    print("="*80)
    print("EVALUATIONS DATABASE ANALYSIS & VALIDATION DOI UPDATE")
    print("="*80)
    
    # Analyze database
    columns = analyze_database()
    
    if columns is None:
        return 1
    
    if args.analyze_only:
        return 0
    
    # Load validation DOIs
    print(f"\n📂 Loading validation DOIs from: {DOIS_FILE}")
    dois = load_validation_dois()
    print(f"✅ Loaded {len(dois)} unique DOIs")
    
    # Update DOIs
    update_validation_dois(dois, dry_run=not args.apply)
    
    print("\n" + "="*80)
    if not args.apply:
        print("🔍 DRY RUN COMPLETE - No changes were made")
        print("   Run with --apply to actually update the database")
    else:
        print("✅ UPDATE COMPLETE")
    print("="*80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
