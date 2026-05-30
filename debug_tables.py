"""Mevcut masaları listele"""
from app import create_app, db
from app.models import Table, Branch

app = create_app()

with app.app_context():
    print("=" * 60)
    branches = Branch.query.all()
    print(f"📍 Şubeler: {len(branches)}")
    for b in branches:
        print(f"   ID: {b.id} | Ad: {b.name}")
    
    print("\n" + "=" * 60)
    tables = Table.query.all()
    print(f"🪑 Toplam masa: {len(tables)}")
    for t in tables:
        print(f"   ID: {t.id} | branch_id: {t.branch_id} | table_number: '{t.table_number}' | location: {t.location}")
    print("=" * 60)
    
    # /menu/1 hangi masayı arıyor?
    branch = Branch.query.first()
    print(f"\n🔍 /menu/1 sorgulamayı şöyle yapıyor:")
    print(f"   Branch.query.first() → ID: {branch.id if branch else 'YOK'}")
    print(f"   Table.query.filter_by(branch_id={branch.id if branch else '?'}, table_number='1').first()")
    
    found = Table.query.filter_by(branch_id=branch.id, table_number='1').first() if branch else None
    if found:
        print(f"   ✅ Bulundu: ID={found.id}")
    else:
        print(f"   ❌ BULUNAMADI! İşte sorun bu.")
        print(f"   📋 Hangi table_number değerleri var:")
        for t in tables:
            print(f"      → '{t.table_number}' (tip: {type(t.table_number).__name__})")