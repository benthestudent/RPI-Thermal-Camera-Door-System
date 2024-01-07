# Raspberry Pi Thermal Camera Doorman

The following software is designed to run on a Raspberry Pi with an Adafruit AMG8833 IR Thermal Camera and a
Raspberry Pi camera. Intended to be installed at the entrance to a building, the system measures the temperature of 
people entering and captures images of people with a temperature above a certain threshold value. The system is 
designed to decrease the spread of diseases such as COVID-19 by integrating with additional 
AWS components (Lambda, Rekognition, and S3) and sending alerts via Slack if people are detected with a fever. 

This repository does not contain the Slack alert and AWS Lambda and Rekognition components of the project, 
only the onboard software for the Raspberry Pi that reads input from both the camera and thermal camera and displays
a video feed and a thermal color map on a GUI.

The software reads thermal input, and if it detects a temperature above a customizable threshold (32 degrees celsius
by default) then it captures an image from the normal camera and uploads it to a AWS S3 bucket.

The software is ran by running "python main.py"
