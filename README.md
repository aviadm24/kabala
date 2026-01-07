# Simple Image Uploader (FastAPI + Cloudinary)

This small app provides a minimal UI to choose an image, set a name and date, and upload to Cloudinary using FastAPI.

Setup

1. Create a free Cloudinary account and get `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.
2. Set environment variables (macOS / zsh example):

```bash
export CLOUDINARY_CLOUD_NAME=your_cloud_name
export CLOUDINARY_API_KEY=your_api_key
export CLOUDINARY_API_SECRET=your_api_secret
export FLASK_SECRET=some_secret  # not used by FastAPI but safe to remove
```

3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run (development):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

Open http://localhost:5000/ui and use the form.

Notes

- The app reads Cloudinary credentials from environment variables.
- Uploaded images are stored in the `uploads` folder on your Cloudinary account.
- This is a simple demo — do not expose API keys or run with reload in production.
