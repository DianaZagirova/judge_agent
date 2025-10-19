#!/usr/bin/env python3
"""
Check if all papers from the source database have been processed.
"""
import sqlite3

# Connect to both databases
papers_db = '/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db'
results_db = '/home/diana.z/hack/llm_judge/data/evaluations.db'

papers_conn = sqlite3.connect(papers_db)
papers_cursor = papers_conn.cursor()

results_conn = sqlite3.connect(results_db)
results_cursor = results_conn.cursor()

# Get total papers in source database
papers_cursor.execute('SELECT COUNT(*) FROM papers')
total_papers = papers_cursor.fetchone()[0]

# Get papers with required fields (doi, title, abstract)
papers_cursor.execute('''
    SELECT COUNT(*) FROM papers 
    WHERE doi IS NOT NULL 
    AND title IS NOT NULL 
    AND abstract IS NOT NULL
    AND abstract != ''
''')
eligible_papers = papers_cursor.fetchone()[0]

# Get processed papers count
results_cursor.execute('SELECT COUNT(*) FROM paper_evaluations')
processed_papers = results_cursor.fetchone()[0]

# Get successfully evaluated papers
results_cursor.execute('SELECT COUNT(*) FROM paper_evaluations WHERE success = 1')
successful_papers = results_cursor.fetchone()[0]

print('=' * 80)
print('PROCESSING COVERAGE CHECK')
print('=' * 80)
print()
print(f'Source database (papers.db):')
print(f'  Total papers: {total_papers:,}')
print(f'  Eligible papers (with DOI, title, abstract): {eligible_papers:,}')
print(f'  Ineligible papers (missing data): {total_papers - eligible_papers:,}')
print()
print(f'Results database (evaluations.db):')
print(f'  Total processed: {processed_papers:,}')
print(f'  Successfully evaluated: {successful_papers:,}')
print(f'  Failed evaluations: {processed_papers - successful_papers:,}')
print()
print('=' * 80)
print('STATUS:')
print('=' * 80)

if processed_papers >= eligible_papers:
    print(f'✓ All eligible papers have been processed!')
    print(f'  Coverage: {100 * processed_papers / eligible_papers:.2f}%')
else:
    remaining = eligible_papers - processed_papers
    print(f'⚠ {remaining:,} papers remaining to process')
    print(f'  Coverage: {100 * processed_papers / eligible_papers:.2f}%')
    print(f'  Processed: {processed_papers:,} / {eligible_papers:,}')

print('=' * 80)

papers_conn.close()
results_conn.close()
