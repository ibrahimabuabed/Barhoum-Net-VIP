from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, random, string, datetime, re, threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
app.secret_key = 'final_barhoum_super_key_v7'

# ==========================================
TELEGRAM_TOKEN = "8818771367:AAHseenDo8CKEQ512zUwpEG4Kbd2F4LtG5A"
# تم وضع رقم حسابك الشخصي لتصلك الإشعارات على الخاص
TELEGRAM_CHAT_ID = "1382237454"
WHATSAPP_NUMBER = "970592052286"
MIKROTIK_LOGIN_IP = "10.0.0.1" 

PAYMENT_METHODS = {
    "jawwal_pay": {"name": "جوال باي", "number": "0592052286"},
    "wallet": {"name": "المحفظة", "number": "0599802541"},
    "bop": {"name": "بنك فلسطين", "number": "0592052286"}
}
# ==========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")

def generate_code(length=7):
    return "VIP-" + "".join(random.choices(string.digits, k=length))

def generate_scratch_code():
    return "".join(random.choices(string.digits, k=14))

def init_db():
    conn = sqlite3.connect('barhoum.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, phone TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0, points INTEGER DEFAULT 0, total_spent REAL DEFAULT 0, join_date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS packages (id INTEGER PRIMARY KEY, name TEXT, duration TEXT, price REAL, validity_days INTEGER, description TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_phone TEXT, package_id INTEGER, quantity INTEGER, payment_method TEXT, transfer_phone TEXT, status TEXT, card_code TEXT, date_time TEXT, expiry_date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS balance_requests (id INTEGER PRIMARY KEY, user_phone TEXT, amount REAL, transfer_phone TEXT, payment_method TEXT, status TEXT, date_time TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS scratch_cards (id INTEGER PRIMARY KEY, code TEXT UNIQUE, amount REAL, is_used INTEGER DEFAULT 0, used_by TEXT, date_generated TEXT)')
    
    c.execute('SELECT COUNT(*) FROM packages')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO packages (name, duration, price, validity_days, description) VALUES ("باقة السهرة", "8 ساعات", 2.0, 1, "للتصفح واليوتيوب الخفيف.")')
        c.execute('INSERT INTO packages (name, duration, price, validity_days, description) VALUES ("باقة التحميل", "24 ساعة", 4.0, 3, "إنترنت بلا حدود ليوم كامل.")')
        c.execute('INSERT INTO packages (name, duration, price, validity_days, description) VALUES ("باقة VIP", "7 أيام", 20.0, 7, "اتصال مستقر وثابت للأعمال.")')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🤖 أوامر البوت (Telegram Webhook)
# ==========================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_order_'))
def handle_approve_order(call):
    order_id = int(call.data.split('_')[-1])
    conn = sqlite3.connect('barhoum.db')
    c = conn.cursor()
    c.execute('SELECT orders.status, orders.user_phone, packages.validity_days FROM orders JOIN packages ON orders.package_id = packages.id WHERE orders.id=?', (order_id,))
    data = c.fetchone()
    
    if data and data[0] == 'قيد المراجعة':
        code = generate_code()
        expiry_date = (datetime.datetime.now() + datetime.timedelta(days=data[2])).strftime("%Y-%m-%d")
        c.execute('UPDATE orders SET status="مقبول", card_code=?, expiry_date=? WHERE id=?', (code, expiry_date, order_id))
        conn.commit()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=call.message.text + f"\\n\\n✅ <b>تمت الموافقة وتوليد الكود:</b> <code>{code}</code>")
    elif data and data[0] != 'قيد المراجعة':
        bot.answer_callback_query(call.id, "هذا الطلب تمت معالجته مسبقاً!")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_order_'))
def handle_reject_order(call):
    order_id = int(call.data.split('_')[-1])
    conn = sqlite3.connect('barhoum.db')
    c = conn.cursor()
    c.execute('SELECT status FROM orders WHERE id=?', (order_id,))
    data = c.fetchone()
    if data and data[0] == 'قيد المراجعة':
        c.execute('UPDATE orders SET status="مرفوض" WHERE id=?', (order_id,))
        conn.commit()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=call.message.text + "\\n\\n❌ <b>تم الرفض.</b>")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_bal_'))
def handle_approve_bal(call):
    req_id = int(call.data.split('_')[-1])
    conn = sqlite3.connect('barhoum.db')
    c = conn.cursor()
    c.execute('SELECT user_phone, amount, status FROM balance_requests WHERE id=?', (req_id,))
    req = c.fetchone()
    if req and req[2] == 'معلق':
        c.execute('UPDATE users SET balance = balance + ? WHERE phone=?', (req[1], req[0]))
        c.execute('UPDATE balance_requests SET status="مقبول" WHERE id=?', (req_id,))
        conn.commit()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=call.message.text + "\\n\\n✅ <b>تم شحن الرصيد للزبون بنجاح.</b>")
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_bal_'))
def handle_reject_bal(call):
    req_id = int(call.data.split('_')[-1])
    conn = sqlite3.connect('barhoum.db')
    c = conn.cursor()
    c.execute('UPDATE balance_requests SET status="مرفوض" WHERE id=?', (req_id,))
    conn.commit()
    conn.close()
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=call.message.text + "\\n\\n❌ <b>تم رفض طلب الشحن.</b>")

def run_bot():
    try: bot.polling(none_stop=True)
    except: pass

threading.Thread(target=run_bot, daemon=True).start()

# ==========================================
# 🌐 مسارات الويب
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        if phone == "admin" and password == "admin":
            session['admin'] = True
            return redirect(url_for('admin'))
            
        conn = sqlite3.connect('barhoum.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE phone=? AND password=?', (phone, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['phone'] = phone
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='رقم الجوال أو كلمة المرور غير صحيحة')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        
        error = None
        if not phone.isdigit(): error = 'يجب إدخال أرقام فقط.'
        elif len(phone) != 10: error = 'يجب أن يتكون من 10 أرقام.'
        elif
