"""
Tüm ingredient (malzeme) ürünlerin fiyatlarını sor ve kaydet.
0 TL olanları teker teker görmek için.
"""
from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    print("🔍 Malzeme ürünlerini listeliyorum...\n")
    
    ingredients = Product.query.filter_by(product_type='ingredient', is_active=True).all()
    
    if not ingredients:
        print("Malzeme ürünü yok.")
    else:
        zero_priced = [p for p in ingredients if float(p.base_price or 0) == 0]
        
        print(f"📋 Toplam {len(ingredients)} malzeme, {len(zero_priced)} tanesi 0 TL\n")
        print("="*60)
        
        for p in ingredients:
            price = float(p.base_price or 0)
            status = "⚠️ 0 TL!" if price == 0 else f"{price} TL"
            print(f"  {p.id:3d} | {p.name:25s} | {status}")
        
        print("="*60)
        print("\n💡 Fiyatları yönetici panelinden tek tek güncelleyebilirsin.")
        print("   Veya bu dosyayı düzenleyip toplu fiyat ata.")