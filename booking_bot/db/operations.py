"""
Database operations for the Booking Bot.
Handles user credentials, sessions, and booking records.
"""
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from booking_bot.config import DATABASE_URL
from booking_bot.utils.crypto import encrypt_text, decrypt_text


def get_db():
    """Get a database connection."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        return None


def init_booking_db():
    """Initialize booking bot database tables."""
    conn = get_db()
    if not conn:
        return False
    try:
        c = conn.cursor()

        # Users table - stores encrypted credentials
        c.execute('''
            CREATE TABLE IF NOT EXISTS booking_users (
                telegram_id    BIGINT PRIMARY KEY,
                tazkarti_id    TEXT NOT NULL,
                encrypted_pass TEXT NOT NULL,
                full_name      TEXT DEFAULT '',
                mobile_number  TEXT DEFAULT '',
                created_at     TIMESTAMP DEFAULT NOW(),
                last_booking   TIMESTAMP,
                is_active      BOOLEAN DEFAULT TRUE
            )
        ''')

        # Active sessions - cached login tokens
        c.execute('''
            CREATE TABLE IF NOT EXISTS active_sessions (
                telegram_id    BIGINT PRIMARY KEY REFERENCES booking_users(telegram_id) ON DELETE CASCADE,
                access_token   TEXT NOT NULL,
                refresh_token  TEXT DEFAULT '',
                profile_json   TEXT DEFAULT '{}',
                expires_at     TIMESTAMP NOT NULL,
                created_at     TIMESTAMP DEFAULT NOW()
            )
        ''')

        # Bookings - track all booking attempts and results
        c.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id             SERIAL PRIMARY KEY,
                telegram_id    BIGINT REFERENCES booking_users(telegram_id) ON DELETE CASCADE,
                match_id       BIGINT NOT NULL,
                team1          TEXT DEFAULT '',
                team2          TEXT DEFAULT '',
                category_name  TEXT DEFAULT '',
                price          NUMERIC DEFAULT 0,
                quantity       INTEGER DEFAULT 1,
                order_seat_guid TEXT DEFAULT '',
                fawry_code     TEXT DEFAULT '',
                fawry_expires  TIMESTAMP,
                status         TEXT DEFAULT 'pending',
                error_message  TEXT DEFAULT '',
                created_at     TIMESTAMP DEFAULT NOW(),
                completed_at   TIMESTAMP
            )
        ''')

        conn.commit()
        c.close()
        conn.close()
        print("✅ Booking DB tables initialized.")
        return True
    except Exception as e:
        print(f"❌ DB Init Error: {e}")
        conn.close()
        return False


# ==========================================
# 👤 User Operations
# ==========================================
def save_user(telegram_id: int, tazkarti_id: str, password: str) -> bool:
    """Save or update user credentials (password is encrypted)."""
    conn = get_db()
    if not conn:
        return False
    try:
        c = conn.cursor()
        encrypted_pass = encrypt_text(password)
        c.execute('''
            INSERT INTO booking_users (telegram_id, tazkarti_id, encrypted_pass)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
                tazkarti_id = EXCLUDED.tazkarti_id,
                encrypted_pass = EXCLUDED.encrypted_pass,
                is_active = TRUE
        ''', (telegram_id, tazkarti_id, encrypted_pass))
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Save User Error: {e}")
        conn.close()
        return False


def get_user(telegram_id: int) -> dict | None:
    """Get user credentials (password is decrypted)."""
    conn = get_db()
    if not conn:
        return None
    try:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute(
            "SELECT * FROM booking_users WHERE telegram_id = %s AND is_active = TRUE",
            (telegram_id,)
        )
        row = c.fetchone()
        c.close()
        conn.close()
        if row:
            return {
                "telegram_id": row["telegram_id"],
                "tazkarti_id": row["tazkarti_id"],
                "password": decrypt_text(row["encrypted_pass"]),
                "full_name": row["full_name"],
                "mobile_number": row["mobile_number"],
            }
        return None
    except Exception as e:
        print(f"❌ Get User Error: {e}")
        conn.close()
        return None


def update_user_profile(telegram_id: int, full_name: str, mobile_number: str):
    """Update user profile info from login response."""
    conn = get_db()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute('''
            UPDATE booking_users SET full_name = %s, mobile_number = %s
            WHERE telegram_id = %s
        ''', (full_name, mobile_number, telegram_id))
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print(f"❌ Update Profile Error: {e}")
        conn.close()


def delete_user(telegram_id: int) -> bool:
    """Deactivate a user (soft delete)."""
    conn = get_db()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE booking_users SET is_active = FALSE WHERE telegram_id = %s",
            (telegram_id,)
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Delete User Error: {e}")
        conn.close()
        return False


# ==========================================
# 🔑 Session Operations
# ==========================================
def save_session(telegram_id: int, access_token: str, refresh_token: str,
                 profile_json: str, expires_in: int = 3600):
    """Save login session for a user."""
    conn = get_db()
    if not conn:
        return
    try:
        c = conn.cursor()
        expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 min buffer
        c.execute('''
            INSERT INTO active_sessions (telegram_id, access_token, refresh_token, profile_json, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                profile_json = EXCLUDED.profile_json,
                expires_at = EXCLUDED.expires_at,
                created_at = NOW()
        ''', (telegram_id, access_token, refresh_token, profile_json, expires_at))
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print(f"❌ Save Session Error: {e}")
        conn.close()


def get_valid_session(telegram_id: int) -> dict | None:
    """Get a valid (non-expired) session for a user."""
    conn = get_db()
    if not conn:
        return None
    try:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute('''
            SELECT * FROM active_sessions
            WHERE telegram_id = %s AND expires_at > NOW()
        ''', (telegram_id,))
        row = c.fetchone()
        c.close()
        conn.close()
        if row:
            return {
                "access_token": row["access_token"],
                "refresh_token": row["refresh_token"],
                "profile_json": row["profile_json"],
                "expires_at": row["expires_at"],
            }
        return None
    except Exception as e:
        print(f"❌ Get Session Error: {e}")
        conn.close()
        return None


def delete_session(telegram_id: int):
    """Delete a user's session."""
    conn = get_db()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute("DELETE FROM active_sessions WHERE telegram_id = %s", (telegram_id,))
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print(f"❌ Delete Session Error: {e}")
        conn.close()


