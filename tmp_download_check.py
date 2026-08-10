from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

resp = client.post('/session/create', json={'employee_code': 'DEMO'})
print('create', resp.status_code, resp.text)
session_id = resp.json()['session_id']
print('session_id', session_id)

# upload a jpeg
files = {'file': ('test.jpg', b'MAGIC', 'image/jpeg')}
resp = client.post(f'/upload/{session_id}', files=files)
print('upload', resp.status_code, resp.text)

resp_head = client.head(f'/download/{session_id}')
print('head', resp_head.status_code, resp_head.headers.get('content-disposition'), resp_head.headers.get('content-type'))

resp_get = client.get(f'/download/{session_id}')
print('get', resp_get.status_code, resp_get.headers.get('content-disposition'), resp_get.headers.get('content-type'), len(resp_get.content))
