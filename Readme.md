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



mesaflash --device=7i92t --addr 192.168.1.121 --readhmid
mesaflash --device 7I92T --addr 192.168.1.121 --write 7i92t_7I85S_1PWMBR.bin
mesaflash --device 7I92T --addr 192.168.1.121 --reload

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


