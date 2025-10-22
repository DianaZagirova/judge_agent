import pandas as pd
import json
import time
import os
import random
from openai import AzureOpenAI, OpenAI, RateLimitError
from src.load_env import load_env
from prompts.system_prompt_judge import PROMPT
load_env()

USE_MODULE = os.getenv("USE_MODULE")
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

OPENAI_MODEL = "gpt-4.1-mini"
RETRIES = 3  # Reduced for demo - less aggressive retries
BASE_DELAY = 0.5  # Reduced base delay for demo
RATE_LIMIT_WAIT = 1.5  # Reduced wait time for demo

# Initialize Azure OpenAI client
if USE_MODULE == "azure":
    client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)
else:
    client = OpenAI(
        api_key=OPENAI_API_KEY
    )


def llm_judge(jointtext: str, retries= RETRIES) -> dict:    
    """
    Evaluate a paper using LLM judge.
    Returns dict with evaluation results and metadata including tokens used.
    Includes intelligent retry logic with exponential backoff for rate limits.
    """
    n = 0
    while n < retries:
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": jointtext},
                ],
                temperature=0.2
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
            
            # Small delay after successful request to avoid rate limits
            time.sleep(BASE_DELAY + random.uniform(0, 0.2))
            return result
            
        except RateLimitError as e:
            # Handle rate limit errors with exponential backoff
            n += 1
            wait_time = RATE_LIMIT_WAIT * (2 ** (n - 1)) + random.uniform(0, 0.5)  # Exponential backoff with jitter
            print(f"⏳ API rate limit - waiting {wait_time:.1f}s before retry...")
            if n < retries:
                time.sleep(wait_time)
            else:
                raise Exception(f"Rate limit exceeded after {retries} retries: {e}")
                
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            n += 1
            print(f"JSON decode error (attempt {n}/{retries}): {e}; retrying in 2s...")
            if n < retries:
                time.sleep(2)
            else:
                raise Exception(f"JSON parsing failed after {retries} retries: {e}")
                
        except Exception as e:
            # Handle other errors
            n += 1
            wait_time = 2 * n  # Linear backoff for other errors
            print(f"LLM call failed (attempt {n}/{retries}): {e}; retrying in {wait_time}s...")
            if n < retries:
                time.sleep(wait_time)
            else:
                raise Exception(f"Failed after {retries} retries: {e}")
    
    raise Exception(f"Failed after {retries} retries")