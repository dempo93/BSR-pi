from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from luma.core.legacy.font import proportional, CP437_FONT
from luma.core.legacy import show_message
import icalendar
import requests
from pathlib import Path
import datetime
import time
import logging
from dotenv import load_dotenv
import os
from io import TextIOWrapper


url = "https://umnewforms.bsr.de/p/de.bsr.adressen.app/abfuhr/kalender/ics/{address}?year={year}&month={month}"
root_folder_path = Path(__file__).parent.resolve()

assets_path = root_folder_path / "assets"
dotenv_path = root_folder_path / ".env"
log_path = root_folder_path / "recycling-notification.log"
notification_start_hour = 17
notification_end_hour = 23

load_dotenv(dotenv_path)
encoded_address = os.getenv("ENCODED_ADDRESS")
calendar_sync_interval_days = int(os.getenv("CALENDAR_SYNC_INTERVAL_DAYS", "30"))
display_on_minutes = int(os.getenv("DISPLAY_ON_MINUTES", "300"))
calendar_sync_metadata_path = assets_path / "calendar_sync"


logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler(log_path))
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

assets_path.mkdir(parents=False, exist_ok=True)
calendar_sync_metadata_path.touch(exist_ok=True)


def cache_ics_monthly_data(path: Path, year: int, month: int) -> str:
    response = requests.get(url.format(address=encoded_address, year=year, month=month))
    if response.status_code == 200:
        with open(path, "w") as f:
            f.write(response.text)
        return response.text
    else:
        raise Exception("Failed to retrieve ICS data.")


def get_or_create_calendar_sync_file() -> TextIOWrapper:
    try:
        file = open(calendar_sync_metadata_path, 'r+')
    except FileNotFoundError:
        file = open(calendar_sync_metadata_path, 'w+')
    return file

def parse_date_from_metadata(data: str) -> datetime.date | None:
    try:
        if not data:
            return None
        return datetime.date.fromisoformat(data.strip())
    except (TypeError, ValueError) as e:
        logger.warning(f"Could not parse last sync metadata: {e}")
        return None

def cache_ics_yearly_data(now: datetime.datetime):
    try:
        with get_or_create_calendar_sync_file() as f:
            last_sync_date = parse_date_from_metadata(f.read())
            if last_sync_date and (now.date() - last_sync_date).days < calendar_sync_interval_days:
                logger.info(f"ICS data is up to date, no need to cache, last sync: {last_sync_date}")
                return
            logger.info(f"Caching ICS data for the next 12 months, last sync: {last_sync_date}")
            for index in range(0, 12):
                current_month = now.month + index
                current_year = now.year
                if current_month > 12:
                    current_month = current_month - 12
                    current_year = current_year + 1
                cache_ics_monthly_data(
                    assets_path / f"recycling_{current_year}_{current_month:02d}.ics",
                    current_year,
                    current_month,
                )
            f.seek(0)
            f.write(now.date().isoformat())
            f.truncate()
    except Exception as e:
        logger.error(f"Error caching ICS data: {e}")
        return


def read_ics_data_for_next_day(now: datetime.datetime) -> str | None:
    tomorrow = now.date() + datetime.timedelta(days=1)
    ics_path = assets_path / f"recycling_{tomorrow.year}_{tomorrow.month:02d}.ics"
    with open(ics_path, "r") as f:
        ics_data = f.read()
        cal = icalendar.Calendar.from_ical(ics_data)
        for event in cal.walk("vevent"):
            if event.get("dtstart") == tomorrow:
                summary = event.get("summary")
                summary_parts = summary.split(" ")
                if len(summary_parts) >= 2:
                    return summary_parts[1]
                return summary
    return None


serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial)
now = datetime.datetime.now()
cache_ics_yearly_data(now)


while True:
    now = datetime.datetime.now()
    if now.hour > notification_start_hour and now.hour < notification_end_hour:
        trash_type = read_ics_data_for_next_day(now)
        logger.info(f"Tomorrow's trash type: {trash_type}, today's date: {now.date()}")
        if trash_type:
            while (
                now.hour > notification_start_hour and now.hour < notification_end_hour
            ):
                show_message(
                    device,
                    trash_type,
                    fill="white",
                    font=proportional(CP437_FONT),
                    scroll_delay=0.05,
                )
                time.sleep(10)
                now = datetime.datetime.now()
    sleep_until = datetime.datetime.combine(
        now.date() + datetime.timedelta(days=1),
        datetime.time(hour=notification_start_hour),
    )
    logger.info(f"Sleeping until {sleep_until} from {now}")
    sleep_for = (sleep_until - now).total_seconds()
    time.sleep(sleep_for)
