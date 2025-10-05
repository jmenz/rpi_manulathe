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
cp ~/linuxcnc/configs/orange-pi-lathe/additional_files/.xsessionrc ~/.xsessionrc
```
NOTE: do this only if you don't have ~/.xsessionrc file yet, Otherwise, copy the commands.

It's a prepared file for 1024x600 display. If You need some other resolution, follow this [instruction](https://askubuntu.com/questions/377937/how-do-i-set-a-custom-resolution)


### Autoload (optional)

Add the next command to autoload (Application->Settings->Session and Startup->Application Autostart):
```
/usr/bin/linuxcnc '~/linuxcnc/configs/orange-pi-lathe/config.ini'
```

not sure:
sudo apt install libgpiod-dev


### To enable pin for power latch 
nano /boot/broadcom/config.txt
add

```
toverlay=gpio-hog,gpio=21,output=1
```
