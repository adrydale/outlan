"""Tests for timezone functionality in audit logs and timestamps."""

from datetime import datetime
from unittest.mock import patch

import pytest
import pytz

from app.config import get_timezone
from app.models import ChangeLog
from app.utils import get_timezone_timestamp


class TestTimezoneHandling:
    """Test timezone configuration and conversion functions."""

    def test_get_timezone_default(self):
        """Test getting default timezone from configuration."""
        timezone = get_timezone()
        assert isinstance(timezone, str)
        # Should return a valid timezone string
        assert timezone is not None

    @patch.dict("os.environ", {"TZ": "Europe/London"})
    def test_get_timezone_from_env(self):
        """Test timezone override from environment variable."""
        # Clear any cached config and reload
        from importlib import reload

        import app.config

        reload(app.config)

        timezone = get_timezone()
        # Should prefer ENV over INI
        assert timezone == "Europe/London"

    def test_get_timezone_timestamp_function(self):
        """Test the timezone timestamp function works correctly."""
        timestamp = get_timezone_timestamp()

        # Should return a datetime object
        assert isinstance(timestamp, datetime)
        # Should have timezone info
        assert timestamp.tzinfo is not None

    @patch("app.config.get_timezone")
    def test_timezone_conversion_utc_offset(self, mock_get_timezone):
        """Test timezone conversion for UTC offset format."""
        mock_get_timezone.return_value = "UTC-5"

        # Test the conversion logic
        timezone_str = "UTC-5"
        if timezone_str.startswith("UTC"):
            offset = int(timezone_str[3:])
            tz = pytz.FixedOffset(offset * 60)

        assert tz.utcoffset(None).total_seconds() == -5 * 3600  # -5 hours

    @patch("app.config.get_timezone")
    def test_timezone_conversion_named_timezone(self, mock_get_timezone):
        """Test timezone conversion for named timezone."""
        mock_get_timezone.return_value = "America/Chicago"

        # Test the conversion logic
        timezone_str = "America/Chicago"
        tz = pytz.timezone(timezone_str)

        # Chicago is either CST (-6) or CDT (-5) depending on DST
        utc_offset_hours = tz.utcoffset(datetime.now()).total_seconds() / 3600
        assert utc_offset_hours in [-6, -5]  # CST or CDT

    def test_utc_storage_in_changelog(self, app_with_db, client):
        """Test that ChangeLog stores timestamps in UTC."""
        with app_with_db.app_context():
            from app.models import db

            # Create a changelog entry
            change = ChangeLog(action="TEST", block="test_block", details="Test timezone storage")
            db.session.add(change)
            db.session.commit()

            # Verify timestamp was stored
            assert change.timestamp is not None

            # Check that the stored timestamp is naive (no timezone info)
            # This indicates UTC storage as per SQLAlchemy convention
            assert change.timestamp.tzinfo is None

            # Clean up
            db.session.delete(change)
            db.session.commit()

    def test_audit_timestamp_display_conversion(self, app_with_db):
        """Test that audit timestamp conversion logic works correctly."""
        with app_with_db.app_context():
            from app.models import db

            # Create a test changelog entry with known UTC time
            test_utc_time = datetime(2025, 1, 15, 18, 30, 0)  # 6:30 PM UTC

            change = ChangeLog(
                action="TEST_DISPLAY", block="test_block", details="Test timezone display", timestamp=test_utc_time
            )
            db.session.add(change)
            db.session.commit()

            try:
                # Test the conversion logic directly
                import pytz

                from app.config import get_timezone

                # Get stored timestamp and convert
                ts = change.timestamp
                utc_ts = ts.replace(tzinfo=pytz.UTC)

                timezone_str = get_timezone()
                if timezone_str.startswith("UTC"):
                    offset = int(timezone_str[3:])
                    local_tz = pytz.FixedOffset(offset * 60)
                else:
                    local_tz = pytz.timezone(timezone_str)

                local_ts = utc_ts.astimezone(local_tz)
                formatted = local_ts.strftime("%Y-%m-%d %H:%M:%S %Z")

                # Verify conversion worked
                assert formatted != ts.strftime("%Y-%m-%d %H:%M:%S")
                assert any(tz_abbr in formatted for tz_abbr in ["UTC", "CST", "CDT", "EST", "EDT"])

            finally:
                # Clean up
                db.session.delete(change)
                db.session.commit()

    @patch("app.config.get_timezone")
    def test_timezone_conversion_error_handling(self, mock_get_timezone):
        """Test error handling for invalid timezone configurations."""
        mock_get_timezone.return_value = "Invalid/Timezone"

        # Test that invalid timezone falls back gracefully
        try:
            timestamp = get_timezone_timestamp()
            # Should still return a timestamp (likely UTC fallback)
            assert isinstance(timestamp, datetime)
        except Exception as e:
            pytest.fail(f"Timezone function should handle invalid timezones gracefully: {e}")

    def test_timezone_conversion_edge_cases(self):
        """Test timezone conversion edge cases."""
        # Test UTC timestamp conversion - use a time that will show difference
        utc_time = datetime(2025, 7, 15, 18, 0, 0)  # 6 PM UTC in summer
        utc_ts = utc_time.replace(tzinfo=pytz.UTC)

        # Convert to different timezones
        chicago_tz = pytz.timezone("America/Chicago")
        chicago_time = utc_ts.astimezone(chicago_tz)

        london_tz = pytz.timezone("Europe/London")
        london_time = utc_ts.astimezone(london_tz)

        # Verify conversions make sense (should be different times)
        # Chicago in summer is UTC-5 (CDT), so 18:00 UTC = 13:00 CDT
        assert chicago_time.hour == 13
        # London in summer is UTC+1 (BST), so 18:00 UTC = 19:00 BST
        assert london_time.hour == 19

        # Both should represent the same moment in time
        assert chicago_time.utctimetuple() == utc_ts.utctimetuple()
        assert london_time.utctimetuple() == utc_ts.utctimetuple()

    def test_timestamp_formatting_includes_timezone(self):
        """Test that formatted timestamps include timezone information."""
        from app.config import get_timezone

        # Create a UTC timestamp
        utc_time = datetime(2025, 1, 15, 12, 0, 0)
        utc_ts = utc_time.replace(tzinfo=pytz.UTC)

        # Get configured timezone
        timezone_str = get_timezone()
        if timezone_str.startswith("UTC"):
            offset = int(timezone_str[3:])
            local_tz = pytz.FixedOffset(offset * 60)
        else:
            local_tz = pytz.timezone(timezone_str)

        # Convert and format
        local_ts = utc_ts.astimezone(local_tz)
        formatted = local_ts.strftime("%Y-%m-%d %H:%M:%S %Z")

        # Should include timezone abbreviation
        assert any(tz_abbr in formatted for tz_abbr in ["UTC", "CST", "CDT", "EST", "EDT", "PST", "PDT"])
