from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import re
import json
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
from typing import Optional

app = FastAPI(title="Receipt Uploader (FastAPI + Cloudinary)")

# Templates
templates = Jinja2Templates(directory="templates")

# Load environment variables from .env if present
load_dotenv()

# Cloudinary configuration
cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
api_key = os.environ.get('CLOUDINARY_API_KEY')
api_secret = os.environ.get('CLOUDINARY_API_SECRET')

if not (cloud_name and api_key and api_secret):
    app.logger = app.logger if hasattr(app, 'logger') else None
    # log via print if logger missing
    print('Warning: Cloudinary credentials are not set in environment variables')

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
    secure=True,
)


def safe_public_id(name: str, date_str: str) -> str:
    base = f"{name}_{date_str}"
    base = base.strip().replace(' ', '_')
    base = re.sub(r'[^A-Za-z0-9_\-]', '', base)
    return base[:200]


@app.get("/", response_class=JSONResponse)
def health_check():
    return {"status": "ok", "message": "API running"}


@app.get('/ui')
def ui(request: Request):
    # get current count of images in Cloudinary uploads folder
    try:
        search_result = cloudinary.Search().expression("folder:uploads").max_results(1).execute()
        count = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
    except Exception:
        count = 0

    return templates.TemplateResponse('index.html', {"request": request, "count": count})


@app.get('/count')
def count_endpoint():
    try:
        search_result = cloudinary.Search().expression("folder:uploads").max_results(1).execute()
        cnt = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
        return JSONResponse({"count": cnt})
    except Exception as e:
        return JSONResponse({"error": str(e), "count": 0}, status_code=500)


@app.post('/upload')
async def upload_receipt(request: Request, name: str = Form(...), date: Optional[str] = Form(None), image: UploadFile = File(...)):
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=422)

    # Normalize date
    try:
        if date:
            date_obj = datetime.fromisoformat(date)
            date_str = date_obj.strftime('%Y-%m-%d')
        else:
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
    except Exception:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')

    public_id = safe_public_id(name, date_str)

    try:
        # Upload using the underlying file-like object
        result = cloudinary.uploader.upload(
            image.file,
            public_id=public_id,
            folder='uploads',
            resource_type='image'
        )
    except Exception as e:
        print('Upload failed:', e)
        return JSONResponse({"error": str(e)}, status_code=500)

    result_json = json.dumps(result, indent=2)

    # If the request came from a browser form, render template
    accept = request.headers.get('accept', '')
    if 'text/html' in accept:
        return templates.TemplateResponse('result.html', {"request": request, "result": result, "result_json": result_json, "name": name, "date": date_str})

    return JSONResponse({"status": "uploaded", "result": result})


@app.get('/search')
def search(request: Request, name: Optional[str] = None, date: Optional[str] = None):
    """Search uploaded images by name and/or date using Cloudinary Search API."""
    expr_parts = ["folder:uploads"]

    if name:
        # sanitize name to match how we build public_id
        safe = re.sub(r'[^A-Za-z0-9_\-]', '', name.strip().replace(' ', '_'))
        # Use quoted wildcard pattern for Cloudinary Search (Lucene-style)
        expr_parts.append(f"public_id:'*{safe}*'")

    if date:
        try:
            d = datetime.fromisoformat(date)
            nxt = d + timedelta(days=1)
            expr_parts.append(f"created_at>='{d.strftime('%Y-%m-%d')}'")
            expr_parts.append(f"created_at<'{nxt.strftime('%Y-%m-%d')}'")
        except Exception:
            # ignore invalid date filter
            pass

    expr = " AND ".join(expr_parts)

    try:
        search_result = cloudinary.Search().expression(expr).max_results(100).execute()
        resources = search_result.get('resources', [])
    except Exception as e:
        return templates.TemplateResponse('index.html', {"request": request, "message": f"Search failed: {e}", "results": []})

    return templates.TemplateResponse('index.html', {"request": request, "results": resources, "name": name, "date": date})


@app.post('/delete')
def delete_image(request: Request, public_id: str = Form(...)):
    """Delete an image by its Cloudinary public_id."""
    try:
        res = cloudinary.uploader.destroy(public_id, resource_type='image')
    except Exception as e:
        return templates.TemplateResponse('index.html', {"request": request, "message": f"Delete failed: {e}", "results": []})

    result_flag = res.get('result')
    if result_flag in ('ok', 'deleted'):
        msg = f"Deleted {public_id}"
    else:
        msg = f"Delete returned: {result_flag}"

    return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": []})

