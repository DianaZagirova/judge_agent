#!/usr/bin/env python3
"""
Debug why some papers are not being found as unprocessed.
"""
import sqlite3

papers_db = '/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db'
results_db = '/home/diana.z/hack/llm_judge/data/evaluations.db'

print("=" * 80)
print("DEBUGGING MISSING PAPERS")
print("=" * 80)

# Connect to databases
papers_conn = sqlite3.connect(papers_db)
papers_conn.row_factory = sqlite3.Row
papers_cursor = papers_conn.cursor()

results_conn = sqlite3.connect(results_db)
results_cursor = results_conn.cursor()

# Get processed DOIs
print("\n1. Getting processed DOIs from evaluations.db...")
results_cursor.execute("SELECT doi FROM paper_evaluations")
processed_dois = {row[0] for row in results_cursor.fetchall()}
print(f"   Found {len(processed_dois)} processed DOIs")

# Get eligible papers from source
print("\n2. Getting eligible papers from papers.db...")
papers_cursor.execute("""
    SELECT doi, pmid, title, abstract 
    FROM papers 
    WHERE doi IS NOT NULL 
    AND title IS NOT NULL 
    AND abstract IS NOT NULL
    AND abstract != ''
""")
all_papers = papers_cursor.fetchall()
print(f"   Found {len(all_papers)} eligible papers")

# Check for duplicates in source database
print("\n3. Checking for duplicate DOIs in papers.db...")
papers_cursor.execute("""
    SELECT doi, COUNT(*) as count 
    FROM papers 
    WHERE doi IS NOT NULL 
    AND title IS NOT NULL 
    AND abstract IS NOT NULL
    AND abstract != ''
    GROUP BY doi 
    HAVING count > 1
    ORDER BY count DESC
    LIMIT 10
""")
duplicates = papers_cursor.fetchall()
if duplicates:
    print(f"   ⚠ Found {len(duplicates)} DOIs with duplicates:")
    for row in duplicates[:5]:
        print(f"     - {row['doi']}: {row['count']} copies")
else:
    print("   ✓ No duplicates found")

# Get unique DOIs from source
unique_source_dois = {row['doi'] for row in all_papers}
print(f"\n4. Unique DOIs in source: {len(unique_source_dois)}")

# Find unprocessed
unprocessed_dois = unique_source_dois - processed_dois
print(f"5. Unprocessed DOIs: {len(unprocessed_dois)}")

# Show some examples
if unprocessed_dois:
    print(f"\n6. Sample of unprocessed DOIs (first 10):")
    for i, doi in enumerate(list(unprocessed_dois)[:10], 1):
        # Get paper info
        papers_cursor.execute("""
            SELECT pmid, title 
            FROM papers 
            WHERE doi = ? 
            LIMIT 1
        """, (doi,))
        paper = papers_cursor.fetchone()
        if paper:
            title = paper['title'][:60] + '...' if len(paper['title']) > 60 else paper['title']
            print(f"   {i}. {doi}")
            print(f"      PMID: {paper['pmid']}")
            print(f"      Title: {title}")

# Check if there are papers in results that aren't in source
print(f"\n7. Checking for papers in results.db not in papers.db...")
papers_cursor.execute("SELECT doi FROM papers WHERE doi IS NOT NULL")
all_source_dois = {row['doi'] for row in papers_cursor.fetchall()}
extra_in_results = processed_dois - all_source_dois
if extra_in_results:
    print(f"   ⚠ Found {len(extra_in_results)} DOIs in results but not in source")
    for doi in list(extra_in_results)[:5]:
        print(f"     - {doi}")
else:
    print(f"   ✓ All processed papers exist in source database")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Source database eligible papers: {len(all_papers)}")
print(f"Unique DOIs in source: {len(unique_source_dois)}")
print(f"Processed DOIs: {len(processed_dois)}")
print(f"Unprocessed DOIs: {len(unprocessed_dois)}")
print(f"Difference (duplicates): {len(all_papers) - len(unique_source_dois)}")
print("=" * 80)

papers_conn.close()
results_conn.close()
