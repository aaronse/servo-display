# *****************************************************************************
#   "Multiverse's Lowest LO-FI Wood Pixel Display-Arduino Art" (Version 2.0)
#   - 2min WTD 2.0 teaser... https://www.youtube.com/watch?v=Xzip1Ln_CbA
#
#   This code was written to power the WTD 2.0 (Wood Tile Display) project 
#   created after participating in Mark Rober's 
#   https://monthly.com/mark-rober-engineering course.

#   Consider buying drivers and other hardware goodies from the Adafruit 
#   shop @ http://www.adafruit.com/products/815
  
#   Adafruit invests time and resources providing this open source code, 
#   please support Adafruit and open-source hardware by purchasing 
#   products from Adafruit!

    # - TODO:P1:Implement per Servo trim adjustment, ideally automated.  Current workaround is to 
    #       simply tweak the velcro'd tiles by hand. 


# *****************************************************************************
from adafruit_servokit import PCA9685   # https://docs.circuitpython.org/projects/pca9685/en/latest/
from adafruit_servokit import ServoKit  # https://docs.circuitpython.org/projects/servokit/en/latest/
from array import array
from configuration import Configuration
from datetime import datetime, timedelta
from flask import (Flask, request, jsonify) # https://flask.palletsprojects.com/en/2.0.x/
from PIL import Image                       # https://pillow.readthedocs.io/en/stable/
from tetris import TetrisGame, InputEvent
from threading import Thread
from time import sleep
from werkzeug.serving import make_server
import argparse
import curses
import json
import math
import neopixel                             # https://github.com/adafruit/Adafruit_CircuitPython_NeoPixel , https://github.com/adafruit/Adafruit_CircuitPython_PixelBuf 
import os
import os
import queue
import RPi.GPIO as GPIO
import select
import sys
import sys
import termios
import threading
import time
import traceback
import tty
from logger import Logger


# Minimum and Maximum rotation angle allowed for any given Servo.  
# - MUST be less than what causes "Stalling" that increases current 
MIN_ANGLE = 5
MAX_ANGLE = 55

ENABLE_PIN = 4

WEB_SERVER_PORT = 4000
webServer = None

_isGameRunning = True

# Current display mode.
mode = None

config = Configuration.load()

canvasWidth = config["width"]
canvasHeight = config["height"]


# To check whether connected, and address...  sudo i2cdetect -y 1
# _pwmDriver = ServoKit(channels=16) #, frequency=50, address=0x40, reference_clock_speed=27000000)
_pwmDrivers = []

_testDriver = 0
_pwmBadDrivers = []
#_pwmBadDrivers = [  1,2,  4,5,6,7,8,9,10,11]

_lastKeyPress = None
_logDebug = False

# TODO:P1:PERF/ENERGY Investigate hardware/wiring/sorftware changes for reliable Enable/Disable of PCA9685 drivers.
# Implemented auto disabling "Enable" Pin when display is inactive.  Goal was to reduce power/noise 
# and extend Servo life.  Unfortunately was observing 'glitches' and tiles unexpectedly moving when
# enable pin is powered down.  Cause of power down 'glitches' is unknown, not sure whether this is
# an artifact of servos being powered down, and/or PCA9685 enable pin changes, and/or how all the
# enable pin wires are connected to a single Raspberry Pi pin, without any capacitors/resistors/anything
# to isolate/smooth noise.
_enablePowerSaver = False


for i in range(12):
    if i in _pwmBadDrivers:
      newDriver = None
      print(f"NOT init ServoKit {i}")
    else:
      newDriver = ServoKit(channels = 16, address = 0x40 + i, frequency = 50)
      print(f"Init ServoKit {i}")

    _pwmDrivers.append(newDriver)

# Constants...
SERVO_MOUTH_INDEX = 15
SERVO_MOUTH_DEFAULT_ANGLE = 0
SERVO_MOUTH_DEFAULT_OPEN_ANGLE = 10
SERVO_MOUTH_CHATTER_WAIT_SECS = 0.05
SERVO_COUNT = 4


# Update Servos based on current timestamp position within currently playing motion sequence
def setPixelByIndex(pixelIndex, lum):
    global _pwmDriver

    angle = convertLumToAngle(lum)

    # Map pixelIndex to servoIndex
    driverIndex = int(pixelIndex / 16)
    servoIndex = pixelIndex % 16
    driver = _pwmDrivers[driverIndex]
    if not driver is None:
      driver.servo[servoIndex].angle = angle

