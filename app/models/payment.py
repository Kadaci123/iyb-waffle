"""
Ödeme ve kasa vardiyası modelleri.
"""
from datetime import datetime
from app import db


class Payment(db.Model):
    """Sipariş ödemesi"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    cash_session_id = db.Column(db.Integer, db.ForeignKey('cash_sessions.id', ondelete='SET NULL'))
    
    # Yöntem: cash, credit_card, debit_card, online, bank_transfer
    payment_method = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transaction_id = db.Column(db.String(255))
    
    # Durum: pending, completed, failed, refunded
    status = db.Column(db.String(50), default='completed')
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.amount}TL via {self.payment_method}>'


class CashSession(db.Model):
    """Kasa vardiyası - kasiyer açar, gün sonunda kapatır"""
    __tablename__ = 'cash_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Açılış
    opening_amount = db.Column(db.Numeric(10, 2), default=0)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Kapanış
    closing_amount = db.Column(db.Numeric(10, 2))
    expected_amount = db.Column(db.Numeric(10, 2))
    difference = db.Column(db.Numeric(10, 2))
    closed_at = db.Column(db.DateTime)
    
    # Vardiya özeti
    total_cash_sales = db.Column(db.Numeric(10, 2), default=0)
    total_card_sales = db.Column(db.Numeric(10, 2), default=0)
    total_online_sales = db.Column(db.Numeric(10, 2), default=0)
    total_orders = db.Column(db.Integer, default=0)
    
    # Durum: open, closed
    status = db.Column(db.String(50), default='open')
    notes = db.Column(db.Text)
    
    def is_open(self):
        return self.status == 'open'
    
    def __repr__(self):
        return f'<CashSession branch={self.branch_id} status={self.status}>'