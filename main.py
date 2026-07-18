import json
import os
import logging
import random
import zipfile
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ==================== تنظیمات ====================
TOKEN = "8565413645:AAGm027C1AwMH9ZcaRkvuzwi2IXzfzMGOck"
ADMIN_ID = 8706836237
PRICE_PER_ITEM = 300000
REF_PERCENT = 10  # درصد سود زیرمجموعه‌گیری

# ==================== فایل‌های دیتابیس ====================
APPLE_IDS_FILE = "apple_ids.json"
SETTINGS_FILE = "settings.json"
SALES_FILE = "sales.json"
PENDING_FILE = "pending.json"
WALLETS_FILE = "wallets.json"
CHANNEL_FILE = "channel.json"
START_TEXT_FILE = "start_text.json"
BOT_STATUS_FILE = "bot_status.json"

# ==================== توابع مدیریت دیتابیس ====================
def load_json(file_path, default_data):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f) or default_data
        except:
            return default_data
    save_json(file_path, default_data)
    return default_data

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ==================== مقداردهی اولیه ====================
settings = load_json(SETTINGS_FILE, {"card_number": "6219861950901305", "card_holder": "محمد مهدی جاودان", "price_per_item": PRICE_PER_ITEM})
bot_status = load_json(BOT_STATUS_FILE, {"enabled": True})
channel_config = load_json(CHANNEL_FILE, {"channel_id": "", "channel_link": "https://t.me/Nexo_IP", "enabled": False})
apple_ids_list = load_json(APPLE_IDS_FILE, [])
sales = load_json(SALES_FILE, [])
pending_payments = load_json(PENDING_FILE, {})
wallets = load_json(WALLETS_FILE, {})

default_start_text = (
    "🛍 *فروشگاه پیشرفته اپل آیدی*\n\n"
    "💰 موجودی کیف پول: {balance:,} تومان\n"
    "💵 قیمت هر اپل آیدی: {price:,} تومان\n\n"
    "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
)
start_text_config = load_json(START_TEXT_FILE, {"text": default_start_text})

# ==================== توابع کیف پول و کاربر ====================
def get_wallet(user_id):
    user_id = str(user_id)
    if user_id not in wallets:
        wallets[user_id] = {
            "balance": 0, "total_deposit": 0, "total_spent": 0,
            "referred_by": None, "last_daily_bonus": None, "is_banned": False
        }
        save_json(WALLETS_FILE, wallets)
    return wallets[user_id]

def add_balance(user_id, amount):
    user_id = str(user_id)
    wallet = get_wallet(user_id)
    wallet["balance"] += amount
    save_json(WALLETS_FILE, wallets)
    return wallet["balance"]

def subtract_balance(user_id, amount):
    user_id = str(user_id)
    wallet = get_wallet(user_id)
    if wallet["balance"] < amount: return False
    wallet["balance"] -= amount
    wallet["total_spent"] += amount
    save_json(WALLETS_FILE, wallets)
    return True

