from database import SessionLocal, engine, Base
from models import Category, Product, User, Booking, Payment
from datetime import datetime, timedelta

db = SessionLocal()

def reset_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

def run_seed():
    cat_suv = Category(name='SUV', description='รถอเนกประสงค์ ลุยได้ทุกที่')
    cat_sedan = Category(name='Sedan', description='รถเก๋ง 4 ประตู ขับสบายในเมือง')
    cat_van = Category(name='Van', description='รถตู้สำหรับครอบครัวหรือหมู่คณะ')
    cat_luxury = Category(name='Luxury', description='รถหรูระดับพรีเมียม')
    cat_sport = Category(name='Sport', description='รถสปอร์ต ขับสนุก อัตราเร่งเร้าใจ')
    
    db.add_all([cat_suv, cat_sedan, cat_van, cat_luxury, cat_sport])
    db.commit()


# ================= Test =================
    # p1 = Product(name='Toyota Fortuner', license_plate='กข-1234', price_per_day=2500, category_id=cat_suv.id, status='available')
    # p2 = Product(name='Honda Civic', license_plate='รย-999', price_per_day=1500, category_id=cat_sedan.id, status='available')
    # p3 = Product(name='Toyota Alphard', license_plate='ตต-8888', price_per_day=4500, category_id=cat_van.id, status='available')
    # p4 = Product(name='BMW 5 Series', license_plate='หรู-1', price_per_day=5500, category_id=cat_luxury.id, status='available')
    # p5 = Product(name='Porsche 911 Carrera', license_plate='สป-911', price_per_day=12000, category_id=cat_sport.id, status='available')
    # p6 = Product(name='Mazda 2', license_plate='งง-555', price_per_day=1000, category_id=cat_sedan.id, status='available')
    
    # db.add_all([p1, p2, p3, p4, p5, p6])
    # db.commit()
# ================= END_Test =================

    print("Seeding Users...")
    u_admin = User(
        fullname='System Admin', 
        email='admin@admin.com', 
        phone='0999999999',
        
        password='1234'
    )
    u1 = User(
        fullname='สมชาย โครตซิ่ง', 
        email='somchai@email.com', 
        phone='0812345678',
        
        password='1234'
    )
    u2 = User(
        fullname='สมศรี สตรีทอง', 
        email='somsri@email.com', 
        phone='0898765432',
        
        password='1234'
    )

    u3 = User(
        fullname='Kitt_Kitn', 
        email='68112444@dpu.ac.th', 
        phone='0981234567',
        
        password='68112444'
    )

    u4 = User(
        fullname='pan_akarapon', 
        email='68113440@dpu.ac.th', 
        phone='0891234567',
        
        password='68113440'
    )
    
    db.add_all([u_admin, u1, u2, u3, u4])
    db.commit()

    now = datetime.now()
    
    b1 = Booking(
        booking_no="BK20260401001",
        user_id=u1.id,
        product_id=p2.id, # Honda Civic
        booking_date=now - timedelta(days=2),
        start_date=now + timedelta(days=5),
        end_date=now + timedelta(days=7),
        total_days=3,
        amount_total=4500, # 1500 * 3
        state="confirmed"
    )
    db.add(b1)
    db.commit()
    
    pay1 = Payment(
        booking_id=b1.id,
        payment_method="Transfer",
        payment_status="Success",
        paid_at=now - timedelta(days=1),
        slip_image=None
    )
    db.add(pay1)

    b2 = Booking(
        booking_no="BK20260401002",
        user_id=u2.id,
        product_id=p3.id,
        booking_date=now - timedelta(hours=5),
        start_date=now + timedelta(days=10),
        end_date=now + timedelta(days=11),
        total_days=2,
        amount_total=9000,
        state="pending"
    )
    
    b3 = Booking(
        booking_no="BK20260401003",
        user_id=u1.id,
        product_id=p5.id,
        booking_date=now - timedelta(days=10),
        start_date=now - timedelta(days=5),
        end_date=now - timedelta(days=3),
        total_days=3,
        amount_total=36000,
        state="cancelled"
    )

    db.add_all([b2, b3])
    db.commit()

if __name__ == "__main__":
    reset_database()
    run_seed()
    db.close()