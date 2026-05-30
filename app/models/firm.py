"""
Firma (Kafe) ve Şube modelleri.
Her firma birden fazla şubeye sahip olabilir.
"""
from datetime import datetime
from app import db


class Firm(db.Model):
    """Kafe firması - SaaS kiracısı (tenant)"""
    __tablename__ = 'firms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    tax_id = db.Column(db.String(50), unique=True)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Türkiye')
    
    # Abonelik bilgileri (SaaS için)
    subscription_plan = db.Column(db.String(50), default='trial')
    subscription_expires_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # İlişkiler (relationships)
    branches = db.relationship('Branch', backref='firm', lazy=True, cascade='all, delete-orphan')
    users = db.relationship('User', backref='firm', lazy=True)
    
    def __repr__(self):
        return f'<Firm {self.name}>'


class Branch(db.Model):
    """Şube - bir firmanın fiziksel lokasyonu"""
    __tablename__ = 'branches'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    qr_code_prefix = db.Column(db.String(50), unique=True)
    
    # Vergi ve para birimi ayarları
    default_tax_rate = db.Column(db.Numeric(5, 2), default=10.00)
    currency = db.Column(db.String(10), default='TRY')
    
    # Müşteri ekranı tema rengi
    theme_color = db.Column(db.String(20), default='#FF6B6B')
    logo_url = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # İlişkiler
    tables = db.relationship('Table', backref='branch', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Branch {self.name}>'