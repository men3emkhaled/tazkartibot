"""
Telegram Bot Handlers for the Booking Bot.
Manages user registration, match selection, and booking flow.
"""
import asyncio
import json
import re
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from booking_bot.bot.states import RegistrationStates, BookingStates
from booking_bot.bot.keyboards import (
    matches_keyboard, categories_keyboard, confirm_keyboard,
    yes_no_keyboard, main_menu_keyboard,
)
from booking_bot.db.operations import (
    get_user, save_user, delete_user, update_user_profile,
    get_valid_session, save_session, delete_session,
    create_booking, update_booking_status, update_booking_last,
)
from booking_bot.api.client import TazkartiClient
from booking_bot.captcha.admin_solver import (
    solve_captcha_via_admin, handle_admin_captcha_reply, resolve_captcha,
)
from booking_bot.config import ADMIN_TELEGRAM_ID, FAWRY_CODE_EXPIRY_MINUTES

router = Router()

# ==========================================
# Helpers
# ==========================================
ARABIC_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
}

def format_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.replace("T", " "), "%Y-%m-%d %H:%M:%S")
        month = ARABIC_MONTHS[dt.month]
        hour = dt.hour % 12 or 12
        period = "صباحاً" if dt.hour < 12 else "مساءً"
        return f"{dt.day} {month} الساعة {hour}:{dt.minute:02d} {period}"
    except Exception:
        return date_str

def clean_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'^(نادي|النادي)\s+', '', name)
    name = name.replace(" الرياضي", "").replace(" رياضي", "")
    name = re.sub(r'\s+(SC|FC|Club)$', '', name, flags=re.IGNORECASE)
    return name.strip()

# ==========================================
# /start Command
# ==========================================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id)
    if user:
        await message.answer(
            f"مرحباً {user['full_name'] or 'بيك'}! 👋\n\n"
            f"🆔 Tazkarti ID: {user['tazkarti_id']}\n\n"
            "اختار من القائمة:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer(
            "مرحباً بيك في بوت حجز التذاكر! 🎫\n\n"
            "محتاج تسجّل بيانات تذكرتي الأول.\n"
            "ابعتلي الـ Tazkarti ID (الرقم القومي):"
        )
        await state.set_state(RegistrationStates.waiting_tazkarti_id)

