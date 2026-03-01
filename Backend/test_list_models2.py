import requests

api_key = "AIzaSyAQ7yVqtUaCPCBkB7bneZsa-umD9oO6IWI"
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
