from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    license_plate = Column(String(20), unique=True)
    price_per_day = Column(Float, nullable=False)
    image = Column(String(255), nullable=True)
    status = Column(String(50), default="available") 
    
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="products")
    bookings = relationship("Booking", back_populates="product")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String(200), nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20), nullable=False)
    driver_license = Column(String(50), nullable=True)
    password = Column(String(255), nullable=False)
    
    bookings = relationship("Booking", back_populates="user")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_no = Column(String(50), unique=True)
    booking_date = Column(DateTime, default=datetime.now)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_days = Column(Integer)
    amount_total = Column(Float)
    state = Column(String(50), default="pending")

    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    user = relationship("User", back_populates="bookings")
    product = relationship("Product", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False)


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    payment_method = Column(String(50))
    payment_status = Column(String(50))
    paid_at = Column(DateTime, default=datetime.now)
    slip_image = Column(String(255), nullable=True)
    
    booking = relationship("Booking", back_populates="payment")