#!/usr/bin/env python3
"""
Export sample papers from each category to JSON files.
"""
import sqlite3
import json
from pathlib import Path

# Database path
RESULTS_DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"
OUTPUT_DIR = Path("/home/diana.z/hack/llm_judge/samples")
SAMPLE_SIZE = 200

def export_category_samples():
    """Export 200 samples from each category to JSON files."""
    
    # Check if database exists
    if not Path(RESULTS_DB_PATH).exists():
        print(f"ERROR: Database not found at {RESULTS_DB_PATH}")
        return
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    categories = [
        {
            'name': 'valid',
            'query': "SELECT * FROM paper_evaluations WHERE success = 1 AND result = 'valid' LIMIT ?",
            'filename': 'valid_papers_sample.json'
        },
        {
            'name': 'doubted',
            'query': "SELECT * FROM paper_evaluations WHERE success = 1 AND result = 'doubted' LIMIT ?",
            'filename': 'doubted_papers_sample.json'
        },
        {
            'name': 'not_valid_low_confidence',
            'query': "SELECT * FROM paper_evaluations WHERE success = 1 AND result = 'not_valid' AND confidence_score <= 7 LIMIT ?",
            'filename': 'not_valid_low_confidence_sample.json'
        },
        {
            'name': 'not_valid_high_confidence',
            'query': "SELECT * FROM paper_evaluations WHERE success = 1 AND result = 'not_valid' AND confidence_score > 7 LIMIT ?",
            'filename': 'not_valid_high_confidence_sample.json'
        }
    ]
    
    print("=" * 80)
    print("EXPORTING SAMPLE PAPERS BY CATEGORY")
    print("=" * 80)
    print(f"Sample size: {SAMPLE_SIZE} papers per category")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    for category in categories:
        cursor.execute(category['query'], (SAMPLE_SIZE,))
        rows = cursor.fetchall()
        
        # Convert rows to list of dictionaries
        papers = []
        for row in rows:
            paper = {
                'doi': row['doi'],
                'pmid': row['pmid'],
                'title': row['title'],
                'result': row['result'],
                'aging_theory': row['aging_theory'],
                'type': row['type'],
                'reasoning': row['reasoning'],
                'confidence_score': row['confidence_score'],
                'prompt_tokens': row['prompt_tokens'],
                'completion_tokens': row['completion_tokens'],
                'total_tokens': row['total_tokens'],
                'cost_usd': row['cost_usd'],
                'processing_time_seconds': row['processing_time_seconds'],
                'timestamp': row['timestamp'],
                'model_used': row['model_used']
            }
            papers.append(paper)
        
        # Save to JSON file
        output_file = OUTPUT_DIR / category['filename']
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)
        
        print(f"✓ {category['name']:30s} | Exported {len(papers):3d} papers → {category['filename']}")
    
    conn.close()
    
    print()
    print("=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"Files saved to: {OUTPUT_DIR}")
    
    # Also create a summary file
    summary = {
        'export_info': {
            'sample_size': SAMPLE_SIZE,
            'export_timestamp': None
        },
        'categories': [
            {
                'name': cat['name'],
                'filename': cat['filename'],
                'description': get_category_description(cat['name'])
            }
            for cat in categories
        ]
    }
    
    summary_file = OUTPUT_DIR / 'README.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary saved to: {summary_file}")
    print("=" * 80)

def get_category_description(category_name):
    """Get description for each category."""
    descriptions = {
        'valid': 'Papers classified as valid aging theory papers',
        'doubted': 'Papers with uncertain classification',
        'not_valid_low_confidence': 'Papers classified as not valid but with low confidence (≤7)',
        'not_valid_high_confidence': 'Papers classified as not valid with high confidence (>7)'
    }
    return descriptions.get(category_name, '')

if __name__ == "__main__":
    export_category_samples()
