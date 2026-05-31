from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import wraps
from sqlalchemy import func, cast, Date
from io import BytesIO
import os
import uuid
import re
import threading
import urllib.request
import urllib.parse
import json
from werkzeug.utils import secure_filename
from app import db
from app.models import (
    Firm, Branch, Category, CategoryRule, Product,
    Table, Order, OrderPlate, OrderPlateIngredient,
    ProductOptionGroup, ProductOptionItem, OrderPlateOption
)

bp = Blueprint('main', __name__)

# ========================================================================
# ⏰ SAAT DİLİMİ
# ========================================================================
TIMEZONE_OFFSET = timedelta(hours=3)

def get_turkey_time():
    return datetime.utcnow() + TIMEZONE_OFFSET

# ========================================================================
# 🔒 GÜVENLİK AYARLARI
# ========================================================================
ADMIN_URL_PREFIX = "px7k2m9-iyb"
MENU_SESSION_TIMEOUT = 300  # 5 dakika

# ========================================================================
# 📱 TELEGRAM BİLDİRİM AYARLARI
# ========================================================================
TELEGRAM_BOT_TOKEN = "8866399794:AAFdfVMswGsvQ4JT7l2OYHfOZuB6eTZlTSs"
TELEGRAM_CHAT_ID = "-5267770642"
TELEGRAM_ENABLED = True


def send_telegram_message(text):
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    def _send():
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = urllib.parse.urlencode({
                'chat_id': TELEGRAM_CHAT_ID,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': 'true'
            }).encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if not result.get('ok'):
                    print(f"⚠️ Telegram hatası: {result.get('description', 'bilinmeyen')}")
        except Exception as e:
            print(f"⚠️ Telegram bildirim hatası: {e}")
    
    threading.Thread(target=_send, daemon=True).start()


