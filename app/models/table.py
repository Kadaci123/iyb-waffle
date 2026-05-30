"""
Masa modeli.
Her şubenin fiziksel masaları var, her birinin QR kodu var.
"""
from datetime import datetime
from app import db


class Table(db.Model):
    """Kafe masası"""
    __tablename__ = 'tables'
    
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    
    table_number = db.Column(db.String(50), nullable=False)
    qr_code = db.Column(db.String(255), unique=True)
    capacity = db.Column(db.Integer, default=4)
    location = db.Column(db.String(100))  # "İç salon", "Bahçe", "Teras"
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Aynı şubede aynı masa numarası iki kere olamaz
    __table_args__ = (
        db.UniqueConstraint('branch_id', 'table_number', name='_branch_table_uc'),
    )
    
    def __repr__(self):
        return f'<Table #{self.table_number} (branch={self.branch_id})>'