from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
import database as db
from handlers import *
from admin_handlers import *

def main():
    db.init_db()
    
    app = Application.builder().token(config.TOKEN).build()
    
    # ========== دستورات عمومی ==========
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_receipt))
    
    # ========== دستور مخفی ادمین ==========
    app.add_handler(MessageHandler(
        filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        admin_panel
    ))
    
    # ========== هندلرهای پیام از ادمین ==========
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        save_ui_setting
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        handle_admin_reply
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        handle_broadcast_message
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        handle_reply_to_user
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        save_new_product
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^hahbyhh555466mamabbbnn$'), 
        save_edit_field
    ))
    
    # ========== Callback handlers ==========
    app.add_handler(CallbackQueryHandler(show_products, pattern="^products$"))
    app.add_handler(CallbackQueryHandler(start_purchase, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(approve_transaction, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_transaction, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(pending_list, pattern="^pending_list$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(back_to_admin, pattern="^back_admin$"))
    app.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    app.add_handler(CallbackQueryHandler(status, pattern="^status$"))
    app.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(view_chats, pattern="^view_chats$"))
    app.add_handler(CallbackQueryHandler(show_user_chat, pattern="^chat_user_"))
    app.add_handler(CallbackQueryHandler(send_message_to_user, pattern="^msg_user_"))
    app.add_handler(CallbackQueryHandler(edit_ui_menu, pattern="^edit_ui$"))
    app.add_handler(CallbackQueryHandler(edit_setting, pattern="^edit_setting_"))
    app.add_handler(CallbackQueryHandler(broadcast_menu, pattern="^broadcast$"))
    app.add_handler(CallbackQueryHandler(send_product_manually, pattern="^send_product_"))
    app.add_handler(CallbackQueryHandler(add_product_menu, pattern="^add_product$"))
    app.add_handler(CallbackQueryHandler(edit_product_menu, pattern="^edit_product$"))
    app.add_handler(CallbackQueryHandler(edit_product_form, pattern="^edit_product_"))
    app.add_handler(CallbackQueryHandler(edit_field, pattern="^edit_field_"))
    app.add_handler(CallbackQueryHandler(delete_product_menu, pattern="^delete_product$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_product, pattern="^delete_product_"))
    app.add_handler(CallbackQueryHandler(delete_product_final, pattern="^delete_confirm_"))
    
    print("🤖 ربات روشن شد!")
    print(f"✅ ادمین‌ها: {config.SECRET_ADMINS}")
    app.run_polling()

if __name__ == "__main__":
    main()
