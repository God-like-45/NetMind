import httpx
import json

def pull_model():
    print("Pulling llama3.2:3b model from Ollama...")
    try:
        # Use a longer timeout as model pulls can take some time
        with httpx.Client(timeout=600.0) as client:
            with client.stream("POST", "http://localhost:11434/api/pull", json={"name": "llama3.2:3b"}) as response:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        print(f"Status: {data.get('status', '')}")
                        if "completed" in data and "total" in data:
                            percent = (data['completed'] / data['total']) * 100
                            print(f"Progress: {percent:.2f}%")
        print("Model pulled successfully!")
    except Exception as e:
        print(f"Failed to pull model: {e}")

if __name__ == "__main__":
    pull_model()
