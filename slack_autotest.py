#!/usr/bin/env python3
"""
Slack Workspace Creation Autotest
=================================
Automates Slack workspace creation flow:
1. Opens slack.com
2. Clicks "Create a new workspace"
3. Handles reCAPTCHA (optional, via 2captcha)
4. Extensible for full signup flow

Usage:
    pip install -r requirements.txt
    playwright install chromium
    python slack_autotest.py

Env vars:
    CAPTCHA_API_KEY - 2captcha API key (optional)
    HEADLESS        - "true" to hide browser (default: false)
"""

import asyncio
import os
import sys
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# ── Config ──────────────────────────────────────────────────────────
SLACK_URL = "https://slack.com/intl/en-gb/"
CREATE_BTN = 'a[data-qa="link_create"]'
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")
CAPTCHA_KEY = os.getenv("CAPTCHA_API_KEY", "")
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]

# ── Helpers ─────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[autotest] {msg}", flush=True)


def die(msg: str) -> None:
    log(f"FATAL: {msg}")
    sys.exit(1)


async def solve_recaptcha(site_key: str, page_url: str) -> str:
    """Send reCAPTCHA to 2captcha and return the token."""
    import aiohttp

    if not CAPTCHA_KEY or CAPTCHA_KEY.startswith("YOUR"):
        die("CAPTCHA_API_KEY not set. Export it or add to .env")

    async with aiohttp.ClientSession() as session:
        # Submit
        payload = {
            "key": CAPTCHA_KEY,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "json": 1,
        }
        async with session.post("http://2captcha.com/in.php", data=payload) as r:
            data = await r.json()
            if data.get("status") != 1:
                die(f"2captcha submit error: {data}")
            cid = data["request"]
            log(f"Captcha id={cid}, waiting for workers...")

        # Poll (max 5 min)
        for i in range(60):
            await asyncio.sleep(5)
            poll_url = (
                f"http://2captcha.com/res.php"
                f"?key={CAPTCHA_KEY}&action=get&id={cid}&json=1"
            )
            async with session.get(poll_url) as r:
                res = await r.json()
                if res.get("status") == 1:
                    log("Captcha solved!")
                    return str(res["request"])
                if res.get("request") == "CAPCHA_NOT_READY":
                    if i % 6 == 0:
                        log("Still solving...")
                    continue
                die(f"2captcha poll error: {res}")

        die("Captcha solving timeout (5 min)")


async def handle_recaptcha(page: Page) -> bool:
    """Detect and solve reCAPTCHA if present. Returns True if handled."""
    iframe = await page.query_selector('iframe[src*="recaptcha"]')
    if not iframe:
        log("No captcha detected")
        return False

    log("reCAPTCHA detected — solving...")

    # Extract sitekey
    site_key = await page.evaluate("""
        () => {
            const el = document.querySelector('.g-recaptcha');
            return el ? el.dataset.sitekey : null;
        }
    """)
    if not site_key:
        src = await iframe.get_attribute("src")
        if src and "k=" in src:
            site_key = src.split("k=")[1].split("&")[0]

    if not site_key:
        die("Could not extract reCAPTCHA sitekey")

    token = await solve_recaptcha(site_key, page.url)

    # Inject token
    await page.evaluate(
        """
        (token) => {
            const el = document.getElementById("g-recaptcha-response");
            if (el) el.innerHTML = token;
            // Also try common callback
            if (window.grecaptcha) {
                try { grecaptcha.getResponse = () => token; } catch(e){}
            }
        }
        """,
        token,
    )
    log("Captcha token injected")
    return True


async def ensure_click(page: Page, selector: str, timeout: int = 10_000) -> None:
    """Wait for selector and click with retry."""
    await page.wait_for_selector(selector, timeout=timeout, state="visible")
    await page.click(selector)


# ── Main Scenario ───────────────────────────────────────────────────

async def run_scenario() -> None:
    log(f"Launching browser (headless={HEADLESS})")

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=BROWSER_ARGS,
        )
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        # Hide automation flags
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
        """)

        page: Page = await context.new_page()

        try:
            # Step 1 — Open Slack (use 'load' instead of 'networkidle' to avoid timeout on heavy pages)
            log(f"Step 1: Opening {SLACK_URL}")
            try:
                await asyncio.sleep(3)
                log("Load timeout, continuing anyway...")
            except Exception:
                await page.goto(SLACK_URL, wait_until="load", timeout=30000)

            # Step 2 — Click "Create a new workspace"
            log("Step 2: Clicking 'Create a new workspace'")
            await ensure_click(page, CREATE_BTN)
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)  # Extra buffer for JS hydration
            log(f"Navigated to: {page.url}")

            # Step 3 — Handle reCAPTCHA if present
            await handle_recaptcha(page)

            # ── EXTENSION POINT ──
            # Add more steps here:
            # await page.fill('input[type="email"]', 'test@example.com')
            # await page.click('button[type="submit"]')
            # confirmation_code = input("Enter code: ")
            # await page.fill('input[name="code"]', confirmation_code)

            log("Scenario completed. Browser stays open for inspection.")
            if not HEADLESS:
                await asyncio.sleep(300)  # 5 min to inspect

        except Exception as e:
            log(f"ERROR: {e}")
            # Save screenshot for debugging
            try:
                await page.screenshot(path="error_screenshot.png")
                log("Screenshot saved: error_screenshot.png")
            except Exception:
                pass
            raise

        finally:
            await browser.close()
            log("Browser closed")


# ── Entrypoint ──────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(run_scenario())
    except KeyboardInterrupt:
        log("Interrupted by user")
    except Exception as e:
        die(str(e))
