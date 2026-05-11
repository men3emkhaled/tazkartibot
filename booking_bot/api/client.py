"""
Tazkarti API Client.
Handles all HTTP communication with the Tazkarti website.
"""
import time
import json
import httpx
from booking_bot.config import (
    TAZKARTI_BASE_URL, TAZKARTI_LOGIN_URL, TAZKARTI_MATCHES_URL,
    TAZKARTI_SEATS_URL, REQ_HEADERS, REQUEST_TIMEOUT,
    BOOKING_ADD_SEATS, BOOKING_ASSIGN_SEATS, BOOKING_GET_ORDERS,
    BOOKING_GOTO_PAY, BOOKING_DELETE_CART, BOOKING_CHECK_PAYMENT_PROVIDERS,
    BOOKING_GET_NOTIFICATION_CART, BOOKING_TICKET_DETAILS,
)


class TazkartiClient:
    """
    Async HTTP client for interacting with the Tazkarti API.
    Each instance represents a single user's session.
    """

    def __init__(self, access_token: str = "", tazkarti_id: str = ""):
        self.access_token = access_token
        self.tazkarti_id = tazkarti_id
        self.profile = {}
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers=REQ_HEADERS.copy(),
            follow_redirects=True,
            verify=True,
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _auth_headers(self) -> dict:
        """Get headers with Bearer token."""
        headers = REQ_HEADERS.copy()
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _booking_url(self, endpoint: str) -> str:
        """
        Build the booking API URL.
        The website uses dynamic load-balanced endpoints based on fan ID modulus.
        We use the base URL as the default.
        """
        return f"{TAZKARTI_BASE_URL}/{endpoint}"

    # ==========================================
    # 🔐 Authentication
    # ==========================================
    async def login(self, username: str, password: str, recaptcha_response: str) -> dict:
        """
        Login to Tazkarti.
        Returns the full login response including token and profile.
        """
        payload = {
            "Username": username,
            "Password": password,
            "recaptchaResponse": recaptcha_response,
        }
        try:
            resp = await self._client.post(
                TAZKARTI_LOGIN_URL,
                json=payload,
                headers=REQ_HEADERS,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get("access_token", "")
                self.profile = data.get("profileInfo", {})
                self.tazkarti_id = username
                return {
                    "success": True,
                    "access_token": data.get("access_token", ""),
                    "refresh_token": data.get("refresh_token", ""),
                    "expires_in": data.get("expires_in", 3600),
                    "profile": self.profile,
                    "full_name": self._get_full_name(),
                    "mobile_number": self.profile.get("mobileNumber", ""),
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {resp.status_code}: {resp.text[:200]}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_full_name(self) -> str:
        """Extract full name from profile."""
        first = self.profile.get("firstName") or self.profile.get("firstNameEn") or ""
        middle = self.profile.get("middleName") or ""
        last = self.profile.get("lastNameAr") or self.profile.get("lastNameEn") or ""
        return f"{first} {middle} {last}".strip()

    # ==========================================
    # 🏟️ Matches
    # ==========================================
    async def get_matches(self) -> list[dict]:
        """Get all available matches."""
        try:
            ts = int(time.time() * 1000)
            resp = await self._client.get(
                f"{TAZKARTI_MATCHES_URL}?_={ts}",
                headers=self._auth_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"❌ Get Matches Error: {e}")
            return []

    async def get_available_matches(self) -> list[dict]:
        """Get only bookable matches (status = 1 = OPEN)."""
        matches = await self.get_matches()
        return [m for m in matches if m.get("matchStatus") == 1]

    # ==========================================
    # 🎫 Categories & Seats
    # ==========================================
    async def get_categories(self, match_id: int) -> list[dict]:
        """Get available ticket categories for a match."""
        try:
            ts = int(time.time() * 1000)
            url = TAZKARTI_SEATS_URL.format(match_id=match_id)
            resp = await self._client.get(
                f"{url}?_={ts}",
                headers=self._auth_headers(),
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            return []
        except Exception as e:
            print(f"❌ Get Categories Error: {e}")
            return []

    async def get_available_categories(self, match_id: int) -> list[dict]:
        """Get non-sold-out categories for a match."""
        categories = await self.get_categories(match_id)
        return [c for c in categories if not c.get("soldOut", False)]

    # ==========================================
    # 🛒 Booking Flow
    # ==========================================
    async def add_seats(self, match_id: int, category_id: int,
                        quantity: int = 1) -> dict:
        """
        Step 1: Add seats to cart.
        This is equivalent to clicking 'Book Ticket' and selecting a category.
        """
        payload = {
            "matchId": match_id,
            "categoryId": category_id,
            "quantity": quantity,
        }
        try:
            resp = await self._client.post(
                self._booking_url(BOOKING_ADD_SEATS),
                json=payload,
                headers=self._auth_headers(),
            )
            data = resp.json() if resp.status_code == 200 else {}
            return {
                "success": resp.status_code == 200,
                "data": data,
                "status_code": resp.status_code,
                "error": resp.text[:300] if resp.status_code != 200 else "",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def assign_seats(self, order_seat_guid: str = "") -> dict:
        """
        Step 2: Assign seats to fan (always 'Myself').
        """
        payload = {
            "assignToMyself": True,
        }
        if order_seat_guid:
            payload["orderSeatGuid"] = order_seat_guid

        try:
            resp = await self._client.post(
                self._booking_url(BOOKING_ASSIGN_SEATS),
                json=payload,
                headers=self._auth_headers(),
            )
            data = resp.json() if resp.status_code == 200 else {}
            return {
                "success": resp.status_code == 200,
                "data": data,
                "status_code": resp.status_code,
                "error": resp.text[:300] if resp.status_code != 200 else "",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_orders(self) -> dict:
        """Get current order details (after adding seats)."""
        try:
            resp = await self._client.get(
                self._booking_url(BOOKING_GET_ORDERS),
                headers=self._auth_headers(),
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.text[:300]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def check_payment_providers(self, match_id: int) -> dict:
        """Check available payment providers for a match."""
        try:
            resp = await self._client.get(
                self._booking_url(f"{BOOKING_CHECK_PAYMENT_PROVIDERS}?matchId={match_id}"),
                headers=self._auth_headers(),
            )
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": resp.text[:300]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def goto_pay_fawry(self, order_seat_guid: str) -> dict:
        """
        Step 3: Proceed to Fawry payment.
        Returns the Fawry order number (the code the user needs to pay).
        """
        try:
            resp = await self._client.get(
                self._booking_url(f"{BOOKING_GOTO_PAY}?OrderSeatGuid={order_seat_guid}"),
                headers=self._auth_headers(),
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "data": data,
                    "fawry_code": self._extract_fawry_code(data),
                }
            return {
                "success": False,
                "error": resp.text[:300],
                "status_code": resp.status_code,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_fawry_code(self, data: dict) -> str:
        """Extract Fawry payment code from the payment response."""
        # The response structure may vary, try common fields
        if isinstance(data, dict):
            for key in ["referenceNumber", "fawryCode", "orderNumber",
                        "paymentReferenceNumber", "fawryReferenceNumber"]:
                if key in data:
                    return str(data[key])
            # Check nested data
            if "data" in data:
                return self._extract_fawry_code(data["data"])
        return ""

    # ==========================================
    # 🗑️ Cart Management
    # ==========================================
    async def clear_cart(self) -> bool:
        """Clear any existing cart items."""
        try:
            resp = await self._client.delete(
                self._booking_url(f"{BOOKING_DELETE_CART}?IsAssign=false"),
                headers=self._auth_headers(),
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def get_notification_cart(self, uguid: str) -> dict:
        """Get notification cart status."""
        try:
            resp = await self._client.get(
                self._booking_url(f"{BOOKING_GET_NOTIFICATION_CART}?uguid={uguid}"),
                headers=self._auth_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception:
            return {}

    # ==========================================
    # 📋 Full Booking Flow
    # ==========================================
    async def book_ticket(self, match_id: int, category_id: int,
                          quantity: int = 1) -> dict:
        """
        Execute the full booking flow:
        1. Clear any existing cart
        2. Add seats
        3. Assign seats (Myself)
        4. Proceed to Fawry payment
        5. Return Fawry code

        Returns dict with success status and fawry_code.
        """
        result = {
            "success": False,
            "step": "",
            "fawry_code": "",
            "error": "",
            "order_seat_guid": "",
        }

        # Step 0: Clear old cart
        result["step"] = "clear_cart"
        await self.clear_cart()

        # Step 1: Add seats
        result["step"] = "add_seats"
        add_result = await self.add_seats(match_id, category_id, quantity)
        if not add_result["success"]:
            result["error"] = f"فشل إضافة التذاكر: {add_result.get('error', 'Unknown')}"
            return result

        # Extract order_seat_guid from the response
        order_data = add_result.get("data", {})
        order_seat_guid = ""
        if isinstance(order_data, dict):
            order_seat_guid = (
                order_data.get("orderSeatGuid") or
                order_data.get("data", {}).get("orderSeatGuid", "") if isinstance(order_data.get("data"), dict) else ""
            )

        # If no guid from addSeats, try getting it from orders
        if not order_seat_guid:
            orders_result = await self.get_orders()
            if orders_result["success"]:
                orders_data = orders_result["data"]
                if isinstance(orders_data, dict):
                    order_seat_guid = orders_data.get("orderSeatGuid", "")
                elif isinstance(orders_data, list) and orders_data:
                    order_seat_guid = orders_data[0].get("orderSeatGuid", "")

        result["order_seat_guid"] = order_seat_guid

        # Step 2: Assign seats (Myself)
        result["step"] = "assign_seats"
        assign_result = await self.assign_seats(order_seat_guid)
        if not assign_result["success"]:
            result["error"] = f"فشل تعيين التذاكر: {assign_result.get('error', 'Unknown')}"
            return result

        # Step 3: Pay with Fawry
        result["step"] = "goto_pay"
        if not order_seat_guid:
            result["error"] = "مفيش OrderSeatGuid - مشكلة في الحجز"
            return result

        pay_result = await self.goto_pay_fawry(order_seat_guid)
        if not pay_result["success"]:
            result["error"] = f"فشل الدفع: {pay_result.get('error', 'Unknown')}"
            return result

        fawry_code = pay_result.get("fawry_code", "")
        if not fawry_code:
            result["error"] = "تم الحجز بس مش لاقي كود فوري في الرد"
            result["step"] = "extract_fawry"
            return result

        result["success"] = True
        result["fawry_code"] = fawry_code
        result["step"] = "done"
        return result
