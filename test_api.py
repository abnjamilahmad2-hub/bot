import urllib.request
import json


models = [
    "openrouter/free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen3-coder:free"
]

for model in models:
    print(f"\n--- Testing {model} ---")
    try:
        req = urllib.request.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "Reply with 'hi'"}],
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req)
        print("NO JSON: Success!")
        
        # Test JSON mode
        req_json = urllib.request.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "Reply with JSON {\"a\": 1}"}],
                "response_format": {"type": "json_object"}
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        resp_json = urllib.request.urlopen(req_json)
        print("JSON: Success!")
    except Exception as e:
        print(f"Failed: {e}")
        try:
            print(e.read().decode())
        except:
            pass
