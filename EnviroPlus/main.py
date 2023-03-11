#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnviroPlus Python
-----------------
[Description]

Credits:
    - Data acquisition (for temperature etc.)        :    E. Shindate, M. Jagpal, J. Keller
    - Data storage/transfer, LCD and calibration code:    A. Marathe

Special thanks to Pimoroni for providing the EnviroPlus Python library (MIT Licence).
Pimoroni EnviroPlus Python library: https://github.com/pimoroni/enviroplus-python

Authors: A. Marathe, E. Shindate, M. Jagpal
Last Updated: 08-03-2023
"""

import logging
import datetime
import sys
import time
import requests
from subprocess import check_output
import sqlite3

from typing import Tuple
from typing import Dict
from typing import Union
from typing import Optional

# EnviroPlus modules
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
from bme280 import BME280
from pms5003 import PMS5003
from ST7735 import ST7735
from ltr559 import LTR559
from enviroplus import gas

# Images and Fonts
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from fonts.ttf import RobotoMedium

# Logging ==============================================================================================================

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

_logging_format = logging.Formatter("%(asctime)s %(name)s | %(levelname)s | %(message)s")

# Logging to output stream
_c_handler = logging.StreamHandler()
_c_handler.setLevel(logging.INFO)
_c_handler.setFormatter(_logging_format)

# Logging to a file
_f_handler = logging.FileHandler("history.log")
_f_handler.setLevel(logging.INFO)
_f_handler.setFormatter(_logging_format)

logger.addHandler(_c_handler)
logger.addHandler(_f_handler)

logger.propagate = False

# EDITABLE: Settings ===================================================================================================

MONITOR_NAME = "My Monitor"

# Measurements
ROUND_DATA_TO_DP: int = 2

MEASURE_PM25: bool = True
MEASURE_PM10: bool = True
MEASURE_TEMPERATURE: bool = True
MEASURE_PRESSURE: bool = True
MEASURE_HUMIDITY: bool = True
MEASURE_GASES: bool = True

MEASURE_CPU_TEMPERATURE: bool = False

COMPENSATE_TEMPERATURE: bool = True
TEMP_COMPENSATION_FACTOR: float = 2.25

# OpenWeatherAPI
ENABLE_OPEN_WEATHER_API: bool = False

# Data management
SAVE_DATA_LOCALLY: bool = True
SEND_TO_MONGODB: bool = False
SEND_TO_LUFTDATEN: bool = False

# Luftdaten
LUFTDATEN_API_URL: str = "https://api.sensor.community/v1/push-sensor-data/"

# Other settings
VERBOSE = True
USER_AUTH_START = False

INSTANT_ACQUISITION_START = False
START_AT_MULTIPLE_OF: int = 5  # min

MEASUREMENT_FREQUENCY: Union[int, float] = 2  # per min

# Style
COLOURS = dict(
    white=(255, 255, 255),
    grey=(180, 180, 180),
    green=(40, 90, 40),
    red=(120, 20, 20),
    blue=(20, 30, 100),
    lime=(0, 250, 70)
)

TEXT_FONT_SIZE = 10
TEXT_FONT = ImageFont.truetype(RobotoMedium, TEXT_FONT_SIZE)

TITLE_FONT_SIZE = 20
TITLE_FONT = ImageFont.truetype(RobotoMedium, TITLE_FONT_SIZE)


# EDITABLE: Calibration ================================================================================================

def calibrate_temperature(temperature: float) -> float:
    """

    :param temperature:
    :return:
    """
    return round(temperature, ROUND_DATA_TO_DP)


def calibrate_pressure(pressure: float) -> float:
    """

    :param pressure:
    :return:
    """
    return round(pressure, ROUND_DATA_TO_DP)


def calibrate_humidity(humidity: float) -> float:
    """

    :param humidity:
    :return:
    """
    return round(humidity, ROUND_DATA_TO_DP)


def calibrate_pm25(pm25: int) -> int:
    """

    :param pm25:
    :return:
    """
    return round(pm25, ROUND_DATA_TO_DP)


def calibrate_pm10(pm10: int) -> int:
    """

    :param pm10:
    :return:
    """
    return round(pm10, ROUND_DATA_TO_DP)


# Functions ============================================================================================================

def get_serial_number() -> str:
    """Gets RPi serial number.

    :return:
    """
    with open("/proc/cpuinfo", "r") as file:
        for line in file:
            if line[0:6] == "Serial":
                return line.split(":")[1].strip()


def init() -> Tuple[str, SMBus, BME280, PMS5003, LTR559, ST7735]:
    """

    :return:
    """
    # Open I2C bus #1
    smbus = SMBus(1)

    # Waits to avoid Error #121
    time.sleep(1)

    # Temp, Pressure and Humidity sensor
    bme280_instance = BME280(i2c_dev=smbus)

    # PM sensor
    pms5003_instance = PMS5003()

    # Light sensor
    ltr559_instance = LTR559()

    # LCD display
    lcd_display = ST7735(port=0, cs=1, dc=9, backlight=12, rotation=270, spi_speed_hz=10_000_000)
    lcd_display.begin()

    # Unique RPi serial number
    serial_num = get_serial_number()

    return serial_num, smbus, bme280_instance, pms5003_instance, ltr559_instance, lcd_display


def get_cpu_temperature() -> float:
    """

    :return:
    """
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as file:
        cpu_temp = int(file.read()) / 1_000.0

    return cpu_temp


def compensate_temperature(raw_temp: float, cpu_temp: float, comp_factor: float = TEMP_COMPENSATION_FACTOR) -> float:
    """

    :param raw_temp:
    :param cpu_temp:
    :param comp_factor:
    :return:
    """
    comp_temp = raw_temp - ((cpu_temp - raw_temp) / comp_factor)
    return round(comp_temp, ROUND_DATA_TO_DP)


def get_sensor_data(bme280_instance: BME280, pms5003_instance: PMS5003) -> Tuple[Dict[str, float], datetime.datetime]:
    """

    :param bme280_instance:
    :param pms5003_instance:
    :return:
    """
    output = dict()

    # Collecting sensor data
    current_time = datetime.datetime.now()

    temperature = bme280_instance.get_temperature()  # deg C
    pressure = bme280_instance.get_pressure()  # hPa
    humidity = bme280_instance.get_humidity()  # %
    cpu_temperature = get_cpu_temperature()  # deg C

    if COMPENSATE_TEMPERATURE:
        temperature = compensate_temperature(temperature, cpu_temperature)  # deg C

    current_pm = pms5003_instance.read()
    pm25 = current_pm.pm_ug_per_m3(2.5)
    pm10 = current_pm.pm_ug_per_m3(10)

    current_gas = gas.read_all()
    oxidising = current_gas.oxidising
    reducing = current_gas.reducing
    nh3 = current_gas.nh3

    # Updating dict
    if MEASURE_TEMPERATURE:
        output["temperature"] = calibrate_temperature(temperature)  # deg C

    if MEASURE_PRESSURE:
        output["pressure"] = calibrate_pressure(pressure)  # hPa

    if MEASURE_HUMIDITY:
        output["humidity"] = calibrate_humidity(humidity)  # %

    if MEASURE_PM25:
        output["P2"] = calibrate_pm25(pm25)  # micro g / cm^3

    if MEASURE_PM10:
        output["P1"] = calibrate_pm10(pm10)  # micro g / cm^3

    if MEASURE_CPU_TEMPERATURE:
        output["cpu_temperature"] = round(cpu_temperature, ROUND_DATA_TO_DP)  # deg C

    if MEASURE_GASES:
        output["oxidising"] = round(oxidising / 1_000, ROUND_DATA_TO_DP)  # kOhm
        output["reducing"] = round(reducing / 1_000, ROUND_DATA_TO_DP)  # kOhm
        output["nh3"] = round(nh3 / 1_000, ROUND_DATA_TO_DP)  # kOhm

    return output, current_time


# Local Database =======================================================================================================

table_name: str = ""
connection: Optional[sqlite3.Connection] = None
cursor: Optional[sqlite3.Cursor] = None


def init_local_db() -> None:
    """

    :return:
    """
    global table_name, connection, cursor

    current_time = str(datetime.datetime.now())
    filename = "./" + MONITOR_NAME.replace(" ", "_") + "_data.db"

    connection = sqlite3.connect(filename)
    cursor = connection.cursor()

    # Create new table
    sql_code_blocks = [
        (["Temperature DOUBLE(5)"], MEASURE_TEMPERATURE),
        (["Humidity DOUBLE(5)"], MEASURE_HUMIDITY),
        (["Pressure DOUBLE(5)"], MEASURE_PRESSURE),
        (["CPUTemperature Double(5)"], MEASURE_CPU_TEMPERATURE),
        (["PM25 DOUBLE(5)"], MEASURE_PM25),
        (["PM10 DOUBLE(5)"], MEASURE_PM10),
        ([
             "OxidisingGases Double(10)",
             "ReducingGases Double(10)",
             "Ammonia Double (10)"
         ], MEASURE_GASES),
        ([
            "APITemperature DOUBLE(5)",
            "APIHumidity DOUBLE(5)",
            "APIPressure DOUBLE(5)",
            "APIWindSpeed DOUBLE(5)",
            "APIWindAngle DOUBLE(5)"
        ], ENABLE_OPEN_WEATHER_API)
    ]

    table_name = "data_" + current_time
    table_name = table_name.replace(" ", "_")
    table_name = table_name.replace("-", "_")
    table_name = table_name.replace(":", "_")
    table_name = table_name.replace(".", "_")
    command = "CREATE TABLE " + table_name + " (time TEXT,"

    for i, (commands, mode) in enumerate(sql_code_blocks):
        if mode:
            for c in commands:
                command += c + ","

        if i == len(sql_code_blocks) - 1:
            command = command[:-1]
            command += ")"

    connection.execute(command)
    connection.commit()


def send_to_local_db(data: Dict[str, float], measurement_time: str) -> None:
    """

    :param data:
    :param measurement_time:
    :return:
    """
    command = "INSERT INTO " + str(table_name) + f" VALUES ('{measurement_time!s}',"

    # Get data
    command += f"{data.get('temperature')!s}," if MEASURE_TEMPERATURE else ""
    command += f"{data.get('humidity')!s}," if MEASURE_HUMIDITY else ""
    command += f"{data.get('pressure')!s}," if MEASURE_PRESSURE else ""
    command += f"{data.get('cpu_temperature')!s}," if MEASURE_CPU_TEMPERATURE else ""
    command += f"{data.get('P2')!s}," if MEASURE_PM25 else ""
    command += f"{data.get('P1')!s}," if MEASURE_PM10 else ""
    if MEASURE_GASES:
        command += f"{data.get('oxidising')!s},{data.get('reducing')!s},{data.get('nh3')!s},"

    command = command[:-1] + ")"

    # Adds data to table
    cursor.execute(command)
    connection.commit()


# Luftdaten API ========================================================================================================

def send_to_luftdaten(data: Dict[str, float], serial_num: str) -> int:
    """

    :param data:
    :param serial_num:
    :return:
    """
    if not (MEASURE_PM25 and MEASURE_PM10):
        logger.error("Failed to send data to Luftdaten due to configuration. Possible fix: Enable `MEASURE_PM25` and "
                     "`MEASURE_PM10`.")
        return -1

    # Reshaping data dict. for Luftdaten API
    pm_data_dict = dict(P1=data["P1"], P2=data["P2"])
    climate_data_dict = dict(i for i in data.items() if not i[0].startswith("P"))  # -> Temp., pressure, humidity, etc.

    # Posting data
    pm_api_response = None
    pm_data_reshaped = [{"value_type": key, "value": val} for key, val in pm_data_dict.items()]

    try:
        pm_api_response = requests.post(
            url=LUFTDATEN_API_URL,
            json={
                "software_version": "enviro-plus 0.0.1",
                "sensordatavalues": pm_data_reshaped
            },
            headers={
                "X-PIN": "1",
                "X-Sensor": str(serial_num),
                "Content-Type": "application/json",
                "cache-control": "no-cache"
            },
            timeout=5  # s
        )
    except requests.exceptions.ConnectionError as e:
        logging.warning(f"Failed to send PM data to Luftdaten due to a connection error. Details: {e}")
    except requests.exceptions.Timeout as e:
        logging.warning(f"Failed to send PM data to Luftdaten because request timed-out. Details: {e}")
    except requests.exceptions.RequestException as e:
        logging.warning(f"Failed to send PM data to Luftdaten due to a request error. Details: {e}")

    climate_api_response = None
    if bool(climate_data_dict):
        climate_data_reshaped = [{"value_type": key, "value": val} for key, val in climate_data_dict.items()]

        try:
            climate_api_response = requests.post(
                url=LUFTDATEN_API_URL,
                json={
                    "software_version": "enviro-plus 0.0.1",
                    "sensordatavalues": climate_data_reshaped
                },
                headers={
                    "X-PIN": "11",
                    "X-Sensor": str(serial_num),
                    "Content-Type": "application/json",
                    "cache-control": "no-cache"
                },
                timeout=5  # s
            )
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"Failed to send PM data to Luftdaten due to a connection error. Details: {e}")
        except requests.exceptions.Timeout as e:
            logging.warning(f"Failed to send PM data to Luftdaten because request timed-out. Details: {e}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to send PM data to Luftdaten due to a request error. Details: {e}")

    # Checking API response
    if (pm_api_response is not None) and (climate_api_response is not None):  # --> if climate data was provided
        if pm_api_response.ok and climate_api_response.ok:
            return 0

        logging.warning(
            "Received bad response from Luftdaten. Details: PM data post received: " + str(pm_api_response.reason)
            + ", Climate data post received: " + str(climate_api_response.reason)
        )
        return -1

    elif (pm_api_response is not None) and (climate_api_response is None):  # --> if no climate data was provided
        if pm_api_response.ok:
            return 0

        logging.warning(
            "Received bad response from Luftdaten. Details: PM data post received: " + str(pm_api_response.reason)
        )
        return -1

    return -1


# Verbose =============================================================================================================

def verbose(data: Dict[str, float], measurement_time: str) -> None:
    temperature = data.get("temperature")
    temperature = bool(temperature) * (" Tmp: " + str(temperature) + " deg C ")

    humidity = data.get("humidity")
    humidity = bool(humidity) * (" Hum: " + str(humidity) + " % ")

    pressure = data.get("pressure")
    pressure = bool(pressure) * (" Prs: " + str(pressure) + " hPa ")

    cpu_temperature = data.get("cpu_temperature")
    cpu_temperature = bool(cpu_temperature) * (" CPU: " + str(cpu_temperature) + " deg C ")

    pm25 = data.get("P2")
    pm25 = bool(pm25) * (" PM2.5: " + str(pm25) + " ug/cm^3 ")

    pm10 = data.get("P1")
    pm10 = bool(pm10) * (" PM10: " + str(pm10) + " ug/cm^3 ")

    oxidising = data.get("oxidising")
    oxidising = bool(oxidising) * (" Oxidising: " + str(oxidising) + " kOhm ")

    reducing = data.get("reducing")
    reducing = bool(reducing) * (" Reducing: " + str(reducing) + " kOhm ")

    nh3 = data.get("nh3")
    nh3 = bool(nh3) * (" NH3: " + str(nh3) + " kOhm ")

    print(
        f"\n{measurement_time!s} | " + temperature + pressure + humidity + cpu_temperature + pm25 + pm10
        + oxidising + reducing + nh3
    )

    # if ENABLE_OPEN_WEATHER_API:
    #    print(f"") time --> 26 length


# Display ==============================================================================================================

mainloop_errors: bool = False
current_scene_id: int = 0


def display_welcome_scene(display: ST7735) -> None:
    """

    :param display:
    :return:
    """
    image = Image.new(mode="RGB", size=(display.width, display.height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image, mode="RGB")

    draw.rectangle((0, 0, display.width, display.height), COLOURS["blue"])

    draw.text((5, 5), text=f"ENVIROPLUS", fill=COLOURS["white"], font=TEXT_FONT)
    draw.text((5, 15), text=MONITOR_NAME, fill=COLOURS["white"], font=TITLE_FONT)

    draw.text(
        (5, display.height - 15),
        text=f"RPi Time: {str(datetime.datetime.now())[:-7]}", fill=COLOURS["white"],
        font=TEXT_FONT
    )

    display.display(image)


def display_status_bg(display: ST7735, draw: ImageDraw.Draw) -> None:
    """

    :param display:
    :param draw:
    :return:
    """
    if mainloop_errors:
        draw.rectangle((0, 0, display.width, display.height), COLOURS["red"])
    else:
        draw.rectangle((0, 0, display.width, display.height), COLOURS["green"])

    draw.rectangle((0, 0, display.width, 10), COLOURS["blue"])


def display_main_scene(draw: ImageDraw.Draw, current_time: str, data: Dict[str, float]) -> None:
    """

    :param draw:
    :param current_time:
    :param data:
    :return:
    """
    draw.text((5, 0), text=f"{MONITOR_NAME}", fill=COLOURS["white"], font=TEXT_FONT)
    draw.text((5, 15), text=f"Last: {current_time!s}", fill=COLOURS["white"], font=TEXT_FONT)

    if current_scene_id == 0:
        draw.text((5, 30), text="PM2.5", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((5, 45), text=str(data.get("P2", 0)), fill=COLOURS["white"], font=TITLE_FONT)

        draw.text((60, 30), text="PM10", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((60, 45), text=str(data.get("P1", 0)), fill=COLOURS["white"], font=TITLE_FONT)

        draw.text((115, 30), text="Temp", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((115, 45), text=str(int(data.get("temperature", 0))), fill=COLOURS["white"], font=TITLE_FONT)
    elif current_scene_id == 1:
        draw.text((5, 30), text="Humidity", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((5, 45), text=str(int(data.get("humidity", 0))), fill=COLOURS["white"], font=TITLE_FONT)

        draw.text((60, 30), text="Pressure", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((60, 45), text=str(int(data.get("pressure", 0))), fill=COLOURS["white"], font=TITLE_FONT)
    elif current_scene_id == 2:
        draw.text((5, 30), text="Oxi", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((5, 45), text=str(int(data.get("oxidising", 0))), fill=COLOURS["white"], font=TITLE_FONT)

        draw.text((60, 30), text="Red", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((60, 45), text=str(int(data.get("reducing", 0))), fill=COLOURS["white"], font=TITLE_FONT)

        draw.text((115, 30), text="NH3", fill=COLOURS["white"], font=TEXT_FONT)
        draw.text((115, 45), text=str(int(data.get("nh3", 0))), fill=COLOURS["white"], font=TITLE_FONT)


def display_progress_bar(display: ST7735, draw: ImageDraw.Draw, percent: float) -> None:
    draw.rectangle((0, display.height - 8, int(display.width * percent), display.height), COLOURS["lime"])


# Main =================================================================================================================

def mainloop(bme280_instance: BME280, pms5003_instance: PMS5003, ltr559_instance: LTR559, display: ST7735) -> None:
    """

    :param bme280_instance:
    :param pms5003_instance:
    :param ltr559_instance:
    :param display:
    :return:
    """
    global mainloop_errors, current_scene_id

    previous_time = time.time()  # s

    update_delay = 60.0 / MEASUREMENT_FREQUENCY

    data = dict()
    measurement_time = "-"

    if SAVE_DATA_LOCALLY:
        init_local_db()

    # Connect to MongoDB database
    ...

    image = Image.new(mode="RGB", size=(display.width, display.height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image, mode="RGB")

    while True:
        try:
            current_time = time.time()
            time_difference = current_time - previous_time

            if time_difference >= update_delay:
                # Update time
                previous_time = current_time

                # Data acquisition
                data, measurement_time = get_sensor_data(bme280_instance, pms5003_instance)

                # Data storage/transfer
                if VERBOSE:
                    verbose(data=data, measurement_time=str(measurement_time))

                if SAVE_DATA_LOCALLY:
                    send_to_local_db(data=data, measurement_time=str(measurement_time))
                    logging.info("Success: Data saved to local storage.")

            # User input -> from Light/Proximity sensor
            proximity = ltr559_instance.get_proximity()

            if proximity > 1_500:
                current_scene_id += 1

                if current_scene_id > 2:
                    current_scene_id = 0

            # Display updates
            display_status_bg(display=display, draw=draw)
            display_main_scene(draw=draw, current_time=str(measurement_time)[:-7], data=data)
            display_progress_bar(display=display, draw=draw, percent=time_difference / update_delay)

            display.display(image)

            # Slow down the loop
            time.sleep(update_delay * 0.05)

        except Exception as e:
            mainloop_errors = True

            logging.critical(f"Mainloop exception occurred: {e}")


def main() -> int:
    """

    :return:
    """
    print("==========================")
    print("[   EnviroPlus Monitor   ]")
    print("==========================\n")

    try:
        device_id, bus, *sensor_instances, display = init()
    except Exception as e:
        logging.critical(f"An error occurred during initialisation: {e}")
        return -1

    display_welcome_scene(display=display)

    # Logging
    logging.debug("Initialised libraries successfully...")
    logging.debug("Set to measure: [ "
                  + MEASURE_TEMPERATURE * " Temperature (degrees Celsius) "
                  + MEASURE_PRESSURE * " Pressure (hPa) "
                  + MEASURE_HUMIDITY * " Humidity (%) "
                  + MEASURE_CPU_TEMPERATURE * " CPU Temperature (degrees Celsius) "
                  + MEASURE_PM25 * " PM2.5 (micro g / cm^2) "
                  + MEASURE_PM10 * " PM10 (micro g / cm^2) " + " ]")

    if SAVE_DATA_LOCALLY:
        _filename = MONITOR_NAME.replace(" ", "_")
        logging.debug(f"Data transfer: Data will be saved locally in the '{_filename}_data.db' file.")

    if SEND_TO_MONGODB:
        logging.debug("Data transfer: Data will be sent to your MongoDB Atlas database.")

        # Tips
        print("\nSending data to MongoDB Atlas:\n------------------------------")
        print("\t - Please ensure that you have a stable internet connection")
        print(f"\t - Please check that you have added the device IP address: {check_output(['hostname', '-I'])}")

    if SEND_TO_LUFTDATEN:
        logging.debug("Data transfer: Data will be sent to Luftdaten.")

        # Tips
        print("\nSending sensor data to Luftdaten:\n---------------------------------")
        print("\t - Please ensure that you have a stable internet connection")
        print(f"\t - Please register your monitor using the following device ID: {device_id}")
        print("\t - Thank you for your contribution to the project :)")

    if not INSTANT_ACQUISITION_START:
        print(
            f"\nNote: Data acquisition will begin when the current minute is a multiple of {START_AT_MULTIPLE_OF}."
        )

    print(f"\nNote: Data collection frequency is set to {MEASUREMENT_FREQUENCY} measurements per minute.\n")

    if USER_AUTH_START:
        input("\nPress enter to begin data acquisition...\n")

    try:
        while not INSTANT_ACQUISITION_START:
            if not (datetime.datetime.now().minute % START_AT_MULTIPLE_OF):
                break

        # Begin mainloop...
        logging.debug("Starting data acquisition mainloop...")
        mainloop(*sensor_instances, display=display)

    except KeyboardInterrupt:
        # Close I2C
        bus.close()

        # Turn off display
        display.set_backlight(0)

        # Close connection to local DB
        if SAVE_DATA_LOCALLY and (connection is not None):
            connection.close()

        logging.debug("Data acquisition stopped by user.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
