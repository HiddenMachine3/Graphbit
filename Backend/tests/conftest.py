from pathlib import Path
from dotenv import load_dotenv

# Ensure tests pick up environment variables from the project's .env
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
