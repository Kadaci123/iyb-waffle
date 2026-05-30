"""
TEK SEFERLIK FIX: PostgreSQL'deki TÜM foreign key'leri otomatik bulur
ve uygun ON DELETE davranışıyla yeniden tanımlar.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🔧 PostgreSQL Constraint Otomatik Düzeltici Başladı...\n")
    
    # 1. Mevcut tüm foreign key'leri sorgula
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
        ORDER BY tc.table_name;
    """)
    
    try:
        constraints = db.session.execute(find_query).fetchall()
    except Exception as e:
        print(f"❌ Constraint sorgusunda hata: {e}")
        exit(1)
    
    print(f"📋 {len(constraints)} adet foreign key bulundu.\n")
    
    # 2. NULL'a izin verilmesi gereken sütunlar (sipariş geçmişi korunsun)
    set_null_cols = [
        ('order_plate_ingredients', 'ingredient_product_id'),
        ('order_plates', 'base_product_id'),
    ]
    
    for src_table, col in set_null_cols:
        try:
            db.session.execute(text(
                f'ALTER TABLE {src_table} ALTER COLUMN {col} DROP NOT NULL'
            ))
            db.session.commit()
            print(f"   ✅ {src_table}.{col} → NULL'a izin verildi")
        except Exception as e:
            db.session.rollback()
    
    print()
    
    # 3. Her foreign key'i sil ve uygun ON DELETE ile yeniden ekle
    success_count = 0
    skip_count = 0
    
    for c in constraints:
        src_table = c[0]
        cons_name = c[1]
        src_col = c[2]
        tgt_table = c[3]
        tgt_col = c[4]
        
        # ON DELETE davranışına karar ver
        if (src_table, src_col) in set_null_cols:
            action = 'SET NULL'
        else:
            action = 'CASCADE'
        
        try:
            # Eski constraint'i sil
            db.session.execute(text(
                f'ALTER TABLE "{src_table}" DROP CONSTRAINT IF EXISTS "{cons_name}"'
            ))
            
            # Yeni constraint'i ekle
            new_name = f"{src_table}_{src_col}_fk_v2"
            db.session.execute(text(
                f'ALTER TABLE "{src_table}" ADD CONSTRAINT "{new_name}" '
                f'FOREIGN KEY ("{src_col}") '
                f'REFERENCES "{tgt_table}"("{tgt_col}") '
                f'ON DELETE {action}'
            ))
            db.session.commit()
            success_count += 1
            print(f"   ✅ {src_table}.{src_col} → {tgt_table}.{tgt_col} [{action}]")
        except Exception as e:
            db.session.rollback()
            skip_count += 1
            err_msg = str(e)[:90].replace('\n', ' ')
            print(f"   ⚠️  {src_table}.{src_col}: {err_msg}")
    
    print(f"\n{'='*60}")
    print(f"✅ Başarılı: {success_count}")
    print(f"⚠️  Atlandı: {skip_count}")
    print(f"{'='*60}")
    print("\n🎉 BİTTİ! Artık tüm silmeler çalışacak.")
    print("👉 Şimdi: python run.py")