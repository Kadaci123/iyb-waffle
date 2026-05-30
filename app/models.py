from datetime import datetime
from flask_login import UserMixin
from app import db


class Firm(db.Model):
    __tablename__ = 'firms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    tax_id = db.Column(db.String(50), unique=True)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Türkiye')
    subscription_plan = db.Column(db.String(50), default='trial')
    subscription_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class Branch(db.Model):
    __tablename__ = 'branches'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    qr_code_prefix = db.Column(db.String(50), unique=True)
    default_tax_rate = db.Column(db.Numeric(5, 2), default=10.00)
    currency = db.Column(db.String(10), default='TRY')
    theme_color = db.Column(db.String(20), default='#FF6B6B')
    logo_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='SET NULL'))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'))
    name = db.Column(db.String(255), nullable=False)
    category_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))
    image_url = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    products = db.relationship('Product', backref='category', lazy=True)
    rule = db.relationship('CategoryRule', backref='category', uselist=False)


class CategoryRule(db.Model):
    __tablename__ = 'category_rules'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False, unique=True)
    free_count = db.Column(db.Integer, default=0)
    extra_price = db.Column(db.Numeric(10, 2), default=0)
    max_count = db.Column(db.Integer)
    use_own_price = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    product_type = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=10.00)
    image_url = db.Column(db.Text)
    stock_quantity = db.Column(db.Integer)
    track_stock = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_out_of_stock = db.Column(db.Boolean, default=False)
    # 🎁 KAMPANYA: Bu ürün başka bir ürünün malzeme kurallarını kullansın
    # (örn. "Waffle+Çay Menüsü" → Klasik Waffle'ın malzeme ekranını kullansın)
    copy_rules_from_product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='SET NULL'))
    # 🎁 Zorunlu seçim grupları (kampanya ürünleri için)
    option_groups = db.relationship('ProductOptionGroup', backref='product', cascade='all, delete-orphan', lazy='joined', order_by='ProductOptionGroup.display_order')


class Table(db.Model):
    __tablename__ = 'tables'
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    table_number = db.Column(db.String(50), nullable=False)
    qr_code = db.Column(db.String(255), unique=True)
    capacity = db.Column(db.Integer, default=4)
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False)
    order_number = db.Column(db.String(50))
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_price = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(50), default='pending')
    payment_status = db.Column(db.String(50), default='unpaid')
    customer_note = db.Column(db.Text)
    customer_name = db.Column(db.String(255))
    customer_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    is_printed = db.Column(db.Boolean, default=False)
    printed_at = db.Column(db.DateTime)


class OrderPlate(db.Model):
    __tablename__ = 'order_plates'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    base_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    ingredients_total = db.Column(db.Numeric(10, 2), default=0)
    plate_total = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OrderPlateIngredient(db.Model):
    __tablename__ = 'order_plate_ingredients'
    id = db.Column(db.Integer, primary_key=True)
    order_plate_id = db.Column(db.Integer, db.ForeignKey('order_plates.id', ondelete='CASCADE'), nullable=False)
    ingredient_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=0)
    is_free = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AppSetting(db.Model):
    """Genel ayarlar: PIN'ler, e-posta vb."""
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# 🎁 ZORUNLU SEÇİM SİSTEMİ (Kampanya ürünleri için)
# ============================================================
class ProductOptionGroup(db.Model):
    """Bir ürüne bağlı zorunlu seçim grubu.
    Örnek: 'Waffle + Çay Menüsü' ürününde 'İçeceğinizi Seçin' grubu."""
    __tablename__ = 'product_option_groups'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(20))
    min_select = db.Column(db.Integer, default=1)
    max_select = db.Column(db.Integer, default=1)
    is_required = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    # 🎁 Grup türü:
    # 'free_addon'  = Bedava ek (Çay/Su) — fiyat etkilemez
    # 'main_waffle' = Ana waffle seçimi (Klasik/Çikolatalı) — seçilen waffle'ın malzemeleri yüklenir
    group_type = db.Column(db.String(20), default='free_addon')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('ProductOptionItem', backref='group', cascade='all, delete-orphan', lazy='joined', order_by='ProductOptionItem.display_order')


class ProductOptionItem(db.Model):
    """Grup içindeki seçenekler. Çay, Su, Kola gibi."""
    __tablename__ = 'product_option_items'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('product_option_groups.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    extra_price = db.Column(db.Numeric(10, 2), default=0)
    display_order = db.Column(db.Integer, default=0)
    
    product = db.relationship('Product', foreign_keys=[product_id])


class OrderPlateOption(db.Model):
    """Sipariş anında müşterinin seçtiği zorunlu seçim sonucu.
    Örnek: 'İçeceğinizi Seçin' → 'Çay' (0 TL)"""
    __tablename__ = 'order_plate_options'
    id = db.Column(db.Integer, primary_key=True)
    order_plate_id = db.Column(db.Integer, db.ForeignKey('order_plates.id', ondelete='CASCADE'), nullable=False)
    group_name = db.Column(db.String(255))
    selected_product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    selected_name = db.Column(db.String(255))
    extra_price = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    selected_product = db.relationship('Product', foreign_keys=[selected_product_id])


OrderPlate.base_product = db.relationship('Product', foreign_keys=[OrderPlate.base_product_id])
OrderPlate.ingredients = db.relationship('OrderPlateIngredient', backref='plate', cascade='all, delete-orphan')
OrderPlate.options = db.relationship('OrderPlateOption', backref='plate', cascade='all, delete-orphan')
OrderPlateIngredient.ingredient = db.relationship('Product', foreign_keys=[OrderPlateIngredient.ingredient_product_id])
Order.plates = db.relationship('OrderPlate', backref='order', cascade='all, delete-orphan')
Order.table = db.relationship('Table', backref='orders')