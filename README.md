# ClimateControlSystem
Climate control system is base on CO2 and temperature sensors ( MT8057S ). Thinkspeak cloud is been using for analyzing. 

## Using Python script

1. Copy file 'thingspeak_raspi-co2.py' to home directory (e.g. /home/pi/)
1. Edit file 'thingspeak_raspi-co2.py' and write correct own key in variable 'THINGSPEAKKEY'
1. Write correct path to file for data storing in variable 'LOGFILE'
1. Start script:

```
sudo python thingspeak_raspi-co2.py
```

## Using Python script as Linux daemon (Raspberry Pi)

1. Copy file 'thingspeak_raspi-co2.py' to home directory (e.g. /home/pi/)
1. Edit file 'thingspeak_raspi-co2.py' and write correct own key in variable 'THINGSPEAKKEY'
1. Write correct path to file for data storing in variable 'LOGFILE'
1. Append following line (with correct paths) to file '/etc/rc.local' and reboot system.

```
sudo python /home/pi/thingspeak_raspi-co2.py  > /home/pi/templogger.log 2>&1
```
