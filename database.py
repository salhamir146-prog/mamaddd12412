import sqlite3
import config

DB_NAME = "shop.db"

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # جدول محصولات
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  price INTEGER NOT NULL,
                  stock INTEGER DEFAULT 0,
                  codes TEXT)''')
    
    # جدول تراکنش‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  product_id INTEGER NOT NULL,
                  amount INTEGER NOT NULL,
                  receipt_file_id TEXT,
                  status TEXT DEFAULT 'pending',
                  assigned_code TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول ادمین‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (user_id INTEGER PRIMARY KEY)''')
    
    # جدول تاریخچه چت‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  username TEXT,
                  first_name TEXT,
                  message TEXT,
                  is_from_user BOOLEAN,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول کاربران (برای پیام همگانی)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول تنظیمات ظاهر ربات
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # مقادیر پیش‌فرض تنظیمات
    defaults = [
        ('welcome_text', '👋 سلام {first_name} عزیز!\n\nبه فروشگاه اپل‌آیدی خوش آمدی.\nلطفاً از منوی زیر یکی از گزینه‌ها رو انتخاب کن:'),
        ('btn_products', '🛒 لیست محصولات'),
        ('btn_support', '📞 پشتیبانی'),
        ('btn_status', '📊 وضعیت خرید'),
        ('btn_back', '🔙 بازگشت'),
        ('btn_buy', '✅ رسید رو ارسال کردم'),
        ('btn_cancel', '🔙 انصراف'),
    ]
    for key, value in defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    
    # اضافه کردن ادمین‌ها
    for admin_id in config.ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))
    
    conn.commit()
    conn.close()

# ========== توابع محصولات ==========
def get_product(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock, codes FROM products WHERE id = ?", (product_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_all_products():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products WHERE stock > 0")
    result = c.fetchall()
    conn.close()
    return result

def add_product(name, price, stock, codes):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO products (name, price, stock, codes) VALUES (?, ?, ?, ?)''', 
              (name, price, stock, codes))
    product_id = c.lastrowid
    conn.commit()
    conn.close()
    return product_id

def update_product(product_id, name=None, price=None, stock=None, codes=None):
    conn = get_db()
    c = conn.cursor()
    if name:
        c.execute("UPDATE products SET name = ? WHERE id = ?", (name, product_id))
    if price:
        c.execute("UPDATE products SET price = ? WHERE id = ?", (price, product_id))
    if stock is not None:
        c.execute("UPDATE products SET stock = ? WHERE id = ?", (stock, product_id))
    if codes:
        c.execute("UPDATE products SET codes = ? WHERE id = ?", (codes, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def use_product_code(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT codes FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    if not row or not row[0]:
        conn.close()
        return None
    codes_list = row[0].split(',')
    if not codes_list:
        conn.close()
        return None
    assigned_code = codes_list[0].strip()
    remaining_codes = ','.join(codes_list[1:])
    c.execute("UPDATE products SET codes = ?, stock = stock - 1 WHERE id = ?", 
              (remaining_codes if remaining_codes else None, product_id))
    conn.commit()
    conn.close()
    return assigned_code

# ========== توابع تراکنش‌ها ==========
def create_transaction(user_id, product_id, amount, file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO transactions 
                 (user_id, product_id, amount, receipt_file_id, status) 
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, product_id, amount, file_id, 'pending'))
    trans_id = c.lastrowid
    conn.commit()
    conn.close()
    return trans_id

def get_transaction(trans_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE id = ?", (trans_id,))
    result = c.fetchone()
    conn.close()
    return result

def update_transaction_status(trans_id, status, assigned_code=None):
    conn = get_db()
    c = conn.cursor()
    if assigned_code:
        c.execute('''UPDATE transactions SET status = ?, assigned_code = ? WHERE id = ?''', 
                  (status, assigned_code, trans_id))
    else:
        c.execute("UPDATE transactions SET status = ? WHERE id = ?", (status, trans_id))
    conn.commit()
    conn.close()

def get_pending_transactions():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE status = 'pending' ORDER BY created_at DESC")
    result = c.fetchall()
    conn.close()
    return result

def get_user_transactions(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    result = c.fetchall()
    conn.close()
    return result

def get_all_transactions(limit=50):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?", (limit,))
    result = c.fetchall()
    conn.close()
    return result

def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT user_id) FROM transactions")
    total_users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE status = 'approved' OR status = 'delivered'")
    total_sales = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM transactions WHERE status = 'pending'")
    pending = c.fetchone()[0] or 0
    conn.close()
    return {
        'total_users': total_users,
        'total_transactions': total_transactions,
        'total_sales': total_sales,
        'pending': pending
    }

# ========== توابع کاربران ==========
def add_user(user_id, username, first_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
              (user_id, username, first_name))
    conn.commit()
    conn.close()

def get_all_users_for_broadcast():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    result = c.fetchall()
    conn.close()
    return [r[0] for r in result]

# ========== توابع تاریخچه چت ==========
def save_chat_message(user_id, username, first_name, message, is_from_user=True):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO chat_history (user_id, username, first_name, message, is_from_user) 
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, username, first_name, message, is_from_user))
    conn.commit()
    conn.close()

def get_user_chat_history(user_id, limit=50):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT message, is_from_user, timestamp 
                 FROM chat_history 
                 WHERE user_id = ? 
                 ORDER BY timestamp DESC LIMIT ?''', (user_id, limit))
    result = c.fetchall()
    conn.close()
    return result

def get_user_info(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT username, first_name, MAX(timestamp) as last_seen
                 FROM chat_history 
                 WHERE user_id = ? 
                 GROUP BY user_id''', (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_all_users(limit=50):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT user_id, username, first_name, MAX(timestamp) as last_msg
                 FROM chat_history 
                 GROUP BY user_id 
                 ORDER BY last_msg DESC LIMIT ?''', (limit,))
    result = c.fetchall()
    conn.close()
    return result

def is_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# ========== توابع تنظیمات ظاهر ==========
def get_setting(key):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()
