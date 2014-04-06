__author__ = 'tigarner'
__email__ = 'tigarner@cisco.com'
import time
import re
import logging
import RPi.GPIO as GPIO
import urwid

logging.basicConfig(filename="/home/pi/brew-temps.log", level=logging.INFO)
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
        temperature /= 1000
        return temperature


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


def main():
    temperature_sensor = TemperatureSensor(device="/sys/bus/w1/devices/28-0000055d0eac/w1_slave")
    led_array = LEDArray()

    try:
        while True:
            temperature = temperature_sensor.get_current_temp()
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
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Logging finished")
        GPIO.cleanup()


if __name__ == '__main__':
    main()
