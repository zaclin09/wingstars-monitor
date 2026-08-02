import asyncio
import json
import logging
import random
import re
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser

import config

logger = logging.getLogger(__name__)


def _parse_count(text: str) -> int:
    """Parse display counts like '1.2K', '3.5M', '150' into integers."""
    if not text:
        return 0
    text = text.strip().replace(",", "").replace(" ", "")
    multipliers = {"K": 1000, "M": 1000000, "B": 1000000000,
                   "k": 1000, "m": 1000000, "萬": 10000, "億": 100000000}
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-len(suffix)]) * mult)
            except ValueError:
                return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


async def _create_browser() -> tuple:
    """Create a Playwright browser instance."""
    pw = await async_playwright().start()
    launch_args = {
        "headless": config.HEADLESS,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",  # crucial for 1GB e2-micro (avoid /dev/shm)
            "--disable-gpu",
        ]
    }
    if config.PROXY:
        launch_args["proxy"] = {"server": config.PROXY}

    browser = await pw.chromium.launch(**launch_args)

    context_args = {
        "viewport": {"width": 430, "height": 932},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/17.5 Mobile/15E148 Safari/604.1",
        "locale": "zh-TW",
    }

    # Load saved Threads login session if available
    session_file = config.DATA_DIR / "threads_session.json"
    if session_file.exists():
        logger.info(f"Loading saved Threads session from {session_file}")
        context_args["storage_state"] = str(session_file)
    else:
        logger.warning("No Threads session file found — running unauthenticated (very limited data).")

    context = await browser.new_context(**context_args)
    return pw, browser, context


async def scrape_account(page: Page, username: str, account_info: dict) -> list[dict]:
    """Scrape recent posts AND replies from a single Threads account."""
    all_posts = []

    # Scrape main Threads tab (posts)
    all_posts.extend(await _scrape_tab(page, username, account_info, "threads"))

    # Scrape Replies tab (comments on others' posts)
    all_posts.extend(await _scrape_tab(page, username, account_info, "replies"))

    return all_posts


async def _scrape_tab(page: Page, username: str, account_info: dict, tab: str) -> list[dict]:
    """Scrape a single tab (threads or replies) from a profile."""
    if tab == "replies":
        url = f"https://www.threads.net/@{username}/replies"
    else:
        url = f"https://www.threads.net/@{username}"

    post_type = "reply" if tab == "replies" else "post"
    posts = []

    try:
        if True:  # py3.10 compat (was: async with asyncio.timeout(45))
            await page.goto(url, timeout=config.SCRAPE_TIMEOUT, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)

            if "Sorry, this page" in (await page.content()):
                if tab == "threads":
                    logger.warning(f"Profile not found: @{username}")
                return []

            try:
                await page.wait_for_selector('[data-pressable-container="true"]', timeout=6000)
            except Exception:
                pass

            # Single deep scroll — multi-scroll caused per-account >2min, scheduler hangs.
            # Use manual_rescrape.py for deep recovery on specific accounts.
            await page.evaluate("window.scrollBy(0, 3000)")
            await page.wait_for_timeout(1500)

            posts = await _extract_posts_from_page(page, username, account_info, tab)
            if not posts and tab == "threads":
                # DOM fallback only for posts tab (replies need is_reply filter we can't do from DOM)
                posts = await _extract_posts_from_dom(page, username, account_info)

            # Tag post_type
            for p in posts:
                p["post_type"] = post_type

    except asyncio.TimeoutError:
        logger.warning(f"Timeout (45s) scraping @{username}/{tab}, skipping")
    except Exception as e:
        logger.error(f"Error scraping @{username}/{tab}: {e}")

    return posts


