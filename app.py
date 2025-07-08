
import os
from pkgutil import get_data
import re
import string
import uuid
import smtplib
from email.mime.text import MIMEText
import logging
from flask import Flask, jsonify, request, redirect, send_file, url_for, send_from_directory, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import json
from flask import session
from models import GeneralNotice, db, OrderItem, Product, Order ,User,CartItem,ActivationKey,Visit,CartAddition,SummaryReport,Offer,Coupon,PaypalOrder
from flask_migrate import Migrate
from flask_login import LoginManager,login_user,login_required, current_user,logout_user
app = Flask(__name__, template_folder='templates')
import sqlite3, smtplib, random
from flask import flash, get_flashed_messages
from datetime import date, datetime ,timedelta, timezone
from flask_migrate import Migrate
from collections import defaultdict
migrate = Migrate(app, db)
from email.mime.multipart import MIMEMultipart
ADMIN_SECRET = "mypassword123"
from sqlalchemy import func
from pytz import timezone
from werkzeug.utils import secure_filename


app.config['UPLOAD_FOLDER'] = 'images'


app.secret_key = 'your_random_secret_key'
SETTINGS_FILE = "settings.json"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# في أعلى الملف app.py
SITE_ENABLED = True  # أو False إذا أردت أن يبدأ الموقع مغلق


def load_products_from_json():
    with open('products.json', 'r', encoding='utf-8') as file:
        data = json.load(file)  # يرجع قاموس مباشرة
        return data  


with open('products.json', 'r', encoding='utf-8') as f:
    all_products = json.load(f)  # يحول JSON إلى dict مباشرة

@app.route('/products.json')
def products_json():
    return send_from_directory(os.getcwd(), 'products.json')

# تحميل متغيرات البيئة
load_dotenv()

def get_config():
    return {
        'usd_to_dzd': 250,
        'global_notice': "⚠️ مرحبًا بكم! العرض ساري حتى نهاية الأسبوع"
    }

def get_products_json():
    with open("products.json", encoding="utf-8") as f:
        return f.read()



def get_products_json_pretty():
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        print("⚠️ خطأ في تحميل ملف JSON:", e)
        return "{}"




def get_site_settings():
    if not os.path.exists(SETTINGS_FILE):
        # إذا لم يكن هناك ملف إعدادات، نرجع القيم الافتراضية
        return {
            "site_enabled": True,
            "usd_to_dzd": 250
        }

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)













def save_site_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

