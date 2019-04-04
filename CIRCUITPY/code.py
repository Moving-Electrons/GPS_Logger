import time
import board
import busio
import adafruit_ssd1306 
import adafruit_gps
from analogio import AnalogIn
from digitalio import DigitalInOut
import adafruit_sdcard
import storage
import os
import sys


# Constants and initial values.
oled_2ndline = oled_1stline = ''
oled_3rdline = 'Initializing...'
last_gps = (0.0, 0.0) 

# Update interval for OLED and screen messages
# IMPORTANT NOTE: Setting this interval to less than 2 seconds
# causes erratic behavior: GPS doesn't seem to be given enough time
# to update data and only a few rows are written to the SD Card. 
UPDATE_INTERVAL = 5.0 #5.0 works well
# Difference between previous and current GPS readings to record change on file.
GPS_DIFF = 0.000025 #0.00002 & 0.00003 work well

# Pin Configuration
batt = AnalogIn(board.VOLTAGE_MONITOR)

# Define RX and TX pins for the board's serial port connected to the GPS.
# These are the defaults you should use for the GPS FeatherWing.
# For other boards set RX = GPS module TX, and TX = GPS module RX pins.
RX = board.RX
TX = board.TX

# Create a serial connection for the GPS connection using default speed and
# a slightly higher timeout (GPS modules typically update once a second).
uart = busio.UART(TX, RX, baudrate=9600, timeout=3)

# for a computer, use the pyserial library for uart access
#import serial
#uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=3000)

# Create a GPS module instance.
gps = adafruit_gps.GPS(uart, debug=False)

# Initialize the GPS module by changing what data it sends and at what rate.
# These are NMEA extensions for PMTK_314_SET_NMEA_OUTPUT and
# PMTK_220_SET_NMEA_UPDATERATE but you can send anything from here to adjust
# the GPS module behavior:
#   https://cdn-shop.adafruit.com/datasheets/PMTK_A11.pdf

# Turn on the basic GGA and RMC info (what you typically want)
gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
# Turn on just minimum info (RMC only, location):
#gps.send_command(b'PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
# Turn off everything:
#gps.send_command(b'PMTK314,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
# Tuen on everything (not all of it is parsed!)
#gps.send_command(b'PMTK314,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0')

# Set update rate to once a second (1hz) which is what you typically want.
gps.send_command(b'PMTK220,1000')
# Or decrease to once every two seconds by doubling the millisecond value.
# Be sure to also increase your UART timeout above!
#gps.send_command(b'PMTK220,2000')
# You can also speed up the rate, but don't go too fast or else you can lose
# data during parsing.  This would be twice a second (2hz, 500ms delay):
#gps.send_command(b'PMTK220,500')

# creating OLED instance.
# First two parameters are the OLED screen Width and Height.
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c=i2c)

# Creating SD Card instance.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = DigitalInOut(board.D5)



def batt_charge(unit='%'):
    '''
    Per Particle documentation, the voltage divider on the Particle Xenon is comprised of
    the following resistors:

    R1 = 806Kohm
    R2 = 2Mohm

    Solving for batt (voltage divider formula):
    batt = (Vpin x (R1+R2))/R2
    batt = Vpin x 1.403

    Maximum value measured at the Vpin is 3.3V, with a resolution of 16 bits (0 to 65535 units)
    provided by CircuitPython, results on 0.00005035477 per unit. Therefore:

    batt = Vpin x 1.403 x 0.00005035477

    '''

    batt_min = 3.20 # min battery level (lipo battery)
    batt_max = 3.8432 # max battery level. Lipo = 4.2v?

    volt = batt.value*1.403*0.00005035477

    # since the battery voltage doesn't go completely to "zero", a direct correlation
    # between the measured voltage and 100% cannot be done. Therefore:

    range_diff = batt_max - batt_min
    volt_diff = volt - batt_min

    percent = (volt_diff*100)/range_diff
    
    if unit == 'v': 
        return volt
    elif unit == '%':
        return percent
    

def oled_update():

    oled.fill(0)
    # Updating battery charge visualization:
    oled.text('Bat:{0:.2f}%'.format(batt_charge()), 67, 0, 1)
    oled.text(oled_1stline, 0, 0, 1)
    
    # Printing voltage on oled's 2nd line:
    #oled.text('{0:.2f} v'.format(batt.value*1.403*0.00005035477), 0, 10, 1)
    oled.text(oled_2ndline, 0, 10, 1)
    oled.text(oled_3rdline, 0, 20, 1)
    oled.show()
    return

