# Berlin Trash Reminder
Turn your raspberry pi into a trash reminder for the Berlin area.
It will show messages like "Wertstoffe", "Hausmüll", "Biogut" on the day before the collection.
Uses a cheap 8x8 red led matrix with a max7219 controller.
Refer to [this link](https://www.az-delivery.de/en/products/64er-led-matrix-display-kostenfreies-e-book) for pin connection and simple examples

## Prerequisites

### SSH
You will need to create and import a ssh key to connect to your raspberry pi without password. For convenience, I added an ssh alias to `~/.ssh/config`
```
Host raspberrypi
    HostName 192.168.178.49
    User pi
    IdentityFile ~/.ssh/pi
    IdentitiesOnly yes
```
You can now `ssh resapberrypi`

### Remote development
I included the `.vscode` folder for **my** convenience, but you can adjust its content to develop from a remote host.
Make sure to adjust paths in `launch.json` and `tasks.json`. I also added this line `192.168.178.49 raspberrypi` to my `/etc/hosts` for convenience. 

### Libraries
Install and activate your favorite virtualenv.
Install the required libraries `python -m pip install -r requirements.txt`

### Env
#### ENCODED_ADDRESS
1. Go to the [BSR website](https://www.bsr.de/abfuhrkalender)
2. Enter your street and house number
3. On the calendar view, find the download link for the ICS calendar
4. Don't click the link, just copy it. It looks like this: `https://umnewforms.bsr.de/p/de.bsr.adressen.app/abfuhr/kalender/ics/012345678901234567890123?year=2025&month=11`
5. extract the encoded address `012345678901234567890123` and put it into the .env file

#### CALENDAR_SYNC_INTERVAL_DAYS
The amount of days between resyncs of the calendar

#### DISPLAY_ON_MINUTES
The amount of time the display will show the message for.

#### DISPLAY_INTERVAL_SECONDS
The amount of time the display will pause before repeating the message

## Run
The script is designed to cache all the ical events from the BSR website and try to refresh them periodically. This is quite useful if you don't have an internet connection.
Then it will load the correct ical event and display the type of trash which is going to be collected on the next day.
Example: Install as cronjob, running everyday at 17:
Run
```
crontab -e
```
Paste
```
0 17 * * * /usr/bin/python3 /path/to/your/script.py
```
Optionally run it in dryrun mode upon reboot. Add this line to your crontab
```
@reboot DRY_RUN_MODE=true /usr/bin/python3 /path/to/your/script.py
```
