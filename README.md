# ClimateControlSystem
Climate control system is base on CO2/temperature sensors (MT8057S) and humidity/temperature sensors (DHT11/DHT22/AM2302 https://github.com/adafruit/Adafruit_Python_DHT). Thinkspeak cloud is been using for analyzing. 

## Installation
sudo apt-get install
sudo apt-get update
sudo pip install pyusb

Clone git-repository to work directory (e.g. /home/pi/ClimateControlSystem)
1. Rename file 'thingspeak_config.ini.example' to 'thingspeak_config.ini'
1. Edit file 'thingspeak_config.ini':
   1. Write own Write API Key in variable 'key'
   1. Set correct type of Humidity sensor in variable 'sensor' (11 for DHT11, 22 for DHT22 or 2302 for AM2302)
   1. Write correct path to file for data storing in variable 'log' or comment for disable logging
   1. Set correct channel number in variable 'bulk_url' if you want to use cache and bulk-mode (https://www.mathworks.com/help/thingspeak/bulkwritejsondata.html)
   1. Set maximal bulk size in variable 'max_bulk_size' if it's necessary (number of messages is limited to 960 messages for users of free accounts and 14,400 messages for users of paid accounts)
   1. Set pause between data sending (seconds) in variable 'pause' if it's necessary (time interval between sequential bulk-update calls should be 15 seconds or more)

## Using Python script
### Using as script

Start script:

```
sudo python thingspeak_raspi-co2.py
```

### Using Python script as Linux daemon (Raspberry Pi)

Append following line (with correct paths) to file '/etc/rc.local' and reboot system.

```
sudo python /home/pi/ClimateControlSystem/Device/thingspeak_raspi-co2.py  >> /home/pi/ClimateControlSystem/daemon.log 2>&1
```
