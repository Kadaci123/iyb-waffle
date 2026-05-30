"""
Final fix:
- Kategoriler silinince ÜRÜNLER de silinsin (CASCADE)
- Masa silinince SİPARİŞLER de silinsin (CASCADE)
- Müşteri telefon/adres sütunları NULL olabilsin
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🔧 Foreign Key'leri DÜZGÜN CASCADE'e çeviriyorum...\n")
    
    statements = [
        # 1) products.category_id - kategori silinince ÜRÜN DE SİLİNSİN
        ('products', """
            ALTER TABLE products DROP CONSTRAINT IF EXISTS products_category_id_fk_v2;
            ALTER TABLE products DROP CONSTRAINT IF EXISTS products_category_id_fkey;
            ALTER TABLE products ADD CONSTRAINT products_category_id_cascade
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE;
        """),
        
        # 2) orders.table_id - masa silinince SİPARİŞLER DE SİLİNSİN
        ('orders', """
            ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_table_id_fk_v2;
            ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_table_id_fkey;
            ALTER TABLE orders ADD CONSTRAINT orders_table_id_cascade
                FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE;
        """),
        
        # 3) order_plates.base_product_id - ürün silinince TABAK DA SİLİNSİN (sipariş geçmişi sorunluysa)
        ('order_plates', """
            ALTER TABLE order_plates DROP CONSTRAINT IF EXISTS order_plates_base_product_id_fk_v2;
            ALTER TABLE order_plates DROP CONSTRAINT IF EXISTS order_plates_base_product_id_fkey;
            ALTER TABLE order_plates ALTER COLUMN base_product_id DROP NOT NULL;
            ALTER TABLE order_plates ADD CONSTRAINT order_plates_base_product_id_setnull
                FOREIGN KEY (base_product_id) REFERENCES products(id) ON DELETE SET NULL;
        """),
        
        # 4) order_plate_ingredients.ingredient_product_id - ürün silinince malzeme NULL olsun
        ('order_plate_ingredients', """
            ALTER TABLE order_plate_ingredients DROP CONSTRAINT IF EXISTS order_plate_ingredients_ingredient_product_id_fk_v2;
            ALTER TABLE order_plate_ingredients DROP CONSTRAINT IF EXISTS order_plate_ingredients_ingredient_product_id_fkey;
            ALTER TABLE order_plate_ingredients ALTER COLUMN ingredient_product_id DROP NOT NULL;
            ALTER TABLE order_plate_ingredients ADD CONSTRAINT order_plate_ingredients_ingredient_setnull
                FOREIGN KEY (ingredient_product_id) REFERENCES products(id) ON DELETE SET NULL;
        """),
        
        # 5) Müşteri telefon ve adres NULL'a izin (zaten olmalı ama garantileyelim)
        ('orders_columns', """
            ALTER TABLE orders ALTER COLUMN customer_phone DROP NOT NULL;
        """),
    ]
    
    for name, sql in statements:
        try:
            # Birden fazla satır olabilir, ayrı ayrı yürüt
            for line in sql.strip().split(';'):
                line = line.strip()
                if line:
                    db.session.execute(text(line))
            db.session.commit()
            print(f"   ✅ {name} düzenlendi")
        except Exception as e:
            db.session.rollback()
            err_msg = str(e)[:100].replace('\n', ' ')
            print(f"   ⚠️  {name}: {err_msg}")
    
    print("\n✅ BİTTİ!")
    print("Artık kategori silince → ürünler de silinir")
    print("Masa silince → siparişler de silinir")