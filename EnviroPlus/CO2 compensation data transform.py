#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd
from datetime import datetime

# Load the measured data
measured_data = pd.read_csv('sensor_data.csv')

# Load the calibration data
calibration_data = pd.read_csv('Aranet4 042DF_2023-03-07T16_46_34+0000.csv')

# Convert time strings to numerical format and round to nearest second
measured_data['timestamp'] = measured_data['timestamp'].apply(lambda x: round(datetime.strptime(x, r"%Y-%m-%d %H:%M:%S.%f").timestamp()))
calibration_data['Time'] = calibration_data['Time'].apply(lambda x: round(datetime.strptime(x, '%d/%m/%Y %H:%M:%S').timestamp()))

# Interpolate the calibration data to match the time of the measured data
calibration_data_interp = np.interp(measured_data['timestamp'], calibration_data['Time'], calibration_data['Carbon dioxide(ppm)'])

# Calculate the correction factor as the mean ratio of measured to interpolated calibration data
correction_factor = np.mean(calibration_data_interp / measured_data['co2_ppm'])

# Save the correction factor to a file
np.savetxt('correction_factor.txt', [correction_factor])

# Apply the correction factor to the measured data
compensated_data = measured_data['co2_ppm'] * correction_factor

# Save the compensated data to a new file
compensated_data.to_csv('compensated_data.csv', index=False)

print()






