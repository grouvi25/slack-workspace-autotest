"""
Slack Workspace Creation Autotest
Stack: Python + Playwright + 2captcha (for reCAPTCHA)
"""

import asyncio
import os
from playwright.async_api import async_playwright, Page

# --- Config ---
SLACK_START_URL = "https://slack.com/intl/en-gb/"
CREATE_WORKSPACE_SELECTOR = 'a[data-qa="link_create"]'
HEADLESS = False  # Set True for CI, False to see the browser

# If using 2captcha / Anti-Captcha for reCAPTCHA
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", "YOUR_2CAPTCHA_KEY_HERE")


async def solve_recaptcha(page: Page, site_key: str, page_url: str) -> str:
    """
    Integrate with 2captcha to solve reCAPTCHA.
    Returns the g-recaptcha-response token.
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        # 1. Send captcha for solving
        payload = {
            "key": CAPTCHA_API_KEY,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "json": 1,
        }
        async with session.post("http://2captcha.com/in.php", data=payload) as resp:
            data = await resp.json()
            if data.get("status") != 1:
                raise RuntimeError(f"2captcha error: {data}")
            captcha_id = data["request"]

        # 2. Poll for result
        print(f"[2captcha] Waiting for solution (id={captcha_id})...")
        for _ in range(60):
            await asyncio.sleep(5)
            async with session.get(
                f"http://2captcha.com/res.php?key={CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1"
            ) as resp:
                result = await resp.json()
                if result.get("status") == 1:
                    print("[2captcha] Solved!")
                    return result["request"]
                if result.get("request") == "CAPCHA_NOT_READY":
                    continue
                raise RuntimeError(f"2captcha error: {result}")

        raise TimeoutError("2captcha solving timeout")


async def handle_recaptcha(page: Page):
    """
    Detects and solves reCAPTCHA on the current page.
    """
    # Check for reCAPTCHA iframe
    recaptcha_frame = await page.query_selector('iframe[src*="recaptcha"]')
    if not recaptcha_frame:
        print("[recaptcha] No captcha detected, skipping...")
        return

    print("[recaptcha] Detected, solving...")

    # Extract sitekey from page or iframe
    site_key = await page.evaluate("""
        () => {
            const el = document.querySelector('.g-recaptcha');
            return el ? el.dataset.sitekey : null;
        }
    """)

    if not site_key:
        # Try to get from iframe src
        frame_src = await recaptcha_frame.get_attribute("src")
        if "k=" in frame_src:
            site_key = frame_src.split("k=")[1].split("&")[0]

    if not site_key:
        raise RuntimeError("Could not extract reCAPTCHA site key")

    token = await solve_recaptcha(page, site_key, page.url)

    # Inject token and submit
    await page.evaluate(
        """
        (token) => {
            document.getElementById("g-recaptcha-response").innerHTML = token;
        }
        """,
        token,
    )
    print("[recaptcha] Token injected")


async def run_scenario():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Hide webdriver flag
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        )

        page = await context.new_page()

        # Step 1: Open Slack
        print(f"[step 1] Opening {SLACK_START_URL}")
        await page.goto(SLACK_START_URL, wait_until="networkidle")

        # Step 2: Click "Create a new workspace"
        print("[step 2] Clicking 'Create a new workspace'...")
        await page.click(CREATE_WORKSPACE_SELECTOR)

        # Wait for navigation or popup
        await page.wait_for_load_state("networkidle")
        print(f"[step 2] Landed on: {page.url}")

        # Step 3: Handle reCAPTCHA if present
        await handle_recaptcha(page)

        # --- EXTENSION POINT ---
        # Add next steps here as scenario expands:
        # - Fill email
        # - Enter confirmation code
        # - Set workspace name
        # - etc.

        print("[done] Scenario completed. Pausing for inspection...")
        await asyncio.sleep(30)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_scenario())