# ==========================================
# /book Command
# ==========================================
@router.message(Command("book"))
async def cmd_book(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user = get_user(message.from_user.id)
    if not user:
        await message.answer(
            "⚠️ لازم تسجّل بياناتك الأول!\n"
            "ابعتلي الـ Tazkarti ID (الرقم القومي):"
        )
        await state.set_state(RegistrationStates.waiting_tazkarti_id)
        return
    await start_booking_flow(message, state, bot, user)

# ==========================================
# Registration Flow
# ==========================================
@router.message(RegistrationStates.waiting_tazkarti_id)
async def reg_tazkarti_id(message: Message, state: FSMContext):
    tazkarti_id = message.text.strip()
    if not tazkarti_id or len(tazkarti_id) < 10:
        await message.answer("⚠️ الرقم القومي غلط. حاول تاني:")
        return
    await state.update_data(tazkarti_id=tazkarti_id)
    await message.answer("🔑 تمام! دلوقتي ابعتلي الباسورد:")
    await state.set_state(RegistrationStates.waiting_password)

@router.message(RegistrationStates.waiting_password)
async def reg_password(message: Message, state: FSMContext):
    password = message.text.strip()
    if not password or len(password) < 4:
        await message.answer("⚠️ الباسورد قصير. حاول تاني:")
        return
    await state.update_data(password=password)
    data = await state.get_data()
    # Try to delete the password message for security
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer(
        f"📋 تأكيد البيانات:\n\n"
        f"🆔 Tazkarti ID: {data['tazkarti_id']}\n"
        f"🔑 Password: {'*' * len(password)}\n\n"
        "هل البيانات صح؟",
        reply_markup=yes_no_keyboard()
    )
    await state.set_state(RegistrationStates.confirming)

@router.callback_query(RegistrationStates.confirming, F.data == "yes")
async def reg_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    success = save_user(
        callback.from_user.id,
        data["tazkarti_id"],
        data["password"]
    )
    if success:
        await callback.message.edit_text(
            "✅ تم حفظ بياناتك بنجاح! 🔐\n\n"
            "بياناتك مشفّرة ومحفوظة بأمان.\n"
            "دلوقتي تقدر تحجز تذاكر! 🎫\n\n"
            "اختار من القائمة:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await callback.message.edit_text("❌ حصل مشكلة في الحفظ. حاول تاني /start")
    await state.clear()

@router.callback_query(RegistrationStates.confirming, F.data == "no")
async def reg_confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ تم الإلغاء.\nابعتلي الـ Tazkarti ID من تاني:"
    )
    await state.set_state(RegistrationStates.waiting_tazkarti_id)

# ==========================================
# Main Menu Callbacks
# ==========================================
@router.callback_query(F.data == "book")
async def cb_book(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("⚠️ سجّل بياناتك الأول /start")
        return
    await callback.message.edit_text("⏳ جاري تسجيل الدخول...")
    await start_booking_flow(callback.message, state, bot, user, callback.from_user.id)

@router.callback_query(F.data == "my_profile")
async def cb_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if user:
        session = get_valid_session(callback.from_user.id)
        session_status = "🟢 نشطة" if session else "🔴 منتهية"
        await callback.message.edit_text(
            f"👤 بياناتك:\n\n"
            f"🆔 Tazkarti ID: {user['tazkarti_id']}\n"
            f"📛 الاسم: {user['full_name'] or 'غير معروف'}\n"
            f"📱 الموبايل: {user['mobile_number'] or 'غير معروف'}\n"
            f"🔑 الجلسة: {session_status}\n",
            reply_markup=main_menu_keyboard()
        )
    else:
        await callback.message.edit_text("⚠️ مفيش بيانات. سجّل الأول /start")

@router.callback_query(F.data == "delete_profile")
async def cb_delete(callback: CallbackQuery):
    success = delete_user(callback.from_user.id)
    delete_session(callback.from_user.id)
    if success:
        await callback.message.edit_text("✅ تم حذف بياناتك. ابدأ من جديد /start")
    else:
        await callback.message.edit_text("❌ مشكلة في الحذف.")

@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ تم الإلغاء.\n\nاختار من القائمة:",
        reply_markup=main_menu_keyboard()
    )

# ==========================================
# Booking Flow
# ==========================================
async def start_booking_flow(message: Message, state: FSMContext, bot: Bot,
                             user: dict, telegram_id: int = None):
    """Start the booking flow: login → show matches."""
    tid = telegram_id or message.from_user.id if message.from_user else 0

    # Check for valid session
    session = get_valid_session(tid)
    client = TazkartiClient(tazkarti_id=user["tazkarti_id"])

    if session:
        client.access_token = session["access_token"]
    else:
        # Need to login - captcha required
        await message.edit_text(
            "🔐 محتاج أسجّل دخول... جاري حل الـ Captcha\n"
            "⏳ استنى شوية..."
        ) if hasattr(message, 'edit_text') else await message.answer(
            "🔐 محتاج أسجّل دخول... جاري حل الـ Captcha\n⏳ استنى شوية..."
        )

        # Solve captcha via admin
        user_label = f"{user['full_name'] or user['tazkarti_id']} (TG: {tid})"
        captcha_token = await solve_captcha_via_admin(bot, user_label)

        if not captcha_token:
            text = "❌ مقدرتش أحل الـ Captcha. حاول تاني بعد شوية."
            if hasattr(message, 'edit_text'):
                await message.edit_text(text, reply_markup=main_menu_keyboard())
            else:
                await message.answer(text, reply_markup=main_menu_keyboard())
            await client.close()
            return

        # Login
        login_result = await client.login(
            user["tazkarti_id"], user["password"], captcha_token
        )

        if not login_result["success"]:
            text = f"❌ فشل تسجيل الدخول: {login_result.get('error', '')[:200]}"
            if hasattr(message, 'edit_text'):
                await message.edit_text(text, reply_markup=main_menu_keyboard())
            else:
                await message.answer(text, reply_markup=main_menu_keyboard())
            await client.close()
            return

        # Save session & update profile
        save_session(
            tid,
            login_result["access_token"],
            login_result["refresh_token"],
            json.dumps(login_result.get("profile", {})),
            login_result.get("expires_in", 3600),
        )
        update_user_profile(
            tid,
            login_result.get("full_name", ""),
            login_result.get("mobile_number", ""),
        )

    # Fetch matches
    matches = await client.get_available_matches()
    await client.close()

    if not matches:
        text = "❌ مفيش ماتشات مفتوحة للحجز دلوقتي."
        if hasattr(message, 'edit_text'):
            await message.edit_text(text, reply_markup=main_menu_keyboard())
        else:
            await message.answer(text, reply_markup=main_menu_keyboard())
        return

    # Store matches in state for later
    matches_simple = []
    for m in matches:
        matches_simple.append({
            "matchId": m.get("matchId"),
            "t1": m.get("teamNameAr1") or m.get("teamName1", ""),
            "t2": m.get("teamNameAr2") or m.get("teamName2", ""),
            "t1_en": m.get("teamName1", ""),
            "t2_en": m.get("teamName2", ""),
            "stadium": m.get("stadiumNameAr") or m.get("stadiumName", ""),
            "kickOff": m.get("kickOffTime", ""),
        })
    await state.update_data(matches=matches_simple)

    text = f"🏟️ الماتشات المتاحة ({len(matches)}):\n\nاختار الماتش:"
    if hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=matches_keyboard(matches))
    else:
        await message.answer(text, reply_markup=matches_keyboard(matches))
    await state.set_state(BookingStates.selecting_match)

