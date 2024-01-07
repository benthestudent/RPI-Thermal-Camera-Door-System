#!/usr/bin/env python3

import argparse
import boto3
import cv2
import datetime
import json
import os
import socket
import traceback

from pathlib import Path

# Initialize home directory, BUCKET_NAME, and JSON_PATH
HOME = str(Path.home())
BUCKET_NAME = os.environ.get("BUCKET_NAME", "thermal-camera.benphillips.site")
JSON_PATH = os.environ.get("JSON_PATH", "{}/.doorman.json".format(HOME))

# Setup the S3 client
s3 = boto3.client("s3")

# This function checks to see if the queue has been updated by the sensor process
# if the queue has been updated with a temperature, then this process will capture
# a picture and upload it to a s3 bucket
def triggered(queue):
    #check queue
    try:
        status = queue.get_nowait()['status']
    except Exception as ex:
        status = False
        #print("Error", ex)

    # if queue is not empty, return the status variable contents
    if status:
        return {
                "filename": status["filename"],
                "temperature": status["temperature"],
                "uploaded": status["uploaded"]
            }
    else:
            return False


def save_json(json_path=JSON_PATH, data=None):
    if data == None:
        data = {"filename": "", "temperature": 0, "uploaded": False}
    with open(json_path, "w") as f:
        json.dump(data, f)
    f.close()
    print(json.dumps(data))


# this function checks to see if the program is connected to the internet
def internet(host="8.8.8.8", port=53, timeout=1):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
    return False

# the capture function captures a frame from the camera, saves the image locally with its metadata,
# and uploads it to an s3 bucket
def capture(args, frame, temperature, s3, filename=""):
    # path refers to the directory in which images are stored
    path = "incoming"

    # meta is the directory that contains metadata for the images
    jsonPath = "meta"

    # if the path doesnt already exist, make it
    if os.path.isdir(path) == False:
        os.mkdir(path)

    # filename for images and metadata
    if filename == "":
        filename = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")

    key = "{}/{}.jpg".format(path, filename)
    jsonKey = "{}/{}.json".format(jsonPath, filename)
    try:
        # save to local
        cv2.imwrite(key, frame)

        # create a s3 file key
        _, jpg_data = cv2.imencode(".jpg", frame)
        data = {
            "temperature": temperature,
            "time": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }

        # upload the picture to s3 bucket
        if internet():
            res = s3.put_object(
                Bucket=args.bucket_name,
                Key=jsonKey,
                Body=json.dumps(data),
                ACL="public-read",
            )
            res = s3.put_object(
                Bucket=args.bucket_name,
                Key=key,
                Body=jpg_data.tostring(),
                ACL="public-read",
            )
    except Exception as ex:
        print("Error", ex)


# this is the main method of this process. It starts reading input from the camera,
# displays it, and captures/uploads an image to s3 if the sensor triggers it
def startCamera(queue, args, s3):
    # Get a reference to webcam #0 (the default one)
    cap = cv2.VideoCapture(args.camera_id)

    if args.width > 0 and args.height > 0:
        frame_w = args.width
        frame_h = args.height
    else:
        frame_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    print(frame_w, frame_h)
    print('Press "Esc", "q" or "Q" to exit.')

    # start capturing and displaying video
    while True:
        # Grab a single frame of video
        ret, frame = cap.read()

        # Invert left and right
        frame = cv2.flip(frame, 1)
        frame = cv2.flip(frame, 0)

        # upload if triggered by sensor
        data = triggered(queue)

        # if data has been sent from sensor, capture and upload image
        if data and data["filename"] != "" and data["uploaded"] == False:
            data["uploaded"] = True
            save_json(args.json_path, data) # log info to json file
            queue.put({"status": {}}) # update queue
            capture(args, frame, data["temperature"], s3, data["filename"]) #capture and upload image

        # mirror image if specified
        if args.mirror:
            # Invert left and right
            frame = cv2.flip(frame, 1)

        # Display the resulting image
        cv2.imshow("Video", frame)

        # Name window
        cv2.namedWindow("Video", cv2.WINDOW_NORMAL)

        if args.full_screen:
            cv2.setWindowProperty(
                "Video", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
            )

        # kill if q is pressed
        ch = cv2.waitKey(1)
        if ch == 27 or ch == ord("q") or ch == ord("Q"):
            break

    # Release handle to the webcam
    cap.release()
    cv2.destroyAllWindows()

