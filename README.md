# Slack Workspace Autotest

**One-command setup.** Download → extract → install → run.

## What It Does

1. Opens [slack.com](https://slack.com/intl/en-gb/)
2. Clicks **"Create a new workspace"**
3. Detects & handles reCAPTCHA (via 2captcha API)
4. Ready for you to extend with email input, confirmation code, workspace name, etc.

## Quick Start

```bash
# 1. Download ZIP from GitHub and extract
#    https://github.com/grouvi25/slack-workspace-autotest/archive/refs/heads/main.zip

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
#    On Windows, if 'playwright' command is not found, use the full path:
#    python -m playwright install chromium
#    Or add Scripts folder to PATH first:
#    $env:PATH += ";C:\Users\YOURNAME\AppData\Roaming\Python\Python3xx\Scripts"
playwright install chromium

# 4. (Optional) Set captcha API key
export CAPTCHA_API_KEY="your-2captcha-key"   # macOS/Linux
set CAPTCHA_API_KEY=your-2captcha-key         # Windows CMD
$env:CAPTCHA_API_KEY="your-2captcha-key"     # Windows PowerShell

# 5. Run
python slack_autotest.py
```
# 1. Download ZIP from GitHub and extract
#    https://github.com/grouvi25/slack-workspace-autotest/archive/refs/heads/main.zip

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. (Optional) Set captcha API key
export CAPTCHA_API_KEY="your-2captcha-key"   # macOS/Linux
set CAPTCHA_API_KEY=your-2captcha-key         # Windows CMD

# 4. Run
python slack_autotest.py
```

## Files

| File | Purpose |
|------|---------|
| `slack_autotest.py` | Main script — runs the scenario |
| `requirements.txt` | Python packages to install |
| `.env.example` | Template for environment variables |

## Extending the Scenario

Open `slack_autotest.py` and add steps after the `# ── EXTENSION POINT ──` comment:

```python
await page.fill('input[type="email"]', 'your@email.com')
await page.click('button[type="submit"]')
```

## reCAPTCHA Note

- **Production**: Google prohibits automated solving. Use this only on test/staging environments.
- **Test key** (always passes): `6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI`
- **Disable captcha**: Best option for automated testing.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `playwright : Имя не распознано` (Windows) | Run `python -m playwright install chromium` instead. Or add `C:\Users\YOU\AppData\Roaming\Python\Python3xx\Scripts` to PATH. |
| `Page.goto: Timeout 30000ms exceeded` | Fixed in latest version — uses `wait_until="load"` with fallback. If still happening, increase timeout in script or check internet connection. |
| `CAPTCHA_API_KEY not set` | Export the env var or edit the script |
| Button not found | Slack may have changed the page — update `CREATE_BTN` selector |
| Blocked by bot detection | Script includes stealth measures; try adding delays between actions |

| Issue | Fix |
|-------|-----|
| `playwright not found` | Run `playwright install chromium` |
| `CAPTCHA_API_KEY not set` | Export the env var or edit the script |
| Button not found | Slack may have changed the page — update `CREATE_BTN` selector |
| Blocked by bot detection | Script includes stealth measures; try adding delays between actions |

## Download

- **ZIP**: [github.com/grouvi25/slack-workspace-autotest/archive/refs/heads/main.zip](https://github.com/grouvi25/slack-workspace-autotest/archive/refs/heads/main.zip)
- **Repo**: [github.com/grouvi25/slack-workspace-autotest](https://github.com/grouvi25/slack-workspace-autotest)
