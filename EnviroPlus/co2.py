
import time
import board
import adafruit_scd4x
import sqlite3
import datetime

i2c = board.I2C()
scd4x = adafruit_scd4x.SCD4X(i2c)
print("Serial number:", [hex(i) for i in scd4x.serial_number])

scd4x.start_periodic_measurement()
print("Waiting for first measurement....")

start_time = time.monotonic()
end_time = start_time + 3600  # 1200 seconds = 20 minutes

# Create a connection to the SQLite database
conn = sqlite3.connect('scd4x_data.db')
c = conn.cursor()

# Create a table for the sensor data
c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
             (timestamp REAL, co2_ppm INTEGER, temperature REAL, humidity REAL)''')
conn.commit()

while True:
    if scd4x.data_ready:
        # Get the current timestamp and sensor data
        timestamp = str(datetime.datetime.now())
        co2_ppm = scd4x.CO2
        temperature = scd4x.temperature
        humidity = scd4x.relative_humidity

        # Print the data to the console
        print("CO2: %d ppm" % co2_ppm)
        print("Temperature: %0.1f *C" % temperature)
        print("Humidity: %0.1f %%" % humidity)
        print()

        # Insert the data into the database
        c.execute("INSERT INTO sensor_data VALUES (?, ?, ?, ?)", (timestamp, co2_ppm, temperature, humidity))
        conn.commit()

        time.sleep(5)  # Wait for 5 seconds before taking the next reading

print("Finished taking readings.")

# Close the database connection
conn.close()
