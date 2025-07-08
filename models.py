from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,date
import uuid
from flask_login import UserMixin
db = SQLAlchemy()

# ✅ جدول المستخدمين
class User(db.Model, UserMixin):  # ✅ تأكد أنك ترث من UserMixin
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(100), nullable=True)  # ✅ العمود الجديد
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="active")  # active, banned
    banned_until = db.Column(db.DateTime, nullable=True)
    is_banned = db.Column(db.Boolean, default=False)

    orders = db.relationship('Order', backref='user', lazy=True)
    verifications = db.relationship('EmailVerification', backref='user', lazy=True)
    admin_profile = db.relationship('AdminRole', backref='user', uselist=False)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    # علاقات
    orders = db.relationship('Order', backref='user', lazy=True)
    verifications = db.relationship('EmailVerification', backref='user', lazy=True)
    admin_profile = db.relationship('AdminRole', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
 # ✅ دالة لفحص إذا كان محظور مؤقتًا
    def is_temporarily_banned(self):
        return self.banned_until and self.banned_until > datetime.utcnow()



# ✅ جدول الطلبات
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    order_id = db.Column(db.String(20), unique=True, default=lambda: str(uuid.uuid4())[:8])  # كود الطلب للعرض
    transaction_id = db.Column(db.String(100))  # رقم عملية الدفع

    status = db.Column(db.String(30), default="pending")  # حالات الطلب
    tracking_code = db.Column(db.String(50), unique=True)  # رقم تتبع خارجي (اختياري)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    email = db.Column(db.String(120), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True)


# ✅ المنتجات داخل الطلب
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    key_type = db.Column(db.String(100))  # نوع المفتاح (steam, epic...)
    restricted_country = db.Column(db.String(100))  # قيود الدولة


# ✅ المنتجات (لو أردت البيع مباشرة من المخزون)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    img = db.Column(db.String(200))  # رابط الصورة أو المسار (مثل images/gta.jpg)
    link = db.Column(db.String(200))  # رابط تفصيلي اختياري (مثل /product/gta5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



# ✅ قسم خاصة بما موجود في السلة وربطها بحساب العميل
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.String, nullable=False)  
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))


# ✅ التحقق عبر الإيميل
class EmailVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    code = db.Column(db.String(64), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ✅ صلاحيات المديرين
class AdminRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    
    can_edit_orders = db.Column(db.Boolean, default=True)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_view_logs = db.Column(db.Boolean, default=True)


# ✅ سجل الأحداث للمراقبة
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120))
    action = db.Column(db.String(200))  # مثل "تعديل الطلب", "تسجيل دخول"
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

#ها خاصة بالمشرفين هو قسم طلبات 
class ActivationKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)  # اسم المنتج المرتبط
    key_code = db.Column(db.String(200), nullable=False)       # الكود نفسه
    status = db.Column(db.String(50), default='available')     # available / used
    notes = db.Column(db.Text)                                 # أي تعليمات أو روابط أو صور
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # تاريخ 
    used_in_order_id = db.Column(db.String(20))                # رقم الطلب الذي استخدم فيه


#هذا حساب عدد الزوار
class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(100))
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_authenticated = db.Column(db.Boolean, default=False)


# ✅ المنتجات الأكثر إضافة للسلة
class CartAddition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)  # اسم المنتج
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ تقارير التلخيص الأسبوعي / الشهري
class SummaryReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period_type = db.Column(db.String(10))  # 'week' or 'month'
    period_label = db.Column(db.String(20))  # مثلًا '2025-W26' أو '2025-07'
    total_visits = db.Column(db.Integer)
    total_users = db.Column(db.Integer)
    total_orders = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship("Product", backref="offers")
    discount = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    highlight_text = db.Column(db.String(100), nullable=True)
    type = db.Column(db.String(10), nullable=False, default='offer')


    # العلاقة للوصول إلى تفاصيل المنتج
    product = db.relationship("Product", backref="offers", lazy=True)



class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), nullable=False)  # "percent" or "fixed"
    discount_value = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    restricted_products = db.Column(db.Text, nullable=True)  # JSON string like '["GOW", "MC"]




class PaypalOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255))
    paypal_order_id = db.Column(db.String(255), unique=True)
    product_code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GeneralNotice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # مثل: info, warning, danger, success
    color = db.Column(db.String(20), nullable=False)  # لون الخلفية
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

