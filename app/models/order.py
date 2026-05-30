"""
Sipariş modelleri.
Order: Ana sipariş kaydı (masaya bağlı)
OrderPlate: Sipariş içindeki her bir tabak (waffle/pancake)
OrderPlateIngredient: Tabağa eklenen her bir malzeme
"""
from datetime import datetime
from app import db


class Order(db.Model):
    """Sipariş - bir masa bir sipariş verir, içinde birden fazla tabak olur"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id', ondelete='CASCADE'), nullable=False)
    
    order_number = db.Column(db.String(50))  # Günlük "001", "002"
    
    # Fiyat detayları
    subtotal = db.Column(db.Numeric(10, 2), default=0)  # KDV hariç
    tax_amount = db.Column(db.Numeric(10, 2), default=0)  # KDV
    discount_amount = db.Column(db.Numeric(10, 2), default=0)  # İndirim
    total_price = db.Column(db.Numeric(10, 2), default=0)  # Ödenecek toplam
    
    # Durum: pending, confirmed, preparing, ready, served, cancelled
    status = db.Column(db.String(50), default='pending')
    # Ödeme durumu: unpaid, partial, paid, refunded
    payment_status = db.Column(db.String(50), default='unpaid')
    
    customer_note = db.Column(db.Text)
    customer_name = db.Column(db.String(255))
    customer_phone = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # İlişkiler
    plates = db.relationship('OrderPlate', backref='order', lazy=True, cascade='all, delete-orphan')
    table = db.relationship('Table', backref='orders')
    
    def __repr__(self):
        return f'<Order #{self.id} table={self.table_id} total={self.total_price}TL>'


class OrderPlate(db.Model):
    """
    Tabak - siparişin içindeki her bir ürün.
    Örnek: Belçika Waffle + (Çilek, Sütlü Çikolata, Karamel) = 1 tabak
    """
    __tablename__ = 'order_plates'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    base_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Integer, default=1)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)  # O anki fiyat snapshot'ı
    ingredients_total = db.Column(db.Numeric(10, 2), default=0)
    plate_total = db.Column(db.Numeric(10, 2), default=0)  # base + ingredients
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    base_product = db.relationship('Product', foreign_keys=[base_product_id])
    ingredients = db.relationship('OrderPlateIngredient', backref='plate', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Plate order={self.order_id} base={self.base_product_id}>'


class OrderPlateIngredient(db.Model):
    """Tabağa eklenmiş bir malzeme"""
    __tablename__ = 'order_plate_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    order_plate_id = db.Column(db.Integer, db.ForeignKey('order_plates.id', ondelete='CASCADE'), nullable=False)
    ingredient_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    unit_price = db.Column(db.Numeric(10, 2), default=0)
    is_free = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişki
    ingredient = db.relationship('Product', foreign_keys=[ingredient_product_id])
    
    def __repr__(self):
        return f'<Ingredient plate={self.order_plate_id} product={self.ingredient_product_id} free={self.is_free}>'