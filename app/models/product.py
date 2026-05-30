"""
Ürün modeli.
İki tip ürün var:
- base: Ana ürün (Belçika Waffle, Klasik Pancake) - kendi fiyatı var
- ingredient: Malzeme (Çilek, Çikolata) - fiyatı kategori kuralından gelir
"""
from datetime import datetime
from app import db


class Product(db.Model):
    """Ürün - base veya ingredient"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    
    # 'base' veya 'ingredient'
    product_type = db.Column(db.String(20), nullable=False)
    
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # BASE için: tabağın temel fiyatı (örn: 180 TL)
    # INGREDIENT için: genelde 0 (kural belirler), ama özel fiyat da olabilir
    base_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=10.00)
    
    image_url = db.Column(db.Text)
    
    # Stok (opsiyonel)
    stock_quantity = db.Column(db.Integer)
    track_stock = db.Column(db.Boolean, default=False)
    
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def is_base(self):
        return self.product_type == 'base'
    
    def is_ingredient(self):
        return self.product_type == 'ingredient'
    
    def __repr__(self):
        return f'<Product {self.name} ({self.product_type}) {self.base_price}TL>'