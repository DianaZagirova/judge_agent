"""
Test script to evaluate a single paper manually.
Useful for testing and debugging.
"""
import sys
sys.path.insert(0, 'src')

from llm_judge import llm_judge
import json

# Test with a sample paper
test_title = "The Free Radical Theory of Aging"
test_abstract = """
The free radical theory of aging proposes that organisms age because cells 
accumulate free radical damage over time. Free radicals are atoms or molecules 
with unpaired electrons that can damage cellular components including DNA, 
proteins, and lipids. This theory suggests that the accumulation of oxidative 
damage is a fundamental cause of aging and age-related diseases. We review the 
evidence for and against this theory, discussing how antioxidant defenses may 
play a role in longevity and the aging process across different species.
"""

if __name__ == "__main__":
    print("Testing LLM Judge with sample paper...")
    print("=" * 80)
    print(f"Title: {test_title}")
    print(f"Abstract: {test_abstract.strip()}")
    print("=" * 80)
    print("\nCalling LLM Judge...\n")
    
    jointtext = f"{test_title}: {test_abstract}"
    
    try:
        result = llm_judge(jointtext)
        
        print("RESULT:")
        print(json.dumps(result, indent=2))
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print(f"Result: {result.get('result')}")
        print(f"Aging Theory: {result.get('aging_theory')}")
        print(f"Type: {result.get('type')}")
        print(f"Confidence: {result.get('confidence_score')}/10")
        
        if '_tokens' in result:
            tokens = result['_tokens']
            print(f"\nTokens Used:")
            print(f"  Prompt: {tokens['prompt_tokens']}")
            print(f"  Completion: {tokens['completion_tokens']}")
            print(f"  Total: {tokens['total_tokens']}")
        
        print("\nReasoning:")
        print(result.get('reasoning', 'N/A'))
        print("=" * 80)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