def setPixel(x, y, lum):
    global _pwmDriver

    angle = convertLumToAngle(lum)

    tileX = math.floor(x / 4)
    tileY = math.floor(y / 4)
    driverIndex = (tileY * math.floor(canvasWidth / 4)) + tileX

    offsetX = x - (tileX * 4)
    offsetY = y - (tileY * 4)
    servoIndex = 4 * offsetX + offsetY

 ###   print(f"setPixel(x: {x}, y: {y} => driverIndex: {driverIndex}, servoIndex: {servoIndex} )")

    #print(f"setPixel(x: {x}, y: {y} => driverIndex: {driverIndex}, servoIndex: {servoIndex} )")
#    pixelIndex = (y * canvasWidth) + x  
#    for i in range(SERVO_COUNT):
            # print("_pwmDriver.servo[{0}].angle = {1}".format(i, frame[i]))
    # Map pixelIndex to servoIndex
    # driverIndex = int(pixelIndex / 16)
    #servoIndex = pixelIndex % 16
    driver = _pwmDrivers[driverIndex]
    if not driver is None:
      driver.servo[servoIndex].angle = angle #frame[i]


def fill(lum):

    angle = convertLumToAngle(lum)

    # KILLS DRIVERS... for i in range(canvasWidth * canvasHeight):
    for i in range(2):
    #for i in range(_testDriver * 16, (_testDriver + 1) * 16 ):
        driverIndex = int(i / 16)
        servoIndex = i % 16
        driver = _pwmDrivers[driverIndex]
        if not driver is None:
          print(f"fill driverIndex: {driverIndex}, servoIndex: {servoIndex}")
          driver.servo[servoIndex].angle = angle #frame[i]


def fillTile(driverIndex, lum):
    angle = convertLumToAngle(lum)
    for i in range(16):
        servoIndex = i
        driver = _pwmDrivers[driverIndex]
        if not driver is None:
          print(f"fill driverIndex: {driverIndex}, servoIndex: {servoIndex}")
          driver.servo[servoIndex].angle = angle


# Convert Luminosity to rotation angle.
def convertLumToAngle(lum):
  angle = ((1.0 - bound(lum, 0, 1.0)) * (MAX_ANGLE - MIN_ANGLE)) + MIN_ANGLE
  return angle


def bound(value, low, high):
  return max(low, min(high, value))


def get_cursor_chars_up(n):
    return f"\r\033[{n}A"

def get_cursor_chars_right(n):
    return f"\r\033[{n}C"


def cursor_up(n):
    print(f"\r\033[{n}A", end="")

def cursor_right(n):
    print(f"\r\033[{n}C", end="")

def cursor_left(n):
    print(f"\r\033[{n}D", end="")


def listen_for_key_press():
    global _isGameRunning, _lastKeyPress, _logDebug

    while _isGameRunning:
        # Use select to wait for input to be available on stdin
        readable, _, _ = select.select([sys.stdin], [], [], 0.1)
        if readable:
            #key_press = sys.stdin.readline().rstrip('\n')
            key_press = sys.stdin.read(1)
            
            # Process the key press here (for example, print it)
            #print(f"Key pressed: {key_press}\n")
            if key_press == 'q':
                _isGameRunning = False

            elif key_press == '\x1b':  # ESC
                next1 = sys.stdin.read(1)
                next2 = sys.stdin.read(1)
                key_press = None
                if next1 == '[':
                    if next2 == 'A':
                        key_press = "UP"
                    elif next2 == 'B':
                        key_press = "DOWN"
                    elif next2 == 'C':
                        key_press = "RIGHT"
                    elif next2 == 'D':
                        key_press = "LEFT"
                    # Delete key (typically sends \x1b[3~)
                    elif next2 == '3':
                        next3 = sys.stdin.read(1)
                        if next3 == '~':
                            key_press = "DELETE"
                else:
                    # Handle ESC key alone
                    key_press = "ESCAPE"

                _lastKeyPress = key_press
            else: 
                _lastKeyPress = key_press


