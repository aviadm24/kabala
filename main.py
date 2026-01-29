from fastapi import FastAPI, UploadFile, File, Form, Request, Depends
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
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import logging
from logging.handlers import RotatingFileHandler
from models import User, Receipt
from datetime import datetime
from init_db import ensure_db
from depts import get_db
from database import SessionLocal, engine
# Load environment variables from .env if present
load_dotenv()
from pathlib import Path

from admin.views import setup_admin
from api.ocr import router as ocr_router

def setup_google_credentials():
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not creds_json:
        return

    creds_path = Path("/tmp/google-creds.json")
    creds_path.write_text(creds_json)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)

setup_google_credentials()

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)



app = FastAPI(title="Receipt Uploader (FastAPI + Cloudinary)")
app.include_router(ocr_router, prefix="/api/ocr")

@app.on_event("startup")
def startup():
    setup_admin(app, engine)
    ensure_db()

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger('kabala')
logger.setLevel(logging.DEBUG)

# File handler with rotation
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'app.log'),
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info('Application started')

# Templates
templates = Jinja2Templates(directory="templates")



# Cloudinary configuration
cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
api_key = os.environ.get('CLOUDINARY_API_KEY')
api_secret = os.environ.get('CLOUDINARY_API_SECRET')

if not (cloud_name and api_key and api_secret):
    logger.warning('Cloudinary credentials are not set in environment variables')

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
    secure=True,
)

# Cookie signing with itsdangerous
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Generate a default key (use env var in production!)
    import secrets
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning('SECRET_KEY not set in environment. Using generated key (not persistent).')

serializer = URLSafeTimedSerializer(SECRET_KEY, salt='cookie-signer')


def sign_cookie_value(value: str) -> str:
    """Sign a cookie value for security."""
    return serializer.dumps(value)


