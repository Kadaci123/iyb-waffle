"""
Kategori modelleri.
İki tip kategori var:
- base: Ana ürün kategorisi (Waffleler, Pancakeler)
- ingredient: Malzeme kategorisi (Çikolatalar, Meyveler)
"""
from datetime import datetime
from app import db


class Category(db.Model):
    """Ürün kategorisi"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'))
    
    name = db.Column(db.String(255), nullable=False)
    # 'base' veya 'ingredient'
    category_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))  # Emoji veya icon class
    image_url = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # İlişkiler
    products = db.relationship('Product', backref='category', lazy=True, cascade='all, delete-orphan')
    rule = db.relationship('CategoryRule', backref='category', uselist=False, cascade='all, delete-orphan')
    
    def is_base(self):
        return self.category_type == 'base'
    
    def is_ingredient(self):
        return self.category_type == 'ingredient'
    
    def __repr__(self):
        return f'<Category {self.name} ({self.category_type})>'


class CategoryRule(db.Model):
    """
    Kategori için bedava ürün kuralı.
    Sadece 'ingredient' tipindeki kategorilerde anlamlı.
    Örnek: Çikolatalar kategorisi → 2 tanesi bedava, 3.sü +20 TL
    """
    __tablename__ = 'category_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Kaç tane bedava
    free_count = db.Column(db.Integer, default=0)
    # Bedava limitten sonra her bir malzemenin ek fiyatı
    extra_price = db.Column(db.Numeric(10, 2), default=0)
    # Maksimum kaç tane seçilebilir (None = sınırsız)
    max_count = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CategoryRule cat={self.category_id} free={self.free_count} extra={self.extra_price}>'