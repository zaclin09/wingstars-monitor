"""Wing Stars 主監測迴圈 — 只抓 posts 分頁（不抓 replies），GCP 上約 15–25 分鐘跑完。

執行模式：
  python wingstars_monitor.py              # 正常：抓新主貼文、即推播
  python wingstars_monitor.py --seed       # 首次：只入 DB、不推
  python wingstars_monitor.py --test       # 測試：推第一則就停
  python wingstars_monitor.py --notify-startup  # 同時推一則啟動通知
"""
import argparse
import asyncio
import logging
import random
import sys
from datetime import datetime

from scraper import _create_browser, _scrape_tab
import config

from wingstars_accounts import load_wingstars_accounts
import wingstars_db as wsdb
import wingstars_notifier as wsnotify


logger = logging.getLogger("wingstars")
BATCH_SIZE = 1  # 每抓 1 人就換新瀏覽器 — 最穩，避免 mid-batch 卡死


async def _scrape_batch(batch: list[dict]) -> list[dict]:
    """一批帳號共用一個瀏覽器，只抓 posts 分頁。"""
    results = []
    pw, browser, context = await _create_browser()
    page = await context.new_page()
    try:
        for j, acc in enumerate(batch):
            username = acc["username"]
            logger.info(f"  scraping @{username}...")
            try:
                posts = await _scrape_tab(page, username, acc, "threads")
                for p in posts:
                    p["post_type"] = "post"
                results.extend(posts)
                logger.info(f"    found {len(posts)} main posts")
            except Exception as e:
                logger.error(f"  error @{username}: {e}")
            if j < len(batch) - 1:
                await asyncio.sleep(
                    random.uniform(config.SCRAPE_DELAY_MIN, config.SCRAPE_DELAY_MAX)
                )
    finally:
        await browser.close()
        await pw.stop()
    return results


async def scrape_wingstars(accounts: list[dict]) -> list[dict]:
    """分批掃所有帳號（每批 BATCH_SIZE 個重開瀏覽器）。"""
    all_posts = []
    total_batches = (len(accounts) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(accounts), BATCH_SIZE):
        batch = accounts[i:i + BATCH_SIZE]
        bn = i // BATCH_SIZE + 1
        logger.info(
            f"--- Batch {bn}/{total_batches}: "
            f"@{batch[0]['username']} ... @{batch[-1]['username']} ---"
        )
        try:
            all_posts.extend(await _scrape_batch(batch))
        except Exception as e:
            logger.error(f"Batch {bn} failed: {e}")
    return all_posts


async def run_once(seed_mode: bool = False, test_mode: bool = False) -> dict:
    wsdb.init_db()
    accounts = load_wingstars_accounts()
    logger.info(
        f"=== Wing Stars check @ {datetime.now().isoformat()} "
        f"(seed={seed_mode}, test={test_mode}) ==="
    )
    logger.info(
        f"Monitoring {len(accounts)} accounts "
        f"in batches of {BATCH_SIZE} (posts tab only)"
    )

    posts = await scrape_wingstars(accounts)
    logger.info(f"Got {len(posts)} main posts")

    # 附上 jersey / account_name（scraper 不會帶這些）
    jersey_by_user = {a["username"]: a.get("jersey", "") for a in accounts}
    name_by_user = {a["username"]: a["name"] for a in accounts}
    for p in posts:
        p["jersey"] = jersey_by_user.get(p["username"], "")
        if not p.get("account_name"):
            p["account_name"] = name_by_user.get(p["username"], "")

    new_count = pushed_count = errors = 0
    for p in posts:
        if not wsdb.is_new_post(p["id"]):
            continue
        new_count += 1
        if seed_mode:
            wsdb.record_post(p, notified=False)
            continue
        ok = wsnotify.notify_new_post(p)
        if ok:
            pushed_count += 1
            wsnotify.rate_limit_sleep()
        else:
            errors += 1
        wsdb.record_post(p, notified=ok)
        if test_mode and pushed_count >= 1:
            logger.info("Test mode: pushed 1, stopping.")
            break

    summary = {
        "main_posts": len(posts),
        "new_posts": new_count,
        "pushed": pushed_count,
        "errors": errors,
        "seed_mode": seed_mode,
    }
    logger.info(f"=== Done: {summary} ===")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", action="store_true")
    p.add_argument("--test", action="store_true")
    p.add_argument("--notify-startup", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.notify_startup:
        wsdb.init_db()
        accts = load_wingstars_accounts()
        mode = "SEED" if args.seed else ("TEST" if args.test else "LIVE")
        wsnotify.send_startup(mode, len(accts), wsdb.count_seen())

    summary = asyncio.run(run_once(seed_mode=args.seed, test_mode=args.test))

    if summary["errors"] > 0 and summary["pushed"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
