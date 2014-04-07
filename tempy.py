import os
import sqlite3
from threading import Thread
import threading
import time
import thread
from concurrent.futures import ThreadPoolExecutor

import re
import logging

from flask import Flask, render_template


try:
    import RPi.GPIO as GPIO
except ImportError:
    from mock import Mock

    GPIO = Mock()

app = Flask(__name__)
filedir = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(filename=os.path.join(filedir, 'tempy.log'), level=logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)


class TemperatureSensor(object):
    def __init__(self, device):
        self.device = device

    def get_current_temp(self):
        with open(self.device) as tfile:
            text = tfile.read()
        temperature = float(re.search('t=(\d+)', text).group(1))
        return temperature / 1000


class LEDArray(object):
    def __init__(self):
        self.RED_LED = 17
        self.GREEN_LED = 18
        self.YELLOW_LED_1 = 23
        self.YELLOW_LED_2 = 25

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RED_LED, GPIO.OUT)
        GPIO.setup(self.GREEN_LED, GPIO.OUT)
        GPIO.setup(self.YELLOW_LED_1, GPIO.OUT)
        GPIO.setup(self.YELLOW_LED_2, GPIO.OUT)

    def blank(self):
        GPIO.output(self.GREEN_LED, GPIO.LOW)
        GPIO.output(self.RED_LED, GPIO.LOW)
        GPIO.output(self.YELLOW_LED_1, GPIO.LOW)
        GPIO.output(self.YELLOW_LED_2, GPIO.LOW)

    def red(self):
        GPIO.output(self.RED_LED, GPIO.HIGH)

    def green(self):
        GPIO.output(self.GREEN_LED, GPIO.HIGH)

    def yellow_led_1(self):
        GPIO.output(self.YELLOW_LED_1, GPIO.HIGH)

    def yellow_led_2(self):
        GPIO.output(self.YELLOW_LED_2, GPIO.HIGH)


@app.route('/')
def hello_world():
    now = int(time.time())
    hour = now - (60 * 60)
    twenty_four_hours = now - (60 * 60 * 24)
    one_week = now - (60 * 60 * 24 * 7)
    four_weeks = now - (60 * 60 * 24 * 7 * 4)

    with sqlite3.connect(os.path.join(filedir, 'temps.db')) as conn:
        c = conn.cursor()

        c.execute("""SELECT * FROM temps WHERE datetime >= ? GROUP BY
                strftime('%M', datetime, 'unixepoch') ORDER BY datetime ASC""", (hour,))
        rows = c.fetchall()
        results_hour = [{'x': row[0], 'y': row[1]} for row in rows]

        c.execute("""SELECT * FROM temps WHERE datetime >= ? GROUP BY
                datetime((strftime('%s', datetime, 'unixepoch') / 900) * 900, 'unixepoch') ORDER BY datetime ASC""",
                  (twenty_four_hours,))
        rows = c.fetchall()
        results_twenty_four_hours = [{'x': row[0], 'y': row[1]} for row in rows]

        c.execute("""SELECT * FROM temps WHERE datetime >= ? GROUP BY
                strftime('%H', datetime, 'unixepoch') ORDER BY datetime ASC""", (one_week,))
        rows = c.fetchall()
        results_one_week = [{'x': row[0], 'y': row[1]} for row in rows]

        c.execute("""SELECT * FROM temps WHERE datetime >= ? GROUP BY
                strftime('%H', datetime, 'unixepoch') ORDER BY datetime ASC""", (four_weeks, ))
        rows = c.fetchall()
        results_four_weeks = [{'x': row[0], 'y': row[1]} for row in rows]

        c.execute('SELECT * FROM temps ORDER BY datetime DESC LIMIT 1')
        temp = c.fetchone()[1]

    return render_template('index.html',
                           temp=temp,
                           results_hour=results_hour,
                           results_twenty_four_hours=results_twenty_four_hours,
                           results_one_week=results_one_week,
                           results_four_weeks=results_four_weeks)
def run():
    with threading.Lock() as lock:
        print "hello"
        logging.info('Starting temp polling loop')
        temperature_sensor = TemperatureSensor(device="/sys/bus/w1/devices/28-0000055d0eac/w1_slave")
        led_array = LEDArray()

        try:
            while True:
                try:
                    temperature = temperature_sensor.get_current_temp()
                except IOError:
                    logging.warning("Couldn't pull current temp")
                    temperature = 0
                with sqlite3.connect(os.path.join(filedir, 'temps.db')) as conn:
                    c = conn.cursor()

                    try:
                        c.execute('CREATE TABLE temps (datetime integer, temp real)')
                    except sqlite3.OperationalError:
                        pass

                    c.execute('INSERT INTO temps VALUES (?, ?)', (int(time.time()), temperature))

                    conn.commit()

                rounded_temp = int(temperature)
                if 23 > temperature < 18:
                    led_array.blank()
                    led_array.red()
                    if (14 <= rounded_temp <= 16) or (25 <= rounded_temp <= 27):
                        led_array.yellow_led_1()
                    if rounded_temp <= 13 or rounded_temp >= 28:
                        led_array.yellow_led_1()
                        led_array.yellow_led_2()
                    logging.warn("Temp at {}c -- outside stable band 18-23c".format(temperature))
                else:
                    led_array.blank()
                    led_array.green()
                    if 20 <= rounded_temp <= 21:
                        led_array.yellow_led_1()
                    if rounded_temp >= 22:
                        led_array.yellow_led_1()
                        led_array.yellow_led_2()
                    logging.info("Temp at {}c".format(temperature))
                time.sleep(30)
        except KeyboardInterrupt:
            logging.info("Logging finished")
            GPIO.cleanup()


if __name__ == '__main__':
    thread.start_new_thread(run, ())
    app.run(debug=False, host='0.0.0.0')

