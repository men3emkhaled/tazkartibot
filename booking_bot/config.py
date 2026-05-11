"""
Configuration for the Tazkarti Booking Bot.
Loads settings from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Telegram Bot
# ==========================================
BOOKING_BOT_TOKEN = os.getenv("BOOKING_BOT_TOKEN", "")
_admin_id = os.getenv("ADMIN_TELEGRAM_ID", "0")
ADMIN_TELEGRAM_ID = int(_admin_id) if _admin_id.isdigit() else 0

# ==========================================
# Database
# ==========================================
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ==========================================
# Encryption
# ==========================================
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# ==========================================
# Tazkarti API
# ==========================================
TAZKARTI_BASE_URL = "https://www.tazkarti.com"
TAZKARTI_LOGIN_URL = f"{TAZKARTI_BASE_URL}/home/Login"
TAZKARTI_MATCHES_URL = f"{TAZKARTI_BASE_URL}/data/matches-list-json.json"
TAZKARTI_EVENTS_URL = f"{TAZKARTI_BASE_URL}/data/events-list-json.json"
TAZKARTI_QUEUES_URL = f"{TAZKARTI_BASE_URL}/data/fanQueuesMatch-list-json.json"
TAZKARTI_SEATS_URL = f"{TAZKARTI_BASE_URL}/data/TicketPrice-AvailableSeats-{{match_id}}.json"

# Booking API - Dynamic endpoints (load balanced by fan ID modulus)
# These are relative to the base URL or dynamic booking URL
BOOKING_ADD_SEATS = "BookingTickets/addSeats"
BOOKING_ASSIGN_SEATS = "BookingTickets/assignSeats"
BOOKING_GET_ORDERS = "BookingTickets/getOrdersSeats"
BOOKING_GOTO_PAY = "BookingTickets/gotoPay"
BOOKING_GET_CART_TYPE = "BookingTickets/getCartType"
BOOKING_DELETE_CART = "BookingTickets/deleteCart"
BOOKING_DELETE_SEATS = "BookingTickets/deleteSeats"
BOOKING_CHECK_PAYMENT_PROVIDERS = "BookingTickets/check-paymentproviders"
BOOKING_GET_PAYMENT_PROVIDERS = "BookingTickets/get-PaymentProviders"
BOOKING_COUNT_SEATS = "BookingTickets/countAvaliableSeats"
BOOKING_GET_TICKET_PRICE = "BookingTickets/getTicketPrice"
BOOKING_GET_NOTIFICATION_CART = "BookingTickets/getNotificationCart"
BOOKING_TICKET_DETAILS = "BookingTickets/GetTicketDetailsbyMatchId"
BOOKING_PENDING_TICKETS = "BookingTickets/PendingTickets"

# reCAPTCHA
RECAPTCHA_SITEKEY = "6LeypS8dAAAAAGWYer3FgEpGtmlBWBhsnGF0tCGZ"

# ==========================================
# Bot Settings
# ==========================================
CAPTCHA_TIMEOUT_SECONDS = 120  # 2 minutes to solve captcha
FAWRY_CODE_EXPIRY_MINUTES = 60  # Fawry code expires in 1 hour
SESSION_EXPIRY_SECONDS = 3500  # Refresh before 1-hour expiry

# HTTP Client Settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Content-Type": "application/json",
    "Origin": TAZKARTI_BASE_URL,
    "Referer": f"{TAZKARTI_BASE_URL}/",
}
