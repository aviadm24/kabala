"""
Minimal FastAPI backend suitable for free deployment on Render.
Purpose:
- Verify deployment works
- Provide a health check endpoint
- Provide a simple upload endpoint (no DB yet)

This is intentionally minimal so you can confirm:
1. Render build works
2. HTTPS works
3. API responds from your phone/browser
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="Minimal Receipt Backend")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Backend is running"}


@app.post("/upload")
async def upload_receipt(image: UploadFile = File(...)):
    """Accept a single image upload and save it to disk."""
    file_path = os.path.join(UPLOAD_DIR, image.filename)

    with open(file_path, "wb") as f:
        f.write(await image.read())

    return JSONResponse(
        {
            "status": "saved",
            "filename": image.filename
        }
    )


# Render looks for a web server on 0.0.0.0
# The actual startup command is provided in Render settings
