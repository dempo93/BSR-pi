import unittest
from unittest.mock import patch, MagicMock, mock_open
import datetime
import sys
import importlib.util
from pathlib import Path

# Mock luma dependencies before importing the module
luma_mock = MagicMock()
sys.modules["luma"] = luma_mock
sys.modules["luma.core"] = luma_mock
sys.modules["luma.core.interface"] = luma_mock
sys.modules["luma.core.interface.serial"] = luma_mock
sys.modules["luma.led_matrix"] = luma_mock
sys.modules["luma.led_matrix.device"] = luma_mock
sys.modules["luma.core.legacy"] = luma_mock
sys.modules["luma.core.legacy.font"] = luma_mock

# Import the module with hyphen in name
spec = importlib.util.spec_from_file_location(
    "recycling_notification", "recycling-notification.py"
)
recycling_notification = importlib.util.module_from_spec(spec)
sys.modules["recycling_notification"] = recycling_notification
spec.loader.exec_module(recycling_notification)


class TestRecyclingNotification(unittest.TestCase):
    def test_replace_german_letters(self):
        self.assertEqual(
            recycling_notification.replace_german_letters("Müll"),
            "M" + chr(0x81) + "ll",
        )
        self.assertEqual(
            recycling_notification.replace_german_letters("ÄÖÜ"),
            chr(0x8E) + chr(0x99) + chr(0x9A),
        )
        self.assertEqual(
            recycling_notification.replace_german_letters("Hello"), "Hello"
        )

    def test_get_ics_file_path(self):
        path = recycling_notification.get_ics_file_path(2023, 5)
        self.assertTrue(str(path).endswith("recycling_2023_05.ics"))
        self.assertIn("assets", str(path))

    def test_extract_trash_type(self):
        # Sample ICS data
        ics_data = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Combined//
BEGIN:VEVENT
UID:12345
DTSTART;VALUE=DATE:20251121
SUMMARY:Abfuhr: Hausmüll
END:VEVENT
BEGIN:VEVENT
UID:67890
DTSTART;VALUE=DATE:20251122
SUMMARY:Abfuhr: Biogut
END:VEVENT
END:VCALENDAR"""

        # Test for date with event
        target_date = datetime.date(2025, 11, 21)
        result = recycling_notification.extract_trash_type(ics_data, target_date)
        self.assertEqual(result, "Hausmüll")

        # Test for another date
        target_date_2 = datetime.date(2025, 11, 22)
        result_2 = recycling_notification.extract_trash_type(ics_data, target_date_2)
        self.assertEqual(result_2, "Biogut")

        # Test for date without event
        target_date_none = datetime.date(2025, 11, 23)
        result_none = recycling_notification.extract_trash_type(
            ics_data, target_date_none
        )
        self.assertIsNone(result_none)

    def test_extract_trash_type_no_prefix(self):
        ics_data = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;VALUE=DATE:20251121
SUMMARY:Hausmüll
END:VEVENT
END:VCALENDAR"""
        target_date = datetime.date(2025, 11, 21)
        # Should return full summary if no split possible (or logic dictates) - current logic splits by space
        # summary "Hausmüll" -> split(" ") -> ["Hausmüll"] (len 1) -> returns "Hausmüll"
        result = recycling_notification.extract_trash_type(ics_data, target_date)
        self.assertEqual(result, "Hausmüll")

    @patch("requests.get")
    def test_cache_ics_monthly_data_success(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ICS DATA"
        mock_get.return_value = mock_response

        # Mock writing to file, we can assume get_ics_file_path works as tested above
        test_path = Path("test_file.ics")

        with patch("builtins.open", mock_open()) as mocked_file:
            result = recycling_notification.cache_ics_monthly_data(test_path, 2025, 10)

            self.assertEqual(result, "ICS DATA")
            mocked_file.assert_called_with(test_path, "w")
            mocked_file().write.assert_called_with("ICS DATA")

        mock_get.assert_called_once()
        self.assertIn(
            "year=2025",
            mock_get.call_args[0][0]
            if mock_get.call_args
            else mock_get.call_args_list[0][0][0],
        )  # Check URL contains year

    @patch("requests.get")
    def test_cache_ics_monthly_data_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        test_path = Path("test_file.ics")

        with self.assertRaises(Exception) as cm:
            recycling_notification.cache_ics_monthly_data(test_path, 2025, 10)

        self.assertIn("Failed to retrieve ICS data", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
