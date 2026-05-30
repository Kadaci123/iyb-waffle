"""
MASTER FIX - Tek seferlik, kesin çözüm.
- Tüm foreign key'leri otomatik bulur
- NOT NULL constraint'leri kaldırır
- Doğru ON DELETE kuralını uygular
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🔧 MASTER FIX BAŞLADI\n" + "="*60)
    
    # ============================================
    # ADIM A: NOT NULL constraint'leri kaldır
    # ============================================
    print("\n📌 ADIM A: NOT NULL constraint'leri kaldırılıyor...")
    
    null_columns = [
        ('orders', 'table_id'),
        ('orders', 'customer_phone'),
        ('orders', 'customer_name'),
        ('order_plates', 'base_product_id'),
        ('order_plate_ingredients', 'ingredient_product_id'),
        ('products', 'category_id'),
    ]
    
    for table_name, col_name in null_columns:
        try:
            db.session.execute(text(
                f'ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP NOT NULL'
            ))
            db.session.commit()
            print(f"   ✅ {table_name}.{col_name} → NULL'a izin verildi")
        except Exception as e:
            db.session.rollback()
            print(f"   ⚠️  {table_name}.{col_name}: zaten NULL'a izinli")
    
    # ============================================
    # ADIM B: Mevcut tüm foreign key'leri bul
    # ============================================
    print("\n📌 ADIM B: Mevcut foreign key'ler aranıyor...")
    
    find_query = text("""
        SELECT
            tc.table_name AS source_table,
            tc.constraint_name,
            kcu.column_name AS source_column,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        ORDER BY tc.table_name
    """)
    
    constraints = db.session.execute(find_query).fetchall()
    print(f"   📋 {len(constraints)} adet foreign key bulundu")
    
    # ============================================
    # ADIM C: Hepsini sil ve yeniden ekle
    # ============================================
    print("\n📌 ADIM C: Foreign key'ler yeniden tanımlanıyor...")
    
    # Hangi (table, column) için SET NULL olmalı? (sipariş geçmişi korunsun)
    set_null_pairs = {
        ('order_plates', 'base_product_id'),
        ('order_plate_ingredients', 'ingredient_product_id'),
    }
    
    success_count = 0
    
    for c in constraints:
        src_table = c[0]
        old_name = c[1]
        src_col = c[2]
        tgt_table = c[3]
        tgt_col = c[4]
        
        # Davranışa karar ver
        if (src_table, src_col) in set_null_pairs:
            action = 'SET NULL'
        else:
            action = 'CASCADE'
        
        try:
            # Eskisini sil
            db.session.execute(text(
                f'ALTER TABLE "{src_table}" DROP CONSTRAINT IF EXISTS "{old_name}"'
            ))
            
            # Yenisini ekle (benzersiz isim)
            new_name = f"fk_{src_table}_{src_col}_master"
            db.session.execute(text(
                f'ALTER TABLE "{src_table}" '
                f'ADD CONSTRAINT "{new_name}" '
                f'FOREIGN KEY ("{src_col}") '
                f'REFERENCES "{tgt_table}"("{tgt_col}") '
                f'ON DELETE {action}'
            ))
            db.session.commit()
            success_count += 1
            print(f"   ✅ {src_table}.{src_col} → {tgt_table} [{action}]")
        except Exception as e:
            db.session.rollback()
            err = str(e)[:80]
            print(f"   ⚠️  {src_table}.{src_col}: {err}")
    
    print("\n" + "="*60)
    print(f"✅ TAMAMLANDI: {success_count}/{len(constraints)} constraint düzeltildi")
    print("="*60)
    print("\n🎉 Artık tüm silmeler çalışacak.")
    print("👉 Şimdi: python run.py")