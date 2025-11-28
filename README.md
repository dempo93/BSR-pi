# Berlin Trash Reminder
Turn your raspberry pi into a trash reminder for the Berlin area.
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

### Encoded Location
1. Go to the [BSR website](https://www.bsr.de/abfuhrkalender)
2. Enter your street and house number
3. On the calendar view, find the download link for the ICS calendar
4. Don't click the link, just copy it. It looks like this: `https://umnewforms.bsr.de/p/de.bsr.adressen.app/abfuhr/kalender/ics/012345678901234567890123?year=2025&month=11`
5. extract the encoded address `012345678901234567890123` and put it into the .env file

## Run

The script is designed to run even without internet connection for up to one year. It will download all the ical events from the BSR website and try to refresh them periodically
Tbd
