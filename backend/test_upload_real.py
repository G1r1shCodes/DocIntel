import requests

url = 'http://localhost:8000/api/documents/upload'
files = {'file': open(r'D:\DocIntel\backend\uploads\2026\07\145a4e422b9d4386ae701a6faf5682f9_Fullstack_AI_Engineer.pdf', 'rb')}
headers = {'Authorization': 'Bearer fake_token'}
try:
    response = requests.post(url, files=files, headers=headers)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
except Exception as e:
    print("ERROR:", e)
