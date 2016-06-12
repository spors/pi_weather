#!/usr/bin/env python3
""" Skript that captures the measurements from the
        - anemometer
        - wind vane
        - temperature sensor
        - barometer
    sensor, processes the data and writes the measurements to
    a file as attribute value pairs for the weewx fileparse
    driver.

    (c) Sascha Spors, MIT License
"""

import numpy as np
import time
import re
import pigpio
import spidev
import Adafruit_BMP.BMP085 as BMP085


tick0 = 0  # a-priori time of ISR
n = 0  # loop counter for ISR
wspeed = 0  # initialze wind speed
wspeed0 = 0  # previous measurement for integry check
out_temp = 0  # init for temperature
in_temp = 0

# data for conversion of ADC values to wind angles
adc_bins = [0, 36, 58, 79, 109, 151, 182, 248, 332, 444, 565, 672, 825, 1023]
bin_angle = [270, 315, 292.5, 0, 337.5, 222.5, 247.5, 45, 22.5, 180, 202.5, 135, 157.5, 90]

def C2F(temperature):
  # convert temperature from degrees Celsius to Fahrenheit
  return(temperature * 9/5 + 32)


def mps2mph(speed):
  # convert speed from meters per second to miles per hour
  return(speed * 2.23694)


def Pa2Hg(pressure):
  # convert pressure from Pascal to Hg
  return(pressure * 0.000295299830714)


def get_DS18B20_temperature(path):
  # read and parse data file of DS18B20 temperature sensor
  value = "U"
  try:
    f = open(path, "r")
    line = f.readline()
    if re.match(r"([0-9a-f]{2} ){9}: crc=[0-9a-f]{2} YES", line):
      line = f.readline()
      m = re.match(r"([0-9a-f]{2} ){9}t=([+-]?[0-9]+)", line)
      if m:
        value = str(float(m.group(2)) / 1000.0)
    f.close()
  except (IOError) as e:
    print("Error reading temp (%s)"%e)
  return float(value)


def get_adc(channel):
  # get value of MCP3008 ADC
  adc = spi.xfer2([1,(8+channel)<<4, 0])
  data = ((adc[1]&3)<<8)+adc[2]

  return(data)


def get_wind_dir():
  # get direction from wind vane
  adc = get_adc(0)
  idx = np.digitize([adc], adc_bins)

  return bin_angle[idx-1]


def ISR(gpio, level, tick):
  # interupt service routine which is called by anemometer
  global tick0, n, wspeed
    
  if ((n%2) & (level==1)):
      T = pigpio.tickDiff(tick0, tick) * 1e-6
      tick0 = tick

      wspeed = 3 * np.pi*0.07/T
        
  n=n+1


# initialize GPIO callback for for anemometer
pi = pigpio.pi()
pi.set_mode(21, pigpio.INPUT)
pi.set_pull_up_down(21, pigpio.PUD_UP)
tick0 = pi.get_current_tick()
cb = pi.callback(21, pigpio.RISING_EDGE, ISR)

# initialize SPI
spi = spidev.SpiDev()
spi.open(0,0)

# initialize pressure sensor
sensor = BMP085.BMP085(mode=BMP085.BMP085_ULTRAHIGHRES)
pressure = 0

# main loop
time.sleep(5)
while 1:

    # open file
    f = open('/home/pi/wxdata.txt','w')
    
    # get temperature and pressure
    if ((round(time.time())%30 == 0) or (pressure==0)):
        out_temp = get_DS18B20_temperature("/sys/bus/w1/devices/28-000007737bbf/w1_slave")
        in_temp = sensor.read_temperature()
        pressure = sensor.read_sealevel_pressure(altitude_m=25.0)

    # get wind direction
    wdir = get_wind_dir()
    # wdir = 0

    # check wind speed for outliers
    #if(abs(wspeed-wspeed0)>10):
    #    wspeed = wspeed0
    #wspeed0 = wspeed

    # write data for weewx
    f.write('windSpeed=%f\n'%mps2mph(wspeed))
    f.write('windDir=%d\n'%wdir)
    f.write('outTemp=%f\n'%C2F(out_temp))
    f.write('inTemp=%f\n'%C2F(in_temp))
    f.write('pressure=%f\n'%Pa2Hg(pressure))

    # close file
    f.close()

    # log to console
    datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print("%s: %f ms from %d deg/ %f C / %f C / %f Pa"%(datetime, wspeed, wdir, in_temp, out_temp, pressure))

    # sleep a bit
    time.sleep(1)
