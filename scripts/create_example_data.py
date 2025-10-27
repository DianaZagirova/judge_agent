#!/usr/bin/env python3
"""
Script to create example JSON data from the evaluations database.
Extracts ~50 random DOIs with their evaluation data for demonstration purposes.
"""

import sqlite3
import json
import sys
from pathlib import Path

def create_example_json(db_path: str, output_path: str, sample_size: int = 50):
    """
    Extract random sample of evaluations from database and save to JSON.
    
    Args:
        db_path: Path to the evaluations database
        output_path: Path to save the example JSON file
        sample_size: Number of random records to extract (default: 50)
    """
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        # Get random sample
        query = """
            SELECT 
                doi, pmid, title, result, aging_theory, type, 
                reasoning, confidence_score, prompt_tokens, 
                completion_tokens, total_tokens, cost_usd, 
                processing_time_seconds, success, error_message, 
                timestamp, model_used, revision
            FROM paper_evaluations
            WHERE success = 1
            ORDER BY RANDOM()
            LIMIT ?
        """
        
        cursor.execute(query, (sample_size,))
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        example_data = []
        for row in rows:
            example_data.append({
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
                'success': row['success'],
                'error_message': row['error_message'],
                'timestamp': row['timestamp'],
                'model_used': row['model_used'],
                'revision': row['revision']
            })
        
        conn.close()
        
        # Save to JSON file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(example_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully created example JSON with {len(example_data)} records")
        print(f"📁 Saved to: {output_path}")
        
        # Print some statistics
        valid_count = sum(1 for item in example_data if item['result'] == 'valid')
        not_valid_count = sum(1 for item in example_data if item['result'] == 'not_valid')
        doubted_count = sum(1 for item in example_data if item['result'] == 'doubted')
        
        print(f"\n📊 Sample Statistics:")
        print(f"   Valid: {valid_count}")
        print(f"   Not Valid: {not_valid_count}")
        print(f"   Doubted: {doubted_count}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Default paths
    db_path = "data/evaluations.db"
    output_path = "data/example_evaluations.json"
    
    # Allow custom paths from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    
    success = create_example_json(db_path, output_path)
    sys.exit(0 if success else 1)
