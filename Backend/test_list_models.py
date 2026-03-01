import requests

api_key = "AIzaSyAQ7yVqtUaCPCBkB7bneZsa-umD9oO6IWI"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print("Listing models...")
resp = requests.get(url)
if resp.status_code == 200:
    for model in resp.json().get("models", []):
        if "embedContent" in model.get("supportedGenerationMethods", []):
            print(f"- {model['name']}: {model.get('description')}")
else:
    print(resp.status_code, resp.text)
