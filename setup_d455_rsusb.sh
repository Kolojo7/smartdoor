#!/bin/bash
# RealSense D455 Setup Script for Raspberry Pi 5 (RSUSB Method)

echo "Step 1: Removing old installations..."
sudo dpkg -l | grep realsense | awk '{print $2}' | xargs sudo dpkg --purge
sudo rm -rf /usr/local/include/librealsense* /usr/local/lib/librealsense*

echo "Step 2: Cloning librealsense and setting up udev rules..."
cd ~
git clone https://github.com/IntelRealSense/librealsense.git
cd librealsense
sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

echo "Step 3: Building with RSUSB backend..."
mkdir build && cd build
cmake .. \
  -DBUILD_EXAMPLES=true \
  -DCMAKE_BUILD_TYPE=Release \
  -DFORCE_LIBUVC=true \
  -DFORCE_RSUSB_BACKEND=ON
make -j$(nproc)
sudo make install

echo "Step 4: Installing Python bindings..."
cd ~/librealsense/build
cmake .. \
  -DBUILD_PYTHON_BINDINGS=TRUE \
  -DPYTHON_EXECUTABLE=$(which python3)
make -j$(nproc)
sudo make install

echo "Step 5: Opening raspi-config for manual settings..."
echo "Please set the following manually in the raspi-config menu:"
echo "  - 3. Boot Options → B1 Desktop/CLI → B4 Desktop Autologin"
echo "  - 5. Interfacing Options → P3 VNC → Yes"
echo "  - 7. Advanced Options → A5 Resolution → DMT Mode 85 1280x720 60Hz 16:9"
echo "  - 7. Advanced Options → A8 GL Driver → G2 GL (Fake KMS)"
read -p "Press Enter to open raspi-config..."
sudo raspi-config

echo "Step 6: Rebooting system..."
sudo reboot
