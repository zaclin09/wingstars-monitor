import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "monitor.db"
ACCOUNTS_EXCEL = DATA_DIR / "accounts.xlsx"

# === Telegram 設定 ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# === 監測門檻 ===
LIKES_THRESHOLD = 100
VIEWS_THRESHOLD = 5000

# === 排程設定 ===
HOURLY_CHECK_MINUTES = 0           # 每小時的第幾分鐘執行
DAILY_SUMMARY_HOUR = 23            # 每日總結：23:00
DAILY_SUMMARY_MINUTE = 0
WEEKLY_REPORT_DAY = "thu"          # 每週四
WEEKLY_REPORT_HOUR = 23
WEEKLY_REPORT_MINUTE = 59

# === 爬蟲設定 ===
SCRAPE_DELAY_MIN = 2               # 每個帳號之間的最小延遲（秒）
SCRAPE_DELAY_MAX = 5               # 每個帳號之間的最大延遲（秒）
SCRAPE_TIMEOUT = 60000             # 頁面載入超時（毫秒）
MAX_POSTS_PER_ACCOUNT = 10         # 每個帳號最多抓幾篇最新貼文
HEADLESS = True                    # 是否無頭模式
PROXY = os.getenv("PROXY", "")     # 代理伺服器（選填）

# === 時區 ===
TIMEZONE = "Asia/Taipei"
