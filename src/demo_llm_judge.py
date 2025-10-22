"""
Demo-specific LLM judge with less aggressive rate limiting for better user experience.
"""
import json
import time
import random
import os
from openai import OpenAI, RateLimitError
from src.load_env import load_env
from prompts.system_prompt_judge import PROMPT

load_env()

# Demo-friendly configuration - less aggressive
OPENAI_MODEL = "gpt-4o-mini"  # Use the more available model
RETRIES = 2  # Fewer retries for demo
BASE_DELAY = 0.3  # Very short base delay
RATE_LIMIT_WAIT = 1.0  # Short wait time

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def demo_llm_judge(jointtext: str) -> dict:    
    """
    Demo version of LLM judge with less aggressive rate limiting.
    """
    n = 0
    while n < RETRIES:
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": jointtext},
                ],
                temperature=0.2,
                max_tokens=200  # Limit tokens for faster response
            )
            result_json = resp.choices[0].message.content.strip()
            if result_json.startswith("```"):
                result_json = result_json.strip(" ```json\n")
            
            result = json.loads(result_json)
            # Add token usage metadata
            result['_tokens'] = {
                'prompt_tokens': resp.usage.prompt_tokens,
                'completion_tokens': resp.usage.completion_tokens,
                'total_tokens': resp.usage.total_tokens
            }
            
            # Very small delay after successful request
            time.sleep(BASE_DELAY)
            return result
            
        except RateLimitError as e:
            n += 1
            wait_time = RATE_LIMIT_WAIT + random.uniform(0, 0.3)
            print(f"⏳ Brief pause ({wait_time:.1f}s)...", end=" ", flush=True)
            if n < RETRIES:
                time.sleep(wait_time)
            else:
                raise Exception(f"API temporarily unavailable: {e}")
                
        except json.JSONDecodeError as e:
            n += 1
            print(f"🔄 Retrying...", end=" ", flush=True)
            if n < RETRIES:
                time.sleep(0.5)
            else:
                raise Exception(f"Processing error: {e}")
                
        except Exception as e:
            n += 1
            print(f"🔄 Retrying...", end=" ", flush=True)
            if n < RETRIES:
                time.sleep(0.5)
            else:
                raise Exception(f"Unexpected error: {e}")
    
    raise Exception(f"Failed after {RETRIES} attempts")
