from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(200))
    password_hash = db.Column(db.String(255))
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    profile_picture = db.Column(db.String(500))
    
    subscription_status = db.Column(db.String(50), default='free')
    subscription_plan = db.Column(db.String(50), default='starter')
    stripe_customer_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    invoices = db.relationship('Invoice', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    stripe_invoice_id = db.Column(db.String(100), unique=True, nullable=True)
    
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(50), default='pending')
    
    billing_date = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    invoice_url = db.Column(db.String(500))
    pdf_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'
