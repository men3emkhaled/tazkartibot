"""
Inline keyboards for the booking bot.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def matches_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    """Build inline keyboard with available matches."""
    builder = InlineKeyboardBuilder()
    for match in matches:
        match_id = match.get("matchId")
        t1 = match.get("teamNameAr1") or match.get("teamName1", "?")
        t2 = match.get("teamNameAr2") or match.get("teamName2", "?")
        stadium = match.get("stadiumNameAr") or match.get("stadiumName", "")

        # Clean team names for display
        t1_short = t1[:15]
        t2_short = t2[:15]
        label = f"⚽ {t1_short} vs {t2_short}"

        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"match_{match_id}"
        ))

    builder.row(InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel"))
    return builder.as_markup()


def categories_keyboard(categories: list[dict], match_id: int) -> InlineKeyboardMarkup:
    """Build inline keyboard with available categories."""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        cat_id = cat.get("categoryId")
        name = cat.get("categoryNameAr") or cat.get("categoryName", "?")
        price = cat.get("price", 0)
        sold_out = cat.get("soldOut", False)

        if sold_out:
            label = f"❌ {name} - {price} ج.م (نفذت)"
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data=f"soldout_{cat_id}"
            ))
        else:
            label = f"✅ {name} - {price} ج.م"
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data=f"cat_{match_id}_{cat_id}"
            ))

    builder.row(InlineKeyboardButton(text="⬅️ رجوع", callback_data="back_matches"))
    builder.row(InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel"))
    return builder.as_markup()


def confirm_keyboard(match_id: int, cat_id: int) -> InlineKeyboardMarkup:
    """Confirm booking keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ أكد الحجز",
            callback_data=f"confirm_{match_id}_{cat_id}"
        ),
        InlineKeyboardButton(
            text="❌ إلغاء",
            callback_data="cancel"
        ),
    )
    return builder.as_markup()


def yes_no_keyboard() -> InlineKeyboardMarkup:
    """Simple yes/no keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ أيوه", callback_data="yes"),
        InlineKeyboardButton(text="❌ لا", callback_data="no"),
    )
    return builder.as_markup()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎫 احجز تذكرة", callback_data="book"))
    builder.row(InlineKeyboardButton(text="📋 حجوزاتي", callback_data="my_bookings"))
    builder.row(InlineKeyboardButton(text="👤 بياناتي", callback_data="my_profile"))
    builder.row(InlineKeyboardButton(text="🗑️ حذف بياناتي", callback_data="delete_profile"))
    return builder.as_markup()
