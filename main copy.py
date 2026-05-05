from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import shutil
import os
import re
from datetime import datetime

# models & database
import models
from models import Product, Category, Order
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Session
app.add_middleware(SessionMiddleware, secret_key="secret123")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Router
from api import router
app.include_router(router)

# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "message": "Hello World",
            "score": 76,
            "activities": ["Running", "Football", "Badminton"],
        }
    )

# ================= PRODUCTS =================
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/products", response_class=HTMLResponse)
def product_list(request: Request):
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        return templates.TemplateResponse(
            request,
            "product_list.html",
            {
                "request": request,
                "products": products
            }
        )
    finally:
        db.close()

@app.get("/products/create", response_class=HTMLResponse)
def create_form(request: Request):
    db = SessionLocal()
    try:
        categories = db.query(Category).all()
        return templates.TemplateResponse(
            request,
            "product_form.html",
            {
                "request": request,
                "categories": categories
            }
        )
    finally:
        db.close()

@app.post("/products/create")
def create_product(
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    image: UploadFile = File(None)
):
    db = SessionLocal()

    filename = None
    if image and image.filename:
        filename = image.filename
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

    product = Product(
        name=name,
        price=price,
        category_id=category_id,
        image=filename
    )

    db.add(product)
    db.commit()
    db.close()

    return RedirectResponse("/products", status_code=303)

@app.get("/products/edit/{id}", response_class=HTMLResponse)
def edit_form(request: Request, id: int):
    db = SessionLocal()
    try:
        product = db.get(Product, id)
        categories = db.query(Category).all()
        return templates.TemplateResponse(
            request,
            "product_form.html",
            {
                "request": request,
                "product": product,
                "categories": categories
            }
        )
    finally:
        db.close()

@app.post("/products/edit/{id}")
def update_product(
    id: int,
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    image: UploadFile = File(None)
):
    db = SessionLocal()
    product = db.get(Product, id)

    product.name = name
    product.price = price
    product.category_id = category_id

    if image and image.filename:
        filename = image.filename
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        product.image = filename

    db.commit()
    db.close()
    return RedirectResponse("/products", status_code=303)

@app.get("/products/delete/{id}")
def delete_product(id: int):
    db = SessionLocal()
    product = db.get(Product, id)
    db.delete(product)
    db.commit()
    db.close()
    return RedirectResponse("/products", status_code=303)

# ================= SEARCH =================
@app.get("/products/search", response_class=HTMLResponse)
def product_search(request: Request):
    return templates.TemplateResponse(
        request,
        "product_search.html",
        {"request": request}
    )

@app.get("/api/products/search")
def product_search_api(search: str = ""):
    db = SessionLocal()
    try:
        return db.query(Product).filter(
            Product.name.like(f"%{search}%")
        ).all()
    finally:
        db.close()

# ================= SERVER TIME =================
@app.get("/api/servertime")
def get_datetime():
    return {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ================= OCR =================
import easyocr
reader = easyocr.Reader(['th', 'en'])

@app.get("/pvs/upload", response_class=HTMLResponse)
def pvs_upload(request: Request):
    return templates.TemplateResponse(
        request,
        "pvs_upload.html",
        {"request": request}
    )

@app.post("/api/pvs/upload-ocr")
async def upload_ocr(file: UploadFile = File(...)):
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    result = process_ocr(filepath)
    return result

def process_ocr(image_path):
    result = reader.readtext(image_path)
    text = " ".join([r[1] for r in result])

    amount_match = re.search(r'\d+\.\d{2}', text)
    amount = float(amount_match.group()) if amount_match else 0

    date_match = parse_thai_datetime(text)

    return {
        "text": text,
        "amount": amount,
        "datetime": date_match,
    }

def parse_thai_datetime(text):
    thai_months = {
        "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3,
        "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
        "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9,
        "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12
    }

    match = re.search(
        r'(\d{1,2})\s+([^\s]+)\s+(\d{2})(?:.*?(\d{1,2}):(\d{2}))?',
        text
    )

    if not match:
        raise ValueError("Invalid date format")

    day = int(match.group(1))
    month = thai_months.get(match.group(2), 1)
    year_ad = int(match.group(3)) + 2500 - 543

    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    hour = int(time_match.group(1))
    minute = int(time_match.group(2))

    return datetime(year_ad, month, day, hour, minute)

# ================= ORDERS =================
@app.get("/api/pvs/orders")
def get_orders():
    db = SessionLocal()
    try:
        orders = db.query(Order).all()
        return [
            {
                "id": o.id,
                "order_no": o.order_no,
                "amount_total": o.amount_total,
                "order_date": str(o.order_date),
                "state": o.state
            }
            for o in orders
        ]
    finally:
        db.close()

# ================= LOGIN =================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request}
    )

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "1234":
        request.session["user"] = username
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "error": "Login failed"
        }
    )

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)