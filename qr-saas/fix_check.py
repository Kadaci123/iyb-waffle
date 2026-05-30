"""
CHECK constraint'leri güncelle:
- categories.category_type → 'base', 'ingredient', 'beverage'
- products.product_type → 'base', 'ingredient', 'beverage'
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🔧 CHECK constraint'ler güncelleniyor...\n")
    
    operations = [
        # Categories
        ('categories', 'category_type', """
            ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_category_type_check;
            ALTER TABLE categories ADD CONSTRAINT categories_category_type_check 
                CHECK (category_type IN ('base', 'ingredient', 'beverage'));
        """),
        # Products  
        ('products', 'product_type', """
            ALTER TABLE products DROP CONSTRAINT IF EXISTS products_product_type_check;
            ALTER TABLE products ADD CONSTRAINT products_product_type_check 
                CHECK (product_type IN ('base', 'ingredient', 'beverage'));
        """),
    ]
    
    for table, col, sql in operations:
        try:
            for line in sql.strip().split(';'):
                line = line.strip()
                if line:
                    db.session.execute(text(line))
            db.session.commit()
            print(f"   ✅ {table}.{col} → 'beverage' eklendi")
        except Exception as e:
            db.session.rollback()
            err = str(e)[:80]
            print(f"   ⚠️  {table}.{col}: {err}")
    
    print("\n✅ TAMAMLANDI - Artık 'beverage' türü çalışacak.")