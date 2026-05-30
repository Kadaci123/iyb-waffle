"""
PostgreSQL'e eksik sütunları/tabloları ekler.
Mevcut veriye dokunmaz, sadece eksikleri tamamlar.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🔧 DB onarımı başlıyor...")
    
    statements = [
        # Orders tablosuna eksik sütunlar
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_address TEXT",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_type VARCHAR(20) DEFAULT 'dine_in'",
        
        # app_settings tablosunu oluştur (PIN'ler için)
        """CREATE TABLE IF NOT EXISTS app_settings (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    
    for sql in statements:
        try:
            db.session.execute(text(sql))
            db.session.commit()
            print(f"✅ OK: {sql[:60]}...")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️  Atlandı: {sql[:60]}... ({e})")
    
    print("✅ DB onarımı bitti!")