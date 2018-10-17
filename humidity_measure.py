import smbus2
import time
from datetime import datetime
import os.path
import csv

class Si7021():

    ADDRESS = 0x40
    RESET = 0xFE

    TEMP_NO_HOLD = 0xF3
    HUMIDITY_NO_HOLD = 0xF5

    READ_HEATER_CTRL = 0x11
    WRITE_HEATER_CTRL = 0x51

    READ_USR_REG = 0xE7
    WRITE_USR_REG = 0xE6

    HEATER_OFFSET = 3.09
    HEATER_STEP = 6.074

    USR_RES1 = 128
    USR_VDDS = 64
    USR_HTRE = 4
    USR_RES0 = 1

    bus = smbus2.SMBus(1)

    def measure(self, cmd_code):
        self.bus.write_byte(self.ADDRESS, cmd_code)
        time.sleep(.5)
        msg = smbus2.i2c_msg.read(self.ADDRESS, 3)
        self.bus.i2c_rdwr(msg)
        msb = ord(msg.buf[0])
        lsb = ord(msg.buf[1])
        checksum = ord(msg.buf[2])
        value = (msb * 256) + lsb
        return value

    def read_humidity(self):
        humidity_value = self.measure(self.HUMIDITY_NO_HOLD)
        humidity = (humidity_value * 125 / 65536.0) - 6
        return humidity

    def read_temp(self):
        temp_value = self.measure(self.TEMP_NO_HOLD)
        temp_c = (temp_value * 175.72 / 65536.0) - 46.85
        temp_f = temp_c * 1.8 + 32
        return temp_f

    def reset(self):
        self.bus.write_byte(self.ADDRESS, self.RESET)

    def heater_mA(self, value):
        """ Set heater current in mA.
        Turing on and off of the heater is handled automatically.
        """
        usr = self.bus.read_byte_data(self.ADDRESS, self.READ_USR_REG)

        if not value:
            usr &= ~self.USR_HTRE
        else:
            # Enable heater and calculate settings
            setting = 0
            if value > self.HEATER_OFFSET:
                value -= self.HEATER_OFFSET
                setting = int(round(value / self.HEATER_STEP)) # See DS 5.5
                setting = min(15, setting) #Avoid overflow
            self.bus.write_byte_data(self.ADDRESS, self.WRITE_HEATER_CTRL, setting)
            usr |= self.USR_HTRE

        self.bus.write_byte_data(self.ADDRESS, self.WRITE_USR_REG, usr)

    def set_resolution(self, bits_rh):
        """ Select measurement resolution.
        bits_rh is the number of bits for the RH measurement. Number of
        bits for temperature is choosen accoring to the table in section 6.1
        of the datasheet.
        """
        usr = self.bus.read_byte_data(self.ADDRESS, self.READ_USR_REG)
        usr &= ~(self.USR_RES0 | self.USR_RES1)
        if bits_rh == 8:
            usr |= self.USR_RES1
        elif bits_rh == 10:
            usr |= self.USR_RES1
        elif bits_rh == 11:
            usr |= self.USR_RES0 | self.USR_RES1
        elif bits_rh != 12:
            raise ValueError("Unsupported number of bits.")
        self.bus.write_byte_data(self.ADDRESS, self.WRITE_USR_REG, usr)	

import json
import requests

class WeatherApi():

    def __init__(self):
        self.BASE_URL = 
        self.API_KEY = 
        self.ZIP_CODE =         
        self.UNITS = 

    def get_current_temp(self):
        weather_json = self.retrieve_weather_info()
        return weather_json['main']['temp']

    def get_current_humidity(self):
        weather_json = self.retrieve_weather_info()
        return weather_json['main']['humidity']

    def retrieve_weather_info(self):
        weather_url = self.BASE_URL + 'zip=' + self.ZIP_CODE + '&units=' + self.UNITS + '&APPID=' + self.API_KEY
        response = requests.get(weather_url)

        if(response.status_code == 200):
            return json.loads(response.content.decode('utf-8'))
        else:
            return None


if (__name__ == '__main__'):

    temp_humidity_sensor = Si7021()
    last_temp = 0
    last_humidity = 0

    weather = WeatherApi()
    print(weather.get_current_temp())

    filename = 'output.csv'
    file_exists = os.path.isfile(filename)

    with open('output.csv', 'a', newline='') as output:

        headers = ['Date', 'Temp', 'Relative Humidity', 'Outdoor Temp', 'Outdoor Humidity']
        writer = csv.DictWriter(output, headers)
        if not file_exists:
            writer.writeheader()

        while(True):
            temp = temp_humidity_sensor.read_temp()
            humidity = temp_humidity_sensor.read_humidity()
            if(abs(humidity - last_humidity) > 1 or abs(temp - last_temp) > 1):
                try:
                    local_humidity = weather.get_current_humidity()
                    local_temp = weather.get_current_temp()
                    writer.writerow({'Date': datetime.now(), 'Temp': temp, 'Relative Humidity': humidity, 'Outdoor Temp': local_temp, 'Outdoor Humidity': local_humidity})
                    print("Relative Humidity is : %.2f %%" %humidity)
                    print("Temperature in Fahrenheit is : %.2f F" %temp)
                    print('Local Humidity is : %.2f %%' %local_humidity)
                    print("Local Temperature in Fahrenheit is : %.2f F" %local_temp)
                    last_temp = temp
                    last_humidity = humidity
                except:
                    print('Error getting local data')

            time.sleep(2)

