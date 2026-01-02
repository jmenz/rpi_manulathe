# Linuxcnc lathe controller

#Disclaimer:
This is my personal hobby project. You can use it or any of its parts at your own risk. I'm not responsible for any damage to your equipment or your injury.

### Autologin:
```
sudo nano /etc/lightdm/lightdm.conf
```
In the  ```[Seat:*]``` section
Find, uncomment, and fill with values the next lines:
```
autologin-user=cnc
autologin-user-timeout=0
autologin-session=xfce
```

### Install custom dark theme
```
cd ~/linuxcnc/configs/orange-pi-lathe
sudo sh ./install-theme.sh
```

### Add custom display resolution (optional)
```
cp additional_files/.xsessionrc ~/.xsessionrc
```
NOTE: do this only if you don't have ~/.xsessionrc file yet, Otherwise, copy the commands.

It's a prepared file for 1024x600 display. If You need some other resolution, follow this [instruction](https://askubuntu.com/questions/377937/how-do-i-set-a-custom-resolution)


### Autoload (optional)

Add the next command to autoload (Application->Settings->Session and Startup->Application Autostart):
```
/usr/bin/linuxcnc '~/linuxcnc/configs/rpi_manulathe/config.ini'
```

not sure:
sudo apt install libgpiod-dev


### To enable pin for power latch 
sudo nano /boot/broadcom/config.txt
add

```
dtoverlay=gpio-hog,gpio=21,output=1
```
Check if usb_max_current_enable has value 1

### Mesa connection:

Setup the static IP:
in the terminal run
``` sudo menu-config ```
Select Networking->Edit interface
the eth0 section should look like this:
```
# Ethernet
allow-hotplug eth0
#iface eth0 inet dhcp
iface eth0 inet static
        address 192.168.1.10
        netmask 255.255.255.0
        #gateway 10.0.0.1
        #dns-nameservers 8.8.8.8 8.8.4.4
```

Test connection:
ping 192.168.1.121

Test mesa card:
mesaflash --device=7i92t --addr 192.168.1.121 --readhmid

To update FPGA firmware:
mesaflash --device 7I92T --addr 192.168.1.121 --write 7i92t_7I85S_1PWMBR.bin
mesaflash --device 7I92T --addr 192.168.1.121 --reload

# test display
# set touchscreen to output
```
xinput list
xinput map-to-output "ke.dei USB2IIC_CTP_CONTROL" HDMI-2
```

# fix pyngcgui reread button:
sudo cp ./additional_files/pyngcgui.py /usr/lib/python3/dist-packages/pyngcgui.py


# fix touchscreen driver

```
sudo nano /etc/X11/xorg.conf.d/99-touchscreen-evdev.conf
```

```
# 1. Explicitly tell libinput to IGNORE touchscreens
Section "InputClass"
        Identifier "libinput touchscreen ignore"
        MatchIsTouchscreen "on"
        MatchDevicePath "/dev/input/event*"
        Driver "libinput"
        Option "Ignore" "on"
EndSection

# 2. Force evdev to handle them
Section "InputClass"
        Identifier "calibration"
        MatchIsTouchscreen "on"
        MatchDevicePath "/dev/input/event*"
        Driver "evdev"
        # Emulate a mouse click immediately on touch
        Option "EmulateThirdButton" "1"
        Option "EmulateThirdButtonTimeout" "750"
        Option "EmulateThirdButtonMoveThreshold" "30"
EndSection
```

