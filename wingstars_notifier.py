"""Wing Stars Telegram 推播 — 使用獨立 bot / chat。

環境變數：
  WINGSTARS_BOT_TOKEN  (必填)
  WINGSTARS_CHAT_ID    (必填)
"""
import logging
import os
import time
import requests

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("WINGSTARS_BOT_TOKEN", "")
CHAT_ID = os.getenv("WINGSTARS_CHAT_ID", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_message(text: str, disable_preview: bool = False) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("WINGSTARS_BOT_TOKEN or WINGSTARS_CHAT_ID missing — skipping push.")
        print(f"[PREVIEW] {text[:200]}...")
        return False
    try:
        resp = requests.post(
            f"{API_URL}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text[:4096],
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(f"Telegram error {resp.status_code}: {resp.text[:300]}")
            return False
        return True
    except Exception as e:
        logger.error(f"Telegram push failed: {e}")
        return False


def notify_new_post(post: dict) -> bool:
    """Format and push a new-post alert."""
    name = post.get("account_name", post["username"])
    jersey = post.get("jersey", "")
    group = post.get("account_group", "") or post.get("group", "")
    jersey_tag = f" #{jersey}" if jersey else ""

    # 球團官方 → 🦅，啦啦隊 → 🌟
    emoji = "🦅" if group == "球團官方" else "🌟"

    content = post.get("content", "") or ""
    if len(content) > 500:
        content = content[:500] + "…"

    likes = post.get("likes", 0) or 0
    replies = post.get("replies", 0) or 0
    url = post.get("post_url", "") or f"https://www.threads.net/@{post['username']}"

    msg = (
        f"{emoji} <b>{_escape_html(name)}</b>{jersey_tag} 發新文\n"
        f"\n"
        f"{_escape_html(content)}\n"
        f"\n"
        f"❤️ {likes}  ·  💬 {replies}\n"
        f"🔗 {url}"
    )
    return send_message(msg, disable_preview=False)


def send_startup(mode: str, n_accounts: int, seen_count: int) -> bool:
    msg = (
        f"✅ <b>Wing Stars 監測啟動</b> ({mode})\n"
        f"\n"
        f"📋 監測帳號：{n_accounts} 位\n"
        f"💾 DB 已記錄：{seen_count} 篇\n"
        f"⏰ 檢查頻率：每 30 分鐘\n"
    )
    return send_message(msg)


def rate_limit_sleep():
    """Telegram 30 msg/sec global limit — safe pacing for bursts."""
    time.sleep(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    send_message("🧪 <b>Wing Stars notifier 測試</b>\n連線正常。")
