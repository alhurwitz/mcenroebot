import time

import cv2
import numpy as np
from adafruit_servokit import ServoKit

# Servo setup
kit = ServoKit(channels=16)
pan_angle = 90
tilt_angle = 90
kit.servo[0].angle = pan_angle
kit.servo[1].angle = tilt_angle

# Camera setup
cap = cv2.VideoCapture(0)
frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
center_x = frame_w // 2
center_y = frame_h // 2

# How aggressively the camera chases the ball (tune these)
pan_speed = 0.05
tilt_speed = 0.05

print(f"Frame size: {frame_w}x{frame_h}")
print("Tracking started. Ctrl+C to stop.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert to HSV for color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Orange ping pong ball color range
        lower_orange = np.array([5, 150, 150])
        upper_orange = np.array([25, 255, 255])
        mask = cv2.inRange(hsv, lower_orange, upper_orange)

        # Clean up the mask
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the largest contour
            c = max(contours, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)

            if radius > 10:  # Ignore tiny blobs
                # How far is the ball from center?
                error_x = x - center_x
                error_y = y - center_y

                # Move servos to chase the ball
                pan_angle -= error_x * pan_speed
                tilt_angle += error_y * tilt_speed

                # Clamp to safe range
                pan_angle = max(0, min(180, pan_angle))
                tilt_angle = max(0, min(180, tilt_angle))

                kit.servo[0].angle = pan_angle
                kit.servo[1].angle = tilt_angle

                print(f"Ball at ({int(x)}, {int(y)}) | Pan: {pan_angle:.1f} Tilt: {tilt_angle:.1f}")
            else:
                print("Ball too small / too far")
        else:
            print("No ball detected")

        time.sleep(0.05)

except KeyboardInterrupt:
    print("Stopping...")
finally:
    cap.release()
