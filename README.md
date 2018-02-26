# ClimateControlSystem
Climate control system is base on CO2 and temperature sensors ( MT8057S ). Thinkspeak cloud is been using for analyzing. 

## Using Python script

1. Copy files 'thingspeak_raspi-co2.py' and 'thingspeak_config.ini' to work directory (e.g. /home/pi/ClimateControlSystem)
1. Edit file 'thingspeak_config.ini' and write correct own key in variable 'key'
1. Write correct path to file for data storing in variable 'log'
1. Start script:

```
sudo python thingspeak_raspi-co2.py
```

## Using Python script as Linux daemon (Raspberry Pi)

1. Copy files 'thingspeak_raspi-co2.py' and 'thingspeak_config.ini' to work directory (e.g. /home/pi/ClimateControlSystem)
1. Edit file 'thingspeak_config.ini' and write correct own key in variable 'key'
1. Write correct path to file for data storing in variable 'log'
1. Append following line (with correct paths) to file '/etc/rc.local' and reboot system.

```
sudo python /home/pi/ClimateControlSystem/thingspeak_raspi-co2.py  >> /home/pi/ClimateControlSystem/daemon.log 2>&1
```
