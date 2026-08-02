# Wing Stars Monitor

自動監測 26 位 Wing Stars 啦啦隊員 + 4 個台鋼球團官方帳號的 Threads 新貼文，
發現新文就推播到 Telegram 群組。

## 架構

- **GitHub Actions cron**（每 30 分鐘）→ 觸發 workflow
- **Playwright + Chromium**（Ubuntu runner）→ 抓 Threads 頁面
- **SQLite** (`data/wingstars.db`) → 記錄看過的 post ID（提交回 repo 作為狀態存放）
- **Telegram Bot API** → 推播新文

## 監測範圍

- 26 位 Wing Stars 啦啦隊員（`wingstars_accounts.py`）
- 4 個球團官方：`@tsg_hawks`（雄鷹）、`@tainan_tsg_ghosthawks`（獵鷹）、`@tsg_skyhawks`（天鷹）、`@wing_stars_official`

## 部署設定

需在 Repository Settings → Secrets and variables → Actions 加入以下 secrets：

| Secret 名稱 | 內容 |
|---|---|
| `WINGSTARS_BOT_TOKEN` | Telegram bot token (`123456:AAA...`) |
| `WINGSTARS_CHAT_ID` | Telegram chat ID（個人 `783287701` / 群組 `-5166719093`） |
| `THREADS_SESSION_B64` | `base64 -i data/threads_session.json` 的輸出 |

## 首次啟動

1. 手動觸發一次 workflow，選 `seed_mode = true` → 只入 DB、不推 Telegram
2. 之後排程正常跑（`seed_mode = false`）

## 維護

- **Threads session 30–90 天會過期** → 本機重跑 `save_session.py` → 更新 `THREADS_SESSION_B64` secret
- **監測不到新貼文**：先看最近 workflow log，多半是 session 過期
