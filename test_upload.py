#!/usr/bin/env python3
import requests
import json

# Upload test file with document types
with open("test_upload.json", "rb") as f:
    files = {"file": f}
    response = requests.post(
        "http://localhost:8000/api/upload?reset_db=true",
        files=files
    )

print("Upload Response:", response.status_code)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# Now check the types
response2 = requests.get("http://localhost:8000/api/filters/types")
print("\nDocument Types:")
print(json.dumps(response2.json(), indent=2, ensure_ascii=False))
