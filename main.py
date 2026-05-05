from fastapi import Depends, FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

import shutil
import os
import re
from datetime import datetime

# models & database
import models
from models import Booking, Payment, Product, Category
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "score": 76,
            "activities": ["Running", "Football", "Badminton"],
        }
    )

# ================= PRODUCTS =================
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/products", response_class=HTMLResponse)
def product_list(request: Request, search: str = ""):
    db = SessionLocal()
    try:
        if search:
            products = db.query(Product).filter(Product.name.ilike(f"%{search}%")).all()
        else:
            products = db.query(Product).all()
            
        return templates.TemplateResponse(
            request,
            "cars.html",
            {
                "request": request,
                "products": products,
                "search_query": search
            }
        )
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
        "payment_upload.html",
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

# ================= BOOKING SYSTEM =================
@app.get("/bookings/create/{id}", response_class=HTMLResponse)
def booking_page(request: Request, id: int, db: Session = Depends(get_db)):
    product = db.get(Product, id)
    if not product:
        return RedirectResponse("/products", status_code=303)
        
    return templates.TemplateResponse(
        request,
        "booking.html", 
        {"request": request, "product": product}
    )

@app.post("/bookings/confirm", response_class=HTMLResponse)
def confirm_booking(
    request: Request,
    product_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    db: Session = Depends(get_db)
):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse("/login", status_code=303)

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    days = (end - start).days + 1
    if days < 1:
        days = 1

    product = db.get(Product, product_id)
    total_amount = days * product.price_per_day

    booking_no = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"

    new_booking = Booking(
        booking_no=booking_no,
        start_date=start,
        end_date=end,
        total_days=days,
        amount_total=total_amount,
        state="pending",
        user_id=user_session["id"],
        product_id=product_id
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return templates.TemplateResponse(request,
        "booking.html", 
        {
            "request": request,
            "success_id": new_booking.booking_no,
            "product": product
        }
    )

# ================= ORDERS & CANCELLATION =================
@app.get("/orders", response_class=HTMLResponse)
def my_orders(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse("/login", status_code=303)

    bookings = db.query(Booking).filter(
        Booking.user_id == user_session["id"]
    ).order_by(Booking.booking_date.desc()).all()

    return templates.TemplateResponse(
        request,
        "orders.html", 
        {"request": request, "bookings": bookings}
    )

@app.get("/bookings/cancel/{id}")
def cancel_booking(request: Request, id: int, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse("/login", status_code=303)

    booking = db.get(Booking, id)
    if booking and booking.user_id == user_session["id"]:
        booking.state = "cancelled"
        db.commit()

    return RedirectResponse("/orders", status_code=303)

# ================= PAYMENT SYSTEM =================
@app.get("/bookings/payment/{booking_id}", response_class=HTMLResponse)
def payment_page(request: Request, booking_id: int, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse("/login", status_code=303)

    booking = db.get(Booking, booking_id)
    
    if not booking or booking.user_id != user_session["id"]:
        return RedirectResponse("/orders", status_code=303)

    return templates.TemplateResponse(
        request,
        "payment.html", 
        {"request": request, "booking": booking}
    )

@app.post("/bookings/payment/{booking_id}")
def upload_payment(
    request: Request,
    booking_id: int,
    slip: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user_session = request.session.get("user")
    if not user_session:
        return RedirectResponse("/login", status_code=303)

    booking = db.get(Booking, booking_id)
    if not booking or booking.user_id != user_session["id"]:
        return RedirectResponse("/orders", status_code=303)

    if slip and slip.filename:
        filename = f"slip_{booking.booking_no}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{slip.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(slip.file, buffer)

        new_payment = Payment(
            booking_id=booking.id,
            payment_method="Transfer",
            payment_status="Success",
            slip_image=filename
        )
        db.add(new_payment)

        booking.state = "confirmed"

        db.commit()

    return RedirectResponse("/orders", status_code=303)

# ================= LOGIN =================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user"):
        if request.session.get("user").get("is_admin"):
            return RedirectResponse("/admin/bookings", status_code=303)
        return RedirectResponse("/", status_code=303)
        
    return templates.TemplateResponse(
        request, 
        "login.html", 
        {"request": request}
    )

@app.post("/login")
def login_process(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == username).first()

    if user and user.password == password: 
        is_admin = True if user.email == "admin@admin.com" else False
        
        request.session["user"] = {
            "id": user.id, 
            "name": user.fullname,
            "is_admin": is_admin
        }
        
        if is_admin:
            return RedirectResponse("/admin/bookings", status_code=303)
            
        return RedirectResponse("/", status_code=303)
    

    return templates.TemplateResponse(
        request, 
        "login.html", 
        {"request": request, "error": "Email หรือรหัสผ่านไม่ถูกต้อง"}
    )

# ================= REGISTER =================
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
    request=request, 
    name="register.html", 
    context={"request": request}
    )

@app.post("/register")
def register_process(
    request: Request, 
    name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...),
    phone: str = Form(...),
    db: Session = Depends(get_db)
):
    user_exists = db.query(models.User).filter(models.User.email == email).first()
    if user_exists:
        return templates.TemplateResponse("register.html", {"request": request, "error": "อีเมลนี้ถูกใช้งานแล้ว"})

    new_user = models.User(fullname=name, email=email, password=password, phone=phone)
    db.add(new_user)
    db.commit()
    return RedirectResponse("/login", status_code=303)

# ================= LOGOUT =================
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ================= ADMIN SYSTEM =================
@app.get("/admin/bookings", response_class=HTMLResponse)
def admin_booking_list(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    bookings = db.query(Booking).order_by(Booking.booking_date.desc()).all()

    return templates.TemplateResponse(
        request,
        "admin/booking.html",
        {"request": request, "bookings": bookings}
    )

@app.get("/admin/users", response_class=HTMLResponse)
def admin_user_list(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    users = db.query(models.User).order_by(models.User.id.desc()).all()
    
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {"request": request, "users": users}
    )

@app.get("/admin/users/delete/{id}")
def delete_user(request: Request, id: int, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    user = db.get(models.User, id)
    if user and user.email != "admin@admin.com":
        db.delete(user)
        db.commit()

    return RedirectResponse("/admin/users", status_code=303)


@app.get("/admin/cars", response_class=HTMLResponse)
def admin_car_list(request: Request, search: str = "", db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    if search:
        products = db.query(Product).filter(Product.name.ilike(f"%{search}%")).all()
    else:
        products = db.query(Product).all()

    return templates.TemplateResponse(
        request,
        "admin/cars.html",
        {"request": request, "products": products, "search_query": search}
    )

@app.get("/admin/cars/create", response_class=HTMLResponse)
def admin_car_create_form(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    categories = db.query(Category).all()
    return templates.TemplateResponse(
        request,
        "admin/car_edit.html",
        {"request": request, "categories": categories, "product": None}
    )

@app.post("/admin/cars/create")
def admin_create_car(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    filename = None
    if image and image.filename:
        filename = image.filename
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

    product = Product(
        name=name,
        price_per_day=price,
        category_id=category_id,
        image=filename
    )
    db.add(product)
    db.commit()

    return RedirectResponse("/admin/cars", status_code=303)

@app.get("/admin/cars/edit/{id}", response_class=HTMLResponse)
def admin_car_edit_form(request: Request, id: int, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    product = db.get(Product, id)
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        request,
        "admin/car_edit.html",
        {"request": request, "product": product, "categories": categories}
    )

@app.post("/admin/cars/edit/{id}")
def admin_update_car(
    request: Request,
    id: int,
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    product = db.get(Product, id)
    product.name = name
    product.price_per_day = price
    product.category_id = category_id

    if image and image.filename:
        filename = image.filename
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        product.image = filename

    db.commit()
    return RedirectResponse("/admin/cars", status_code=303)

@app.get("/admin/cars/delete/{id}")
def admin_delete_car(request: Request, id: int, db: Session = Depends(get_db)):
    user_session = request.session.get("user")
    if not user_session or not user_session.get("is_admin"):
        return RedirectResponse("/", status_code=303)

    product = db.get(Product, id)
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse("/admin/cars", status_code=303)


