from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import timedelta
import os

load_dotenv()
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'iyb-waffle-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Fotoğraf upload limiti (8 MB)
    app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
    
    # Oturum süresi: 365 gün (mutfak cihazı sürekli açık kalır)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    db.init_app(app)
    
    with app.app_context():
        from app import models
        db.create_all()
        
        # ============ MIGRATION: use_own_price sütunu yoksa ekle ============
        from sqlalchemy import text, inspect
        try:
            inspector = inspect(db.engine)
            cols = [c['name'] for c in inspector.get_columns('category_rules')]
            if 'use_own_price' not in cols:
                print('🔧 category_rules.use_own_price sütunu ekleniyor...')
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'ALTER TABLE category_rules ADD COLUMN use_own_price BOOLEAN DEFAULT FALSE NOT NULL'
                    ))
                    conn.commit()
                print('✅ use_own_price sütunu eklendi!')
        except Exception as e:
            print(f'⚠️ Migration uyarı (ilk kurulumda normal): {e}')
        
        # ============ Upload klasörünü oluştur ============
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
    
    from app.routes import bp
    app.register_blueprint(bp)
    
    return app