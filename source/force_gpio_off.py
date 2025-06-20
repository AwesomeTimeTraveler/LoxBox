import RPi.GPIO as GPIO
for pin in ( … all your pins …):
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)
GPIO.cleanup()
