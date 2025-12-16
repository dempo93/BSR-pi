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

load_dotenv(dotenv_path)
encoded_address = os.getenv("ENCODED_ADDRESS")
calendar_sync_interval_days = int(os.getenv("CALENDAR_SYNC_INTERVAL_DAYS", "30"))
display_on_minutes = int(os.getenv("DISPLAY_ON_MINUTES", "300"))
display_interval_seconds = int(os.getenv("DISPLAY_INTERVAL_SECONDS", "10"))
calendar_sync_metadata_path = assets_path / "calendar_sync"
dryrun = os.getenv("DRY_RUN_MODE", "False").lower() == "true"


logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)

assets_path.mkdir(parents=False, exist_ok=True)
calendar_sync_metadata_path.touch(exist_ok=True)


def get_ics_file_path(year: int, month: int) -> Path:
    return assets_path / f"recycling_{year}_{month:02d}.ics"


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
        file = open(calendar_sync_metadata_path, "r+")
    except FileNotFoundError:
        file = open(calendar_sync_metadata_path, "w+")
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
            if (
                last_sync_date
                and (now.date() - last_sync_date).days < calendar_sync_interval_days
            ):
                logger.info(
                    f"ICS data is up to date, no need to cache, last sync: {last_sync_date}"
                )
                return
            logger.info(
                f"Caching ICS data for the next 12 months, last sync: {last_sync_date}"
            )
            for index in range(0, 12):
                current_month = now.month + index
                current_year = now.year
                if current_month > 12:
                    current_month = current_month - 12
                    current_year = current_year + 1
                cache_ics_monthly_data(
                    get_ics_file_path(current_year, current_month),
                    current_year,
                    current_month,
                )
            f.seek(0)
            f.write(now.date().isoformat())
            f.truncate()
    except Exception as e:
        logger.error(f"Error caching ICS data: {e}")
        return


def extract_trash_type(ics_data: str, target_date: datetime.date) -> str | None:
    cal = icalendar.Calendar.from_ical(ics_data)
    for event in cal.walk("vevent"):
        if event.get("dtstart").dt == target_date:
            summary = event.get("summary")
            summary_parts = summary.split(" ")
            if len(summary_parts) >= 2:
                return summary_parts[1]
            return summary
    return None


def read_ics_data_for_next_day(now: datetime.datetime) -> str | None:
    tomorrow = now.date() + datetime.timedelta(days=1)
    ics_path = get_ics_file_path(tomorrow.year, tomorrow.month)
    try:
        with open(ics_path, "r") as f:
            ics_data = f.read()
            return extract_trash_type(ics_data, tomorrow)
    except FileNotFoundError:
        logger.error(f"ICS file not found for {tomorrow.year}-{tomorrow.month:02d}")
    return None


def replace_german_letters(text: str) -> str:
    cp437_map = {
        "Ä": chr(0x8E),
        "Ö": chr(0x99),
        "Ü": chr(0x9A),
        "ä": chr(0x84),
        "ö": chr(0x94),
        "ü": chr(0x81),
        "ß": chr(0xE1),
    }
    return "".join(cp437_map.get(ch, ch) for ch in text)


def main():
    try:
        serial = spi(port=0, device=0, gpio=noop())
        device = max7219(serial)
    except Exception as e:
        logger.error(f"Could not initialize device: {e}")
        if not dryrun:
            raise e
        device = None

    now = datetime.datetime.now()
    end_time = now + datetime.timedelta(minutes=display_on_minutes)

    if not dryrun:
        cache_ics_yearly_data(now)

    trash_type = read_ics_data_for_next_day(now)
    log_msg = f"Tomorrow's trash type: {trash_type}, today's date: {now.date()}"
    logger.info(log_msg)

    if dryrun:
        logger.info("Dry run mode enabled")
        if device:
            show_message(
                device,
                log_msg,
                fill="white",
                font=proportional(CP437_FONT),
                scroll_delay=0.05,
            )
        exit(0)

    if trash_type:
        trash_type_binary = replace_german_letters(trash_type)

        while now < end_time:
            show_message(
                device,
                trash_type_binary,
                fill="white",
                font=proportional(CP437_FONT),
                scroll_delay=0.05,
            )
            time.sleep(display_interval_seconds)
            now = datetime.datetime.now()


if __name__ == "__main__":
    main()
