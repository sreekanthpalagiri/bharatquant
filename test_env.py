import os
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env.local'

print(f"Current working directory: {os.getcwd()}")
print(f"Script location: {Path(__file__).resolve()}")
print(f"BASE_DIR: {BASE_DIR}")
print(f"ENV_PATH: {ENV_PATH}")
print(f"ENV file exists: {ENV_PATH.exists()}")

# Load environment variables
load_dotenv(ENV_PATH)

# Check what was loaded
DATABASE_URL = os.getenv('DATABASE_URL')
print(f"\nDATABASE_URL from env: {DATABASE_URL}")
print(f"FLASK_APP from env: {os.getenv('FLASK_APP')}")
print(f"SECRET_KEY from env: {os.getenv('SECRET_KEY')}")