# ==========================================
# 🎫 Booking Operations
# ==========================================
def create_booking(telegram_id: int, match_id: int, team1: str, team2: str,
                   category_name: str, price: float) -> int | None:
    """Create a new booking record. Returns booking ID."""
    conn = get_db()
    if not conn:
        return None
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO bookings (telegram_id, match_id, team1, team2, category_name, price)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (telegram_id, match_id, team1, team2, category_name, price))
        booking_id = c.fetchone()[0]
        conn.commit()
        c.close()
        conn.close()
        return booking_id
    except Exception as e:
        print(f"❌ Create Booking Error: {e}")
        conn.close()
        return None


def update_booking_status(booking_id: int, status: str, fawry_code: str = "",
                          order_seat_guid: str = "", error_message: str = ""):
    """Update booking status and result."""
    conn = get_db()
    if not conn:
        return
    try:
        c = conn.cursor()
        updates = ["status = %s"]
        values = [status]

        if fawry_code:
            updates.append("fawry_code = %s")
            values.append(fawry_code)
            updates.append("fawry_expires = %s")
            values.append(datetime.now() + timedelta(minutes=60))

        if order_seat_guid:
            updates.append("order_seat_guid = %s")
            values.append(order_seat_guid)

        if error_message:
            updates.append("error_message = %s")
            values.append(error_message)

        if status in ("success", "failed"):
            updates.append("completed_at = NOW()")

        values.append(booking_id)

        c.execute(
            f"UPDATE bookings SET {', '.join(updates)} WHERE id = %s",
            values
        )
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print(f"❌ Update Booking Error: {e}")
        conn.close()


def update_booking_last(telegram_id: int):
    """Update user's last_booking timestamp."""
    conn = get_db()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE booking_users SET last_booking = NOW() WHERE telegram_id = %s",
            (telegram_id,)
        )
        conn.commit()
        c.close()
        conn.close()
    except Exception as e:
        print(f"❌ Update Last Booking Error: {e}")
        conn.close()
