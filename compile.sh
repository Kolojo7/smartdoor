#!/bin/bash
# Compile the Smart Door project
g++ -std=c++11 -o smartdoor *.cpp \
    -I/home/pi/librealsense/include \
    -I/usr/include/opencv4 \
    -I/usr/local/include \
    -L/home/pi/librealsense/build \
    -L/usr/lib \
    -L/usr/local/lib \
    -lrealsense2 \
    -lopencv_core \
    -lopencv_imgcodecs \
    -lopencv_highgui \
    -lopencv_imgproc \
    -laws-cpp-sdk-s3 \
    -laws-cpp-sdk-core \
    -lcurl \
    -lssl \
    -lcrypto \
    -lz

