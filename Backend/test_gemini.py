import requests

api_key = "AIzaSyAQ7yVqtUaCPCBkB7bneZsa-umD9oO6IWI"
model = "text-embedding-004"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"

body = {
    "model": f"models/{model}",
    "content": {"parts": [{"text": "Hello world"}]},
}

print(f"Testing {model}...")
resp = requests.post(url, json=body)
print(resp.status_code, resp.text)

model2 = "embedding-001"
url2 = f"https://generativelanguage.googleapis.com/v1beta/models/{model2}:embedContent?key={api_key}"
body2 = {
    "model": f"models/{model2}",
    "content": {"parts": [{"text": "Hello world"}]},
}
print(f"Testing {model2}...")
resp2 = requests.post(url2, json=body2)
print(resp2.status_code, resp2.text)