def write_to_csv():

    # Handling optional values. Some of them may be = None.
    altitude = satellites = speed = 'Unknown'

    if gps.altitude_m is not None:
        altitude = gps.altitude_m
    if gps.satellites is not None:
        satellites = gps.satellites
    if gps.speed_knots is not None:
        speed = gps.speed_knots

    #Creates the file with header if it hasn't been created yet:
    try:
        os.stat('/sd/'+filename+'.csv')
    except OSError:
        with open ('/sd/'+filename+'.csv', 'w') as file:
            file.write('Date,Time,Latitude,Longitude,Altitude (Mts.),Speed (Knots),Fix Quality,# Satellites\r\n')

    with open ('/sd/'+filename+'.csv', 'a') as file:
        file.write('{}-{}-{},{:02}:{:02}:{:02},{:.6f},{:.6f},{},{},{},{}\r\n'.format(
            gps.timestamp_utc.tm_year,
            gps.timestamp_utc.tm_mon,
            gps.timestamp_utc.tm_mday,
            gps.timestamp_utc.tm_hour,  
            gps.timestamp_utc.tm_min,
            gps.timestamp_utc.tm_sec,
            gps.latitude,
            gps.longitude,
            altitude,
            speed,
            gps.fix_quality,
            satellites))

    return

# Mounting SD Card:
try:
    sdcard = adafruit_sdcard.SDCard(spi, cs)
except OSError:
    print('No SD card detected. Turn off, insert one and turn back on.')
    oled_1stline = ''
    oled_2ndline = 'No SD Card detected.'
    oled_3rdline = 'Off > Insert > On'
    oled_update()
    sys.exit()

vfs = storage.VfsFat(sdcard)
storage.mount(vfs, '/sd')

# Initial oled update.
oled_update()

# Main loop runs forever printing the location, etc. every second.
last_time = time.monotonic()
while True:
    # Make sure to call gps.update() every loop iteration and at least twice
    # as fast as data comes from the GPS unit (usually every second).
    # This returns a bool that's true if it parsed new data (you can ignore it
    # though if you don't care and instead look at the has_fix property).
    gps.update()


    # Updates data on oled screen, terminal and - potentially - SD Card
    # per UPDATE_INTERVAL. 
    current_time = time.monotonic()
    if current_time - last_time >= UPDATE_INTERVAL:
        last_time = current_time

        # Updates oled screen
        oled_update()
    
        
        if not gps.has_fix:
            # Try again if we don't have a fix yet.
            print('Waiting for fix...')
            print('Battery voltage: {} v.'.format(batt_charge('v')))
            oled_3rdline = 'Waiting for fix...'
            continue
        
        # We have a fix! (gps.has_fix is true)
        # Print out details about the fix like location, date, etc.
        print('=' * 40)  # Print a separator line.
        print('Fix timestamp: {}/{}/{} {:02}:{:02}:{:02}'.format(
            gps.timestamp_utc.tm_mon,   # Grab parts of the time from the
            gps.timestamp_utc.tm_mday,  # struct_time object that holds
            gps.timestamp_utc.tm_year,  # the fix time.  Note you might
            gps.timestamp_utc.tm_hour,  # not get all data like year, day,
            gps.timestamp_utc.tm_min,   # month!
            gps.timestamp_utc.tm_sec))
        print('Latitude: {} degrees'.format(gps.latitude))
        print('Longitude: {} degrees'.format(gps.longitude))
        oled_2ndline = '{},{}'.format(gps.latitude, gps.longitude)
        print('Fix quality: {}'.format(gps.fix_quality))
        oled_1stline = 'Q:{} Sat:..'.format(gps.fix_quality)
        
        # Some attributes beyond latitude, longitude and timestamp are optional
        # and might not be present.  Check if they're None before trying to use!
        if gps.satellites is not None:
            print('# satellites: {}'.format(gps.satellites))
            oled_1stline = 'Q:{} Sat:{}'.format(gps.fix_quality, gps.satellites)
       
        if gps.altitude_m is not None:
            print('Altitude: {} meters'.format(gps.altitude_m))
            oled_3rdline = 'Alt:{} mts.'.format(gps.altitude_m)
        else:
            oled_3rdline = 'Alt:...'

        if gps.track_angle_deg is not None:
            print('Speed: {} knots'.format(gps.speed_knots))
        if gps.track_angle_deg is not None:
            print('Track angle: {} degrees'.format(gps.track_angle_deg))
        if gps.horizontal_dilution is not None:
            print('Horizontal dilution: {}'.format(gps.horizontal_dilution))
        if gps.height_geoid is not None:
            print('Height geo ID: {} meters'.format(gps.height_geoid))

        print('Battery voltage: {} v.'.format(batt_charge('v')))
            
        # Writes to SD Card only if difference between the last GPS reading 
        # (latitude or longitude) and the current GPS reading is larger than 
        # a predefined value.
        current_gps = (gps.latitude, gps.longitude)
        if abs(current_gps[0] - last_gps[0]) >= GPS_DIFF or abs(current_gps[1] - last_gps[1]) >= GPS_DIFF:
            last_gps = current_gps

            filename = 'GPS_Data_{}-{}-{}'.format(
                gps.timestamp_utc.tm_year, 
                gps.timestamp_utc.tm_mon,
                gps.timestamp_utc.tm_mday)
            write_to_csv()
            