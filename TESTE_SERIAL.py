import serial
import time

ser = serial.Serial(
    '/dev/ttyAMA0',
    115200,
    timeout=2
)

while True:

    print("FRENTE")

    ser.write(b'#ML+006\r')

    time.sleep(0.05)

    ser.write(b'#MR-006\r')

    time.sleep(3)

    print("STOP")

    ser.write(b'#ML+000\r')

    time.sleep(0.05)

    ser.write(b'#MR+000\r')

    time.sleep(3)