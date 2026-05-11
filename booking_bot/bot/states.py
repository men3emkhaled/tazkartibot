"""
FSM States for the booking conversation flow.
"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """States for first-time user registration."""
    waiting_tazkarti_id = State()
    waiting_password = State()
    confirming = State()


class BookingStates(StatesGroup):
    """States for the booking flow."""
    selecting_match = State()
    selecting_category = State()
    confirming_booking = State()
    waiting_captcha = State()
    processing = State()
