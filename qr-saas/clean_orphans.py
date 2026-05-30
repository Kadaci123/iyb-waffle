"""
Eğer fix_cascade.py çalıştırırken hala hata verirse,
orphan rows varsa bunu çalıştır.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🧹 Orphan rows kontrol ediliyor...\n")
    
    try:
        # Önce kaç tane orphan row var kontrol et
        result = db.session.execute(text("""
            SELECT COUNT(*) as orphan_count
            FROM category_rules 
            WHERE category_id NOT IN (SELECT id FROM categories);
        """)).fetchone()
        
        orphan_count = result[0] if result else 0
        
        if orphan_count == 0:
            print("✅ Orphan row yok - veritabanı temiz!")
        else:
            print(f"⚠️  {orphan_count} orphan row bulundu\n")
            
            # Orphan rows'ları göster
            print("🔍 Silinecek kurallar:")
            orphans = db.session.execute(text("""
                SELECT id, category_id FROM category_rules 
                WHERE category_id NOT IN (SELECT id FROM categories);
            """)).fetchall()
            
            for rule_id, cat_id in orphans:
                print(f"   - Kural #{rule_id} (silinmiş kategori #{cat_id})")
            
            # Orphan rows'ları sil
            print("\n🗑️  Siliniliyor...")
            db.session.execute(text("""
                DELETE FROM category_rules 
                WHERE category_id NOT IN (SELECT id FROM categories);
            """))
            db.session.commit()
            
            print(f"   ✅ {orphan_count} orphan row silindi")
        
        print("\n✅ TAMAMLANDI - Veritabanı temiz!")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ HATA: {str(e)}")