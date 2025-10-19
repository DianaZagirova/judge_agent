"""Load environment variables from .env file."""
import os
from pathlib import Path


def load_env():
    """Load environment variables from .env file in project root."""
    # Get project root (parent of src directory)
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    if not env_file.exists():
        print(f"Warning: .env file not found at {env_file}")
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                os.environ[key] = value
