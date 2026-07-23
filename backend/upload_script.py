import os
from fastapi.testclient import TestClient
from main import app
from auth.clerk_auth import get_current_user_from_token

def override_get_current_user():
    return {"user_id": "test_1", "username": "AdminUser", "role": "Admin"}

app.dependency_overrides[get_current_user_from_token] = override_get_current_user

client = TestClient(app)
pdf_path = r"D:\DocIntel\backend\uploads\2026\07\145a4e422b9d4386ae701a6faf5682f9_Fullstack_AI_Engineer.pdf"
with open(pdf_path, "rb") as f:
    res = client.post("/api/documents/upload", files={"file": ("Fullstack_AI_Engineer.pdf", f, "application/pdf")})
    print(res.json())
