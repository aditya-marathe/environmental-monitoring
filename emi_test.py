#!/usr/bin/env python3

import time
import requests
import logging
import datetime
import pickle
import sqlite3

from subprocess import PIPE, Popen, check_output

# Sensor data
import ST7735
from bme280 import BME280
from pms5003 import PMS5003, ReadTimeoutError, ChecksumMismatchError
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

# Image, Fonts
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont

# Logging ===============================================================================
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("Data acquisition started.")

# Sensors ===============================================================================
bus = SMBus(1)

# Create BME280 instance
bme280 = BME280(i2c_dev=bus)

# Create PMS5003 instance
pms5003 = PMS5003()

# Create LCD instance
disp = ST7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)

# Initialize display
disp.begin()

# Constants =============================================================================

# Compensation factor for temperature
comp_factor = 2.25

# Width and height to calculate text position
WIDTH = disp.width
HEIGHT = disp.height

# Text settings
font_size = 16
font = ImageFont.truetype(UserFont, font_size)

# Read values from BME280 and PMS5003 and return as dict ================================
def read_values():
    values = {}

    # Temperature compensation
    cpu_temp = get_cpu_temperature()
    raw_temp = bme280.get_temperature()
    comp_temp = raw_temp - ((cpu_temp - raw_temp) / comp_factor)

    # Current time
    current_time = str(datetime.datetime.now())

    values["temperature"] = "{:.2f}".format(comp_temp)
    values["pressure"] = "{:.2f}".format(bme280.get_pressure()) #* 100)
    values["humidity"] = "{:.2f}".format(bme280.get_humidity())

    # PM2.5, PM10
    try:
        pm_values = pms5003.read()
        values["P2"] = str(pm_values.pm_ug_per_m3(2.5))
        values["P1"] = str(pm_values.pm_ug_per_m3(10))
    except(ReadTimeoutError, ChecksumMismatchError):
        logging.info("Failed to read PMS5003. Reseting and retrying.")
        pms5003.reset()
        pm_values = pms5003.read()
        values["P2"] = str(pm_values.pm_ug_per_m3(2.5))
        values["P1"] = str(pm_values.pm_ug_per_m3(10))
        
    return values, current_time


# Helper functions ======================================================================
def get_cpu_temperature():
    # Get the temperature of the CPU for compensation
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = f.read()
        temp = int(temp) / 1000.0
    return temp


def get_serial_number():
    # Get Raspberry Pi serial number to use as ID
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line[0:6] == 'Serial':
                return line.split(":")[1].strip()


def check_wifi():
    # Check for Wi-Fi connection
    if check_output(['hostname', '-I']):
        return True
    else:
        return False


def display_status():
    # Display Raspberry Pi serial and Wi-Fi status on LCD
    text_colour = (255, 255, 255)
    back_colour = (0, 170, 170) if check_wifi() else (85, 15, 15)
    
    id = get_serial_number()
    wifi_status = "connected" if check_wifi() else "disconnected"

    message = "{}\nWi-Fi: {}".format(id, wifi_status)
    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    size_x, size_y = draw.textsize(message, font)

    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)

    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), message, font=font, fill=text_colour)
    disp.display(img)


def create_file():
    current_time = str(datetime.datetime.now())
    outfile = open(f"{current_time}_session.pickle", "wb")
    infile = open(f"{current_time}_session.pickle", "rb")

    return outfile, infile


def add_data(c_time, values, outfile, infile):
    new_dict = pickle.load(infile)
    new_dict[c_time] = values
    pickle.dump(new_dict, outfile)
    logging.info("Added to file...")


