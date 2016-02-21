#!/usr/bin/env python3
""" Skript that gets measurements from the sonsors and
    writes it to a file for the weewx fileparse driver
"""


import RPi.GPIO as GPIO
import numpy as np
import time
import re, os
import spidev
import Adafruit_BMP.BMP085 as BMP085

adict = {5:0, 3:45, 0:90, 1:135, 2:180, 4:225, 7:270, 6:315}


def C2F(temperature):
  # convert temperature from degrees Celsius to Fahrenheit
  return(temperature * 9/5 + 32)


def mps2mph(speed):
  # convert meters per second to miles per hour
  return(speed * 2.23694)


def Pa2Hg(pressure):
  # convert Pascal to Hg
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
  # get value of ADC
  adc = spi.xfer2([1,(8+channel)<<4, 0])
  data = ((adc[1]&3)<<8)+adc[2]

  return(data)


def get_wind_dir():
  # get wind direction from resistance of vane
  adc = get_adc(0)    
  V = 3.3 * adc / 1023
  R2 = 2000*5/V - 2000	
  idx = np.round(np.log2(R2/1000))

  return adict[idx]


def ISR(channel):
  # interupt service routine which is called by anemometer
  global t0, n, wspeed, t
    
  if n%2:
    t1 = time.time()
    T = t1 - t0
    t0 = t1

    wspeed = 3 * np.pi*0.07/T
        
  n=n+1


# initialize GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(40, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# initialize SPI
spi = spidev.SpiDev()
spi.open(0,0)

# initialize pressure sensor
sensor = BMP085.BMP085(mode=BMP085.BMP085_ULTRAHIGHRES)
pressure = 0

# initialize time/counter for ISR
t0 = time.time()
n = 0  # loop counter for ISR
wspeed = 0  # initialze wind speed
wspeed0 = 0  # previous measurement for integry check
out_temp = 0  # init for temperatures
in_temp = 0

# register event loop
GPIO.add_event_detect(40, GPIO.RISING, callback = ISR)

# loop that writes the results
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

    # check wind speed for outliers
    if(abs(wspeed-wspeed0)>10):
        wspeed = wspeed0
    wspeed0 = wspeed

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
