import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
MASTER_ADMIN = int(os.getenv("MASTER_ADMIN"))
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS").split(",")]
CARD_NUMBER = os.getenv("CARD_NUMBER")
CARD_OWNER = os.getenv("CARD_OWNER")

# هر دو ادمین می‌تونن با دستور مخفی وارد بشن
SECRET_ADMINS = [8911508795, 8706836237]
