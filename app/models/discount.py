"""
İndirim / promosyon kodu modeli.
"""
from datetime import datetime
from app import db


class Discount(db.Model):
    """İndirim kodu - örnek: HOSGELDIN10 → %10 indirim"""
    __tablename__ = 'discounts'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'))
    
    code = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Tip: percentage (yüzde) veya fixed_amount (sabit TL)
    discount_type = db.Column(db.String(50), nullable=False)
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    
    min_order_amount = db.Column(db.Numeric(10, 2), default=0)
    max_uses = db.Column(db.Integer)
    used_count = db.Column(db.Integer, default=0)
    
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Discount {self.code} {self.discount_value}{"%" if self.discount_type == "percentage" else "TL"}>'