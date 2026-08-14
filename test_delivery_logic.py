import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "-100111")
os.environ.setdefault("PUBLIC_CHAT_ID", "@public_channel")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import tazkarti_bot as app


class FakeCursor:
    def __init__(self):
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((statement, params))

    def fetchone(self):
        return (0,)

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def close(self):
        pass


class FailingCommitConnection(FakeConnection):
    def commit(self):
        raise RuntimeError("commit failed")


class FakeBot:
    def __init__(self, resolved_ids):
        self.resolved_ids = resolved_ids
        self.sent_messages = []

    def get_chat(self, chat_ref):
        return SimpleNamespace(id=self.resolved_ids[str(chat_ref)])

    def send_message(self, chat_ref, message):
        self.sent_messages.append((chat_ref, message))


class DeliveryLogicTests(unittest.TestCase):
    def setUp(self):
        app._recently_sent.clear()
        app._resolved_chat_ids.clear()

    def test_same_channel_alias_skips_immediate_and_schedules_public(self):
        fake_bot = FakeBot({"-100111": -100999, "@public_channel": -100999})
        fake_connection = FakeConnection()

        with patch("builtins.print"), patch.object(app, "bot", fake_bot), patch.object(app, "get_db", return_value=fake_connection):
            result = app.send_notification("same-channel-message")

        self.assertTrue(result)
        self.assertEqual(fake_bot.sent_messages, [])
        self.assertTrue(fake_connection.committed)
        self.assertTrue(any("INSERT INTO delayed_notifications" in sql for sql, _ in fake_connection.cursor_instance.statements))

    def test_different_channels_send_private_now_and_schedule_public(self):
        fake_bot = FakeBot({"-100111": -100111, "@public_channel": -100222})
        fake_connection = FakeConnection()

        with patch("builtins.print"), patch.object(app, "bot", fake_bot), patch.object(app, "get_db", return_value=fake_connection):
            result = app.send_notification("different-channel-message")

        self.assertTrue(result)
        self.assertEqual(fake_bot.sent_messages, [(app.TELEGRAM_CHAT_ID, "different-channel-message")])
        self.assertTrue(fake_connection.committed)

    def test_fallback_timer_runs_only_when_database_scheduling_fails(self):
        fake_bot = FakeBot({"-100111": -100111, "@public_channel": -100222})
        fake_connection = FailingCommitConnection()

        with patch("builtins.print"), patch.object(app, "bot", fake_bot), patch.object(app, "get_db", return_value=fake_connection), patch.object(app.threading, "Timer") as timer:
            result = app.send_notification("database-failure-message")

        self.assertTrue(result)
        timer.assert_called_once_with(600.0, app.send_delayed_notification_fallback, args=["database-failure-message"])

    def test_logging_failure_after_commit_does_not_create_second_timer(self):
        fake_bot = FakeBot({"-100111": -100111, "@public_channel": -100222})
        fake_connection = FakeConnection()

        def print_with_scheduling_failure(*args, **kwargs):
            if args and "تم جدولة الإشعار" in str(args[0]):
                raise OSError("console unavailable")

        with patch("builtins.print", side_effect=print_with_scheduling_failure), patch.object(app, "bot", fake_bot), patch.object(app, "get_db", return_value=fake_connection), patch.object(app.threading, "Timer") as timer:
            result = app.send_notification("logging-failure-message")

        self.assertTrue(result)
        self.assertTrue(fake_connection.committed)
        timer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
