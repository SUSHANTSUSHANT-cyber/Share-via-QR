import os

import requests

payload = {"employee_code": "EMP0001"}
server_url = os.getenv("SERVER_URL", "https://your-public-domain.example.com")
response = requests.post(f"{server_url}/session/create", json=payload)
print(response.status_code)
print(response.text)
