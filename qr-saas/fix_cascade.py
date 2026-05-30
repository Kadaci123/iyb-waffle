"""
CategoryRule tablosundaki Foreign Key'i ON DELETE CASCADE ile güncelle.
Kategori silinince, ilgili kurallar otomatik silinir.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🔧 CategoryRule Foreign Key güncelleniyor...\n")
    
    try:
        # Mevcut constraint'i sil
        print("   1️⃣ Eski constraint kaldırılıyor...")
        db.session.execute(text("""
            ALTER TABLE category_rules DROP CONSTRAINT IF EXISTS category_rules_category_id_fkey;
        """))
        db.session.commit()
        print("      ✅ Eski constraint silindi")
        
        # Yeni constraint'i ON DELETE CASCADE ile ekle
        print("   2️⃣ Yeni CASCADE constraint ekleniyor...")
        db.session.execute(text("""
            ALTER TABLE category_rules 
            ADD CONSTRAINT category_rules_category_id_fkey 
            FOREIGN KEY (category_id) 
            REFERENCES categories(id) 
            ON DELETE CASCADE;
        """))
        db.session.commit()
        print("      ✅ Yeni constraint eklendi")
        
        print("\n✅ TAMAMLANDI")
        print("   Artık bir kategoriyi sildiğinde ilgili kurallar otomatik silinecek.")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ HATA: {str(e)[:150]}")
        print("\nDikkat: Eğer hala sorun varsa, veritabanında orphan rows olabilir.")
        print("Bunu temizlemek için çalıştır:")
        print("""
    DELETE FROM category_rules 
    WHERE category_id NOT IN (SELECT id FROM categories);
        """)