# Luftdaten API =========================================================================
def send_to_luftdaten(values, id):
    pm_values = dict(i for i in values.items() if i[0].startswith("P"))
    temp_values = dict(i for i in values.items() if not i[0].startswith("P"))

    pm_values_json = [{"value_type": key, "value": val} for key, val in pm_values.items()]
    temp_values_json = [{"value_type": key, "value": val} for key, val in temp_values.items()]

    resp_pm = None
    resp_bmp = None

    try:
        resp_pm = requests.post(
            "https://api.sensor.community/v1/push-sensor-data/",
            json={
                "software_version": "enviro-plus 0.0.1",
                "sensordatavalues": pm_values_json
            },
            headers={
                "X-PIN": "1",
                "X-Sensor": id,
                "Content-Type": "application/json",
                "cache-control": "no-cache"
            },
            timeout=5
        )
    except requests.exceptions.ConnectionError as e:
        logging.warning('Sensor.Community (Luftdaten) PM Connection Error: {}'.format(e))
    except requests.exceptions.Timeout as e:
        logging.warning('Sensor.Community (Luftdaten) PM Timeout Error: {}'.format(e))
    except requests.exceptions.RequestException as e:
        logging.warning('Sensor.Community (Luftdaten) PM Request Error: {}'.format(e))

    try:
        resp_bmp = requests.post(
            "https://api.sensor.community/v1/push-sensor-data/",
            json={
                "software_version": "enviro-plus 0.0.1",
                "sensordatavalues": temp_values_json
            },
            headers={
                "X-PIN": "11",
                "X-Sensor": id,
                "Content-Type": "application/json",
                "cache-control": "no-cache"
            },
            timeout=5
        )
    except requests.exceptions.ConnectionError as e:
        logging.warning('Sensor.Community (Luftdaten) Climate Connection Error: {}'.format(e))
    except requests.exceptions.Timeout as e:
        logging.warning('Sensor.Community (Luftdaten) Climate Timeout Error: {}'.format(e))
    except requests.exceptions.RequestException as e:
        logging.warning('Sensor.Community (Luftdaten) Climate Request Error: {}'.format(e))

    if resp_pm is not None and resp_bmp is not None:
        if resp_pm.ok and resp_bmp.ok:
            return True
        else:
            logging.warning('Luftdaten Error. PM: {}, Climate: {}'.format(resp_pm.reason, resp_bmp.reason))
            return False
    else:
        return False


# Initialisation ========================================================================
# Raspberry Pi ID to send to Luftdaten
id = "raspi-" + get_serial_number()

# Log Raspberry Pi serial and Wi-Fi status
logging.info("Raspberry Pi serial: {}".format(get_serial_number()))
logging.info("Wi-Fi: {}\n".format("connected" if check_wifi() else "disconnected"))

# Create database =======================================================================

conn = sqlite3.connect("./session.db")
cursor = conn.cursor()

conn.execute("""CREATE TABLE data (
                time TEXT,
                temperature DOUBLE(10),
                humidity DOUBLE(10),
                pressure DOUBLE(10),
                pmlarge DOUBLE(10),
                pmsmall DOUBLE(10)
                )""")

conn.commit()

def add_data_to_db(conn, cursor, time, values):
    temp = values["temperature"]
    humidity = values["humidity"]
    pressure = values["pressure"]
    pm10 = values["pm10"]
    pm25 = values["pm25"]

    command = str(f"INSERT INTO data VALUES ('{time!s}', {temp!s}, {humidity!s}, {pressure!s}, {pm10!s}, {pm25!s})")
    
    cursor.execute(command)
    conn.commit()

    logging.info("Data logged...")

# Main loop =============================================================================
def mainloop(local=True):
    time_since_update = 0
    update_time = time.time()

    # data = dict()

    while True:
        try:
            values, measurement_time = read_values()
            
            print(measurement_time, values)
            print()

            time_since_update = time.time() - update_time

            if time_since_update > 30:
                logging.info(values)
                update_time = time.time()

                if local:
                    # Save data to SD card
                    # add_data(measurement_time, values, outfile, infile)
                    add_data_to_db(conn, cursor, measurement_time, values)
                else:
                    # Send data to Luftdaten
                    if send_to_luftdaten(values, id):
                        logging.info("Luftdaten Response: OK")
                    else:
                        logging.warning("Luftdaten Response: Failed")
            
            # display_status()

        except Exception as e:
            logging.warning('Main Loop Exception: {}'.format(e))


while True:
    if not (datetime.datetime.now().minute % 5):
        # outfile, infile = create_file()

        try:
            logging.info("Mainloop started")
            mainloop(local=True)

        except KeyboardInterrupt:
            conn.close()

        break
    