async def _extract_posts_from_page(page: Page, username: str, account_info: dict, tab: str = "threads") -> list[dict]:
    """Try to extract post data from Threads page's script tags / API responses.

    Filtering rules:
      - Author must match target username (filter out parent posts from other users)
      - On "threads" tab: only keep is_reply=False (original posts, not user's replies)
      - On "replies" tab: only keep is_reply=True (user's own replies)
      - Exclude reposts (reposted_post is not None)
    """
    posts = []

    try:
        # Threads embeds data in script tags with type="application/json"
        script_contents = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/json"]');
                return Array.from(scripts).map(s => s.textContent).filter(Boolean);
            }
        """)

        want_reply = (tab == "replies")

        seen_ids = set()
        for script_text in script_contents:
            try:
                data = json.loads(script_text)
                extracted = _find_thread_items(data, username)
                for item in extracted:
                    # 1. Must be authored by target user
                    user_info = item.get("user", {})
                    if isinstance(user_info, dict):
                        author = user_info.get("username", "")
                        if not author or author.lower() != username.lower():
                            continue
                    else:
                        continue  # no author info → skip for safety

                    # 2. Check is_reply vs tab
                    tpai = item.get("text_post_app_info", {})
                    if not isinstance(tpai, dict):
                        continue
                    is_reply = bool(tpai.get("is_reply", False))
                    if is_reply != want_reply:
                        continue

                    # 3. Exclude reposts
                    share_info = tpai.get("share_info", {})
                    if isinstance(share_info, dict) and share_info.get("reposted_post"):
                        continue

                    post = _normalize_post(item, username, account_info)
                    if post and post["id"] not in seen_ids:
                        seen_ids.add(post["id"])
                        posts.append(post)
            except (json.JSONDecodeError, TypeError):
                continue

    except Exception as e:
        logger.debug(f"JSON extraction failed for @{username}: {e}")

    return posts[:config.MAX_POSTS_PER_ACCOUNT]


def _find_thread_items(data, username: str, depth: int = 0) -> list[dict]:
    """Recursively search JSON data for thread/post items.

    Threads embeds post data in:
      data.mediaData.edges[].node.thread_items[].post
    Each post has: pk, code, caption.text, text_post_app_info, taken_at, like_count, etc.
    """
    if depth > 20:
        return []
    results = []

    if isinstance(data, dict):
        # Primary pattern: thread_items array containing post objects
        if "thread_items" in data and isinstance(data["thread_items"], list):
            for item in data["thread_items"]:
                if isinstance(item, dict):
                    post_data = item.get("post", item)
                    if isinstance(post_data, dict) and ("pk" in post_data or "code" in post_data):
                        results.append(post_data)

        # Secondary pattern: dict with pk + caption (a post object itself)
        elif "pk" in data and "caption" in data and isinstance(data.get("caption"), dict):
            results.append(data)

        # Recurse into all values (skip if we already found thread_items here)
        if "thread_items" not in data:
            for v in data.values():
                results.extend(_find_thread_items(v, username, depth + 1))
        else:
            # Still recurse into edges/nodes for other thread groups
            for key in ("edges", "node", "data", "result", "mediaData"):
                if key in data:
                    results.extend(_find_thread_items(data[key], username, depth + 1))

    elif isinstance(data, list):
        for item in data:
            results.extend(_find_thread_items(item, username, depth + 1))

    return results


def _normalize_post(raw: dict, username: str, account_info: dict) -> dict | None:
    """Normalize a raw post dict into our standard format.

    Threads JSON post structure:
      - caption.text → content
      - text_post_app_info.text_fragments.fragments[].plaintext → content (fallback)
      - pk → post ID
      - code → URL slug
      - like_count → likes (may be 0 or missing in initial load)
      - text_post_app_info.direct_reply_count → replies
      - taken_at → timestamp
    """
    # Extract content from caption or text_fragments
    caption = raw.get("caption")
    content = ""
    if isinstance(caption, dict):
        content = caption.get("text", "")

    if not content:
        # Try text_fragments
        tpai = raw.get("text_post_app_info")
        if isinstance(tpai, dict):
            tf = tpai.get("text_fragments", {})
            if isinstance(tf, dict):
                fragments = tf.get("fragments", [])
                if isinstance(fragments, list):
                    parts = []
                    for f in fragments:
                        if isinstance(f, dict):
                            parts.append(f.get("plaintext", "") or "")
                    content = "".join(parts)

    if not content:
        content = raw.get("text", "") or ""

    if not content:
        return None

    # Post ID and URL
    pk = str(raw.get("pk", ""))
    code = raw.get("code", "")
    post_id = pk or code or str(hash(f"{username}_{content[:50]}"))
    post_url = f"https://www.threads.net/@{username}/post/{code}" if code else ""

    # Metrics
    likes = raw.get("like_count", 0) or 0
    views = raw.get("view_count", 0) or 0

    replies = 0
    reposts = 0
    tpai = raw.get("text_post_app_info")
    if isinstance(tpai, dict):
        replies = tpai.get("direct_reply_count", 0) or 0
        reposts = (tpai.get("repost_count", 0)
                   or tpai.get("reshare_count", 0) or 0)
    # fallback on top-level
    if not reposts:
        reposts = raw.get("reshare_count", 0) or raw.get("repost_count", 0) or 0

    # Timestamp
    created_at = ""
    ts = raw.get("taken_at") or raw.get("timestamp")
    if ts and isinstance(ts, (int, float)):
        created_at = datetime.fromtimestamp(ts).isoformat()

    # Media detection: Threads media_type 1=image, 2=video, 8=carousel
    media = "none"
    mt = raw.get("media_type")
    if mt == 2 or raw.get("video_versions"):
        media = "video"
    elif mt == 1 or raw.get("image_versions2") or raw.get("carousel_media"):
        media = "image"
    elif mt == 8:
        # Check carousel for any video
        cm = raw.get("carousel_media") or []
        media = "image"
        for m in cm:
            if isinstance(m, dict) and (m.get("video_versions") or m.get("media_type") == 2):
                media = "video"
                break

    return {
        "id": post_id,
        "username": username,
        "account_id": account_info.get("id", ""),
        "account_name": account_info.get("name", ""),
        "account_group": account_info.get("group", ""),
        "content": content,
        "likes": int(likes),
        "views": int(views),
        "replies": int(replies),
        "post_url": post_url,
        "post_type": "post",  # caller may override to "reply"
        "created_at": created_at,
        "media": media,
        "reposts": int(reposts),
    }


async def _extract_posts_from_dom(page: Page, username: str, account_info: dict) -> list[dict]:
    """Fallback: extract posts by parsing the visible DOM elements."""
    posts = []

    try:
        # Wait for post containers to appear
        await page.wait_for_selector('[data-pressable-container="true"]', timeout=5000)

        post_elements = await page.query_selector_all('[data-pressable-container="true"]')

        for i, el in enumerate(post_elements[:config.MAX_POSTS_PER_ACCOUNT]):
            try:
                # Extract text content
                text_el = await el.query_selector('[dir="auto"]')
                content = await text_el.inner_text() if text_el else ""

                # Extract link
                link_el = await el.query_selector('a[href*="/post/"]')
                post_url = ""
                code = ""
                if link_el:
                    href = await link_el.get_attribute("href") or ""
                    if "/post/" in href:
                        code = href.split("/post/")[-1].rstrip("/")
                        post_url = f"https://www.threads.net{href}"

                # Extract metrics from aria-labels or visible text
                all_text = await el.inner_text()
                likes = _extract_metric(all_text, ["likes", "like", "個讚", "愛心"])
                views = _extract_metric(all_text, ["views", "view", "次查看", "瀏覽"])
                replies = _extract_metric(all_text, ["replies", "reply", "則回覆", "回覆"])

                if content:
                    post_id = code or str(hash(f"{username}_{content[:50]}_{i}"))
                    posts.append({
                        "id": post_id,
                        "username": username,
                        "account_id": account_info.get("id", ""),
                        "account_name": account_info.get("name", ""),
                        "account_group": account_info.get("group", ""),
                        "content": content,
                        "likes": likes,
                        "views": views,
                        "replies": replies,
                        "post_url": post_url,
                        "post_type": "post",
                        "created_at": "",
                    })
            except Exception as e:
                logger.debug(f"Failed to parse post element for @{username}: {e}")
                continue

    except Exception as e:
        logger.debug(f"DOM extraction failed for @{username}: {e}")

    return posts


def _extract_metric(text: str, keywords: list[str]) -> int:
    """Extract a numeric metric from text near specific keywords."""
    for kw in keywords:
        pattern = rf'(\d[\d,.]*[KkMm萬億]?)\s*{re.escape(kw)}'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _parse_count(match.group(1))
        pattern = rf'{re.escape(kw)}\s*(\d[\d,.]*[KkMm萬億]?)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _parse_count(match.group(1))
    return 0


async def scrape_all_accounts(accounts: list[dict]) -> list[dict]:
    """Scrape all accounts and return all posts found."""
    all_posts = []

    pw, browser, context = await _create_browser()
    page = await context.new_page()

    try:
        for i, account in enumerate(accounts):
            username = account["username"]
            logger.info(f"[{i+1}/{len(accounts)}] Scraping @{username}...")

            posts = await scrape_account(page, username, account)
            all_posts.extend(posts)
            logger.info(f"  Found {len(posts)} posts for @{username}")

            if i < len(accounts) - 1:
                delay = random.uniform(config.SCRAPE_DELAY_MIN, config.SCRAPE_DELAY_MAX)
                await asyncio.sleep(delay)

    finally:
        await browser.close()
        await pw.stop()

    logger.info(f"Total: scraped {len(all_posts)} posts from {len(accounts)} accounts")
    return all_posts


if __name__ == "__main__":
    import sys
    from accounts import load_accounts

    logging.basicConfig(level=logging.INFO)

    accts = load_accounts()
    if len(sys.argv) > 1:
        test_user = sys.argv[1]
        accts = [a for a in accts if a["username"] == test_user]

    posts = asyncio.run(scrape_all_accounts(accts[:2]))
    for p in posts:
        print(f"  @{p['username']}: {p['content'][:80]}... | likes={p['likes']} views={p['views']}")