app.secret_key = os.getenv('SECRET_KEY', 'dev_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///orders.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['IMAGE_FOLDER'] = os.path.join(os.path.dirname(__file__), 'images')

db.init_app(app)  # ✅ الربط الصحيح
migrate = Migrate(app, db)
logging.basicConfig(level=logging.INFO)

# استيراد النماذج بعد ربط db بالتطبيق
from models import Order

with app.app_context():
    db.create_all()

with open('products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# إعدادات البريد
EMAIL_ACCOUNT = 'gamesbeststore9@gmail.com'
APP_PASSWORD  = 'yziz brml iurf cmvm'       # كلمة مرور التطبيقات 
SMTP_SERVER   = 'smtp.gmail.com'
SMTP_PORT     = 587  # لا تستخدم 465 هنا لأنه خاص بـ SSL
USD_TO_DZD    = 250
# بيانات الرسالة
recipient = 'recipient@example.com'            # المستلم
subject   = 'Test Message'
body      = 'This is a test email sent using Python and Gmail SMTP.'

def send_email(to, subject, body):
    try:
        msg = MIMEText(body, 'html', 'utf-8')

        msg['From'] = EMAIL_ACCOUNT
        msg['To'] = to
        msg['Subject'] = subject

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(EMAIL_ACCOUNT, APP_PASSWORD)
            smtp.send_message(msg)

        print(f"✅ تم إرسال البريد إلى {to}")

    except Exception as e:
        print(f"❌ خطأ أثناء إرسال البريد: {e}")


def send_verification_email(to_email, code):
    subject = "رمز التحقق من بريدك الإلكتروني"
    body = f"""
    <html>
    <body style="font-family: Arial; direction: rtl; text-align: right;">
        <h2>🔐 رمز التحقق</h2>
        <p>مرحبًا،</p>
        <p>رمز التحقق الخاص بك هو:</p>
        <h1 style="color: blue;">{code}</h1>
        <p>يرجى إدخال هذا الرمز في صفحة التحقق لإكمال عملية التسجيل.</p>
        <p>شكرًا لاستخدامك متجرنا.</p>
    </body>
    </html>
    """
    send_email(to_email, subject, body)



@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory("images", filename)




@app.route('/images/<filename>')
def image(filename):
    return send_from_directory(app.config['IMAGE_FOLDER'], filename)

 
@app.route("/")
def index():
    # 1. تسجيل الزيارة
    ip = request.remote_addr
    visit = Visit(ip_address=ip, is_authenticated=current_user.is_authenticated)
    db.session.add(visit)
    db.session.commit()

    # 2. التحقق من الحظر
    if current_user.is_authenticated:
        if current_user.is_banned:
            return "🚫 حسابك محظور نهائيًا", 403
        if current_user.banned_until and current_user.banned_until > datetime.utcnow():
            return f"⏳ حسابك محظور مؤقتًا حتى {current_user.banned_until.strftime('%Y-%m-%d %H:%M')}", 403

    # ✅ جلب المنتجات من قاعدة البيانات بدل products.json
    products = Product.query.all()

    # ✅ تحميل العروض الفعالة
    today = date.today()
    active_offers = Offer.query.filter(
        Offer.start_date <= today,
        Offer.end_date >= today,
        Offer.is_active == True
    ).all()

    # ✅ ربط العروض بكود المنتج
    offers_dict = {}
    for offer in active_offers:
        if offer.product:
            offers_dict[offer.product.name] = offer


            print("✅ العروض الفعالة:")
    for k, v in offers_dict.items():
     print(f"{k} → خصم {v.discount}% من {v.start_date} إلى {v.end_date}")


    return render_template("index.html", products=products, offers=offers_dict)




   

    

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not full_name or not email or not password:
            flash("❗ جميع الحقول مطلوبة")
            return redirect("/register")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("❌ البريد الإلكتروني مستخدم بالفعل")
            return redirect("/register")

        code = str(random.randint(100000, 999999))

        new_user = User(
            full_name=full_name,
            email=email,
            is_verified=False,                            
            verification_code=code
        )
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            print("✅ تم الحفظ في قاعدة البيانات")

            send_verification_email(email, code)
            session['verify_email'] = email
            return redirect("/verify")
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطأ أثناء حفظ المستخدم: {e}")
            flash("حدث خطأ أثناء إنشاء الحساب")
            return redirect("/register")

    return render_template("register.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        email = request.form.get("email")
        code = request.form.get("code")

        if not email or not code:
            flash("❗ يجب إدخال البريد الإلكتروني ورمز التحقق")
            return redirect("/verify")

        user = User.query.filter_by(email=email, verification_code=code).first()
        if user:
            user.is_verified = True
            user.verification_code = None
            db.session.commit()
            flash("✅ تم التحقق، يمكنك تسجيل الدخول الآن")
            session.pop('verify_email', None)
            return redirect("/login")
        else:
            flash("❌ رمز التحقق أو البريد غير صحيح")
            return redirect("/verify")

    email = session.get("verify_email", "")
    return render_template("verify.html", email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user:
            print("❌ المستخدم غير موجود")
            flash("❌ البريد غير مسجل")
            return redirect("/login")

        if not user.is_verified:
            print("❌ المستخدم غير مفعل")
            flash("❌ يجب التحقق من البريد الإلكتروني أولاً")
            return redirect("/login")

        if not user.check_password(password):
            print("❌ كلمة المرور غير صحيحة")
            flash("❌ كلمة المرور غير صحيحة")
            return redirect("/login")

        login_user(user)
        session["user_email"] = user.email
        session["is_admin"] = user.is_admin
        print(f"✅ تسجيل دخول ناجح: {user.email}")
        flash("✅ تم تسجيل الدخول بنجاح")
        return redirect("/")
               # تحقق من حالة الحظر
        if user.is_banned:
                return "🚫 حسابك محظور نهائيًا", 403

        if user.ban_until and user.ban_until > datetime.utcnow():
                return f"⏳ حسابك محظور مؤقتًا حتى {user.ban_until.strftime('%Y-%m-%d %H:%M')}", 403

    return render_template("login.html")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/dashboard")
@login_required
def dashboard():
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", orders=user_orders, name=current_user.full_name)
    return f"✅ تم تسجيل الدخول بنجاح. مرحبًا، {current_user.full_name}"
@app.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect("/login")


@app.route('/cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', cart_items=cart_items)



@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'GET':
        return render_template('checkout.html', email=current_user.email)

    data = request.get_json()
    names = data.get('names')
    payment_method = data.get('payment_method')
    coupon = data.get("coupon")

    if not names:
        return jsonify({"error": "❗ لم يتم اختيار أي منتج"}), 400

    with open('products.json', 'r', encoding='utf-8') as f:
        all_products = json.load(f)

    order_uuid = str(uuid.uuid4())[:8].upper()

    new_order = Order(
        user_id=current_user.id,
        email=current_user.email,
        order_id=order_uuid,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.session.add(new_order)
    db.session.flush()

    total_usd = 0
    detailed_products = []

    for code in names:
        p = all_products.get(code)
        if not p:
            db.session.rollback()
            return jsonify({"error": f"❌ المنتج {code} غير موجود"}), 400

        total_usd += p["price"]
        detailed_products.append(p)

        db.session.add(OrderItem(
            order_id=new_order.id,
            product_id=code,
            product_name=p.get("name", code),
            price=p["price"],
            category=p.get("category"),
            key_type=p.get("key_type"),
            restricted_country=p.get("restricted_country")
        ))

    # ✅ تطبيق الخصم
    discount_amount = 0
    if coupon:
        if coupon.get("type") == "percent":
            discount_amount = total_usd * (coupon.get("value", 0) / 100)
        elif coupon.get("type") == "fixed":
            discount_amount = coupon.get("value", 0)

    final_total = round(max(total_usd - discount_amount, 0), 2)

    db.session.commit()

    return jsonify({
        "email": current_user.email,
        "order_id": order_uuid,
        "items": detailed_products,
        "total_usd": total_usd,
        "discount": round(discount_amount, 2),
        "final_total": final_total
    }), 200


          
@app.route('/upload')
@login_required
def upload():
    return render_template('upload.html', email=current_user.email)

@app.route('/policy')

def policy():
     return render_template('policy.html')

@app.route('/confirm_payment', methods=['POST'])
@login_required
def confirm_payment():
    email = request.form.get('email')
    txn_id = request.form.get('transaction_id')


    order = Order.query.filter_by(email=email, status='pending', user_id=current_user.id).order_by(Order.id.desc()).first()
    if not email or not txn_id:
        return "❗ البريد الإلكتروني ورمز العملية مطلوبان", 400

    order = Order.query.filter_by(email=email, status='pending').order_by(Order.id.desc()).first()
    if not order:
        return jsonify({'error': 'الطلب غير موجود'}), 404

    order.transaction_id = txn_id
    db.session.commit()

    # إرسال روابط الموافقة للبائع
    approve_link = request.host_url + f"approve_order?order_id={order.order_id}"
    reject_link = request.host_url + f"reject_order?order_id={order.order_id}"

    send_email(EMAIL_ACCOUNT, "🟡 طلب جديد", f"✅ للموافقة: {approve_link}\n❌ للرفض: {reject_link}")

    return jsonify({'success': True, 'order_id': order.order_id})

@app.route('/order_status')
def order_status():
    order_id = request.args.get('order_id')

    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({'error': 'الطلب غير موجود'}), 404

    return jsonify({'status': order.status})





@app.route('/approve_order')
def approve_order():
    order_id = request.args.get('order_id')
    if not order_id:
        return "❗ رقم الطلب غير موجود في الرابط"

    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return "❌ الطلب غير موجود"

    if order.status == 'verified':
        return "✅ تم تأكيد هذا الطلب بالفعل"
    elif order.status == 'rejected':
        return "⚠️ لا يمكن تأكيد طلب تم رفضه"

    # تحديث الحالة
    order.status = 'verified'
    db.session.commit()

    # حساب الإجمالي
    total_usd = sum(item.price for item in order.items)
    total_dzd = round(total_usd * USD_TO_DZD, 2)

    # ✅ بناء محتوى الرسالة (بدون قالب خارجي)
    product_details = ""
    for item in order.items:
        product_details += f"""
        🟢 <b>اسم المنتج:</b> {item.product_name}<br>
        💰 السعر: {item.price} USD<br>
        🧩 <b>النوع:</b> {item.key_type}<br>
        🗂️ <b>الفئة:</b> {item.category}<br>
        🌍 الدولة المقيدة: {item.restricted_country or "لا يوجد"}<br><br>
        """

    message = f"""
    ✅ <b>تم تأكيد الطلب بنجاح</b><br><br>
    🆔 <b>رقم الطلب:</b> {order.order_id}<br>
    🔑 <b>رقم العملية:</b> {order.transaction_id}<br>
    💵 <b>السعر الإجمالي:</b> {total_dzd} DZD ({total_usd:.2f} USD)<br><br>
    📧 <b>بريد العميل:</b> {order.email}<br>
    <b>تفاصيل المنتجات:</b><br>
    {product_details}
    <hr>
    شكرًا لثقتك بنا 🌟
    """

    # إرسال للعميل والبائع
    send_email(order.email, "✅ تم تأكيد طلبك", message)
    send_email(EMAIL_ACCOUNT, "📦 طلب مؤكد جديد", message)

    return "✅ تم تأكيد الطلب وإرسال إشعار للعميل والبائع."

@app.route('/reject_order')
def reject_order():
    order_id = request.args.get('order_id')
    order = Order.query.filter_by(order_id=order_id, status='pending').first()

    if not order:
        return "❌ الطلب غير موجود أو مرفوض سابقًا"

    order.status = 'rejected'
    db.session.commit()

    msg = f"❌ نأسف، تم رفض طلبك رقم: {order.order_id}.\nإذا كان لديك أي استفسار، يرجى التواصل معنا عبر البريد."
    send_email(order.email, "❌ تم رفض الطلب", msg)

    return "❌ تم رفض الطلب وإرسال إشعار للعميل."

    
@app.route('/product/<product_code>')
def show_product(product_code):
    product = products.get(product_code) # type: ignore
    if not product:
        abort(404) # type: ignore
        return render_template('product.html',
                           product_name=product['name'],
                           product_description=product['description'],
                           product_image=product['image'])
 
    




 

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get("is_admin_authenticated"):
        if request.method == "POST":
            password = request.form.get("password")
            if password == ADMIN_SECRET:
                session["is_admin_authenticated"] = True
                return redirect(url_for('admin_dashboard'))
            else:
                return "❌ كلمة المرور غير صحيحة", 403
        return render_template("admin_login.html")

    site_settings = get_site_settings()

    keys_by_product = defaultdict(list)
    all_keys = ActivationKey.query.order_by(
        ActivationKey.product_name,
        ActivationKey.created_at.desc()
    ).all()
    for key in all_keys:
       keys_by_product[key.product_name].append({
    'key_code': key.key_code,
    'status': key.status,
    'created_at': key.created_at.strftime('%Y-%m-%d %H:%M')
})


        
         
        
    orders = Order.query.order_by(Order.created_at.desc()).all()
    users = User.query.order_by(User.registered_at.desc()).all()

    top_products = db.session.query(
        OrderItem.product_name,
        db.func.count(OrderItem.id)
    ).group_by(OrderItem.product_name).order_by(db.func.count(OrderItem.id).desc()).limit(5).all()

    top_product_names = [item[0] for item in top_products]
    top_product_counts = [item[1] for item in top_products]

    available_count = ActivationKey.query.filter_by(status='available').count()
    sold_count = ActivationKey.query.filter_by(status='sold').count()

    try:
        cart_adds = db.session.query(
            CartAddition.product_name,
            db.func.count(CartAddition.id)
        ).group_by(CartAddition.product_name).order_by(db.func.count(CartAddition.id).desc()).limit(5).all()
        cart_product_names = [item[0] for item in cart_adds]
        cart_product_counts = [item[1] for item in cart_adds]
    except Exception:
        cart_product_names = []
        cart_product_counts = []

    verified_users_count = User.query.filter_by(is_verified=True).count()

    # ✅ حساب عدد الزوار لكل ساعة بالتوقيت المحلي
    ALGERIA_TZ = timezone("Africa/Algiers")
    today = datetime.now(ALGERIA_TZ).date()

    hourly_labels = [f"{h}:00" for h in range(24)]
    hourly_counts = []
    for hour in range(24):
        local_hour = datetime.combine(today, datetime.min.time()) + timedelta(hours=hour)
        utc_hour_start = local_hour.astimezone(timezone("UTC"))
        utc_hour_end = (local_hour + timedelta(hours=1)).astimezone(timezone("UTC"))
        count = db.session.query(Visit).filter(
            Visit.visited_at >= utc_hour_start,
            Visit.visited_at < utc_hour_end
        ).count()
        hourly_counts.append(count)

    # ✅ الزوار اليوميين
    now = datetime.utcnow()
    today = now.date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    daily_guests = []
    daily_authenticated = []
    daily_labels = []
    arabic_days = {
        'Monday': 'الإثنين',
        'Tuesday': 'الثلاثاء',
        'Wednesday': 'الأربعاء',
        'Thursday': 'الخميس',
        'Friday': 'الجمعة',
        'Saturday': 'السبت',
        'Sunday': 'الأحد'
    }

    for day in last_7_days:
        guest_count = db.session.query(Visit).filter(
            func.date(Visit.visited_at) == day,
            Visit.is_authenticated == False
        ).count()
        auth_count = db.session.query(Visit).filter(
            func.date(Visit.visited_at) == day,
            Visit.is_authenticated == True
        ).count()
        daily_guests.append(guest_count)
        daily_authenticated.append(auth_count)
        daily_labels.append(arabic_days[day.strftime('%A')])

    # ✅ الزوار الأسبوعيين
    weekly_labels = []
    weekly_counts = []
    for i in range(3, -1, -1):
        start_week = today - timedelta(days=today.weekday() + i * 7)
        end_week = start_week + timedelta(days=6)
        label = f"الأسبوع {4 - i}"
        count = db.session.query(Visit).filter(
            Visit.visited_at >= start_week,
            Visit.visited_at <= end_week
        ).count()
        weekly_labels.append(label)
        weekly_counts.append(count)

    # ✅ الزوار الشهريين
    monthly_labels = []
    monthly_counts = []
    arabic_months = {
        'January': 'يناير', 'February': 'فبراير',
        'March': 'مارس', 'April': 'أبريل', 'May': 'مايو',
        'June': 'يونيو', 'July': 'يوليو', 'August': 'أغسطس',
        'September': 'سبتمبر', 'October': 'أكتوبر',
        'November': 'نوفمبر', 'December': 'ديسمبر'
    }

    daily_counts = [5, 8, 3, 7, 10, 12, 4]  # بيانات وهمية إن كنت تستخدمها

    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        label = arabic_months[month_start.strftime('%B')]
        count = db.session.query(Visit).filter(
            Visit.visited_at >= month_start,
            Visit.visited_at < next_month
        ).count()
        monthly_labels.append(label)
        monthly_counts.append(count)

        products_file = "templates/partials/products.html"
    products_list = []

    if os.path.exists(products_file):
        with open(products_file, "r", encoding="utf-8") as f:
            content = f.read()
            # استخراج كل كتلة منتج <div class="product">...</div>
            products_list = re.findall(r'(<div class="product">.*?</div>)', content, re.DOTALL)
        offers_list = Offer.query.filter_by(type='offer', is_active=True).all()
        offers_dict = {offer.product.name: offer for offer in offers_list if offer.product}


    notices = GeneralNotice.query.order_by(GeneralNotice.created_at.desc()).all()

    return render_template(
        "admin_dashboard.html",
        orders=orders,
        now=now,
        keys_by_product=keys_by_product,
        users=users,
        verified_users_count=verified_users_count,
        daily_labels=daily_labels,
        daily_guests=daily_guests,
        daily_authenticated=daily_authenticated,
        weekly_labels=weekly_labels,
        weekly_counts=weekly_counts,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts,
        top_product_names=top_product_names,
        top_product_counts=top_product_counts,
        available_count=available_count,
        sold_count=sold_count,
        cart_product_names=cart_product_names,
        cart_product_counts=cart_product_counts,
        site_settings=site_settings,
        config=get_config(),
        products_json=get_products_json(),
        hourly_labels=hourly_labels,
        hourly_counts=hourly_counts,
        daily_counts=daily_counts,
        offers=offers_dict,
        products_list=products_list,
         notices=notices
    )





@app.route('/add_code', methods=['POST'])
def add_code():
    if not session.get("is_admin_authenticated"):
        return "ممنوع", 403

    product_name = request.form.get("product_name")
    key_code = request.form.get("key_code")

    new_code = ActivationKey(product_name=product_name, key_code=key_code)
    db.session.add(new_code)
    db.session.commit()



    return redirect('/admin_dashboard')



@app.route('/send_key', methods=['POST'])
def send_key():
    email = request.form.get('email')
    order_id = request.form.get('order_id')
    product_name = request.form.get('product_name')
    activation_code = request.form.get('activation_code')
    note = request.form.get('note')

    key = ActivationKey.query.filter_by(product_name=product_name, key_code=activation_code, status='available').first()
    if not key:
        return "❌ الكود غير متوفر أو تم استخدامه", 400

    # تحديث الحالة
    key.status = 'sold'
    db.session.commit()

    # إرسال البريد
    success = send_activation_email(email, product_name, activation_code, note)
    if success:
        flash("✅ تم إرسال الكود بنجاح وتحديث حالته")
    else:
        flash("⚠️ تم تحديث الكود، لكن فشل في إرسال البريد")

    return redirect(url_for('admin_dashboard'))


def send_activation_email(to_email, product_name, code_value, notes=None):
    sender_email = "gamesbeststore9@gmail.com"
    sender_password = "yziz brml iurf cmvm"

    subject = f"🔑 رمز تفعيل منتجك - {product_name}"

    # النسخة النصية الاحتياطية
    text_body = f"""
    عزيزي العميل،

    إليك تفاصيل منتجك:

    🕹️ المنتج: {product_name}
    🔑 رمز التفعيل: {code_value}

    {f"📝 ملاحظات:\n{notes}" if notes else ""}

    شكرًا لثقتك بنا.
    """

    # النسخة HTML الأساسية
    html_body = f"""
    <html dir="rtl" lang="ar">
      <body style="font-family: Tahoma, sans-serif; background-color: #f7f7f7; padding: 20px; color: #333;">
        <div style="max-width: 600px; margin: auto; background-color: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
          <h2 style="color: #4fc3f7;">🔑 تم تسليم رمز تفعيل منتجك</h2>
          <p>مرحبًا عزيزي العميل،</p>
          <p>شكرًا لثقتك بنا. إليك تفاصيل منتجك:</p>

          <ul style="list-style: none; padding: 0;">
            <li><strong>🕹️ المنتج:</strong> {product_name}</li>
            <li><strong>🔑 رمز التفعيل:</strong> <span style="color: green; font-weight: bold;">{code_value}</span></li>
            {f"<li><strong>📝 ملاحظات:</strong> {notes}</li>" if notes else ""}
          </ul>

          <p style="margin-top: 20px;">📩 لا تتردد في التواصل معنا إذا واجهت أي مشكلة.</p>
          <p>مع تحيات،<br><strong>فريق Games Best Store</strong></p>

          <div style="margin-top: 30px; text-align: center; font-size: 13px; color: #888;">
            هذا البريد تم إنشاؤه تلقائيًا، الرجاء عدم الرد عليه.
          </div>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # إرفاق النسختين
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"خطأ أثناء إرسال البريد: {e}")
        return False
    

@app.route("/user_action", methods=["POST"])
def user_action():
    user_id = request.form.get("user_id")
    action = request.form.get("action")
    user = User.query.get(user_id)

    if not user:
        return "❌ المستخدم غير موجود", 404

    if action == "ban_temp":
        user.banned_until = datetime.utcnow() + timedelta(days=7)
        user.status = "banned"
    elif action == "ban_permanent":
        user.banned_until = None
        user.status = "banned"
    elif action == "unban":
        user.banned_until = None
        user.status = "active"
    elif action == "delete":
        db.session.delete(user)

    db.session.commit()
    flash("✅ تم تنفيذ الإجراء بنجاح")
    return redirect(url_for("admin_dashboard"))


@app.route('/ban_user', methods=['POST'])
def ban_user():
    user_id = request.form.get('user_id')
    duration = request.form.get('ban_duration')

    user = User.query.get(user_id)
    if not user:
        flash("❌ المستخدم غير موجود")
        return redirect(url_for('admin_dashboard'))

    if duration == "permanent":
        user.is_banned = True
        user.ban_until = None
    else:
        user.is_banned = False
        user.ban_until = datetime.utcnow() + timedelta(days=int(duration))

    db.session.commit()
    flash("✅ تم حظر المستخدم بنجاح")
    return redirect(url_for('admin_dashboard'))


@app.route('/unban_user', methods=['POST'])
def unban_user():
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if user:
        user.is_banned = False
        user.ban_until = None
        db.session.commit()
        flash("✅ تم رفع الحظر عن المستخدم")
    return redirect(url_for('admin_dashboard'))




def generate_summary_if_needed():
    today = datetime.utcnow()
    week_label = f"{today.year}-W{today.isocalendar()[1]}"
    month_label = today.strftime("%Y-%m")

    # 🔄 تحقق إذا الملخص موجود
    existing_week = SummaryReport.query.filter_by(period_type='week', period_label=week_label).first()
    existing_month = SummaryReport.query.filter_by(period_type='month', period_label=month_label).first()

    if not existing_week and today.weekday() == 6:  # يوم الأحد
        report = SummaryReport(
            period_type='week',
            period_label=week_label,
            total_visits=Visit.query.count(),
            total_users=User.query.count(),
            total_orders=Order.query.count()
        )
        db.session.add(report)
        db.session.commit()

    if not existing_month and today.day == 1:
        report = SummaryReport(
            period_type='month',
            period_label=month_label,
            total_visits=Visit.query.count(),
            total_users=User.query.count(),
            total_orders=Order.query.count()
        )
        db.session.add(report)
        db.session.commit()

@app.route("/toggle_site_status", methods=["POST"])
def toggle_site_status():
    if not session.get("is_admin_authenticated"):
        return "🚫 غير مصرح", 403

    settings = get_site_settings()
    new_status = request.form.get("new_status") == "true"

    if not new_status:
        # إذا الموقع سيتم إيقافه
        selected_reason = request.form.get("selected_reason", "")
        custom_reason = request.form.get("custom_reason", "").strip()

        messages = {
            "maintenance": "🛠️ نقوم حاليًا بأعمال صيانة، نعود قريبًا بإذن الله.",
            "weekend": "💤 تم إغلاق الموقع مؤقتًا بمناسبة عطلة نهاية الأسبوع.",
            "update": "🔄 يتم حاليًا إجراء تحديثات على النظام، شكرًا لصبركم.",
            "security": "🔒 الموقع مغلق مؤقتًا لإجراء فحص أمني وتحسين الحماية.",
            "custom": custom_reason or "🚧 الموقع غير متاح مؤقتًا."
        }

        settings["site_enabled"] = False
        settings["maintenance_message"] = messages.get(selected_reason, "🚧 الموقع غير متاح مؤقتًا.")
    else:
        # إذا إعادة تشغيل
        settings["site_enabled"] = True
        settings["maintenance_message"] = ""

    save_site_settings(settings)
    return redirect(url_for("admin_dashboard"))




@app.route('/admin/edit_products_json', methods=['POST'])
def edit_products_json():
    try:
        new_content = request.form.get('json_content', '').strip()

        # تأكد أن المحتوى قابل للتحويل إلى JSON
        json.loads(new_content)  # ✅ لو فيه خطأ في الصيغة، سيتوقف هنا

        # ثم احفظه في الملف
        with open("products.json", "w", encoding="utf-8") as f:
            f.write(new_content)

        return redirect(url_for('admin_dashboard'))  # ✅ رجع للمشرف بعد الحفظ
    except Exception as e:
        return f"❌ حدث خطأ أثناء حفظ JSON: {e}", 400




@app.route('/apply_coupon', methods=['POST'])
def apply_coupon():
    code = request.form.get('coupon_code')
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()

    if not coupon:
        return jsonify({'success': False, 'message': '❌ الكوبون غير صالح'})

    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        return jsonify({'success': False, 'message': '⌛ انتهت صلاحية الكوبون'})

    # ✅ إرجاع خصائص إضافية
    return jsonify({
        'success': True,
        'message': f'✅ تم تطبيق الكوبون: -{coupon.discount_value} ({coupon.discount_type})',
        'discount_type': coupon.discount_type,
        'discount_value': coupon.discount_value,
        'code': coupon.code,
        'restricted_products': coupon.restricted_products  # إن وُجدت
    })





@app.route("/current_coupon")
def current_coupon():
    coupon = session.get("applied_coupon")
    if not coupon:
        return jsonify({"success": False})
    return jsonify({
        "success": True,
        "discount_type": coupon["discount_type"],
        "discount_value": coupon["discount_value"]
    })



@app.route("/admin/add_coupon", methods=["POST"])
def add_coupon():
    if not session.get("is_admin_authenticated"): return "🚫", 403

    code = request.form["code"]
    discount_value = float(request.form["discount_value"])
    discount_type = request.form["discount_type"]
    expires_at = request.form.get("expires_at")
    restricted = request.form.get("restricted_products")

    coupon = Coupon(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        restricted_products=restricted if restricted else None,
        expires_at=datetime.strptime(expires_at, "%Y-%m-%d") if expires_at else None
    )
    db.session.add(coupon)
    db.session.commit()
    return redirect("/admin_dashboard")







@app.route('/admin/add_offer', methods=['POST'])
def add_offer():
    product_code = request.form['product_code']
    discount = int(request.form['discount'])
    highlight_text = request.form.get('highlight_text', '')
    start_date = datetime.strptime(request.form['start_date'], "%Y-%m-%d").date()
    end_date = datetime.strptime(request.form['end_date'], "%Y-%m-%d").date()

    product = Product.query.filter_by(name=product_code).first()
    if not product:
        flash("❌ لم يتم العثور على المنتج بهذا الكود.")
        return redirect('/admin_dashboard')

    offer = Offer(
        product_id=product.id,
        discount=discount,
        highlight_text=highlight_text,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        type='offer'
    )
    db.session.add(offer)
    db.session.commit()

   

    flash("✅ تم إضافة العرض بنجاح!")
    return redirect('/admin_dashboard')






@app.route('/admin/delete_offer', methods=['POST'])
def delete_offer():
    offer_id = request.form.get('offer_id')
    offer = Offer.query.get(offer_id)

    if offer:
        product = offer.product
        db.session.delete(offer)
        db.session.commit()

        

        flash(f"✅ تم حذف العرض عن المنتج {product.name}")
    else:
        flash("❌ لم يتم العثور على العرض")

    return redirect('/admin_dashboard')




@app.route("/admin/add_home_product", methods=["POST"])
def add_home_product():
    name = request.form['product_name']
    desc = request.form['description']
    price = float(request.form['usd_price'])
    image_file = request.files['image_file']

    # الكود المختصر للمنتج
    product_code = name.strip().upper().replace(" ", "")[:10]

    if image_file:
        filename = secure_filename(image_file.filename)
        image_path = os.path.join('images', filename)  # 🔄 حر وليس static
        image_file.save(image_path)

        image_url = f"images/{filename}"  # 🔄 يظهر في HTML مباشرة


        product_html = f"""
<div class="product">
  <img src="{image_url}" alt="{name}">
  <h3>{product_code}</h3>

  {{% if '{product_code}' in offers %}}
    {{% set offer = offers['{product_code}'] %}}
    <div class="offer-banner" style="color: red;">
      🎯 عرض خاص من {{{{ offer.start_date }}}} إلى {{{{ offer.end_date }}}}
    </div>
    <p>
      <del>{price}$</del>
      <span style="color: green;">
        {{{{ ( {price} - ( {price} * offer.discount / 100 ) ) | round(2) }}}}$
      </span>
    </p>
  {{% else %}}
    <p>{price}$</p>
  {{% endif %}}

  <p>{desc}</p>
  <button class="btn" onclick="addToCart('{product_code}', {price})">أضف إلى السلة</button>
  <button class="btn" onclick="buyNow('{product_code}')">اشتري الآن</button>
</div>
"""

        with open("templates/partials/products.html", "a", encoding="utf-8") as f:
            f.write(product_html + "\n")

    return redirect("/admin_dashboard")





@app.route("/admin/update_product/<int:index>", methods=["POST"])
def update_product(index):
    new_html = request.form['product_html'].strip() + "\n"

    with open("templates/partials/products.html", "r", encoding="utf-8") as f:
        content = f.read()
        blocks = re.findall(r'(<div class="product">.*?</div>)', content, re.DOTALL)

    if 0 <= index < len(blocks):
        blocks[index] = new_html
        new_content = "\n".join(blocks)

        with open("templates/partials/products.html", "w", encoding="utf-8") as f:
            f.write(new_content)

    return redirect("/admin_dashboard")




@app.route("/admin/delete_product/<int:index>")
def delete_product(index):
    with open("templates/partials/products.html", "r", encoding="utf-8") as f:
        content = f.read()
        blocks = re.findall(r'(<div class="product">.*?</div>)', content, re.DOTALL)

    if 0 <= index < len(blocks):
        blocks.pop(index)
        new_content = "\n".join(blocks)

        with open("templates/partials/products.html", "w", encoding="utf-8") as f:
            f.write(new_content)

    return redirect("/admin_dashboard")



@app.route("/product/<code>")
def product_page(code):
    print(f"✅ تم طلب صفحة المنتج: {code}")

    try:
        with open("product_descriptions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            print("📂 المفاتيح الموجودة في JSON:", data.keys())
    except Exception as e:
        return f"❌ خطأ في تحميل الملف: {e}", 500

    product = data.get(code)
    if not product:
        print("🚫 لم يتم العثور على المنتج:", code)
        return "❌ المنتج غير موجود", 404

    return render_template("product_details.html", product=product)



@app.route("/delete_code", methods=["POST"])
def delete_code():
    if not session.get("is_admin_authenticated"):
        return "ممنوع", 403

    key_code = request.form.get("key_code")
    key = ActivationKey.query.filter_by(key_code=key_code).first()
    if key:
        db.session.delete(key)
        db.session.commit()
        flash("✅ تم حذف الكود بنجاح")
    else:
        flash("❌ لم يتم العثور على الكود")
    return redirect(url_for("admin_dashboard"))




@app.route("/edit_code", methods=["POST"])
def edit_code():
    if not session.get("is_admin_authenticated"):
        return "ممنوع", 403

    key_code = request.form.get("key_code")
    new_name = request.form.get("new_product_name")

    key = ActivationKey.query.filter_by(key_code=key_code).first()
    if key:
        key.product_name = new_name
        db.session.commit()
        flash("✅ تم تحديث اسم المنتج للكود")
    else:
        flash("❌ لم يتم العثور على الكود")
    return redirect(url_for("admin_dashboard"))




def generate_code(length=12):
    """توليد كود عشوائي مكون من حروف كبيرة وأرقام"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))



@app.context_processor
def inject_general_notice():
    notice = GeneralNotice.query.filter_by(is_active=True).order_by(GeneralNotice.created_at.desc()).first()
    return dict(general_notice=notice)





@app.route("/admin/add_notice", methods=["POST"])
def add_notice():
    text = request.form.get("text")
    color = request.form.get("color")
    type_ = request.form.get("type")

    notice = GeneralNotice(text=text, color=color, type=type_, is_active=True)
    db.session.add(notice)
    db.session.commit()
    flash("✅ تم إضافة الإشعار العام بنجاح!")
    return redirect("/admin_dashboard")


@app.route("/admin/delete_notice", methods=["POST"])
def delete_notice():
    notice_id = request.form.get("notice_id")
    notice = GeneralNotice.query.get(notice_id)
    if notice:
        db.session.delete(notice)
        db.session.commit()
        flash("🗑️ تم حذف الإشعار بنجاح.")
    else:
        flash("❌ لم يتم العثور على الإشعار.")
    return redirect("/admin_dashboard")




@app.route('/paypal-success', methods=['POST'])
def paypal_success():
    data = request.json
    payer_email = data.get('payerEmail')
    full_name = data.get('fullName')
    paypal_order_id = data.get('orderID')

    if not payer_email or not paypal_order_id:
        return jsonify({"error": "بيانات ناقصة"}), 400

    cart = session.get("cart_items")
    if not cart:
        return jsonify({"error": "السلة مفقودة"}), 400

    # تحميل المنتجات
    with open("products.json", "r", encoding="utf-8") as f:
        products_data = json.load(f)

    selected_products = []
    total_usd = 0
    for code in cart:
        product = products_data.get(code)
        if product:
            selected_products.append(product)
            total_usd += product['price']

    usd_to_dzd = 250  # ← عدل حسب إعدادك
    total_dzd = total_usd * usd_to_dzd

    # توليد رقم طلب
    order_code = generate_code(8)  # توليد عشوائي مثلاً

    # إرسال رسالة إلى البائع فقط (أنت)
    from_email = "gamesbeststore9@gmail.com"
    to_email = from_email  # إرسال لنفسك
    subject = f"✅ تم تأكيد طلب PayPal رقم {order_code}"

    # نص الرسالة HTML
    products_text = ""
    for p in selected_products:
        products_text += f"""
        <hr>
        🟢 <b>اسم المنتج:</b> {p['name']}<br>
        💰 <b>السعر:</b> {p['price']} USD<br>
        🧩 <b>النوع:</b> {p['type']}<br>
        🗂️ <b>الفئة:</b> {p['category']}<br>
        🌍 <b>الدولة المقيدة:</b> {p.get('region', 'غير محددة')}<br>
        """

    html_body = f"""
    ✅ <b>تم تأكيد الطلب بنجاح</b><br><br>
    🆔 <b>رقم الطلب:</b> {order_code}<br>
    🔑 <b>رقم العملية:</b> {paypal_order_id}<br>
    💵 <b>السعر الإجمالي:</b> {total_dzd:.0f} DZD ({total_usd:.2f} USD)<br>
    📧 <b>بريد العميل:</b> {payer_email}<br>
    💳 <b>وسيلة الدفع:</b> PayPal<br><br>
    <b>تفاصيل المنتجات:</b><br>
    {products_text}
    """

    send_email(to=to_email, subject=subject, body=html_body)

    # 🧾 حفظ الطلب في قاعدة البيانات (اختياري)
    order = Order(
        email=payer_email,
        name=full_name,
        payment_method="paypal",
        total_amount=total_usd,
        status="تم الدفع",
        products=json.dumps(selected_products),
        code=order_code,
        transaction_id=paypal_order_id
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({"success": True})




@app.route('/checkout_success')
def checkout_success():
    latest_order = PaypalOrder.query.order_by(PaypalOrder.id.desc()).first()
    return render_template("checkout_success.html", order=latest_order)



@app.route('/my_orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)


@app.route('/profile')
@login_required
def profile():
    user = current_user
    total_orders = Order.query.filter_by(email=user.email).count()
    verified_orders = Order.query.filter_by(email=user.email, status='verified').count()
    pending_orders = Order.query.filter_by(email=user.email, status='pending').count()
    rejected_orders = Order.query.filter_by(email=user.email, status='rejected').count()
    if current_user.is_banned:
        return "🚫 حسابك محظور نهائيًا", 403

    if current_user.banned_until and current_user.banned_until > datetime.utcnow():
        return f"⏳ حسابك محظور مؤقتًا حتى {current_user.banned_until.strftime('%Y-%m-%d %H:%M')}", 403
    return render_template("profile.html", user=user,
                           total_orders=total_orders,
                           verified_orders=verified_orders,
                           pending_orders=pending_orders,
                           rejected_orders=rejected_orders)



@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({'success': False, 'message': '❌ معرف المنتج مطلوب'})

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': '❌ المنتج غير موجود'})

    # تحقق إن كان المنتج موجود بالفعل في السلة
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(item)

    db.session.commit()
    return jsonify({'success': True, 'message': '✅ تمت إضافة المنتج إلى السلة'})




def clear_cart(user_id):
    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()







@app.route("/show-users")
def show_users():
    users = User.query.all()
    result = "<h2>📋 المستخدمون المسجلون:</h2><ul>"
    for user in users:
        result += f"<li>{user.full_name} - {user.email} - تحقق: {user.is_verified}</li>"
    result += "</ul>"
    return result


@app.route("/debug-users")
def debug_users():
    users = User.query.all()
    if not users:
        return "🚫 لا يوجد مستخدمين في قاعدة البيانات."
    
    output = []
    for user in users:
        output.append(f"{user.full_name} | {user.email} | Verified: {user.is_verified}")
    return "<br>".join(output)

@app.route("/add-test-user")
def add_test_user():
    from werkzeug.security import generate_password_hash
    test_user = User(
        full_name="مستخدم تجريبي",
        email="test@test.com",
        is_verified=True
    )
    test_user.password_hash = generate_password_hash("123456")

    db.session.add(test_user)
    db.session.commit()
    return "✅ تم إنشاء مستخدم تجريبي"



@app.before_request
def unified_before_request():
    # ✅ استثناءات لا يجب منعها حتى في وضع الصيانة
    if (
        request.path.startswith("/admin")
        or request.endpoint in ("toggle_site_status", "admin_dashboard", "static")
    ):
        pass  # نكمل إلى باقي المهام
    else:
        # 🔒 تحقق من حالة الصيانة
        settings = get_site_settings()
        if not settings.get("site_enabled", True):
            reason = settings.get("maintenance_message", "🚧 الموقع تحت الصيانة مؤقتًا.")
            return render_template("maintenance.html", reason=reason), 503

    # ✅ المهام التلقائية (مثلاً تلخيص تلقائي)
    generate_summary_if_needed()

    # ✅ تسجيل زيارات الزوار
    if request.endpoint != "static":
        ip = request.remote_addr
        already_visited = Visit.query.filter_by(ip_address=ip).first()
        if not already_visited:
            db.session.add(Visit(ip_address=ip))
            db.session.commit()






if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # ⬅️ هذا ينشئ الجداول
    app.run(host='0.0.0.0', port=5000, debug=True)


