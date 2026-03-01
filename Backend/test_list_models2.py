import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent / ".env")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is required in Backend/.env")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print("Listing models...")
resp = requests.get(url)
if resp.status_code == 200:
    for model in resp.json().get("models", []):
        name = model['name']
        if 'embed' in name.lower() or 'embedContent' in model.get('supportedGenerationMethods', []):
            print(f"- {name}: methods={model.get('supportedGenerationMethods')}")
else:
    print(resp.status_code, resp.text)
