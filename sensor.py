import argparse
import boto3
import datetime
import json
import math
import numpy as np
import os
import pygame
import time
import traceback
import time
import busio
import board
import requests
import adafruit_amg88xx
from scipy.interpolate import griddata
from colour import Color
from colormap import colormap




def save_json(json_path, data=None):
    if data == None:
        data = {"filename": "", "temperature": 0, "uploaded": False}
    with open(json_path, "w") as f:
        json.dump(data, f)
    f.close()
    print(json.dumps(data))


# some utility functions
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))


def map_value(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def get_color(v):
    i = min(255, max(0, int(v)))
    return (
        colormap[i * 3],
        colormap[i * 3 + 1],
        colormap[i * 3 + 2],
    )

# this is the main function of the sensor process. It contains a loop that reads sensor data
# and if it detects a temperature above a defined trigger amount, it pushes its data to a queue, which
# triggers the camera process to capture a photo.
def startSensing(queue, args, s3):
    # low range of the sensor (this will be blue on the screen)
    MINTEMP = args.min

    # high range of the sensor (this will be red on the screen)
    MAXTEMP = args.max

    FRAME_RATE = 15

    width = 8
    height = 8

    pixel_width = 10
    pixel_height = 10

    screen_width = int(width * pixel_width * 4)
    screen_height = int(height * pixel_height * 4)

    print(screen_width, screen_height)
    print(args.min, args.max)
    print('Press "Esc", "q" or "Q" to exit.')

    points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0, 64)]
    grid_x, grid_y = np.mgrid[0:7:32j, 0:7:32j]

    # i2c_bus
    i2c_bus = busio.I2C(board.SCL, board.SDA)

    # initialize the sensor
    sensor = adafruit_amg88xx.AMG88XX(i2c_bus)

    # let the sensor initialize
    time.sleep(0.1)

    # pygame
    pygame.init()

    clock = pygame.time.Clock()

    screen = pygame.display.set_mode((screen_width, screen_height))

    screen.fill((0, 0, 0))
    # initialize pygame GUI
    pygame.display.update()

    # run input loop
    run = True
    while run:
        capture = False

        # if the user wants to quit, stop reading new input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
            run = False
        elif keys[pygame.K_c]:
            capture = True

        if run == False:
            break

        # read the pixels
        pixels = []
        for row in sensor.pixels:
            pixels = pixels + row
        # get min and max temperatures of input
        min_temp = min(pixels)
        max_temp = max(pixels)

        pixels = [map_value(p, MINTEMP, MAXTEMP, 0, 255) for p in pixels]

        # perform interpolation
        bicubic = griddata(points, pixels, (grid_x, grid_y), method="cubic")

        # draw colormap of temperature readings on GUI
        for ix, row in enumerate(bicubic):
            for jx, pixel in enumerate(row):
                color = get_color(pixel)
                pygame.draw.rect(
                    screen,
                    color,
                    (
                        # left, top, width, height
                        pixel_width * ix,
                        pixel_height * jx,
                        pixel_width,
                        pixel_height,
                    ),
                )

        print("{:2.1f} {:2.1f}".format(min_temp, max_temp))

        # if the sensor detects a temperature above the max temperature, trigger the camera
        if max_temp > MAXTEMP or capture:
            # record filename information of timestamp and temperature information
            filename = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
            data = {"filename": filename, "temperature": max_temp, "uploaded": False}
            data = {
                "status": data
            }
            # push data to queue to trigger camera
            queue.put(data)

            # wait 10 seconds to allow person to move out of the way to avoid capturing multiple images
            # of the same person
            time.sleep(10)  
        pygame.display.update()
        clock.tick(FRAME_RATE)

    pygame.quit()