def game_loop():
    global _isGameRunning, _lastKeyPress, _logDebug
   
    tick_count = 0
    isPaused = False

    logger = Logger()
    game = TetrisGame(logger, canvasWidth, canvasHeight)

    prevBuffer = array("i", [-1] * canvasWidth * canvasHeight)
    lastChangeTime = datetime.min
    isEnabled = True
    while _isGameRunning:
        loopStart = datetime.now()

        # Process key press(es)
        key_press = _lastKeyPress
        if not key_press is None:

            if key_press == 'v':
                _logDebug = not _logDebug
            elif key_press == 'p':
                isPaused = not isPaused
            else:
                game.process_key_press(key_press)

            _lastKeyPress = None

        # Advance game mechanics
        if not isPaused:
            tick_count += 1
            game.game_tick()

        # Draw game
        buffer = game.get_display_buffer()
        debugOutput = []
        hasChanges = 0
        for y in range(canvasHeight):
            for x in range(canvasWidth):
                pixelColor = buffer[y * canvasWidth + x]
                prevPixelColor = prevBuffer[y * canvasWidth + x]
                
                # Only consume time/IO writing pixels that changed
                if (pixelColor != prevPixelColor):

                    # Ensure drivers enabled
                    if _enablePowerSaver and not isEnabled:
                        isEnabled = True
                        GPIO.output(ENABLE_PIN, GPIO.LOW)

                    setPixel(x, y, pixelColor)
                    hasChanges += 1

                if _logDebug:
                    debugOutput.append(str(pixelColor))
            if _logDebug:
                debugOutput.append("\r\n")
        prevBuffer = buffer
        if hasChanges:
            lastChangeTime = datetime.now()

        # Check if can power down, save energe/noise/servo-life if display has been idle for a while
        if _enablePowerSaver and (datetime.now() - lastChangeTime).total_seconds() > 0.5:
            isEnabled = False
            GPIO.output(ENABLE_PIN, GPIO.HIGH)

        # Visually log display state
        if _logDebug:
            logLineCount = logger.get_lines_printed()

            if logLineCount > 0 or hasChanges:
                terminalRes = os.get_terminal_size()
                up_chars = get_cursor_chars_up(canvasHeight + 1)  if tick_count > 0 else ""
                indent_chars_len = terminalRes.columns - canvasWidth - 1
                indent_chars = get_cursor_chars_right(indent_chars_len)
                
                # Wipe out (overwrite with blank spaces) game display characters that have scrolled
                # up due to recent debug logging statements.
                wipe_up_chars = ""
                if (logLineCount > 0):
                    wipe_up_chars = get_cursor_chars_up(logLineCount)
                    for i in range(logLineCount):
                        wipe_up_chars += indent_chars + (" " * canvasWidth) + "\n"

                print(up_chars + wipe_up_chars + indent_chars + "".join(debugOutput)
                    .replace("1", u"\u2588")
                    .replace("0", " ")
                    .replace("\n", indent_chars + "\n")
                    + "\r")

        # Game loop delay for smooth game play...
        loopDurMs = (datetime.now() - loopStart).total_seconds() * 1000
        frameRate = 6
        frameIntervalMs = 1000 / frameRate
        if (loopDurMs + 25 < frameIntervalMs):
            sleep((frameIntervalMs - loopDurMs) / 1000)

parser = argparse.ArgumentParser(add_help=False)
# # try:
# # except KeyboardInterrupt:
# print('\nDone')
# #     parser.exit(0)
# # except Exception as e:
# #     parser.exit(type(e).__name__ + ': ' + str(e))


try:
    print('Started... ')

    GPIO.setup(ENABLE_PIN, GPIO.OUT)
    GPIO.output(ENABLE_PIN, GPIO.LOW)

    # Set stdin to non-blocking mode
    sys.stdin.flush()
    stdin_fileno = sys.stdin.fileno()
    old_stdin_settings = termios.tcgetattr(stdin_fileno)
    tty.setraw(sys.stdin.fileno())

    # Start the key listener in a separate thread
    listener_thread = threading.Thread(target=listen_for_key_press)
    listener_thread.start()

    try:
        game_loop()

    finally:
        # Clean up: restore stdin settings and wait for listener thread to finish
        termios.tcsetattr(stdin_fileno, termios.TCSADRAIN, old_stdin_settings)
        listener_thread.join()

    GPIO.output(ENABLE_PIN, GPIO.HIGH)



except KeyboardInterrupt:
    GPIO.output(ENABLE_PIN, GPIO.HIGH)
    print('\nExiting...')
    parser.exit(0)
except Exception as e:
    GPIO.output(ENABLE_PIN, GPIO.HIGH)
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    traceback.print_exc()
    parser.exit("EXCEPTION " + type(e).__name__ + ': ' + str(e))
