from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

print('=== create single upload session ===')
resp = client.post('/session/create', json={'employee_code': 'DEMO'})
print('create', resp.status_code, resp.json())
sid = resp.json()['session_id']
files = [('files', ('a.jpg', b'JPEG1', 'image/jpeg'))]
resp = client.post(f'/upload/{sid}', files=files)
print('upload single', resp.status_code, resp.json())
resp = client.get(f'/session/{sid}')
print('session single files', resp.status_code, resp.json())

print('\n=== create multiple upload session ===')
resp = client.post('/session/create', json={'employee_code': 'DEMO'})
sid2 = resp.json()['session_id']
print('create2', sid2)
files = [
    ('files', ('a1.jpg', b'JPG1', 'image/jpeg')),
    ('files', ('a2.jpg', b'JPG2', 'image/jpeg')),
]
resp = client.post(f'/upload/{sid2}', files=files)
print('upload multiple', resp.status_code, resp.json())
resp = client.get(f'/session/{sid2}')
print('session multi', resp.status_code, resp.json())

print('\n=== duplicate filenames in batch ===')
resp = client.post('/session/create', json={'employee_code': 'DEMO'})
sid3 = resp.json()['session_id']
files = [
    ('files', ('a.jpg', b'JPG1', 'image/jpeg')),
    ('files', ('a.jpg', b'JPG2', 'image/jpeg')),
]
resp = client.post(f'/upload/{sid3}', files=files)
print('duplicate names', resp.status_code, resp.text)

print('\n=== invalid mixed with valid ===')
resp = client.post('/session/create', json={'employee_code': 'DEMO'})
sid4 = resp.json()['session_id']
files = [
    ('files', ('valid.jpg', b'JPG1', 'image/jpeg')),
    ('files', ('bad.exe', b'BAD', 'application/octet-stream')),
]
resp = client.post(f'/upload/{sid4}', files=files)
print('invalid mixed', resp.status_code, resp.text)

print('\n=== space in filename ===')
resp = client.post('/session/create', json={'employee_code': 'DEMO'})
sid5 = resp.json()['session_id']
files = [('files', ('space name.jpg', b'JPG', 'image/jpeg'))]
resp = client.post(f'/upload/{sid5}', files=files)
print('space filename upload', resp.status_code, resp.json())
resp = client.get(f'/download/{sid5}', params={'filename': 'space name.jpg'})
print('download space file', resp.status_code, resp.headers.get('content-disposition'))

print('\n=== file too large ===')
resp = client.post('/session/create', json={'employee_code': 'DEMO'})
sid6 = resp.json()['session_id']
large = b'a' * (101 * 1024 * 1024)
files = [('files', ('large.jpg', large, 'image/jpeg'))]
resp = client.post(f'/upload/{sid6}', files=files)
print('oversize', resp.status_code, resp.text)