def verify_cookie_value(signed_value: str, max_age: int = None) -> Optional[str]:
    """Verify and unsign a cookie value. Returns None if invalid."""
    try:
        return serializer.loads(signed_value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def get_verified_cookies(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Safely get and verify user_id and username cookies. Returns (user_id, username) or (None, None)."""
    user_id_signed = request.cookies.get('user_id')
    username_signed = request.cookies.get('username')
    
    user_id = verify_cookie_value(user_id_signed) if user_id_signed else None
    username = verify_cookie_value(username_signed) if username_signed else None
    
    return user_id, username


def safe_public_id(name: str, date_str: str) -> str:
    base = f"{name}_{date_str}"
    base = base.strip().replace(' ', '_')
    base = re.sub(r'[^A-Za-z0-9_\-]', '', base)
    return base[:200]


@app.get("/health", response_class=JSONResponse)
def health_check():
    return {"status": "ok", "message": "API running"}


@app.get('/')
def ui(request: Request,
       db=Depends(get_db)):
    user_id, username = get_verified_cookies(request)
    
    # get current count of images in Cloudinary uploads folder for this user
    if user_id and username:
        try:
            uid = int(user_id)
        except (ValueError, TypeError):
            uid = None
        
        if uid:
            try:
                search_result = cloudinary.Search().expression(f"folder:uploads AND context.user_id:{uid}").max_results(1).execute()
                count = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
            except Exception:
                count = 0
        else:
            count = 0
    else:
        count = 0

    user_data = get_user_db(db, username) if username else None
    
    # parse user data lists into arrays
    family_members = []
    insurance_companies = []
    if user_data:
        if user_data.family_members:
            family_members = [x.strip() for x in user_data.family_members.split(',') if x.strip()]
        if user_data.insurance_companies:
            insurance_companies = [x.strip() for x in user_data.insurance_companies.split(',') if x.strip()]
    
    return templates.TemplateResponse('index.html', {"request": request, "count": count, "username": username, "family_members": family_members, "insurance_companies": insurance_companies})


@app.get('/count')
def count_endpoint(request: Request):
    user_id, username = get_verified_cookies(request)
    if not user_id or not username:
        return JSONResponse({"count": 0})
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return JSONResponse({"count": 0})
    
    try:
        search_result = cloudinary.Search().expression(f"folder:uploads AND context.user_id:{user_id}").max_results(1).execute()
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
def signup_post(request: Request, username: str = Form(...), phone: Optional[str] = Form(None), 
                email: Optional[str] = Form(None), family_members: Optional[str] = Form(None), 
                insurance_companies: Optional[str] = Form(None), 
                db=Depends(get_db)):
    if not username:
        logger.warning('Signup attempt without username')
        return templates.TemplateResponse('signup.html', {"request": request, "message": "Username is required"})
    
    # check if user already exists
    logger.info("Checking if user exists")
    existing = get_user_db(db, username)
    logger.info(f"Existing user lookup result: {existing}")
    if existing:
        logger.warning(f'Signup attempt with existing username: {username}')
        return templates.TemplateResponse('signup.html', {"request": request, "message": "Username already exists. Please try another or sign in."})
    
    # try:
    insert_user(db, username, phone or '', email or '', family_members or '', insurance_companies or '')
    db.flush()
    logger.info("Session flushed")
        # Get the new use's ID
    logger.info("Fetching user after insert")
    user_data = get_user_db(db, username)
    logger.info(f"Fetched user after insert: {user_data}")

    user_id = user_data.user_id
    logger.info(f'User signup successful: username={username}, user_id={user_id}')
    # except Exception as e:
    #     logger.error(f'Sign up failed for {username}: {e}')
    #     return templates.TemplateResponse('signup.html', {"request": request, "message": f"Sign up failed: {e}"})
    
    # auto login
    resp = RedirectResponse(url='/', status_code=302)
    resp.set_cookie('user_id', sign_cookie_value(str(user_id)), httponly=True, secure=False, samesite='lax')
    resp.set_cookie('username', sign_cookie_value(username), httponly=True, secure=False, samesite='lax')
    logger.info("Signup completed, returning response")
    return resp


@app.post('/login')
def login_post(request: Request, username: str = Form(...), 
               db=Depends(get_db)):
    user_data = get_user_db(db, username)
    if not user_data:
        logger.warning(f'Login attempt with non-existent username: {username}')
        return templates.TemplateResponse('login.html', {"request": request, "message": "Username not found"})
    
    user_id = user_data.user_id
    logger.info(f'User login successful: username={username}, user_id={user_id}')
    resp = RedirectResponse(url='/', status_code=302)
    resp.set_cookie('user_id', sign_cookie_value(str(user_id)), httponly=True, secure=True, samesite='lax')
    resp.set_cookie('username', sign_cookie_value(username), httponly=True, secure=True, samesite='lax')
    return resp


@app.get('/logout')
def logout(request: Request):
    user_id, username = get_verified_cookies(request)
    logger.info(f'User logout: username={username}, user_id={user_id}')
    resp = RedirectResponse(url='/login', status_code=302)
    resp.delete_cookie('user_id')
    resp.delete_cookie('username')
    return resp


@app.get('/profile')
def profile_get(request: Request,
                db=Depends(get_db)):
    user_id, username = get_verified_cookies(request)
    if not user_id or not username:
        return RedirectResponse(url='/login', status_code=302)
    
    user_data = get_user_db(db, username)
    if not user_data:
        return templates.TemplateResponse('profile.html', {"request": request, "message": "User not found"})
    
    # Parse lists
    family_members = []
    insurance_companies = []
    if user_data.family_members:
        family_members = [x.strip() for x in user_data.family_members.split(',') if x.strip()]
    if user_data.insurance_companies:
        insurance_companies = [x.strip() for x in user_data.insurance_companies.split(',') if x.strip()]
    
    # Get message from cookie if exists
    message = request.cookies.get('profile_message', '')
    
    resp = templates.TemplateResponse('profile.html', {
        "request": request,
        "username": username,
        "email": user_data.email,
        "phone": user_data.phone,
        "family_members": family_members,
        "insurance_companies": insurance_companies,
        "family_members_str": user_data.family_members,
        "insurance_companies_str": user_data.insurance_companies,
        "message": message
    })
    
    # Clear message cookie
    resp.delete_cookie('profile_message')
    return resp


@app.post('/profile')
def profile_post(request: Request, email: Optional[str] = Form(None), phone: Optional[str] = Form(None), family_members: Optional[str] = Form(None), insurance_companies: Optional[str] = Form(None)):
    user_id, username = get_verified_cookies(request)
    if not user_id or not username:
        return RedirectResponse(url='/login', status_code=302)
    
    # Update user profile
    try:
        db = SessionLocal()
        update_user_db(db, username, {
            'email': email or '',
            'phone': phone or '',
            'family_members': family_members or '',
            'insurance_companies': insurance_companies or ''
        })
        message = "Profile updated successfully!"
    except Exception as e:
        message = f"Error updating profile: {e}"
    
    # Redirect back to profile page with message
    resp = RedirectResponse(url='/profile', status_code=302)
    resp.set_cookie('profile_message', message, httponly=True, )
    return resp


def run_ocr_on_image(image: UploadFile) -> dict:
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()

    content = image.file.read()
    image = vision.Image(content=content)

    response = client.text_detection(image=image)

    if not response.text_annotations:
        return {"text": ""}

    return {
        "text": response.text_annotations[0].description
    }



@app.post('/upload')
async def upload_receipt(request: Request, 
                         name: str = Form(...), 
                         date: Optional[str] = Form(None), 
                         image: UploadFile = File(...),
                         action: str = Form("save"),
                         db = Depends(get_db)):
    # require a logged-in user
    user_id, username = get_verified_cookies(request)
    if not user_id or not username:
        return templates.TemplateResponse('login.html', {"request": request, "message": "Please log in before uploading."})
    
    user_id = int(user_id)

    if not name:
        return JSONResponse({"error": "name is required"}, status_code=422)
    
    # Get user email and phone from database
    user_data = get_user_db(db, username)
    user_email = user_data.email if user_data else ''
    user_phone = user_data.phone if user_data else ''

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

    # Support multiple insurance companies sent to
    sent_to_list = []
    for key in form:
        if key.startswith('sent_to_insurance_'):
            company = form.get(key, '').strip()
            if company:
                sent_to_list.append(company)
    sent_to_insurance = '|'.join(sent_to_list) if sent_to_list else ''
    
    # Support multiple refunds (JSON format)
    refund_details_list = []
    for key in form:
        if key.startswith('refund_company_'):
            idx = key.replace('refund_company_', '')
            company = form.get(f'refund_company_{idx}', '').strip()
            amount = form.get(f'refund_amount_{idx}', '').strip()
            if company and amount:
                refund_details_list.append({"company": company, "amount": amount})
    refund_details = json.dumps(refund_details_list) if refund_details_list else '[]'
    
    insurance_company = (form.get('insurance_company') or '').strip()
    account_username = (form.get('account_username') or username).strip()
    try:
        family_count = int(form.get('family_count')) if form.get('family_count') else 0
    except Exception:
        family_count = 0
    family_names = (form.get('family_names') or '').strip()
    how_work = (form.get('how_work') or '').strip()

    # build Cloudinary context string with user_id and refund stage
    def _safe(v: str) -> str:
        return re.sub(r"[|\n\r]", '', (v or '').strip())

    # Determine refund stage
    refund_stage = "received"
    if refund_details_list:
        refund_stage = "reimbursed"
    elif sent_to_insurance:
        refund_stage = "processing"

    ctx_parts = [
        f"user_id={user_id}",
        f"username={_safe(username)}",
        f"refund_stage={_safe(refund_stage)}",
        f"refund_details={_safe(refund_details[:100])}"
    ]
    if user_email:
        ctx_parts.append(f"email={_safe(user_email)}")
    if user_phone:
        ctx_parts.append(f"phone={_safe(user_phone)}")
    if sent_to_insurance:
        ctx_parts.append(f"sent_to_insurance={_safe(sent_to_insurance)}")
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

        ocr_result = None

        if action == "ocr":
            try:
                # IMPORTANT: rewind file, Cloudinary already consumed it
                await image.seek(0)

                # Call your OCR logic (Vision / LangGraph)
                ocr_result = run_ocr_on_image(image)

                logger.info(
                    f"OCR completed for user={username}, public_id={public_id}"
                )

            except Exception as e:
                logger.error(
                    f"OCR failed for user={username}, public_id={public_id}: {e}"
                )
                ocr_result = {"error": str(e)}


        logger.info(f'Image uploaded successfully: public_id={public_id}, user_id={user_id}, username={username}')
    except Exception as e:
        logger.error(f'Upload failed for user {username} (id={user_id}): {e}')
        # stay on UI and show error message
        msg = f"Upload failed: {e}"
        try:
            search_result = cloudinary.Search().expression(f"folder:uploads AND context.username:{username}").max_results(1).execute()
            count = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
        except Exception:
            count = 0
        return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": [], "name": name, "date": date_str, "count": count, "username": username})

    # Success: store metadata in SQLite and show index UI with success message
    msg = f"Uploaded: {result.get('public_id', public_id)}"
    try:
        search_result = cloudinary.Search().expression(f"folder:uploads AND context.username:{username}").max_results(1).execute()
        count = search_result.get('total_count') or search_result.get('total') or len(search_result.get('resources', []))
    except Exception:
        count = 0

    # save to sqlite
    rec = {
        'public_id': result.get('public_id', public_id),
        'user_id': user_id,
        'username': username,
        'name': name,
        'date': date_str,
        'sent_to_insurance': sent_to_insurance,
        'refund_details': refund_details,
        'insurance_company': insurance_company,
        'account_username': account_username,
        'family_count': family_count,
        'family_names': family_names,
        'how_work': how_work,
        'secure_url': result.get('secure_url'),
        'created_at': result.get('created_at')
    }
    try:
        db = SessionLocal()
        insert_receipt(db, rec)
    except Exception:
        pass

    # attach db copy to result so template can show values
    result['_db'] = rec

    return templates.TemplateResponse('index.html', 
                                      {"request": request, 
                                       "message": msg, 
                                       "results": [result], 
                                       "name": name, 
                                       "date": date_str, 
                                       "count": count, 
                                       "username": username,
                                       "ocr": ocr_result, })


@app.get('/search')
def search(request: Request, name: Optional[str] = None, date: Optional[str] = None, refunded: Optional[str] = None, sent_to_insurance: Optional[str] = None, insurance_company: Optional[str] = None):
    """Search uploaded images by name, date and metadata using Cloudinary Search API."""
    user_id, username = get_verified_cookies(request)
    if not user_id or not username:
        return RedirectResponse(url='/login', status_code=302)
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return RedirectResponse(url='/login', status_code=302)
    
    expr_parts = [f"folder:uploads", f"context.user_id:{user_id}"]

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

    # metadata filters stored in context string
    if refunded and refunded.lower() in ('yes', 'no'):
        expr_parts.append(f"context:'refund_stage=*{refunded}*'")

    if sent_to_insurance and sent_to_insurance.lower() in ('yes', 'no'):
        if sent_to_insurance.lower() == 'yes':
            expr_parts.append(f"context:'sent_to_insurance:*'")
        else:
            expr_parts.append(f"NOT context:'sent_to_insurance'")

    if insurance_company:
        safe_comp = re.sub(r'[^A-Za-z0-9_\- ]', '', insurance_company.strip())
        # wildcard match on company name inside context
        expr_parts.append(f"context:'insurance_company:*{safe_comp}*'")

    expr = " AND ".join(expr_parts)

    try:
        search_result = cloudinary.Search().expression(expr).max_results(100).execute()
        resources = search_result.get('resources', [])
    except Exception as e:
        return templates.TemplateResponse('index.html', {"request": request, "message": f"Search failed: {e}", "results": [], "username": username})

    # enrich results with DB metadata if available
    enriched = []
    db = SessionLocal()
    for r in resources:
        receipt = get_receipt_db(db, r.get('public_id'))
        if receipt:
            r['_db'] = receipt
        enriched.append(r)

    return templates.TemplateResponse('index.html', {"request": request, "results": enriched, "name": name, "date": date, "refunded": refunded, "sent_to_insurance": sent_to_insurance, "insurance_company": insurance_company, "username": username})


@app.post('/update')
def update_metadata(request: Request, public_id: str = Form(...), refunded: Optional[str] = Form(None), sent_to_insurance: Optional[str] = Form(None), insurance_company: Optional[str] = Form(None)):
    """Update metadata (context) for an existing image."""
    user_id, username = get_verified_cookies(request)
    if not user_id or not username:
        return RedirectResponse(url='/login', status_code=302)
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return RedirectResponse(url='/login', status_code=302)
    
    # Verify user owns this receipt
    db = SessionLocal()
    db_rec = get_receipt_db(db, public_id)
    if not db_rec or db_rec.get('user_id') != user_id:
        return JSONResponse({"error": "Access denied"}, status_code=403)
    
    try:
        # Parse refund details from form (multiple refunds)
        refund_details_list = []
        refund_stage = "received"
        
        # Check if any refunds in form
        sent_to_list = []
        if sent_to_insurance and sent_to_insurance.lower() in ('yes', 'on', 'true'):
            refund_stage = "processing"
        
        insurance_val = (insurance_company or '').strip()
        if insurance_val:
            # Simple update for now - in full implementation, would parse multiple refunds
            refund_details_list.append({"company": insurance_val, "amount": "0"})
            refund_stage = "reimbursed"
        
        refund_details = json.dumps(refund_details_list)
        sent_val = sent_to_insurance if sent_to_insurance and sent_to_insurance.lower() in ('yes', 'on', 'true') else ''

        def _safe(v: str) -> str:
            return re.sub(r"[|\n\r]", '', (v or '').strip())

        ctx_parts = [
            f"username={_safe(username)}",
            f"refund_stage={_safe(refund_stage)}",
            f"refund_details={_safe(refund_details[:100])}"
        ]
        if sent_val:
            ctx_parts.append(f"sent_to_insurance={_safe(sent_val)}")
        if insurance_val:
            ctx_parts.append(f"insurance_company={_safe(insurance_val)}")
        
        context_str = '|'.join(ctx_parts)
        cloudinary.uploader.add_context(context_str, public_id=public_id)
        
        # also update sqlite
        update_fields = {
            'sent_to_insurance': sent_val,
            'refund_details': refund_details,
            'insurance_company': insurance_val
        }
        update_receipt_db(db, public_id, update_fields)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # fetch updated resource
    try:
        res = cloudinary.api.resource(public_id)
    except Exception:
        res = None

    msg = f"Updated metadata for {public_id}"
    return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": [res] if res else [], "count": 0, "username": username})


@app.post('/delete')
def delete_image(request: Request, public_id: str = Form(...)):
    """Delete an image by its Cloudinary public_id."""
    user_id, username = get_verified_cookies(request)
    if not user_id or not username:
        return RedirectResponse(url='/login', status_code=302)
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return RedirectResponse(url='/login', status_code=302)
    
    # Verify user owns this receipt
    db = SessionLocal()
    db_rec = get_receipt_db(db, public_id)
    if not db_rec or db_rec.get('user_id') != user_id:
        logger.warning(f'Unauthorized delete attempt: public_id={public_id}, user_id={user_id}, username={username}')
        return JSONResponse({"error": "Access denied"}, status_code=403)
    
    try:
        res = cloudinary.uploader.destroy(public_id, resource_type='image')
        logger.info(f'Image deleted successfully: public_id={public_id}, user_id={user_id}, username={username}')
    except Exception as e:
        logger.error(f'Delete failed for {public_id} by user {username} (id={user_id}): {e}')
        return templates.TemplateResponse('index.html', {"request": request, "message": f"Delete failed: {e}", "results": [], "username": username})

    result_flag = res.get('result')
    if result_flag in ('ok', 'deleted'):
        msg = f"Deleted {public_id}"
    else:
        msg = f"Delete returned: {result_flag}"

    # remove from sqlite as well
    try:
        delete_receipt_db(db, public_id)
    except Exception:
        pass

    return templates.TemplateResponse('index.html', {"request": request, "message": msg, "results": [], "username": username})



def insert_user(db, username, phone, email, family_members, insurance_companies):
    logger.info(f"Inserting user: {username}")
    user = db.query(User).filter(User.username == username).first()

    if user:
        user.phone = phone
        user.email = email
        user.family_members = family_members
        user.insurance_companies = insurance_companies
    else:
        user = User(
            username=username,
            phone=phone,
            email=email,
            family_members=family_members,
            insurance_companies=insurance_companies,
            created_at=datetime.utcnow()
        )
        db.add(user)
        logger.info("User added to session")

    return user

def get_user_db(db, username):
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db, user_id):
    return db.query(User).filter(User.user_id == user_id).first()

def insert_receipt(db, rec: dict):
    receipt = db.query(Receipt).filter(
        Receipt.public_id == rec["public_id"]
    ).first()

    if receipt:
        for k, v in rec.items():
            setattr(receipt, k, v)
    else:
        receipt = Receipt(**rec)
        db.add(receipt)

    db.commit()
    return receipt

def update_receipt_db(db, public_id: str, fields: dict):
    receipt = db.query(Receipt).filter(
        Receipt.public_id == public_id
    ).first()

    if not receipt:
        return None

    for k, v in fields.items():
        setattr(receipt, k, v)

    db.commit()
    return receipt

def delete_receipt_db(db, public_id: str):
    receipt = db.query(Receipt).filter(
        Receipt.public_id == public_id
    ).first()

    if receipt:
        db.delete(receipt)
        db.commit()

def get_receipt_db(db, public_id: str):
    return db.query(Receipt).filter(
        Receipt.public_id == public_id
    ).first()

def update_user_db(db, username: str, fields: dict):
    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return None

    for k, v in fields.items():
        setattr(user, k, v)

    db.commit()
    return user

@app.post("/users")
def create_user(username: str, db=Depends(get_db)):
    return insert_user(db, username, None, None, None, None)