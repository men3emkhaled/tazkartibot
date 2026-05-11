"""
Captcha Admin Solver.
Sends reCAPTCHA challenges to the admin via Telegram and waits for the solution.
Uses Playwright to interact with the reCAPTCHA widget.
"""
import asyncio
import time
from playwright.async_api import async_playwright, Page, BrowserContext
from booking_bot.config import (
    TAZKARTI_BASE_URL, CAPTCHA_TIMEOUT_SECONDS, ADMIN_TELEGRAM_ID
)

# Pending captcha solutions: {captcha_id: asyncio.Future}
_pending_captchas: dict[str, asyncio.Future] = {}
_captcha_counter = 0


async def solve_captcha_via_admin(bot, user_label: str) -> str | None:
    """
    Opens the Tazkarti login page in Playwright, triggers the reCAPTCHA,
    screenshots the challenge, sends it to admin, and waits for the solution.

    Returns the g-recaptcha-response token or None on failure/timeout.
    """
    global _captcha_counter
    _captcha_counter += 1
    captcha_id = f"C{_captcha_counter:04d}"

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 450, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # Navigate to login page
            await page.goto(f"{TAZKARTI_BASE_URL}/#/sign-in", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Find and click the reCAPTCHA checkbox
            recaptcha_frame = None
            for frame in page.frames:
                if "recaptcha" in frame.url:
                    recaptcha_frame = frame
                    break

            if not recaptcha_frame:
                await bot.send_message(
                    ADMIN_TELEGRAM_ID,
                    f"⚠️ #{captcha_id} | مفيش reCAPTCHA في صفحة اللوجين!\n"
                    f"👤 {user_label}"
                )
                return None

            # Click the checkbox
            checkbox = await recaptcha_frame.query_selector("#recaptcha-anchor")
            if checkbox:
                await checkbox.click()
                await asyncio.sleep(3)

            # Check if solved immediately (no image challenge)
            token = await _extract_recaptcha_token(page)
            if token:
                await bot.send_message(
                    ADMIN_TELEGRAM_ID,
                    f"✅ #{captcha_id} | Captcha اتحلت أوتوماتيك!\n👤 {user_label}"
                )
                return token

            # Image challenge appeared - screenshot and send to admin
            return await _handle_image_challenge(
                bot, page, context, captcha_id, user_label
            )

    except Exception as e:
        await bot.send_message(
            ADMIN_TELEGRAM_ID,
            f"❌ #{captcha_id} | خطأ في الـ Captcha: {str(e)[:200]}\n👤 {user_label}"
        )
        return None
    finally:
        if browser:
            await browser.close()


async def _handle_image_challenge(bot, page: Page, context: BrowserContext,
                                  captcha_id: str, user_label: str) -> str | None:
    """Handle reCAPTCHA image challenge by sending screenshots to admin."""
    max_attempts = 5

    for attempt in range(max_attempts):
        # Find the challenge iframe
        challenge_frame = None
        for frame in page.frames:
            if "api2/bframe" in frame.url or "recaptcha" in frame.url:
                el = await frame.query_selector(".rc-imageselect-challenge")
                if el:
                    challenge_frame = frame
                    break

        if not challenge_frame:
            await asyncio.sleep(2)
            continue

        # Screenshot the challenge
        challenge_el = await challenge_frame.query_selector(".rc-imageselect-challenge")
        if not challenge_el:
            continue

        screenshot_bytes = await challenge_el.screenshot()

        # Create a future to wait for admin's response
        future = asyncio.get_event_loop().create_future()
        _pending_captchas[captcha_id] = future

        # Send to admin
        from aiogram.types import BufferedInputFile
        photo = BufferedInputFile(screenshot_bytes, filename=f"captcha_{captcha_id}.png")
        await bot.send_photo(
            ADMIN_TELEGRAM_ID,
            photo=photo,
            caption=(
                f"🔐 Captcha #{captcha_id} | محاولة {attempt + 1}/{max_attempts}\n"
                f"👤 {user_label}\n\n"
                f"📝 ابعت أرقام المربعات الصح (مثال: 1 3 5 7)\n"
                f"المربعات مرقمة من اليسار لليمين، من فوق لتحت:\n"
                f"1️⃣ 2️⃣ 3️⃣\n4️⃣ 5️⃣ 6️⃣\n7️⃣ 8️⃣ 9️⃣\n\n"
                f"ابعت: #{captcha_id} الأرقام\n"
                f"مثال: #{captcha_id} 1 4 7"
            )
        )

        # Wait for admin's response
        try:
            selected_cells = await asyncio.wait_for(future, timeout=CAPTCHA_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            del _pending_captchas[captcha_id]
            await bot.send_message(
                ADMIN_TELEGRAM_ID,
                f"⏰ #{captcha_id} | انتهت المهلة! الكابتشا اتكنسلت.\n👤 {user_label}"
            )
            return None
        finally:
            _pending_captchas.pop(captcha_id, None)

        # Click the selected cells
        await _click_captcha_cells(challenge_frame, selected_cells)

        # Click verify/submit
        verify_btn = await challenge_frame.query_selector("#recaptcha-verify-button")
        if verify_btn:
            await verify_btn.click()
            await asyncio.sleep(3)

        # Check if solved
        token = await _extract_recaptcha_token(page)
        if token:
            await bot.send_message(
                ADMIN_TELEGRAM_ID,
                f"✅ #{captcha_id} | تمام! الـ Captcha اتحلت! 🎉\n👤 {user_label}"
            )
            return token

        # Not solved yet, loop again for a new challenge

    return None


async def _click_captcha_cells(frame, cell_numbers: list[int]):
    """Click specific cells in the reCAPTCHA image grid."""
    # reCAPTCHA grid cells are typically td elements in a table
    cells = await frame.query_selector_all("td.rc-imageselect-tile")
    if not cells:
        # Try alternative selector
        cells = await frame.query_selector_all(".rc-imageselect-tile")

    for num in cell_numbers:
        idx = num - 1  # Convert 1-based to 0-based
        if 0 <= idx < len(cells):
            await cells[idx].click()
            await asyncio.sleep(0.3)


async def _extract_recaptcha_token(page: Page) -> str | None:
    """Extract the g-recaptcha-response token from the page."""
    try:
        token = await page.evaluate("""
            () => {
                const textarea = document.querySelector('#g-recaptcha-response')
                    || document.querySelector('[name="g-recaptcha-response"]')
                    || document.querySelector('textarea[name="g-recaptcha-response"]');
                return textarea ? textarea.value : null;
            }
        """)
        if token and len(token) > 20:
            return token
        return None
    except Exception:
        return None


def handle_admin_captcha_reply(text: str) -> tuple[str, list[int]] | None:
    """
    Parse admin's captcha solution reply.
    Format: #C0001 1 3 5 7
    Returns (captcha_id, cell_numbers) or None if not a captcha reply.
    """
    if not text.startswith("#C"):
        return None

    parts = text.split()
    if len(parts) < 2:
        return None

    captcha_id = parts[0][1:]  # Remove '#'
    try:
        cell_numbers = [int(x) for x in parts[1:] if x.isdigit()]
    except ValueError:
        return None

    return captcha_id, cell_numbers


def resolve_captcha(captcha_id: str, cell_numbers: list[int]) -> bool:
    """Resolve a pending captcha with the admin's solution."""
    if captcha_id in _pending_captchas:
        future = _pending_captchas[captcha_id]
        if not future.done():
            future.set_result(cell_numbers)
            return True
    return False


def get_pending_count() -> int:
    """Get the number of pending captcha solutions."""
    return len(_pending_captchas)
