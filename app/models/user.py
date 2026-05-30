"""
Kullanıcı modeli - tüm roller için.
Roller: super_admin, owner, manager, cashier, chef
"""
from datetime import datetime
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    """
    Sistem kullanıcısı.
    UserMixin sayesinde Flask-Login otomatik özellikler ekler (is_authenticated, get_id, vb.)
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='SET NULL'))
    
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    
    # Rol: super_admin, owner, manager, cashier, chef
    role = db.Column(db.String(50), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Yardımcı metodlar - rol kontrolü için
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_owner(self):
        return self.role == 'owner'
    
    def is_manager(self):
        return self.role == 'manager'
    
    def is_chef(self):
        return self.role == 'chef'
    
    def is_cashier(self):
        return self.role == 'cashier'
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'"""
Kullanıcı modeli - tüm roller için.
Roller: super_admin, owner, manager, cashier, chef
"""
from datetime import datetime
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    """
    Sistem kullanıcısı.
    UserMixin sayesinde Flask-Login otomatik özellikler ekler (is_authenticated, get_id, vb.)
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id', ondelete='CASCADE'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='SET NULL'))
    
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    
    # Rol: super_admin, owner, manager, cashier, chef
    role = db.Column(db.String(50), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Yardımcı metodlar - rol kontrolü için
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_owner(self):
        return self.role == 'owner'
    
    def is_manager(self):
        return self.role == 'manager'
    
    def is_chef(self):
        return self.role == 'chef'
    
    def is_cashier(self):
        return self.role == 'cashier'
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'