"""
Captcha Admin Solver.
Sends captcha request to admin via Telegram.
Admin solves it manually on their browser and sends the token back.
"""
import asyncio
from booking_bot.config import CAPTCHA_TIMEOUT_SECONDS, ADMIN_TELEGRAM_ID, TAZKARTI_BASE_URL

# Pending captcha solutions: {captcha_id: asyncio.Future}
_pending_captchas: dict[str, asyncio.Future] = {}
_captcha_counter = 0


async def solve_captcha_via_admin(bot, user_label: str) -> str | None:
    """
    Ask admin to solve captcha manually and return the token.
    
    Flow:
    1. Bot sends admin a message asking them to solve captcha on tazkarti.com
    2. Admin opens tazkarti.com, solves captcha, copies token from console
    3. Admin sends token back to bot
    4. Bot uses token for login
    """
    global _captcha_counter
    _captcha_counter += 1
    captcha_id = f"C{_captcha_counter:04d}"

    # Create future to wait for response
    future = asyncio.get_event_loop().create_future()
    _pending_captchas[captcha_id] = future

    # Send request to admin
    await bot.send_message(
        ADMIN_TELEGRAM_ID,
        f"🔐 Captcha مطلوبة #{captcha_id}\n"
        f"👤 {user_label}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 الخطوات:\n"
        f"1. افتح: {TAZKARTI_BASE_URL}/#/sign-in\n"
        f"2. حل الـ Captcha (بس متعملش login)\n"
        f"3. افتح Console (F12) واكتب:\n"
        f"document.querySelector('#g-recaptcha-response').value\n"
        f"4. انسخ الـ token وابعته هنا كده:\n\n"
        f"#{captcha_id} TOKEN_HERE\n\n"
        f"⏰ عندك دقيقتين"
    )

    # Wait for admin's response
    try:
        token = await asyncio.wait_for(future, timeout=CAPTCHA_TIMEOUT_SECONDS)
        return token
    except asyncio.TimeoutError:
        _pending_captchas.pop(captcha_id, None)
        await bot.send_message(
            ADMIN_TELEGRAM_ID,
            f"⏰ #{captcha_id} | انتهت المهلة!"
        )
        return None


def handle_admin_captcha_reply(text: str) -> tuple[str, str] | None:
    """
    Parse admin's captcha solution reply.
    Format: #C0001 <token>
    Returns (captcha_id, token) or None if not a captcha reply.
    """
    if not text.startswith("#C"):
        return None

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None

    captcha_id = parts[0][1:]  # Remove '#'
    token = parts[1].strip()

    if len(token) < 20:
        return None  # Token too short, probably not valid

    return captcha_id, token


def resolve_captcha(captcha_id: str, token: str) -> bool:
    """Resolve a pending captcha with the admin's token."""
    if captcha_id in _pending_captchas:
        future = _pending_captchas[captcha_id]
        if not future.done():
            future.set_result(token)
            del _pending_captchas[captcha_id]
            return True
    return False


def get_pending_count() -> int:
    """Get the number of pending captcha solutions."""
    return len(_pending_captchas)