# ==================== دکوراتورها و امنیت ربات ====================
def require_user_access(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        wallet = get_wallet(user_id)
        
        # بررسی بن بودن
        if wallet.get("is_banned", False):
            if update.callback_query: await update.callback_query.answer("🚫 شما از سرور ربات مسدود شده‌اید!", show_alert=True)
            else: await update.message.reply_text("🚫 دسترسی شما به ربات مسدود شده است.")
            return
        
        # بررسی وضعیت آپدیت ربات
        if not bot_status.get("enabled", True) and user_id != ADMIN_ID:
            if update.callback_query:
                await update.callback_query.answer("⛔ ربات در حال آپدیت است!", show_alert=True)
            else:
                await update.message.reply_text("⛔ ربات در حال آپدیت است! لطفاً چند دقیقه دیگر مجدداً تلاش کنید.")
            return
            
        # بررسی عضویت اجباری کانال
        if channel_config.get("enabled", False) and user_id != ADMIN_ID:
            channel_id = channel_config.get("channel_id", "")
            if channel_id:
                try:
                    member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                    if member.status not in ["member", "administrator", "creator"]: raise Exception()
                except:
                    keyboard = [
                        [InlineKeyboardButton("📢 عضویت در کانال", url=channel_config.get("channel_link"))],
                        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
                    ]
                    text = "🔒 *عضویت اجباری*\n\nبرای استفاده از ربات ابتدا باید عضو کانال ما شوید."
                    if update.callback_query:
                        await update.callback_query.answer("🔒 ابتدا عضو کانال شوید!", show_alert=True)
                        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                    return
                    
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== دستورات عمومی و کاربر ====================
@require_user_access
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
    else:
        user_id = update.message.from_user.id
        # بررسی لینک رفرال و زیرمجموعه‌گیری
        if context.args and context.args[0].startswith("ref_"):
            wallet = get_wallet(user_id)
            ref_id = context.args[0].split("_")[1]
            if ref_id != str(user_id) and str(ref_id) in wallets and not wallet.get("referred_by"):
                wallet["referred_by"] = ref_id
                save_json(WALLETS_FILE, wallets)
                try: await context.bot.send_message(chat_id=int(ref_id), text="🎉 یک کاربر جدید با لینک شما وارد ربات شد!")
                except: pass

    wallet = get_wallet(user_id)
    keyboard = [
        [InlineKeyboardButton("🛒 خرید اپل آیدی", callback_data="buy_apple"), InlineKeyboardButton("📦 خریدهای من", callback_data="my_orders")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="my_wallet"), InlineKeyboardButton("💳 شارژ حساب", callback_data="charge_wallet")],
        [InlineKeyboardButton("🎁 هدیه روزانه", callback_data="daily_bonus"), InlineKeyboardButton("🔗 زیرمجموعه‌گیری", callback_data="referral_menu")],
        [InlineKeyboardButton("📞 پشتیبانی ربات", callback_data="support")]
    ]
    if int(user_id) == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت ادمین", callback_data="admin_panel")])
    
    formatted_text = start_text_config.get("text", default_start_text).format(balance=wallet['balance'], price=settings['price_per_item'])
    
    if update.callback_query: await query.edit_message_text(formatted_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else: await update.message.reply_text(formatted_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== قابلیت‌های جدید بخش کاربر ====================
@require_user_access
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    wallet = get_wallet(user_id)
    
    now = datetime.now()
    last_bonus = wallet.get("last_daily_bonus")
    
    if last_bonus and datetime.strptime(last_bonus, "%Y-%m-%d %H:%M:%S") + timedelta(days=1) > now:
        await query.edit_message_text("❌ رفیق! شما هدیه امروز رو گرفتی. ۲۴ ساعت بعد دوباره شانست رو امتحان کن!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))
        return
        
    gift = random.randint(1000, 3000)
    add_balance(user_id, gift)
    wallet["last_daily_bonus"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_json(WALLETS_FILE, wallets)
    
    await query.edit_message_text(f"🎁 *تبریک رفیق!*\n\nچرخ گردونه شانس چرخید و مبلغ *{gift:,}* تومان به کیف پولت اضافه شد!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("دمت گرم 😍", callback_data="back_to_menu")]]))

@require_user_access
async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    invited_count = sum(1 for u in wallets.values() if u.get("referred_by") == user_id)
    
    text = (
        f"🔗 *سیستم کسب درآمد زیرمجموعه‌گیری*\n\n"
        f"با دعوت از دوستان خود، بنر زیر را برای آن‌ها بفرستید. هر زمان دوستان شما اکانت خود را شارژ کنند، *{REF_PERCENT}%* از مبلغ شارژ مستقیم به حساب شما واریز می‌شود!\n\n"
        f"👥 تعداد زیرمجموعه‌های شما: {invited_count} نفر\n"
        f"🔗 لینک اختصاصی شما:\n`{ref_link}`"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

@require_user_access
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    user_sales = [s for s in sales if str(s["user_id"]) == user_id]
    if not user_sales:
        await query.edit_message_text("📦 شما هنوز هیچ خریدی در ربات ثبت نکرده‌اید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))
        return
        
    text = "📦 *لیست تمام اکانت‌های خریداری شده شما:*\n\n"
    for idx, sale in enumerate(user_sales, 1):
        text += f"🛒 *خرید شماره {idx}* ({sale.get('count')} عدد):\n"
        for item in sale.get("items", []):
            text += f"🔑 `{item}`\n"
        text += "—" * 12 + "\n"
        
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

# ==================== سیستم خرید و کیف پول ====================
@require_user_access
async def buy_apple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    wallet = get_wallet(user_id)
    total_apple = len(apple_ids_list)

    if total_apple == 0:
        await query.edit_message_text("❌ متاسفانه در حال حاضر اپل آیدی موجود نیست. ادمین به زودی انبار رو شارژ می‌کنه.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))
        return
    
    keyboard = []
    for i in range(1, min(total_apple, 10) + 1):
        price = i * settings['price_per_item']
        keyboard.append([InlineKeyboardButton(f"📱 {i} عدد - {price:,} تومان", callback_data=f"buy_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")])
    
    await query.edit_message_text(
        f"📱 *انتخاب تعداد خرید:*\n\n💰 موجودی کیف پول: {wallet['balance']:,} تومان\n📦 موجودی انبار ربات: {total_apple} عدد\n💵 قیمت هر عدد: {settings['price_per_item']:,} تومان",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

@require_user_access
async def buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    count = int(query.data.split("_")[1])
    total_price = count * settings['price_per_item']
    wallet = get_wallet(user_id)
    
    global apple_ids_list
    if len(apple_ids_list) < count:
        await query.edit_message_text("❌ موجودی انبار تغییر کرده است! لطفاً مجدد تلاش کنید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="buy_apple")]]))
        return
        
    if wallet['balance'] < total_price:
        keyboard = [[InlineKeyboardButton("💳 شارژ کیف پول", callback_data="charge_wallet")], [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_apple")]]
        await query.edit_message_text(f"❌ موجودی کافی نیست!\n\n💰 موجودی: {wallet['balance']:,} تومان\n💵 هزینه خرید: {total_price:,} تومان\n🔴 کمبود موجودی: {total_price - wallet['balance']:,} تومان", reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    subtract_balance(user_id, total_price)
    
    selected_accounts = apple_ids_list[:count]
    apple_ids_list = apple_ids_list[count:]
    save_json(APPLE_IDS_FILE, apple_ids_list)
    
    # ثبت در دیتابیس فروش همراه با خود اکانت‌ها برای آرشیو کاربر
    sale = {"user_id": user_id, "count": count, "total_price": total_price, "items": selected_accounts, "date": str(datetime.now())}
    sales.append(sale)
    save_json(SALES_FILE, sales)
    
    text = "🎉 *خرید شما با موفقیت انجام شد!*\n\n📧 اطلاعات اکانت‌های خریداری شده:\n━━━━━━━━━━━━━━━━\n"
    for i, acc in enumerate(selected_accounts, 1): text += f"{i}. `{acc}`\n"
    text += "━━━━━━━━━━━━━━━━\n🔒 رفیق حتماً بعد از ورود مشخصات و رمز عبورت رو تغییر بده."
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_menu")]]))
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🛒 *فروش جدید!*\n👤 کاربر: {user_id}\n📦 تعداد: {count} عدد\n💰 سود: {total_price:,} تومان")
    except: pass

# ==================== بخش مالی و شارژ حساب ====================
@require_user_access
async def my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    wallet = get_wallet(user_id)
    await query.edit_message_text(f"💰 *وضعیت حساب شما:*\n\n💵 موجودی فعلی: {wallet['balance']:,} تومان\n💳 شماره کارت جهت واریز:\n`{settings['card_number']}`\n👤 بنام: {settings['card_holder']}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 شارژ حساب", callback_data="charge_wallet")], [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

@require_user_access
async def charge_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💳 ۵۰,۰۰۰ تومان", callback_data="charge_50000"), InlineKeyboardButton("💳 ۱۰۰,۰۰۰ تومان", callback_data="charge_100000")],
        [InlineKeyboardButton("💳 ۲۰۰,۰۰۰ تومان", callback_data="charge_200000"), InlineKeyboardButton("💳 ۵۰۰,۰۰۰ تومان", callback_data="charge_500000")],
        [InlineKeyboardButton("✏️ ورود مبلغ دلخواه", callback_data="charge_custom")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]
    ]
    await query.edit_message_text("💳 مبلغی که می‌خواهی حساب خود را شارژ کنی انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

@require_user_access
async def charge_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'charge_custom'
    await query.edit_message_text("✏️ لطفاً مبلغ مورد نظر خودت را به عدد و به *تومان* وارد کن (مثال: 150000):", parse_mode="Markdown")

async def handle_charge_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        if amount < 10000: raise Exception()
    except:
        await update.message.reply_text("❌ خطا! لطفاً یک عدد معتبر بزرگتر از ۱۰,۰۰۰ تومان وارد کن.")
        return
    context.user_data['admin_action'] = None
    await initiate_payment(update.message.from_user.id, amount, context)

@require_user_access
async def charge_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    amount = int(query.data.split("_")[1])
    await initiate_payment(query.from_user.id, amount, context, query)

async def initiate_payment(user_id, amount, context, query=None):
    user_id = str(user_id)
    pending_payments[user_id] = {"amount": amount, "status": "waiting"}
    save_json(PENDING_FILE, pending_payments)
    
    text = f"💳 *درخواست شارژ حساب*\n\n💰 مبلغ: *{amount:,}* تومان\n\n📌 لطفاً مبلغ فوق را به شماره کارت زیر واریز کنید:\n`{settings['card_number']}`\n👤 صاحب حساب: {settings['card_holder']}\n\n✅ پس از واریز، *عکس رسید* خود را مستقیماً در همین چت ارسال کنید."
    if query: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="back_to_menu")]]))
    else: await context.bot.send_message(chat_id=int(user_id), text=text, parse_mode="Markdown")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in pending_payments or pending_payments[user_id]["status"] != "waiting":
        await update.message.reply_text("❌ رفیق، شما هیچ فاکتور پرداخت منتظری نداری! ابتدا از منو شارژ حساب رو بزن.")
        return
        
    photo_file = update.message.photo[-1].file_id
    pending_payments[user_id]["photo"] = photo_file
    pending_payments[user_id]["status"] = "pending"
    save_json(PENDING_FILE, pending_payments)
    
    amount = pending_payments[user_id]["amount"]
    keyboard = [[InlineKeyboardButton("✅ تایید رسید", callback_data=f"approve_{user_id}"), InlineKeyboardButton("❌ رد رسید", callback_data=f"reject_{user_id}")]]
    
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file, caption=f"📩 *رسید جدید آمد!*\n\n👤 کاربر: `{user_id}`\n💰 مبلغ واریزی: {amount:,} تومان", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("✅ رسید شما با موفقیت برای ادمین ارسال شد. پس از تایید حساب شما شارژ می‌شود.")

# ==================== تایید / رد رسید توسط ادمین و پورسانت رفرال ====================
async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    
    user_id = query.data.split("_")[1]
    if user_id not in pending_payments:
        await query.edit_message_text("❌ این رسید قبلاً تعیین تکلیف شده است.")
        return
        
    amount = pending_payments[user_id]["amount"]
    new_balance = add_balance(user_id, amount)
    
    # 💥 بررسی سیستم زیرمجموعه‌گیری و پرداخت پورسانت به معرف
    wallet = get_wallet(user_id)
    referrer_id = wallet.get("referred_by")
    if referrer_id and str(referrer_id) in wallets:
        bonus = int(amount * REF_PERCENT / 100)
        add_balance(referrer_id, bonus)
        try: await context.bot.send_message(chat_id=int(referrer_id), text=f"💰 *سود دعوت!*\n\nزیرمجموعه شما حسابش را شارژ کرد و مبلغ *{bonus:,}* تومان پورسانت به کیف پول شما واریز شد! 🔥", parse_mode="Markdown")
        except: pass

    try: await context.bot.send_message(chat_id=int(user_id), text=f"✅ *رسید شما تایید شد!*\n\n💰 مبلغ {amount:,} تومان به کیف پول شما اضافه شد.\n💵 موجودی فعلی: {new_balance:,} تومان", parse_mode="Markdown")
    except: pass
    
    del pending_payments[user_id]
    save_json(PENDING_FILE, pending_payments)
    await query.edit_message_text(f"✅ رسید کاربر {user_id} تایید و حسابش شارژ شد.")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    
    user_id = query.data.split("_")[1]
    if user_id not in pending_payments: return
    
    try: await context.bot.send_message(chat_id=int(user_id), text="❌ رسید واریزی شما توسط ادمین رد شد! لطفاً رسید معتبر ارسال کنید یا با پشتیبانی در ارتباط باشید.")
    except: pass
    
    del pending_payments[user_id]
    save_json(PENDING_FILE, pending_payments)
    await query.edit_message_text("❌ رسید رد شد و به کاربر اطلاع داده شد.")

@require_user_access
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📞 *پشتیبانی فروشگاه:*\n\nجهت حل مشکلات یا تمایل به خرید عمده با آیدی زیر در ارتباط باشید:\n👤 @admin_username", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]))

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ==================== پنل ادمین فوق حرفه‌ای ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن اپل آیدی", callback_data="admin_add_ids"), InlineKeyboardButton("📋 انبار اکانت‌ها", callback_data="admin_list_ids")],
        [InlineKeyboardButton("💰 تغییر قیمت", callback_data="admin_change_price"), InlineKeyboardButton("💳 تنظیمات کارت", callback_data="admin_change_card")],
        [InlineKeyboardButton("👤 مدیریت کاربر (بن/شارژ)", callback_data="admin_manage_user"), InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📢 تنظیمات کانال جوین", callback_data="admin_channel"), InlineKeyboardButton("🔄 روشن/خاموش ربات", callback_data="admin_toggle_bot")],
        [InlineKeyboardButton("💾 پشتیبان‌گیری دیتابیس (Backup)", callback_data="admin_backup"), InlineKeyboardButton("📊 آمار فروش", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت به منوی کاربر", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(f"⚙️ *به پنل مدیریت خوش آمدی رفیق!*\n\n📦 موجودی انبار: {len(apple_ids_list)} عدد\n💵 قیمت فعلی: {settings['price_per_item']:,} تومان\n🤖 وضعیت ربات: {'✅ روشن' if bot_status.get('enabled') else '❌ در حال آپدیت'}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# 💾 قابلیت بکاپ‌گیری کل اطلاعات ربات
async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    
    zip_name = "bot_backup.zip"
    files_to_backup = [APPLE_IDS_FILE, SETTINGS_FILE, SALES_FILE, PENDING_FILE, WALLETS_FILE, CHANNEL_FILE, START_TEXT_FILE, BOT_STATUS_FILE]
    
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for f in files_to_backup:
            if os.path.exists(f): zipf.write(f)
            
    with open(zip_name, 'rb') as f:
        await context.bot.send_document(chat_id=ADMIN_ID, document=f, filename=f"Backup_{datetime.now().strftime('%Y%m%d')}.zip", caption="💾 نسخه پشتیبان تمام دیتابیس ربات شما با موفقیت ساخته و فرستاده شد.")
    os.remove(zip_name)

# 👤 مدیریت کاربر (شارژ دستوری / بن و آن‌بن)
async def admin_manage_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'target_user'
    await query.edit_message_text("👤 لطفاً آیدی عددی تلگرام کاربر مورد نظر را وارد کن:")

async def handle_admin_text_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID: return
    action = context.user_data.get('admin_action')
    text = update.message.text.strip()
    
    if action == 'target_user':
        if text in wallets:
            context.user_data['target_user_id'] = text
            context.user_data['admin_action'] = None
            u = wallets[text]
            status = "❌ مسدود" if u.get("is_banned") else "✅ آزاد"
            keyboard = [
                [InlineKeyboardButton("💰 تغییر موجودی حساب", callback_data="mod_balance"), InlineKeyboardButton("🚫 بن / آن‌بن کاربر", callback_data="mod_ban")],
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel")]
            ]
            await update.message.reply_text(f"👤 وضعیت کاربر `{text}`:\n💰 موجودی: {u['balance']:,} تومان\n📌 وضعیت دسترسی: {status}\n\nچه کاری می‌خواهی انجام دهی؟", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ چنین آیدی کاربری در دیتابیس پیدا نشد!")
            context.user_data['admin_action'] = None
            
    elif action == 'input_new_balance':
        try:
            amt = int(text)
            t_id = context.user_data['target_user_id']
            wallets[t_id]['balance'] = amt
            save_json(WALLETS_FILE, wallets)
            await update.message.reply_text(f"✅ موجودی کاربر `{t_id}` با موفقیت به {amt:,} تومان تغییر کرد.", parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ عدد نامعتبر بود.")
        context.user_data['admin_action'] = None

    elif action == 'change_price':
        try:
            settings['price_per_item'] = int(text)
            save_json(SETTINGS_FILE, settings)
            await update.message.reply_text("✅ قیمت با موفقیت تغییر کرد.")
        except: await update.message.reply_text("❌ خطا در ورود عدد.")
        context.user_data['admin_action'] = None

    elif action == 'add_ids':
        new_ids = [line.strip() for line in text.split('\n') if line.strip()]
        apple_ids_list.extend(new_ids)
        save_json(APPLE_IDS_FILE, apple_ids_list)
        await update.message.reply_text(f"✅ تعداد {len(new_ids)} اکانت جدید به انبار اضافه شد.")
        context.user_data['admin_action'] = None

    elif action == 'broadcast':
        context.user_data['admin_action'] = None
        u_ids = list(wallets.keys())
        await update.message.reply_text(f"⏳ فرستادن پیام همگانی به {len(u_ids)} کاربر آغاز شد...")
        succ = 0
        for uid in u_ids:
            try:
                await context.bot.send_message(chat_id=int(uid), text=text)
                succ += 1
            except: pass
        await update.message.reply_text(f"✅ پیام همگانی به {succ} کاربر با موفقیت ارسال شد.")

async def mod_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['admin_action'] = 'input_new_balance'
    await update.callback_query.edit_message_text("💰 موجودی جدید کاربر را به تومان وارد کن:")

async def mod_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    t_id = context.user_data['target_user_id']
    wallets[t_id]['is_banned'] = not wallets[t_id].get('is_banned', False)
    save_json(WALLETS_FILE, wallets)
    await update.callback_query.edit_message_text(f"✅ وضعیت مسدودیت کاربر تغییر کرد. وضعیت فعلی بن: {wallets[t_id]['is_banned']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_panel")]]))

# بقیه بخش‌های عمومی پنل مدیریت تنظیمات
async def admin_toggle_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_status["enabled"] = not bot_status.get("enabled", True)
    save_json(BOT_STATUS_FILE, bot_status)
    await update.callback_query.answer(f"وضعیت ربات تغییر کرد", show_alert=True)
    await admin_panel(update, context)

async def admin_change_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['admin_action'] = 'change_price'
    await update.callback_query.edit_message_text("💵 قیمت جدید هر اپل آیدی را به تومان وارد کن:")

async def admin_add_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['admin_action'] = 'add_ids'
    await update.callback_query.edit_message_text("📧 مشخصات اکانت‌ها را بفرست (هر خط یک ایمیل:رمز):")

async def admin_list_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not apple_ids_list: text = "📭 انبار خالی است رفیق!"
    else: text = f"📋 لیست ۲۰ اکانت اول موجود در انبار:\n\n" + "\n".join([f"{i}. {acc}" for i, acc in enumerate(apple_ids_list[:20], 1)])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    rev = sum(s["total_price"] for s in sales)
    await update.callback_query.edit_message_text(f"📊 *آمار کلی بیزینس شما:*\n\n💰 تعداد کل سفارشات ثبت شده: {len(sales)} عدد\n💵 درآمد ناخالص کل: {rev:,} تومان\n📦 اکانت‌های باقیمانده در انبار: {len(apple_ids_list)} عدد", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]))

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['admin_action'] = 'broadcast'
    await update.callback_query.edit_message_text("📢 متن پیام همگانی خود را ارسال کنید:")

async def admin_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    # تغییر سوئیچ وضعیت عضویت اجباری
    channel_config["enabled"] = not channel_config.get("enabled", False)
    save_json(CHANNEL_FILE, channel_config)
    await update.callback_query.edit_message_text(f"📢 وضعیت عضویت اجباری تغییر کرد!\nوضعیت فعلی: {'✅ فعال' if channel_config['enabled'] else '❌ غیرفعال'}\n\nنکته: برای تنظیم دستی آیدی/لینک مستقیما فایل channel.json را ویرایش کنید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت ادمین", callback_data="admin_panel")]]))

# ==================== اجرای ربات ====================
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    # کالبک‌های بخش کاربر
    app.add_handler(CallbackQueryHandler(buy_apple, pattern="^buy_apple$"))
    app.add_handler(CallbackQueryHandler(buy_confirm, pattern="^buy_\\d+$"))
    app.add_handler(CallbackQueryHandler(my_wallet, pattern="^my_wallet$"))
    app.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(charge_wallet, pattern="^charge_wallet$"))
    app.add_handler(CallbackQueryHandler(charge_custom, pattern="^charge_custom$"))
    app.add_handler(CallbackQueryHandler(charge_confirm, pattern="^charge_\\d+$"))
    app.add_handler(CallbackQueryHandler(daily_bonus, pattern="^daily_bonus$"))
    app.add_handler(CallbackQueryHandler(referral_menu, pattern="^referral_menu$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^check_membership$"))
    
    # کالبک‌های بخش ادمین
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_add_ids, pattern="^admin_add_ids$"))
    app.add_handler(CallbackQueryHandler(admin_list_ids, pattern="^admin_list_ids$"))
    app.add_handler(CallbackQueryHandler(admin_change_price, pattern="^admin_change_price$"))
    app.add_handler(CallbackQueryHandler(admin_manage_user, pattern="^admin_manage_user$"))
    app.add_handler(CallbackQueryHandler(mod_balance, pattern="^mod_balance$"))
    app.add_handler(CallbackQueryHandler(mod_ban, pattern="^mod_ban$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_bot, pattern="^admin_toggle_bot$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_channel, pattern="^admin_channel$"))
    app.add_handler(CallbackQueryHandler(admin_backup, pattern="^admin_backup$"))
    app.add_handler(CallbackQueryHandler(approve_payment, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_payment, pattern="^reject_"))
    
    # رسانه‌ها و پیام‌های متنی
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text_logic), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_charge_custom), group=2)
    
    print("🚀 ربات فول آپشن شما با موفقیت استارت شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
