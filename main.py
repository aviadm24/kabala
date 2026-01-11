from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
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
import sqlite3

# SQLite DB
DB_PATH = os.path.join(os.path.dirname(__file__), 'receipts.db')


def get_conn():
    return sqlite3.connect(DB_PATH)


def ensure_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        phone TEXT,
        email TEXT,
        family_members TEXT,
        insurance_companies TEXT,
        created_at TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS receipts (
        public_id TEXT PRIMARY KEY,
        name TEXT,
        date TEXT,
        refunded TEXT,
        sent_to_insurance TEXT,
        insurance_company TEXT,
        account_username TEXT,
        family_count INTEGER,
        family_names TEXT,
        how_work TEXT,
        secure_url TEXT,
        created_at TEXT
    )
    ''')
    conn.commit()
    conn.close()


def insert_receipt(rec: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''INSERT OR REPLACE INTO receipts(public_id, name, date, refunded, sent_to_insurance, insurance_company, account_username, family_count, family_names, how_work, secure_url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        rec.get('public_id'), rec.get('name'), rec.get('date'), rec.get('refunded'), rec.get('sent_to_insurance'), rec.get('insurance_company'), rec.get('account_username'), rec.get('family_count'), rec.get('family_names'), rec.get('how_work'), rec.get('secure_url'), rec.get('created_at')
    ))
    conn.commit()
    conn.close()


def update_receipt_db(public_id: str, fields: dict):
    if not fields:
        return
    keys = list(fields.keys())
    vals = [fields[k] for k in keys]
    set_clause = ','.join([f"{k}=?" for k in keys])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE receipts SET {set_clause} WHERE public_id=?", vals + [public_id])
    conn.commit()
    conn.close()


def delete_receipt_db(public_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM receipts WHERE public_id=?", (public_id,))
    conn.commit()
    conn.close()


def get_receipt_db(public_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT public_id, name, date, refunded, sent_to_insurance, insurance_company, account_username, family_count, family_names, how_work, secure_url, created_at FROM receipts WHERE public_id=?", (public_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    cols = ['public_id', 'name', 'date', 'refunded', 'sent_to_insurance', 'insurance_company', 'account_username', 'family_count', 'family_names', 'how_work', 'secure_url', 'created_at']
    return dict(zip(cols, row))


def insert_user(username: str, phone: str, email: str, family_members: str, insurance_companies: str):
    conn = get_conn()
    cur = conn.cursor()
    created_at = datetime.utcnow().isoformat()
    cur.execute('''INSERT OR REPLACE INTO users(username, phone, email, family_members, insurance_companies, created_at)
    VALUES (?, ?, ?, ?, ?, ?)''', (username, phone, email, family_members, insurance_companies, created_at))
    conn.commit()
    conn.close()


def get_user_db(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, phone, email, family_members, insurance_companies, created_at FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    cols = ['username', 'phone', 'email', 'family_members', 'insurance_companies', 'created_at']
    return dict(zip(cols, row))


def update_user_db(username: str, fields: dict):
    if not fields:
        return
    keys = list(fields.keys())
    vals = [fields[k] for k in keys]
    set_clause = ','.join([f"{k}=?" for k in keys])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {set_clause} WHERE username=?", vals + [username])
    conn.commit()
    conn.close()


# ensure DB exists on startup
ensure_db()

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


@app.get("/health", response_class=JSONResponse)
def health_check():
    return {"status": "ok", "message": "API running"}


@app.get('/')
def ui(request: Request):
    # get current count of images in Cloudinary uploads folder
    try:
        search_result = cloudinary.Search().expression("folder:uploads").max_results(1).execute()
        count = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
    except Exception:
        count = 0

    username = request.cookies.get('username')
    user_data = get_user_db(username) if username else None
    
    # parse user data lists into arrays
    family_members = []
    insurance_companies = []
    if user_data:
        if user_data.get('family_members'):
            family_members = [x.strip() for x in user_data['family_members'].split(',') if x.strip()]
        if user_data.get('insurance_companies'):
            insurance_companies = [x.strip() for x in user_data['insurance_companies'].split(',') if x.strip()]
    
    return templates.TemplateResponse('index.html', {"request": request, "count": count, "username": username, "family_members": family_members, "insurance_companies": insurance_companies})


@app.get('/count')
def count_endpoint():
    try:
        search_result = cloudinary.Search().expression("folder:uploads").max_results(1).execute()
        cnt = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
        return JSONResponse({"count": cnt})
    except Exception as e:
        return JSONResponse({"error": str(e), "count": 0}, status_code=500)


@app.get('/login')
def login_get(request: Request):
    return templates.TemplateResponse('login.html', {"request": request, "message": request.query_params.get('message','')})


@app.get('/signup')
def signup_get(request: Request):
    return templates.TemplateResponse('signup.html', {"request": request, "message": request.query_params.get('message','')})


@app.post('/signup')
def signup_post(request: Request, username: str = Form(...), phone: Optional[str] = Form(None), email: Optional[str] = Form(None), family_members: Optional[str] = Form(None), insurance_companies: Optional[str] = Form(None)):
    if not username:
        return templates.TemplateResponse('signup.html', {"request": request, "message": "Username is required"})
    
    # check if user already exists
    existing = get_user_db(username)
    if existing:
        return templates.TemplateResponse('signup.html', {"request": request, "message": "Username already exists. Please try another or sign in."})
    
    try:
        insert_user(username, phone or '', email or '', family_members or '', insurance_companies or '')
    except Exception as e:
        return templates.TemplateResponse('signup.html', {"request": request, "message": f"Sign up failed: {e}"})
    
    # auto login
    resp = RedirectResponse(url='/', status_code=302)
    resp.set_cookie('username', username, httponly=True)
    return resp


@app.post('/login')
def login_post(request: Request, username: str = Form(...)):
    resp = RedirectResponse(url='/', status_code=302)
    # set simple username cookie (httponly)
    resp.set_cookie('username', username, httponly=True)
    return resp


@app.get('/logout')
def logout(request: Request):
    resp = RedirectResponse(url='/login', status_code=302)
    resp.delete_cookie('username')
    return resp


@app.get('/profile')
def profile_get(request: Request):
    username = request.cookies.get('username')
    if not username:
        return RedirectResponse(url='/login', status_code=302)
    
    user_data = get_user_db(username)
    if not user_data:
        return templates.TemplateResponse('profile.html', {"request": request, "message": "User not found"})
    
    # Parse lists
    family_members = []
    insurance_companies = []
    if user_data.get('family_members'):
        family_members = [x.strip() for x in user_data['family_members'].split(',') if x.strip()]
    if user_data.get('insurance_companies'):
        insurance_companies = [x.strip() for x in user_data['insurance_companies'].split(',') if x.strip()]
    
    # Get message from cookie if exists
    message = request.cookies.get('profile_message', '')
    
    resp = templates.TemplateResponse('profile.html', {
        "request": request,
        "username": username,
        "email": user_data.get('email', ''),
        "phone": user_data.get('phone', ''),
        "family_members": family_members,
        "insurance_companies": insurance_companies,
        "family_members_str": user_data.get('family_members', ''),
        "insurance_companies_str": user_data.get('insurance_companies', ''),
        "message": message
    })
    
    # Clear message cookie
    resp.delete_cookie('profile_message')
    return resp


@app.post('/profile')
def profile_post(request: Request, email: Optional[str] = Form(None), phone: Optional[str] = Form(None), family_members: Optional[str] = Form(None), insurance_companies: Optional[str] = Form(None)):
    username = request.cookies.get('username')
    if not username:
        return RedirectResponse(url='/login', status_code=302)
    
    # Update user profile
    try:
        update_user_db(username, {
            'email': email or '',
            'phone': phone or '',
            'family_members': family_members or '',
            'insurance_companies': insurance_companies or ''
        })
        message = "✓ Profile updated successfully!"
    except Exception as e:
        message = f"Error updating profile: {e}"
    
    # Redirect back to profile page with message
    resp = RedirectResponse(url='/profile', status_code=302)
    resp.set_cookie('profile_message', message, httponly=True)
    return resp


@app.post('/upload')
async def upload_receipt(request: Request, name: str = Form(...), date: Optional[str] = Form(None), image: UploadFile = File(...)):
    # require a logged-in user
    username = request.cookies.get('username')
    if not username:
        return templates.TemplateResponse('login.html', {"request": request, "message": "Please log in before uploading."})

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

    # gather metadata fields
    try:
        form = await request.form()
    except Exception:
        form = {}

    refunded = 'yes' if form.get('refunded') in ('yes', 'on', 'true') else 'no'
    sent_to_insurance = 'yes' if form.get('sent_to_insurance') in ('yes', 'on', 'true') else 'no'
    insurance_company = (form.get('insurance_company') or '').strip()
    account_username = (form.get('account_username') or username).strip()
    try:
        family_count = int(form.get('family_count')) if form.get('family_count') else 0
    except Exception:
        family_count = 0
    family_names = (form.get('family_names') or '').strip()
    how_work = (form.get('how_work') or '').strip()

    # build Cloudinary context string (sanitize pipes/newlines)
    def _safe(v: str) -> str:
        return re.sub(r"[|\n\r]", '', (v or '').strip())

    ctx_parts = [f"refund={_safe(refunded)}", f"sent_to_insurance={_safe(sent_to_insurance)}"]
    if insurance_company:
        ctx_parts.append(f"insurance_company={_safe(insurance_company)}")
    if account_username:
        ctx_parts.append(f"account_username={_safe(account_username)}")
    if family_count:
        ctx_parts.append(f"family_count={int(family_count)}")
    if family_names:
        ctx_parts.append(f"family_names={_safe(family_names)}")
    if how_work:
        ctx_parts.append(f"how_work={_safe(how_work)}")

    context_str = '|'.join(ctx_parts)

    try:
        # Upload using the underlying file-like object
        result = cloudinary.uploader.upload(
            image.file,
            public_id=public_id,
            folder='uploads',
            resource_type='image',
            context=context_str
        )
    except Exception as e:
        print('Upload failed:', e)
        # stay on UI and show error message
        msg = f"Upload failed: {e}"
        try:
            search_result = cloudinary.Search().expression("folder:uploads").max_results(1).execute()
            count = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
        except Exception:
            count = 0
        return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": [], "name": name, "date": date_str, "count": count})

    # Success: store metadata in SQLite and show index UI with success message and the uploaded result
    msg = f"Uploaded: {result.get('public_id', public_id)}"
    try:
        search_result = cloudinary.Search().expression("folder:uploads").max_results(1).execute()
        count = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
    except Exception:
        count = 0

    # save to sqlite
    rec = {
        'public_id': result.get('public_id', public_id),
        'name': name,
        'date': date_str,
        'refunded': refunded,
        'sent_to_insurance': sent_to_insurance,
        'insurance_company': insurance_company,
        'account_username': account_username,
        'family_count': family_count,
        'family_names': family_names,
        'how_work': how_work,
        'secure_url': result.get('secure_url'),
        'created_at': result.get('created_at')
    }
    try:
        insert_receipt(rec)
    except Exception:
        pass

    # attach db copy to result so template can show values
    result['_db'] = rec

    return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": [result], "name": name, "date": date_str, "count": count, "username": username})


@app.get('/search')
def search(request: Request, name: Optional[str] = None, date: Optional[str] = None, refunded: Optional[str] = None, sent_to_insurance: Optional[str] = None, insurance_company: Optional[str] = None):
    """Search uploaded images by name, date and metadata using Cloudinary Search API."""
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

    # metadata filters stored in context string (e.g. refund=yes|sent_to_insurance=yes|insurance_company=Name)
    if refunded and refunded.lower() in ('yes', 'no'):
        expr_parts.append(f"context:'refund={refunded.lower()}'")

    if sent_to_insurance and sent_to_insurance.lower() in ('yes', 'no'):
        expr_parts.append(f"context:'sent_to_insurance={sent_to_insurance.lower()}'")

    if insurance_company:
        safe_comp = re.sub(r'[^A-Za-z0-9_\- ]', '', insurance_company.strip())
        # wildcard match on company name inside context
        expr_parts.append(f"context:'insurance_company:*{safe_comp}*'")

    expr = " AND ".join(expr_parts)

    try:
        search_result = cloudinary.Search().expression(expr).max_results(100).execute()
        resources = search_result.get('resources', [])
    except Exception as e:
        return templates.TemplateResponse('index.html', {"request": request, "message": f"Search failed: {e}", "results": []})

    # enrich results with DB metadata if available
    enriched = []
    for r in resources:
        db = get_receipt_db(r.get('public_id'))
        if db:
            r['_db'] = db
        enriched.append(r)

    return templates.TemplateResponse('index.html', {"request": request, "results": enriched, "name": name, "date": date, "refunded": refunded, "sent_to_insurance": sent_to_insurance, "insurance_company": insurance_company})


@app.post('/update')
def update_metadata(request: Request, public_id: str = Form(...), refunded: Optional[str] = Form(None), sent_to_insurance: Optional[str] = Form(None), insurance_company: Optional[str] = Form(None)):
    """Update metadata (context) for an existing image."""
    try:
        refunded_val = 'yes' if refunded in ('yes', 'on', 'true') else 'no'
        sent_val = 'yes' if sent_to_insurance in ('yes', 'on', 'true') else 'no'
        insurance_val = (insurance_company or '').strip()

        ctx_parts = [f"refund={refunded_val}", f"sent_to_insurance={sent_val}"]
        if insurance_val:
            safe_company = re.sub(r"[|]", '', insurance_val)
            ctx_parts.append(f"insurance_company={safe_company}")
        context_str = '|'.join(ctx_parts)

        cloudinary.uploader.add_context(context_str, public_id=public_id)
        # also update sqlite
        update_fields = {'refunded': refunded_val, 'sent_to_insurance': sent_val}
        if insurance_val:
            update_fields['insurance_company'] = insurance_val
        update_receipt_db(public_id, update_fields)
    except Exception as e:
        return templates.TemplateResponse('index.html', {"request": request, "message": f"Update failed: {e}", "results": []})

    # fetch updated resource
    try:
        res = cloudinary.api.resource(public_id)
    except Exception:
        res = None

    msg = f"Updated metadata for {public_id}"
    return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": [res] if res else [], "count": 0})


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

    # remove from sqlite as well
    try:
        delete_receipt_db(public_id)
    except Exception:
        pass

    return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": []})