def format_order_for_telegram(order, table, plates_with_data, standalone_bevs, standalone_desserts):
    """Telegram için güzel, okunaklı sipariş mesajı oluşturur."""
    lines = []
    lines.append(f"🔔 <b>YENİ SİPARİŞ #{order.id}</b>")
    lines.append(f"🪑 <b>Masa {table.table_number}</b>")
    
    if order.customer_name:
        lines.append(f"👤 <b>{order.customer_name}</b>")
    
    turkey_time = order.created_at + TIMEZONE_OFFSET if order.created_at else get_turkey_time()
    lines.append(f"🕐 {turkey_time.strftime('%H:%M')}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    
    # WAFFLE TABAKLARI
    for idx, (plate, malzemeler, icecekler, dondurmalar, options) in enumerate(plates_with_data, 1):
        # 🎁 Kampanya ürünü mü? (option grupları varsa)
        is_combo = bool(options)
        prefix = "🎁" if is_combo else "🧇"
        lines.append(f"\n{prefix} <b>Tabak {idx}: {plate['base_name']}</b>")
        
        # 🧇 Main waffle seçimi varsa ayır
        main_waffle = None
        other_options = []
        if is_combo:
            for opt in options:
                gname = (opt.get('group_name') or '').lower()
                if main_waffle is None and ('waffle' in gname or 'tür' in gname):
                    main_waffle = opt
                else:
                    other_options.append(opt)
        
        if main_waffle:
            lines.append(f"   🧇 <b>SEÇİLEN WAFFLE: {main_waffle['selected_name']}</b>")
        
        if malzemeler:
            mlz_str = ", ".join([f"{'🆓' if m['free'] else ''}{m['name']}" for m in malzemeler])
            lines.append(f"   🍫 <b>Malzemeler:</b> {mlz_str}")
        else:
            lines.append(f"   🍫 <i>Sade</i>")
        
        if icecekler:
            ic_str = ", ".join([i['name'] for i in icecekler])
            lines.append(f"   🥤 <b>İçecek:</b> {ic_str}")
        
        if dondurmalar:
            dn_str = ", ".join([d['name'] for d in dondurmalar])
            lines.append(f"   🍦 <b>Dondurma:</b> {dn_str}")
        
        # 🎁 Kampanya bedava ek seçimleri (waffle hariç)
        for opt in other_options:
            lines.append(f"   🎁 <b>{opt['group_name']}:</b> {opt['selected_name']}")
    
    if standalone_bevs:
        lines.append("")
        lines.append("🥤 <b>İÇECEKLER:</b>")
        for b in standalone_bevs:
            lines.append(f"   • {b['name']}")
    
    if standalone_desserts:
        lines.append("")
        lines.append("🍦 <b>DONDURMALAR:</b>")
        for d in standalone_desserts:
            lines.append(f"   • {d['name']}")
    
    if order.customer_note:
        lines.append("")
        lines.append(f"📝 <b>Not:</b> <i>{order.customer_note}</i>")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💰 <b>TOPLAM: {float(order.total_price):.2f} TL</b>")
    
    return "\n".join(lines)


# ========================================================================
# PIN KODLARI
# ========================================================================
YONETICI_PIN = "1234"
MUTFAK_PIN = "5678"
KASA_PIN = "9999"

PIN_PATTERN = re.compile(r'^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]{4,12}$')

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def require_role(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get(f'role_{role}'):
                return redirect(url_for('main.login', target=role))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ============ ANA SAYFA ============
@bp.route('/')
def index():
    return render_template('index.html', admin_prefix=ADMIN_URL_PREFIX)


# ============ GİRİŞ (GİZLİ URL) ============
@bp.route(f'/{ADMIN_URL_PREFIX}-giris', methods=['GET', 'POST'])
def login():
    target = request.args.get('target', '')
    if request.method == 'POST':
        pin = request.form.get('pin', '')
        valid = False
        if target == 'yonetici':
            valid = (pin == YONETICI_PIN)
        elif target == 'mutfak':
            valid = (pin == MUTFAK_PIN or pin == YONETICI_PIN)
        elif target == 'kasa':
            valid = (pin == KASA_PIN or pin == YONETICI_PIN)
        
        if valid:
            session.pop('role_yonetici', None)
            session.pop('role_mutfak', None)
            session.pop('role_kasa', None)
            session[f'role_{target}'] = True
            return redirect(url_for('main.' + target))
        else:
            return render_template('login.html', target=target, error="Yanlış PIN!", admin_prefix=ADMIN_URL_PREFIX)
    
    return render_template('login.html', target=target, error=None, admin_prefix=ADMIN_URL_PREFIX)


@bp.route(f'/{ADMIN_URL_PREFIX}-cikis')
def logout():
    target = request.args.get('target', '')
    if target in ('yonetici', 'mutfak', 'kasa'):
        session.pop(f'role_{target}', None)
    else:
        session.pop('role_yonetici', None)
        session.pop('role_mutfak', None)
        session.pop('role_kasa', None)
    return redirect(url_for('main.index'))


# ============ MÜŞTERİ ============
@bp.route('/menu/<masa>')
def menu(masa):
    branch = Branch.query.first()
    table = Table.query.filter_by(branch_id=branch.id, table_number=masa).first()
    if not table:
        table = Table.query.filter_by(branch_id=branch.id, table_number=f'masa {masa}').first()
    if not table:
        try:
            table_id = int(masa)
            table = Table.query.filter_by(id=table_id, branch_id=branch.id).first()
        except:
            pass
    if not table:
        return f"<h1>❌ Masa '{masa}' bulunamadı</h1>", 404
    
    locked_table_id = session.get('locked_table_id')
    if locked_table_id and locked_table_id != table.id:
        locked_started_iso = session.get(f'menu_{locked_table_id}_started')
        if locked_started_iso:
            try:
                locked_started_at = datetime.fromisoformat(locked_started_iso)
                locked_elapsed = (datetime.utcnow() - locked_started_at).total_seconds()
                if locked_elapsed <= MENU_SESSION_TIMEOUT:
                    locked_table = Table.query.get(locked_table_id)
                    locked_table_no = locked_table.table_number if locked_table else '?'
                    remaining = int(MENU_SESSION_TIMEOUT - locked_elapsed)
                    rem_m = remaining // 60
                    rem_s = remaining % 60
                    return render_template('table_locked.html',
                                           locked_table=locked_table_no,
                                           attempted_table=table.table_number,
                                           remaining_min=rem_m,
                                           remaining_sec=rem_s), 403
                else:
                    session.pop(f'menu_{locked_table_id}_started', None)
                    session.pop('locked_table_id', None)
            except:
                session.pop('locked_table_id', None)
        else:
            session.pop('locked_table_id', None)
    
    session[f'menu_{table.id}_started'] = datetime.utcnow().isoformat()
    session['locked_table_id'] = table.id
    
    base_products = Product.query.filter_by(product_type='base', is_active=True).order_by(Product.display_order).all()
    # 🎁 KAMPANYA ÜRÜNLERİ - product_type='campaign'
    campaign_products = Product.query.filter_by(product_type='campaign', is_active=True).order_by(Product.display_order).all()
    ingredient_cats = Category.query.filter_by(category_type='ingredient', is_active=True).order_by(Category.display_order).all()
    beverage_cats = Category.query.filter_by(category_type='beverage', is_active=True).order_by(Category.display_order).all()
    dessert_cats = Category.query.filter_by(category_type='dessert', is_active=True).order_by(Category.display_order).all()
    
    # 🎁 Tüm ürünlerin (base + campaign) option_groups'larını JSON olarak hazırla
    # Müşteri tarafında bu ürüne tıklayınca zorunlu seçim ekranı çıksın
    products_with_options = {}
    # copy_rules_from haritası: kampanya ürün → kaynak ürün ID
    campaign_copy_rules = {}
    
    all_relevant = list(base_products) + list(campaign_products)
    for p in all_relevant:
        # Kampanya kural-kopyalama
        if p.product_type == 'campaign' and p.copy_rules_from_product_id:
            campaign_copy_rules[p.id] = p.copy_rules_from_product_id
        
        if p.option_groups:
            groups_data = []
            for g in p.option_groups:
                items_data = []
                for it in g.items:
                    if it.product and it.product.is_active and not it.product.is_out_of_stock:
                        items_data.append({
                            'id': it.product.id,
                            'name': it.product.name,
                            'image_url': it.product.image_url or '',
                            'extra_price': float(it.extra_price or 0)
                        })
                if items_data:
                    groups_data.append({
                        'id': g.id,
                        'name': g.name,
                        'icon': g.icon or '🎁',
                        'min_select': g.min_select,
                        'max_select': g.max_select,
                        'is_required': g.is_required,
                        'group_type': g.group_type or 'free_addon',
                        'items': items_data
                    })
            if groups_data:
                products_with_options[p.id] = groups_data
    
    return render_template('menu.html', branch=branch, table=table,
                           base_products=base_products,
                           campaign_products=campaign_products,
                           ingredient_cats=ingredient_cats,
                           beverage_cats=beverage_cats,
                           dessert_cats=dessert_cats,
                           products_with_options=products_with_options,
                           campaign_copy_rules=campaign_copy_rules,
                           session_timeout=MENU_SESSION_TIMEOUT)


@bp.route('/api/order', methods=['POST'])
def create_order():
    try:
        data = request.json
        table_id = data.get('table_id')
        
        session_key = f'menu_{table_id}_started'
        started_iso = session.get(session_key)
        
        if not started_iso:
            return jsonify({
                'ok': False, 
                'error': 'session_expired',
                'message': 'Sipariş oturumu bulunamadı. Lütfen QR kodu tekrar okutun.'
            }), 403
        
        try:
            started_at = datetime.fromisoformat(started_iso)
            elapsed = (datetime.utcnow() - started_at).total_seconds()
        except:
            session.pop(session_key, None)
            session.pop('locked_table_id', None)
            return jsonify({
                'ok': False, 
                'error': 'session_expired',
                'message': 'Geçersiz oturum. Lütfen QR kodu tekrar okutun.'
            }), 403
        
        if elapsed > MENU_SESSION_TIMEOUT:
            session.pop(session_key, None)
            session.pop('locked_table_id', None)
            return jsonify({
                'ok': False, 
                'error': 'session_expired',
                'message': f'Sipariş süresi ({MENU_SESSION_TIMEOUT // 60} dk) doldu. Lütfen QR kodu tekrar okutun.'
            }), 403
        
        table = Table.query.get_or_404(table_id)
        branch = Branch.query.get(table.branch_id)
        
        plates_data = data.get('plates', [])
        standalone_items = data.get('standalone_items', [])
        
        if not plates_data and not standalone_items:
            return jsonify({'ok': False, 'error': 'Sepet boş'}), 400
        
        order = Order(
            firm_id=branch.firm_id,
            branch_id=branch.id,
            table_id=table.id,
            customer_name=data.get('customer_name', '').strip() or None,
            customer_phone=data.get('customer_phone', '').strip() or None,
            customer_note=data.get('note', '').strip() or None,
            status='pending',
            payment_status='unpaid'
        )
        db.session.add(order)
        db.session.flush()
        
        total = Decimal('0')
        
        # ============ WAFFLE / KAMPANYA TABAKLARI ============
        for plate_data in plates_data:
            base_product = Product.query.get(plate_data['base_id'])
            if not base_product:
                continue
            
            plate = OrderPlate(
                order_id=order.id,
                base_product_id=base_product.id,
                base_price=base_product.base_price,
                quantity=1,
                notes=plate_data.get('note', '')
            )
            db.session.add(plate)
            db.session.flush()
            
            # Malzemeler
            ingredients_by_cat = {}
            for ing_id in plate_data.get('ingredients', []):
                ing = Product.query.get(ing_id)
                if ing:
                    ingredients_by_cat.setdefault(ing.category_id, []).append(ing)
            
            plate_ing_total = Decimal('0')
            
            for cat_id, ings in ingredients_by_cat.items():
                cat_obj = Category.query.get(cat_id)
                is_special = cat_obj and cat_obj.category_type in ('beverage', 'dessert')
                rule = None if is_special else CategoryRule.query.filter_by(category_id=cat_id).first()
                
                if not rule:
                    for ing in ings:
                        price = ing.base_price or Decimal('0')
                        db.session.add(OrderPlateIngredient(
                            order_plate_id=plate.id,
                            ingredient_product_id=ing.id,
                            unit_price=price,
                            is_free=False
                        ))
                        plate_ing_total += price
                else:
                    free_count = rule.free_count
                    use_own = bool(rule.use_own_price)
                    extra_price = rule.extra_price or Decimal('0')
                    
                    for i, ing in enumerate(ings):
                        is_free = i < free_count
                        if is_free:
                            price = Decimal('0')
                        elif use_own:
                            price = ing.base_price or Decimal('0')
                        else:
                            price = extra_price
                        
                        db.session.add(OrderPlateIngredient(
                            order_plate_id=plate.id,
                            ingredient_product_id=ing.id,
                            unit_price=price,
                            is_free=is_free
                        ))
                        plate_ing_total += price
            
            # 🎁 ZORUNLU SEÇİMLER (kampanya - bedava içecek vb.)
            # options = [{ 'group_id': X, 'product_id': Y }, ...]
            options_data = plate_data.get('options', [])
            plate_options_total = Decimal('0')
            
            # Validate: zorunlu grupların hepsi seçilmiş mi?
            required_groups = ProductOptionGroup.query.filter_by(
                product_id=base_product.id, is_required=True
            ).all()
            selected_group_ids = set(o.get('group_id') for o in options_data if o.get('group_id'))
            
            for rg in required_groups:
                if rg.id not in selected_group_ids:
                    db.session.rollback()
                    return jsonify({
                        'ok': False,
                        'error': f"'{base_product.name}' için '{rg.name}' seçimi zorunlu!"
                    }), 400
            
            for opt_data in options_data:
                group_id = opt_data.get('group_id')
                selected_pid = opt_data.get('product_id')
                if not group_id or not selected_pid:
                    continue
                
                # Validate: bu group bu product'a ait mi? selected_pid bu group'ta mı?
                group = ProductOptionGroup.query.filter_by(id=group_id, product_id=base_product.id).first()
                if not group:
                    continue
                opt_item = ProductOptionItem.query.filter_by(group_id=group.id, product_id=selected_pid).first()
                if not opt_item:
                    continue
                
                selected_prod = Product.query.get(selected_pid)
                if not selected_prod:
                    continue
                
                opt_price = opt_item.extra_price or Decimal('0')
                db.session.add(OrderPlateOption(
                    order_plate_id=plate.id,
                    group_name=group.name,
                    selected_product_id=selected_prod.id,
                    selected_name=selected_prod.name,
                    extra_price=opt_price
                ))
                plate_options_total += opt_price
            
            plate.ingredients_total = plate_ing_total
            plate.plate_total = base_product.base_price + plate_ing_total + plate_options_total
            total += plate.plate_total
        
        # ============ BAĞIMSIZ İÇECEK / DONDURMA ============
        for item_id in standalone_items:
            prod = Product.query.get(item_id)
            if not prod:
                continue
            price = prod.base_price or Decimal('0')
            plate = OrderPlate(
                order_id=order.id,
                base_product_id=prod.id,
                base_price=price,
                quantity=1,
                notes='',
                ingredients_total=Decimal('0'),
                plate_total=price
            )
            db.session.add(plate)
            total += price
        
        order.subtotal = total
        order.tax_amount = total * Decimal('0.10')
        order.total_price = total
        
        db.session.commit()
        
        session.pop(session_key, None)
        session.pop('locked_table_id', None)
        
        # 📱 TELEGRAM BİLDİRİMİ
        try:
            plates_with_data = []
            order_plates = OrderPlate.query.filter_by(order_id=order.id).all()
            standalone_bevs_list = []
            standalone_desserts_list = []
            
            for plate in order_plates:
                base = Product.query.get(plate.base_product_id) if plate.base_product_id else None
                if not base:
                    continue
                base_cat = Category.query.get(base.category_id) if base.category_id else None
                base_cat_type = base_cat.category_type if base_cat else 'base'
                
                if base_cat_type == 'beverage':
                    standalone_bevs_list.append({'name': base.name})
                    continue
                if base_cat_type == 'dessert':
                    standalone_desserts_list.append({'name': base.name})
                    continue
                
                ings_list = OrderPlateIngredient.query.filter_by(order_plate_id=plate.id).all()
                malzemeler = []
                icecekler = []
                dondurmalar = []
                for i in ings_list:
                    ing_prod = Product.query.get(i.ingredient_product_id) if i.ingredient_product_id else None
                    if not ing_prod:
                        continue
                    ing_cat = Category.query.get(ing_prod.category_id) if ing_prod.category_id else None
                    ing_cat_type = ing_cat.category_type if ing_cat else 'ingredient'
                    item = {'name': ing_prod.name, 'free': bool(i.is_free)}
                    if ing_cat_type == 'beverage':
                        icecekler.append(item)
                    elif ing_cat_type == 'dessert':
                        dondurmalar.append(item)
                    else:
                        malzemeler.append(item)
                
                # 🎁 Plate'in option seçimleri (kampanya)
                opts = OrderPlateOption.query.filter_by(order_plate_id=plate.id).all()
                opts_list = [{'group_name': o.group_name, 'selected_name': o.selected_name} for o in opts]
                
                plates_with_data.append((
                    {'base_name': base.name},
                    malzemeler,
                    icecekler,
                    dondurmalar,
                    opts_list
                ))
            
            telegram_msg = format_order_for_telegram(
                order, table, plates_with_data, 
                standalone_bevs_list, standalone_desserts_list
            )
            send_telegram_message(telegram_msg)
        except Exception as e:
            print(f"⚠️ Telegram bildirim hazırlama hatası: {e}")
        
        return jsonify({'ok': True, 'order_id': order.id, 'total': float(order.total_price)})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ YÖNETİCİ ============
@bp.route(f'/{ADMIN_URL_PREFIX}-yonetici')
@require_role('yonetici')
def yonetici():
    categories = Category.query.order_by(Category.category_type, Category.display_order).all()
    products = Product.query.order_by(Product.product_type, Product.display_order).all()
    
    today = date.today()
    today_orders = Order.query.filter(cast(Order.created_at, Date) == today).all()
    
    daily_count = len(today_orders)
    daily_revenue = sum(float(o.total_price or 0) for o in today_orders)
    pending_count = len([o for o in today_orders if o.status in ['pending', 'preparing']])
    
    branch = Branch.query.first()
    tables = Table.query.filter_by(branch_id=branch.id).all() if branch else []
    
    # 🎁 Seçim gruplarında kullanılabilecek ürünler:
    # - main_waffle grubu için → base ürünleri
    # - free_addon grubu için → beverage + dessert
    selectable_products = Product.query.filter(
        Product.product_type.in_(['base', 'beverage', 'dessert']),
        Product.is_active == True
    ).order_by(Product.product_type, Product.name).all()
    
    return render_template('yonetici.html',
                           categories=categories, products=products, tables=tables,
                           selectable_products=selectable_products,
                           daily_count=daily_count, daily_revenue=daily_revenue,
                           pending_count=pending_count,
                           admin_prefix=ADMIN_URL_PREFIX)


@bp.route('/api/category', methods=['POST'])
def save_category():
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        firm = Firm.query.first()
        cat = Category(
            firm_id=firm.id,
            name=data['name'],
            category_type=data['type'],
            icon=data.get('icon', ''),
            display_order=int(data.get('order', 0))
        )
        db.session.add(cat)
        db.session.commit()
        return jsonify({'ok': True, 'id': cat.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/category/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        cat = Category.query.get_or_404(cat_id)
        CategoryRule.query.filter_by(category_id=cat_id).delete(synchronize_session=False)
        db.session.flush()
        products_in_cat = Product.query.filter_by(category_id=cat_id).all()
        for p in products_in_cat:
            if p.image_url and p.image_url.startswith('/static/uploads/'):
                try:
                    fp = os.path.join('app', p.image_url.lstrip('/'))
                    if os.path.exists(fp):
                        os.remove(fp)
                except:
                    pass
        Product.query.filter_by(category_id=cat_id).delete(synchronize_session=False)
        db.session.flush()
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/product', methods=['POST'])
def save_product():
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        firm = Firm.query.first()
        p = Product(
            firm_id=firm.id,
            category_id=int(data['category_id']),
            product_type=data['type'],
            name=data['name'],
            description=data.get('description', ''),
            base_price=Decimal(str(data.get('price', 0))),
            image_url=data.get('image_url', ''),
            display_order=int(data.get('order', 0))
        )
        db.session.add(p)
        db.session.commit()
        return jsonify({'ok': True, 'id': p.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/product/<int:pid>', methods=['PUT'])
def update_product(pid):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        p = Product.query.get_or_404(pid)
        if 'name' in data:
            p.name = data['name']
        if 'price' in data:
            p.base_price = Decimal(str(data['price']))
        if 'description' in data:
            p.description = data['description']
        # 🎁 Kampanya: hangi ürünün malzeme havuzundan kopyalanacak?
        if 'copy_rules_from' in data:
            val = data['copy_rules_from']
            p.copy_rules_from_product_id = int(val) if val else None
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/product/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        p = Product.query.get_or_404(pid)
        if p.image_url and p.image_url.startswith('/static/uploads/'):
            try:
                fp = os.path.join('app', p.image_url.lstrip('/'))
                if os.path.exists(fp):
                    os.remove(fp)
            except:
                pass
        db.session.delete(p)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ FOTOĞRAF YÜKLEME ============
@bp.route('/api/product/<int:pid>/upload-image', methods=['POST'])
def upload_product_image(pid):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        if 'image' not in request.files:
            return jsonify({'ok': False, 'error': 'Dosya seçilmedi'}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({'ok': False, 'error': 'Dosya seçilmedi'}), 400
        if not allowed_file(file.filename):
            return jsonify({'ok': False, 'error': 'Sadece PNG/JPG/JPEG/GIF/WEBP'}), 400
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        p = Product.query.get_or_404(pid)
        if p.image_url and p.image_url.startswith('/static/uploads/'):
            try:
                old_path = os.path.join('app', p.image_url.lstrip('/'))
                if os.path.exists(old_path):
                    os.remove(old_path)
            except:
                pass
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"prod_{pid}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        p.image_url = f'/static/uploads/{filename}'
        db.session.commit()
        return jsonify({'ok': True, 'image_url': p.image_url})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/product/<int:pid>/delete-image', methods=['DELETE'])
def delete_product_image(pid):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        p = Product.query.get_or_404(pid)
        if p.image_url and p.image_url.startswith('/static/uploads/'):
            try:
                fp = os.path.join('app', p.image_url.lstrip('/'))
                if os.path.exists(fp):
                    os.remove(fp)
            except:
                pass
        p.image_url = ''
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/product/<int:pid>/toggle-stock', methods=['POST'])
def toggle_product_stock(pid):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        prod = Product.query.get_or_404(pid)
        prod.is_out_of_stock = not prod.is_out_of_stock
        db.session.commit()
        
        if prod.is_out_of_stock:
            msg = f"⚠️ <b>ÜRÜN BİTTİ</b>\n🧇 {prod.name} artık sipariş verilemez."
        else:
            msg = f"✅ <b>ÜRÜN GERİ STOKTA</b>\n🧇 {prod.name} tekrar sipariş verilebilir."
        send_telegram_message(msg)
        
        return jsonify({'ok': True, 'is_out_of_stock': prod.is_out_of_stock})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ STOK DURUMU (MÜŞTERİ POLLING) ============
@bp.route('/api/stock-status')
def stock_status():
    try:
        products = Product.query.filter_by(is_active=True).all()
        stock_map = {
            str(p.id): bool(p.is_out_of_stock) 
            for p in products
        }
        return jsonify({'ok': True, 'stock': stock_map})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ KURAL ============
@bp.route('/api/rule', methods=['POST'])
def save_rule():
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        cat_id = int(data['category_id'])
        rule = CategoryRule.query.filter_by(category_id=cat_id).first()
        if not rule:
            rule = CategoryRule(category_id=cat_id)
            db.session.add(rule)
        rule.free_count = int(data.get('free_count', 0))
        rule.extra_price = Decimal(str(data.get('extra_price', 0)))
        rule.use_own_price = bool(data.get('use_own_price', False))
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/rule/<int:cat_id>', methods=['DELETE'])
def delete_rule(cat_id):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        CategoryRule.query.filter_by(category_id=cat_id).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# 🎁 ÜRÜNÜN ZORUNLU SEÇİM GRUPLARI (Kampanya kuralları)
# ============================================================
@bp.route('/api/product/<int:pid>/option-groups')
def get_product_option_groups(pid):
    """Bir ürünün tüm option_groups listesini döndürür."""
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        p = Product.query.get_or_404(pid)
        groups = []
        for g in p.option_groups:
            items = []
            for it in g.items:
                if it.product:
                    items.append({
                        'id': it.id,
                        'product_id': it.product.id,
                        'product_name': it.product.name,
                        'extra_price': float(it.extra_price or 0)
                    })
            groups.append({
                'id': g.id,
                'name': g.name,
                'icon': g.icon or '',
                'min_select': g.min_select,
                'max_select': g.max_select,
                'is_required': g.is_required,
                'display_order': g.display_order,
                'items': items
            })
        return jsonify({'ok': True, 'groups': groups})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/product/<int:pid>/option-group', methods=['POST'])
def create_option_group(pid):
    """Bir ürüne yeni zorunlu seçim grubu ekle."""
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        p = Product.query.get_or_404(pid)
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'ok': False, 'error': 'Grup adı zorunlu'}), 400
        
        product_ids = data.get('product_ids', [])  # [id, id, ...]
        if not product_ids:
            return jsonify({'ok': False, 'error': 'En az 1 seçenek ekle'}), 400
        
        group = ProductOptionGroup(
            product_id=p.id,
            name=name,
            icon=data.get('icon', '🎁'),
            min_select=int(data.get('min_select', 1)),
            max_select=int(data.get('max_select', 1)),
            is_required=bool(data.get('is_required', True)),
            display_order=int(data.get('display_order', 0)),
            group_type=data.get('group_type', 'free_addon')
        )
        db.session.add(group)
        db.session.flush()
        
        for item in product_ids:
            opt_pid = item.get('id') if isinstance(item, dict) else item
            extra = item.get('extra_price', 0) if isinstance(item, dict) else 0
            if not opt_pid:
                continue
            db.session.add(ProductOptionItem(
                group_id=group.id,
                product_id=int(opt_pid),
                extra_price=Decimal(str(extra))
            ))
        
        db.session.commit()
        return jsonify({'ok': True, 'group_id': group.id})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/option-group/<int:gid>', methods=['DELETE'])
def delete_option_group(gid):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        group = ProductOptionGroup.query.get_or_404(gid)
        db.session.delete(group)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ 🎁 KAMPANYA: BASİT CHECKBOX ENDPOINT'LERİ ============
@bp.route('/api/campaign/<int:pid>/set-main-waffles', methods=['POST'])
def set_main_waffles(pid):
    """Bir kampanya ürününe 'Ana Waffle Seçimi' havuzunu ayarlar.
    Body: { product_ids: [1, 2, 3], group_name: 'Waffle Türünü Seçin' }
    Mevcut main_waffle grubunu siler, yenisini oluşturur (idempotent)."""
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        product_ids = data.get('product_ids', [])
        group_name = data.get('group_name', 'Waffle Türünü Seçin').strip() or 'Waffle Türünü Seçin'
        
        product = Product.query.get_or_404(pid)
        
        # Mevcut main_waffle gruplarını sil
        ProductOptionGroup.query.filter_by(
            product_id=pid, group_type='main_waffle'
        ).delete(synchronize_session=False)
        db.session.flush()
        
        # Yeni ürün varsa yeni grup oluştur
        if product_ids:
            group = ProductOptionGroup(
                product_id=pid,
                name=group_name,
                icon='🧇',
                min_select=1,
                max_select=1,
                is_required=True,
                group_type='main_waffle',
                display_order=0
            )
            db.session.add(group)
            db.session.flush()
            
            for prod_id in product_ids:
                if not prod_id:
                    continue
                db.session.add(ProductOptionItem(
                    group_id=group.id,
                    product_id=int(prod_id),
                    extra_price=Decimal('0')
                ))
        
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/campaign/<int:pid>/set-free-addons', methods=['POST'])
def set_free_addons(pid):
    """Bir kampanya ürününe 'Bedava İçecek/Dondurma' havuzunu ayarlar.
    Body: { product_ids: [4, 5, 6], group_name: 'İçeceğinizi Seçin' }
    Mevcut free_addon grubunu siler, yenisini oluşturur (idempotent)."""
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        product_ids = data.get('product_ids', [])
        group_name = data.get('group_name', 'Bedava İçecek/Dondurma').strip() or 'Bedava İçecek/Dondurma'
        
        product = Product.query.get_or_404(pid)
        
        # Mevcut free_addon gruplarını sil
        ProductOptionGroup.query.filter_by(
            product_id=pid, group_type='free_addon'
        ).delete(synchronize_session=False)
        db.session.flush()
        
        if product_ids:
            group = ProductOptionGroup(
                product_id=pid,
                name=group_name,
                icon='🎁',
                min_select=1,
                max_select=1,
                is_required=True,
                group_type='free_addon',
                display_order=1
            )
            db.session.add(group)
            db.session.flush()
            
            for prod_id in product_ids:
                if not prod_id:
                    continue
                db.session.add(ProductOptionItem(
                    group_id=group.id,
                    product_id=int(prod_id),
                    extra_price=Decimal('0')  # bedava
                ))
        
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ MASA ============
@bp.route('/api/table', methods=['POST'])
def save_table():
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        branch = Branch.query.first()
        table = Table(
            branch_id=branch.id,
            table_number=data.get('table_number', ''),
            location=data.get('location', ''),
            capacity=int(data.get('capacity', 4))
        )
        db.session.add(table)
        db.session.commit()
        return jsonify({'ok': True, 'id': table.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/table/<int:table_id>', methods=['DELETE'])
def delete_table(table_id):
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        table = Table.query.get_or_404(table_id)
        # Bu masaya bağlı tüm siparişleri ve alt kayıtlarını sil
        orders = Order.query.filter_by(table_id=table_id).all()
        for o in orders:
            plates = OrderPlate.query.filter_by(order_id=o.id).all()
            for plate in plates:
                OrderPlateIngredient.query.filter_by(order_plate_id=plate.id).delete(synchronize_session=False)
                OrderPlateOption.query.filter_by(order_plate_id=plate.id).delete(synchronize_session=False)
            db.session.flush()
            OrderPlate.query.filter_by(order_id=o.id).delete(synchronize_session=False)
            db.session.flush()
        Order.query.filter_by(table_id=table_id).delete(synchronize_session=False)
        db.session.flush()
        db.session.delete(table)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ PIN ============
@bp.route('/api/pin', methods=['POST'])
def change_pin():
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    try:
        data = request.json
        role = data.get('role')
        pin = data.get('pin', '').strip()
        if role not in ('yonetici', 'mutfak', 'kasa'):
            return jsonify({'ok': False, 'error': 'Geçersiz rol'}), 400
        if not pin:
            return jsonify({'ok': False, 'error': 'PIN boş olamaz'}), 400
        if len(pin) < 4 or len(pin) > 12:
            return jsonify({'ok': False, 'error': 'PIN 4-12 karakter olmalı'}), 400
        if not PIN_PATTERN.match(pin):
            return jsonify({'ok': False, 'error': 'PIN sadece harf, rakam ve noktalama içerebilir'}), 400
        routes_path = __file__
        with open(routes_path, 'r', encoding='utf-8') as f:
            content = f.read()
        var_name = f'{role.upper()}_PIN'
        pin_escaped = pin.replace('\\', '\\\\').replace('"', '\\"')
        pattern = rf'({var_name}\s*=\s*)"[^"]*"'
        new_content = re.sub(pattern, rf'\g<1>"{pin_escaped}"', content, count=1)
        if new_content == content:
            return jsonify({'ok': False, 'error': 'PIN değişkeni bulunamadı'}), 500
        with open(routes_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return jsonify({'ok': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ TELEGRAM TEST ============
@bp.route('/api/telegram-test', methods=['POST'])
def telegram_test():
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    
    if not TELEGRAM_ENABLED:
        return jsonify({'ok': False, 'error': 'Telegram bildirimleri kapalı'}), 400
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return jsonify({'ok': False, 'error': 'TOKEN veya CHAT_ID ayarlanmamış'}), 400
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        test_msg = (
            "🧪 <b>TEST MESAJI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ iyb waffle Telegram bot'u <b>çalışıyor</b>!\n\n"
            "Yeni sipariş geldiğinde bu gruba otomatik bildirim gelecek.\n\n"
            f"🕐 {get_turkey_time().strftime('%H:%M:%S')} (Türkiye Saati)"
        )
        data = urllib.parse.urlencode({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': test_msg,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                return jsonify({'ok': True, 'message': 'Test bildirimi gönderildi!'})
            else:
                return jsonify({
                    'ok': False, 
                    'error': f"Telegram hatası: {result.get('description', 'bilinmeyen')}"
                }), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Bağlantı hatası: {str(e)}'}), 500


# ============ DASHBOARD ============
@bp.route('/api/dashboard-stats')
def dashboard_stats():
    if not session.get('role_yonetici'):
        return jsonify({'ok': False, 'error': 'Oturum sona erdi'}), 403
    
    today = date.today()
    branch = Branch.query.first()
    
    today_orders = Order.query.filter(
        cast(Order.created_at, Date) == today,
        Order.branch_id == branch.id
    ).all()
    daily_revenue = sum(o.total_price for o in today_orders) if today_orders else Decimal('0')
    daily_count = len(today_orders)
    
    top_products = db.session.query(
        Product.name,
        func.count(OrderPlateIngredient.id).label('count')
    ).join(
        OrderPlateIngredient, OrderPlateIngredient.ingredient_product_id == Product.id
    ).join(
        OrderPlate, OrderPlate.id == OrderPlateIngredient.order_plate_id
    ).join(
        Order, Order.id == OrderPlate.order_id
    ).filter(
        cast(Order.created_at, Date) == today,
        Order.branch_id == branch.id
    ).group_by(Product.id, Product.name).order_by(
        func.count(OrderPlateIngredient.id).desc()
    ).limit(5).all()
    
    base_products = db.session.query(
        Product.name,
        func.count(OrderPlate.id).label('count')
    ).join(
        Product, Product.id == OrderPlate.base_product_id
    ).join(
        Order, Order.id == OrderPlate.order_id
    ).filter(
        cast(Order.created_at, Date) == today,
        Order.branch_id == branch.id,
        OrderPlate.base_product_id != None
    ).group_by(Product.id, Product.name).order_by(
        func.count(OrderPlate.id).desc()
    ).limit(5).all()
    
    all_products = list(top_products) + list(base_products)
    all_products.sort(key=lambda x: x[1], reverse=True)
    top_products_list = [
        {'name': p[0], 'count': p[1]} 
        for p in all_products[:5]
    ]
    
    hourly_data = []
    for hour in range(24):
        count = db.session.query(func.count(Order.id)).filter(
            cast(Order.created_at, Date) == today,
            func.extract('hour', Order.created_at) == hour,
            Order.branch_id == branch.id
        ).scalar() or 0
        hourly_data.append({'hour': hour, 'count': int(count)})
    
    return jsonify({
        'ok': True,
        'daily_revenue': float(daily_revenue),
        'daily_count': daily_count,
        'top_products': top_products_list,
        'hourly_data': hourly_data
    })


# ============ QR ============
@bp.route('/qr/<int:table_id>')
def generate_qr(table_id):
    try:
        import qrcode
        table = Table.query.get_or_404(table_id)
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        base_url = request.host_url.rstrip('/')
        qr.add_data(f"{base_url}/menu/{table.table_number}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')
    except Exception as e:
        return f"QR Hata: {e}", 500


@bp.route('/api/whoami')
def whoami():
    roles = []
    if session.get('role_yonetici'): roles.append('yonetici')
    if session.get('role_mutfak'): roles.append('mutfak')
    if session.get('role_kasa'): roles.append('kasa')
    return jsonify({'roles': roles, 'logged_in': len(roles) > 0})


# ============ MUTFAK ============
@bp.route(f'/{ADMIN_URL_PREFIX}-mutfak')
@require_role('mutfak')
def mutfak():
    return render_template('mutfak.html', admin_prefix=ADMIN_URL_PREFIX)


@bp.route('/api/orders')
def list_orders():
    if not session.get('role_mutfak'):
        return jsonify({'error': 'yetkisiz'}), 403
    try:
        orders = Order.query.filter(
            Order.status.in_(['pending', 'preparing'])
        ).order_by(Order.created_at.asc()).all()
        
        result = []
        for o in orders:
            waffle_plates = []
            standalone_bevs = []
            standalone_desserts = []
            
            plates = OrderPlate.query.filter_by(order_id=o.id).all()
            
            for plate in plates:
                base = Product.query.get(plate.base_product_id) if plate.base_product_id else None
                if not base:
                    continue
                base_cat = Category.query.get(base.category_id) if base.category_id else None
                base_cat_type = base_cat.category_type if base_cat else 'base'
                
                if base_cat_type == 'beverage':
                    standalone_bevs.append({'name': base.name})
                    continue
                if base_cat_type == 'dessert':
                    standalone_desserts.append({'name': base.name})
                    continue
                
                ings_list = OrderPlateIngredient.query.filter_by(order_plate_id=plate.id).all()
                malzemeler = []
                icecekler = []
                dondurmalar = []
                for i in ings_list:
                    ing_prod = Product.query.get(i.ingredient_product_id) if i.ingredient_product_id else None
                    if not ing_prod:
                        continue
                    ing_cat = Category.query.get(ing_prod.category_id) if ing_prod.category_id else None
                    ing_cat_type = ing_cat.category_type if ing_cat else 'ingredient'
                    item = {'name': ing_prod.name, 'free': i.is_free}
                    if ing_cat_type == 'beverage':
                        icecekler.append(item)
                    elif ing_cat_type == 'dessert':
                        dondurmalar.append(item)
                    else:
                        malzemeler.append(item)
                
                # 🎁 Plate'in option seçimleri (kampanya bedava içecek vb.)
                opts = OrderPlateOption.query.filter_by(order_plate_id=plate.id).all()
                options_list = [{'group_name': op.group_name, 'name': op.selected_name} for op in opts]
                
                waffle_plates.append({
                    'base_name': base.name,
                    'note': plate.notes or '',
                    'malzemeler': malzemeler,
                    'icecekler': icecekler,
                    'dondurmalar': dondurmalar,
                    'options': options_list,
                    'is_combo': len(options_list) > 0  # zorunlu seçim varsa kampanya
                })
            
            table_obj = Table.query.get(o.table_id) if o.table_id else None
            table_no = table_obj.table_number if table_obj else "?"
            
            result.append({
                'id': o.id,
                'table_no': table_no,
                'customer_name': o.customer_name or 'İsimsiz',
                'customer_phone': o.customer_phone or '',
                'status': o.status,
                'total': float(o.total_price or 0),
                'note': o.customer_note or '',
                'plates': waffle_plates,
                'standalone_bevs': standalone_bevs,
                'standalone_desserts': standalone_desserts,
                'created_at': o.created_at.strftime('%H:%M')
            })
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/orders/<int:oid>/status', methods=['POST'])
def update_order_status(oid):
    if not session.get('role_mutfak'):
        return jsonify({'ok': False, 'error': 'yetkisiz'}), 403
    o = Order.query.get_or_404(oid)
    o.status = request.json.get('status', 'preparing')
    if o.status == 'served':
        o.completed_at = datetime.utcnow()
        o.payment_status = 'paid'
    db.session.commit()
    return jsonify({'ok': True})


# ============ KASA ============
@bp.route(f'/{ADMIN_URL_PREFIX}-kasa')
@require_role('kasa')
def kasa():
    return render_template('kasa.html', admin_prefix=ADMIN_URL_PREFIX)


@bp.route('/api/kasa/orders')
def kasa_list():
    if not session.get('role_kasa'):
        return jsonify({'error': 'yetkisiz'}), 403
    try:
        orders = Order.query.filter(
            Order.status == 'ready', Order.payment_status == 'unpaid'
        ).order_by(Order.created_at).all()
        
        tables_data = {}
        for o in orders:
            plates_data = []
            plates = OrderPlate.query.filter_by(order_id=o.id).all()
            for plate in plates:
                base = Product.query.get(plate.base_product_id) if plate.base_product_id else None
                base_name = base.name if base else "?"
                ings_list = OrderPlateIngredient.query.filter_by(order_plate_id=plate.id).all()
                ings = []
                for i in ings_list:
                    ing_prod = Product.query.get(i.ingredient_product_id) if i.ingredient_product_id else None
                    ings.append({'name': ing_prod.name if ing_prod else '?', 'free': i.is_free})
                # 🎁 Opsiyonlar
                opts = OrderPlateOption.query.filter_by(order_plate_id=plate.id).all()
                options_list = [{'group_name': op.group_name, 'name': op.selected_name} for op in opts]
                plates_data.append({
                    'base_name': base_name, 
                    'ingredients': ings, 
                    'options': options_list,
                    'total': float(plate.plate_total or 0)
                })
            
            table_obj = Table.query.get(o.table_id) if o.table_id else None
            table_no = table_obj.table_number if table_obj else "?"
            
            key = f'masa_{o.table_id}' if o.table_id else f'order_{o.id}'
            if key not in tables_data:
                tables_data[key] = {'table_id': o.table_id, 'table_no': table_no, 'is_takeaway': False, 'orders': [], 'total': 0}
            
            tables_data[key]['orders'].append({
                'id': o.id, 'customer_name': o.customer_name or 'İsimsiz',
                'customer_phone': o.customer_phone or '', 'customer_address': '',
                'note': o.customer_note or '', 'total': float(o.total_price or 0),
                'plates': plates_data, 'created_at': o.created_at.strftime('%H:%M')
            })
            tables_data[key]['total'] += float(o.total_price or 0)
        
        today = date.today()
        paid_today = Order.query.filter(
            cast(Order.created_at, Date) == today, Order.payment_status == 'paid'
        ).all()
        daily_revenue = sum(float(o.total_price or 0) for o in paid_today)
        daily_count = len(paid_today)
        
        return jsonify({'tables': list(tables_data.values()), 'daily_revenue': daily_revenue, 'daily_count': daily_count})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/kasa/pay-table', methods=['POST'])
def kasa_pay_table():
    if not session.get('role_kasa'):
        return jsonify({'ok': False, 'error': 'yetkisiz'}), 403
    data = request.json
    table_id = data.get('table_id')
    orders = Order.query.filter(
        Order.status == 'ready', Order.payment_status == 'unpaid', Order.table_id == table_id
    ).all()
    for o in orders:
        o.status = 'served'
        o.payment_status = 'paid'
        o.completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'count': len(orders)})


@bp.route('/api/kasa/pay-order/<int:oid>', methods=['POST'])
def kasa_pay_order(oid):
    if not session.get('role_kasa'):
        return jsonify({'ok': False, 'error': 'yetkisiz'}), 403
    o = Order.query.get_or_404(oid)
    o.status = 'served'
    o.payment_status = 'paid'
    o.completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})


@bp.route('/api/kasa/cancel/<int:oid>', methods=['POST'])
def kasa_cancel_order(oid):
    if not session.get('role_kasa'):
        return jsonify({'ok': False, 'error': 'yetkisiz'}), 403
    o = Order.query.get_or_404(oid)
    o.status = 'cancelled'
    db.session.commit()
    return jsonify({'ok': True})

# ============================================================
# 🖨️ YAZICI BOTU - Bluetooth Termal Yazıcı Sistemi (DÜZELTİLMİŞ)
# ============================================================
# Bu bloğun TAMAMINI routes.py'deki ESKİ printer bloğunun
# YERİNE koy (eski printer kodunu sil, bunu yapıştır).
# ============================================================

PRINTER_BOT_URL = "px7k2m9-iyb-yazici-botu-x9k3"


@bp.route(f'/{PRINTER_BOT_URL}')
def yazici_botu():
    """Kasanın altındaki Android telefonda sürekli açık duracak gizli sayfa."""
    return render_template('yazici_botu.html', bot_url=PRINTER_BOT_URL)


def _build_plate_data(plate):
    """Bir OrderPlate'in tüm verisini toplar (mutfak/telegram ile aynı mantık)."""
    base = Product.query.get(plate.base_product_id) if plate.base_product_id else None
    if not base:
        return None
    
    base_cat = Category.query.get(base.category_id) if base.category_id else None
    base_cat_type = base_cat.category_type if base_cat else 'base'
    
    # Standalone içecek/dondurma (plate'in kendisi içecek/dondurma ise)
    if base_cat_type == 'beverage':
        return {'base_name': base.name, 'malzemeler': [], 'icecekler': [{'name': base.name, 'free': False}], 'dondurmalar': [], 'options': [], 'standalone': True}
    if base_cat_type == 'dessert':
        return {'base_name': base.name, 'malzemeler': [], 'icecekler': [], 'dondurmalar': [{'name': base.name, 'free': False}], 'options': [], 'standalone': True}
    
    # Normal waffle tabağı
    ings_list = OrderPlateIngredient.query.filter_by(order_plate_id=plate.id).all()
    malzemeler = []
    icecekler = []
    dondurmalar = []
    for i in ings_list:
        ing_prod = Product.query.get(i.ingredient_product_id) if i.ingredient_product_id else None
        if not ing_prod:
            continue
        ing_cat = Category.query.get(ing_prod.category_id) if ing_prod.category_id else None
        ing_cat_type = ing_cat.category_type if ing_cat else 'ingredient'
        item = {'name': ing_prod.name, 'free': bool(i.is_free)}
        if ing_cat_type == 'beverage':
            icecekler.append(item)
        elif ing_cat_type == 'dessert':
            dondurmalar.append(item)
        else:
            malzemeler.append(item)
    
    # Kampanya option seçimleri
    opts = OrderPlateOption.query.filter_by(order_plate_id=plate.id).all()
    options = [{'group_name': o.group_name or '', 'name': o.selected_name or ''} for o in opts]
    
    return {
        'base_name': base.name,
        'malzemeler': malzemeler,
        'icecekler': icecekler,
        'dondurmalar': dondurmalar,
        'options': options,
        'standalone': False
    }


def _serialize_order_for_print(o):
    """Bir Order'ı fiş için tam veriyle paketler."""
    table = Table.query.get(o.table_id)
    plates = OrderPlate.query.filter_by(order_id=o.id).all()
    
    plates_data = []
    for plate in plates:
        pd = _build_plate_data(plate)
        if pd:
            plates_data.append(pd)
    
    local_time = o.created_at + timedelta(hours=3) if o.created_at else None
    time_str = local_time.strftime('%H:%M') if local_time else ''
    
    return {
        'id': o.id,
        'order_number': o.order_number or str(o.id),
        'table_number': table.table_number if table else '?',
        'customer_name': o.customer_name or 'Musteri',
        'customer_note': o.customer_note or '',
        'total': float(o.total_price or 0),
        'time': time_str,
        'plates': plates_data
    }


@bp.route('/api/printer/pending')
def printer_pending():
    """Henüz basılmamış siparişleri döndürür."""
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=15)
        unprinted = Order.query.filter(
            Order.is_printed == False,
            Order.created_at >= cutoff,
            Order.status != 'cancelled'
        ).order_by(Order.created_at.asc()).limit(10).all()
        
        result = [_serialize_order_for_print(o) for o in unprinted]
        return jsonify({'ok': True, 'orders': result, 'count': len(result)})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e), 'orders': []}), 500


@bp.route('/api/printer/order/<int:order_id>')
def printer_get_order(order_id):
    """Tek bir siparişin tam fiş verisini döndürür (yeniden yazdırma için)."""
    try:
        o = Order.query.get_or_404(order_id)
        data = _serialize_order_for_print(o)
        return jsonify({'ok': True, 'order': data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/printer/mark-printed/<int:order_id>', methods=['POST'])
def printer_mark_printed(order_id):
    """Sipariş başarıyla yazdırıldıktan sonra bot bunu çağırır."""
    try:
        order = Order.query.get_or_404(order_id)
        if not order.is_printed:
            order.is_printed = True
            order.printed_at = datetime.utcnow()
            db.session.commit()
        return jsonify({'ok': True, 'order_id': order_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/printer/reprint/<int:order_id>', methods=['POST'])
def printer_reprint(order_id):
    """Manuel yeniden yazdırma - is_printed=False yapar."""
    try:
        order = Order.query.get_or_404(order_id)
        order.is_printed = False
        order.printed_at = None
        db.session.commit()
        return jsonify({'ok': True, 'message': 'Siparis yeniden yazdirilacak'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/printer/recent')
def printer_recent():
    """Son 20 siparişi listeler (bot ekranında 'yeniden bas' butonu için)."""
    try:
        cutoff = datetime.utcnow() - timedelta(hours=12)
        orders = Order.query.filter(
            Order.created_at >= cutoff,
            Order.status != 'cancelled'
        ).order_by(Order.created_at.desc()).limit(20).all()
        
        result = []
        for o in orders:
            table = Table.query.get(o.table_id)
            local_time = o.created_at + timedelta(hours=3) if o.created_at else None
            result.append({
                'id': o.id,
                'table_number': table.table_number if table else '?',
                'customer_name': o.customer_name or 'Musteri',
                'total': float(o.total_price or 0),
                'time': local_time.strftime('%H:%M') if local_time else '',
                'is_printed': bool(o.is_printed),
                'printed_at': (o.printed_at + timedelta(hours=3)).strftime('%H:%M') if o.printed_at else None
            })
        
        return jsonify({'ok': True, 'orders': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'orders': []}), 500