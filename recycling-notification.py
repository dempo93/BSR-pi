from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from luma.core.legacy.font import proportional, CP437_FONT
from luma.core.legacy import show_message
import icalendar
import requests
from pathlib import Path
import datetime
import time
from logging import getLogger
from dotenv import load_dotenv
import os



# logger = getLogger(__name__)


url = "https://umnewforms.bsr.de/p/de.bsr.adressen.app/abfuhr/kalender/ics/{address}?year={year}&month={month}"
root_folder_path = Path(__file__).parent.resolve()

assets_path = root_folder_path / "assets"
dotenv_path = root_folder_path / ".env"
notification_start_hour = 17
notification_end_hour = 23

load_dotenv(dotenv_path)
encoded_address = os.getenv("ENCODED_ADDRESS")


def cache_ics_monthly_data(path: Path, year: int, month: int) -> str:
    response = requests.get(url.format(address=encoded_address, year=year, month=month))
    if response.status_code == 200:
        with open(path, "w") as f:
            f.write(response.text)
        return response.text
    else:
        raise Exception("Failed to retrieve ICS data.")
    
def cache_ics_yearly_data(now: datetime.datetime):
    try:
        assets_path.mkdir(parents=False, exist_ok=True)
        for index in range(0, 12):
            current_month = now.month + index
            current_year = now.year
            if current_month > 12:
                current_month = current_month - 12
                current_year = current_year + 1
            cache_ics_monthly_data(assets_path/f"recycling_{current_year}_{current_month:02d}.ics", current_year, current_month)
    except Exception as e:
        print(f"Error caching ICS data: {e}")
        return

def read_ics_data_for_next_day(now: datetime.datetime) -> str | None:
    tomorrow = now.date() + datetime.timedelta(days=1)
    ics_path = assets_path / f"recycling_{tomorrow.year}_{tomorrow.month:02d}.ics"
    with open(ics_path, "r") as f:
        ics_data = f.read()
        cal = icalendar.Calendar.from_ical(ics_data)
        for event in cal.walk("vevent"):
            if event.get("dtstart") == tomorrow:
                return event.get("summary").split(" ")[1]
    return None

serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial)
now = datetime.datetime.now()
cache_ics_yearly_data(now)


while True:
    now = datetime.datetime.now()
    if now.hour > notification_start_hour and now.hour < notification_end_hour:
        trash_type = read_ics_data_for_next_day(now)
        print(f"Tomorrow's trash type: {trash_type}, today's date: {now.date()}")
        if trash_type:
            while now.hour > notification_start_hour and now.hour < notification_end_hour:
                show_message(device, trash_type, fill='white', font=proportional(CP437_FONT), scroll_delay=0.05)
                time.sleep(10)
                now = datetime.datetime.now()          
    sleep_until = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time(hour=notification_start_hour))
    print(f"Sleeping until {sleep_until} from {now}")
    sleep_for = (sleep_until - now).total_seconds()
    time.sleep(sleep_for)
