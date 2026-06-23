import time

from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

# Pan servo (channel 0) - sweep left to right
print("Panning...")
for angle in range(0, 181, 10):
    kit.servo[0].angle = angle
    time.sleep(0.05)
for angle in range(180, -1, -10):
    kit.servo[0].angle = angle
    time.sleep(0.05)

# Tilt servo (channel 1) - sweep up and down
print("Tilting...")
for angle in range(0, 181, 10):
    kit.servo[1].angle = angle
    time.sleep(0.05)
for angle in range(180, -1, -10):
    kit.servo[1].angle = angle
    time.sleep(0.05)

print("Done!")
