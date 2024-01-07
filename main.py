# Imports
from multiprocessing import Process, Queue
import camera
import sensor
import argparse
import os
import boto3
import cv2
import json
import socket
import traceback
import datetime
from pathlib import Path
import requests
import psutil
import time

# Define and initialize important constants

#  Home directory
HOME = str(Path.home())

#Name of S3 bucket
BUCKET_NAME = os.environ.get("BUCKET_NAME", "rpi-thermal-camera")

# Name of JSON file to dump information. This is primarily used for debugging
JSON_PATH = os.environ.get("JSON_PATH", "{}/.doorman.json".format(HOME))

# low range of the sensor (this will be blue on the screen)
MINTEMP = 18.0
# high range of the sensor (this will be red on the screen)
MAXTEMP = 32.0

# initialize s3 client
s3 = boto3.client("s3")

# the function parse_args parses the command line arguments for customizable preferences.
# the user can specify the s3 bucket name, a different camera device ID, whether or not
# the display should be fullscreen, if the image should be mirrored, the height and width of the display,
# the min and max temepratures, and the json_path defined above
def parse_args():
    p = argparse.ArgumentParser(description="doorman")
    p.add_argument("-b", "--bucket-name", default=BUCKET_NAME, help="bucket name")
    p.add_argument("-c", "--camera-id", type=int, default=0, help="camera id")
    p.add_argument("-f", "--full-screen", action="store_true", help="full screen")
    p.add_argument("-m", "--mirror", action="store_true", help="mirror")
    p.add_argument("--width", type=int, default=0, help="width")
    p.add_argument("--height", type=int, default=0, help="height")
    p.add_argument("--min", type=float, default=MINTEMP, help="minT")
    p.add_argument("--max", type=float, default=MAXTEMP, help="maxT")
    p.add_argument("--json-path", default=JSON_PATH, help="json path")
    return p.parse_args()

def main():
    # Parse command line args to allow user to change default preferences
    args = parse_args()

    # Initialize status and data variables
    status = {}
    data = {
        'status': status
    }

    # Initialize queue for multiprocessing processes and put the data in it
    q = Queue()
    q.put(data)

    # Create two processes, one to read input from the camera and display it and another
    # to read the input from the sensor and use it to trigger an alert.
    cameraProcess = Process(name="camera", target=camera.startCamera, args=((q), args, s3,))
    sensorProcess = Process(name="sensor", target=sensor.startSensing, args=((q), args, s3,))

    #start camera and sensor processes
    cameraProcess.start()
    sensorProcess.start()

    #wait for processes to finish
    cameraProcess.join()
    sensorProcess.join()

    #clean up queue
    q.close()
    q.join_thread()

# the internet() function checks to see if the device is connected to the internet.
def internet(host="8.8.8.8", port=53, timeout=1):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
    return False


if __name__ == '__main__':
    print("Connecting to Internet")
    # Because this program is designed to run on boot, it may need to wait for the device to
    # finish connecting to the internet. Thus, we have a 7 second timer to pause the program until
    # it finishes connecting.
    time.sleep(7)

    # Check to see if we have connected to the internet and alert the user if we still havent
    while not internet():
        print("You are not connected to the Internet")
        print("Please Use Raspberry Pi WiFi Utility (in the far-right corner) to Connect to the Internet")
        next = input("Press Enter When You Have Connected")

    # Assume the user did it correctly.
    print("Connected to the Internet")

    # start the program
    main()