# ==========================================
# Match Selection
# ==========================================
@router.callback_query(BookingStates.selecting_match, F.data.startswith("match_"))
async def cb_select_match(callback: CallbackQuery, state: FSMContext):
    match_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    matches = data.get("matches", [])

    selected = next((m for m in matches if m["matchId"] == match_id), None)
    if not selected:
        await callback.answer("⚠️ الماتش مش موجود!")
        return

    await state.update_data(selected_match=selected)
    await callback.message.edit_text("⏳ جاري جلب الدرجات المتاحة...")

    # Get categories
    user = get_user(callback.from_user.id)
    session = get_valid_session(callback.from_user.id)
    if not session:
        await callback.message.edit_text("⚠️ الجلسة انتهت. حاول تاني /book")
        await state.clear()
        return

    client = TazkartiClient(access_token=session["access_token"])
    categories = await client.get_available_categories(match_id)
    await client.close()

    if not categories:
        await callback.message.edit_text(
            "❌ مفيش درجات متاحة لهذا الماتش!",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
        return

    # Store categories
    cats_simple = [{
        "categoryId": c.get("categoryId"),
        "name": c.get("categoryNameAr") or c.get("categoryName", ""),
        "price": c.get("price", 0),
        "soldOut": c.get("soldOut", False),
    } for c in categories]
    await state.update_data(categories=cats_simple)

    t1 = clean_name(selected["t1"])
    t2 = clean_name(selected["t2"])
    kick = format_date(selected.get("kickOff", ""))

    await callback.message.edit_text(
        f"🏆 {t1} 🆚 {t2}\n"
        f"🏟️ {selected['stadium']}\n"
        f"📅 {kick}\n\n"
        "🎫 اختار الدرجة:",
        reply_markup=categories_keyboard(categories, match_id)
    )
    await state.set_state(BookingStates.selecting_category)

@router.callback_query(F.data == "back_matches")
async def cb_back_matches(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    matches = data.get("matches", [])
    if matches:
        # Rebuild match objects for keyboard
        match_objs = [{"matchId": m["matchId"],
                       "teamNameAr1": m["t1"], "teamNameAr2": m["t2"]} for m in matches]
        await callback.message.edit_text(
            "🏟️ اختار الماتش:",
            reply_markup=matches_keyboard(match_objs)
        )
        await state.set_state(BookingStates.selecting_match)
    else:
        await callback.message.edit_text("⚠️ حاول تاني /book")
        await state.clear()

# ==========================================
# Category Selection → Confirm → Book
# ==========================================
@router.callback_query(BookingStates.selecting_category, F.data.startswith("cat_"))
async def cb_select_category(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    match_id = int(parts[1])
    cat_id = int(parts[2])

    data = await state.get_data()
    cats = data.get("categories", [])
    selected_cat = next((c for c in cats if c["categoryId"] == cat_id), None)
    selected_match = data.get("selected_match", {})

    if not selected_cat:
        await callback.answer("⚠️ الدرجة مش موجودة!")
        return

    await state.update_data(selected_category=selected_cat)

    t1 = clean_name(selected_match.get("t1", ""))
    t2 = clean_name(selected_match.get("t2", ""))

    await callback.message.edit_text(
        f"📋 تأكيد الحجز:\n\n"
        f"🏆 {t1} 🆚 {t2}\n"
        f"🏟️ {selected_match.get('stadium', '')}\n"
        f"🎫 الدرجة: {selected_cat['name']}\n"
        f"💰 السعر: {selected_cat['price']} ج.م\n"
        f"⚠️ ممكن يتضاف رسوم FanId Renew (150 ج.م)\n\n"
        "هل تأكد الحجز؟",
        reply_markup=confirm_keyboard(match_id, cat_id)
    )
    await state.set_state(BookingStates.confirming_booking)

@router.callback_query(F.data.startswith("soldout_"))
async def cb_soldout(callback: CallbackQuery):
    await callback.answer("❌ الدرجة دي نفذت!", show_alert=True)

@router.callback_query(BookingStates.confirming_booking, F.data.startswith("confirm_"))
async def cb_confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    parts = callback.data.split("_")
    match_id = int(parts[1])
    cat_id = int(parts[2])

    data = await state.get_data()
    selected_match = data.get("selected_match", {})
    selected_cat = data.get("selected_category", {})

    t1 = clean_name(selected_match.get("t1", ""))
    t2 = clean_name(selected_match.get("t2", ""))

    await callback.message.edit_text(
        f"⏳ جاري الحجز...\n\n"
        f"🏆 {t1} 🆚 {t2}\n"
        f"🎫 {selected_cat.get('name', '')}\n\n"
        f"🔄 الخطوات:\n"
        f"1️⃣ إضافة التذكرة للسلة...\n"
        f"2️⃣ تعيين التذكرة...\n"
        f"3️⃣ الدفع عبر فوري..."
    )

    # Create booking record
    booking_id = create_booking(
        callback.from_user.id, match_id, t1, t2,
        selected_cat.get("name", ""), selected_cat.get("price", 0)
    )

    # Execute booking
    session = get_valid_session(callback.from_user.id)
    if not session:
        await callback.message.edit_text(
            "⚠️ الجلسة انتهت! محتاج أسجّل دخول تاني.\n"
            "اضغط /book",
            reply_markup=main_menu_keyboard()
        )
        if booking_id:
            update_booking_status(booking_id, "failed", error_message="Session expired")
        await state.clear()
        return

    client = TazkartiClient(
        access_token=session["access_token"],
        tazkarti_id=get_user(callback.from_user.id)["tazkarti_id"]
    )

    result = await client.book_ticket(match_id, cat_id, quantity=1)
    await client.close()

    if result["success"]:
        fawry_code = result["fawry_code"]
        expires = datetime.now() + timedelta(minutes=FAWRY_CODE_EXPIRY_MINUTES)
        expires_str = expires.strftime("%H:%M")

        if booking_id:
            update_booking_status(
                booking_id, "success",
                fawry_code=fawry_code,
                order_seat_guid=result.get("order_seat_guid", "")
            )
        update_booking_last(callback.from_user.id)

        await callback.message.edit_text(
            f"✅ تم الحجز بنجاح! 🎉\n\n"
            f"🏆 {t1} 🆚 {t2}\n"
            f"🎫 {selected_cat.get('name', '')}\n"
            f"💰 السعر: {selected_cat.get('price', 0)} ج.م\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 كود فوري: {fawry_code}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"⏰ ادفع قبل الساعة {expires_str}\n"
            f"📍 ادفع من أي فرع فوري أو من تطبيق فوري\n\n"
            f"🔗 https://www.atfawry.com",
            reply_markup=main_menu_keyboard()
        )

        # Notify admin
        await bot.send_message(
            ADMIN_TELEGRAM_ID,
            f"🎫 حجز جديد ناجح!\n"
            f"👤 {t1} 🆚 {t2}\n"
            f"🎫 {selected_cat.get('name', '')}\n"
            f"💳 فوري: {fawry_code}\n"
            f"👤 TG ID: {callback.from_user.id}"
        )
    else:
        error = result.get("error", "خطأ غير معروف")
        step = result.get("step", "unknown")
        if booking_id:
            update_booking_status(booking_id, "failed", error_message=f"[{step}] {error}")

        await callback.message.edit_text(
            f"❌ فشل الحجز!\n\n"
            f"📍 الخطوة: {step}\n"
            f"⚠️ السبب: {error[:300]}\n\n"
            f"حاول تاني:",
            reply_markup=main_menu_keyboard()
        )
    await state.clear()

# ==========================================
# Admin Captcha Reply Handler
# ==========================================
@router.message(F.from_user.id == ADMIN_TELEGRAM_ID, F.text.startswith("#C"))
async def admin_captcha_reply(message: Message):
    parsed = handle_admin_captcha_reply(message.text)
    if parsed:
        captcha_id, cells = parsed
        if resolve_captcha(captcha_id, cells):
            await message.reply(f"✅ تم إرسال الحل لـ #{captcha_id}: {cells}")
        else:
            await message.reply(f"⚠️ #{captcha_id} مش موجود أو انتهت المهلة.")
    else:
        await message.reply("⚠️ صيغة غلط. استخدم: #C0001 1 3 5 7")

# ==========================================
# /help Command
# ==========================================
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🎫 بوت حجز تذاكر تذكرتي\n\n"
        "الأوامر:\n"
        "/start - القائمة الرئيسية\n"
        "/book - احجز تذكرة\n"
        "/help - المساعدة\n\n"
        "📋 طريقة الاستخدام:\n"
        "1️⃣ سجّل بيانات تذكرتي (مرة واحدة)\n"
        "2️⃣ اضغط 'احجز تذكرة'\n"
        "3️⃣ اختار الماتش والدرجة\n"
        "4️⃣ البوت يحجز ويجيبلك كود فوري\n"
        "5️⃣ ادفع الكود من فوري خلال ساعة\n"
    )
