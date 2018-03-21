import sys
import time
import threading
import usb.core
import usb.util
import datetime
import signal
import urllib            # URL functions
import urllib2           # URL functions
import configparser
import os
import Adafruit_DHT

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'thingspeak_config.ini'))
thingspeak_config = config['thingspeak.com']

debug = thingspeak_config.getboolean('debug', False) # Loging data sending to console
pause = int(thingspeak_config.get('pause', 30))      # Pause between data sending (seconds)

class mt8057(threading.Thread):
    """
    Class for MT8057 control
    """
    VID = 0x04d9
    PID = 0xa052
    RW_TIMEOUT = 0
    REQUEST_TYPE_SEND = usb.util.build_request_type(
        usb.util.CTRL_OUT,
        usb.util.CTRL_TYPE_CLASS,
        usb.util.CTRL_RECIPIENT_INTERFACE)
    REQ_HID_SET_REPORT = 0x09
    HID_REPORT_TYPE_FEATURE = 0x03 << 8

    magic_buf = [0xc4, 0xc6, 0xc0, 0x92, 0x40, 0x23, 0xdc, 0x96]
    ctmp = [0x84, 0x47, 0x56, 0xd6, 0x07, 0x93, 0x93, 0x56]

    def __init__(self):
        """
        MT8057 initialization
        """
        threading.Thread.__init__(self, name="mt")
        self._event_stop = threading.Event()
        self._lock = threading.Lock()
        self._temperature = None
        self._concentration = None
        self._had_driver = False
        self._dev = usb.core.find(idVendor=self.VID, idProduct=self.PID)

        if self._dev is None:
            raise ValueError("Device wasn't found.")

        if self._dev.is_kernel_driver_active(0):
            self._dev.detach_kernel_driver(0)
            self._had_driver = True

        self._dev.set_configuration()
        # print(self._dev)
        self._ep = self._dev[0][(0, 0)][0]

    def stop(self):
        """
        Stop data reading
        """
        self._event_stop.set()

    def run(self):
        """
        Loop data reading
        """
        self._dev.ctrl_transfer(
            self.REQUEST_TYPE_SEND,
            self.REQ_HID_SET_REPORT,
            self.HID_REPORT_TYPE_FEATURE,
            0x00, self.magic_buf,
            self.RW_TIMEOUT)
        self._event_stop.clear()
        while not self._event_stop.is_set():
            try:
                data = self._read()
                self._parse(data)
                # time.sleep(0.1)
            except BaseException as e:
                print('{} USB reading error: {}'.format(str(datetime.datetime.now()), str(e)))
            except:
                print('{} USB reading error.'.format(str(datetime.datetime.now())))
        self._release()

    def get_data(self):
        """
        Return last read data
        """
        self._lock.acquire()
        value = (self._concentration, self._temperature)
        self._lock.release()
        return value

    def _read(self):
        """
        Reading data from MT8057
        """
        return self._dev.read(self._ep, 8, self.RW_TIMEOUT)

    def _decode(self, data):
        """
        Decoding necessory bytes in packet
        """
        shuffle = [2, 4, 0, 7, 1, 6, 5, 3]
        phase1 = []
        phase2 = []
        phase3 = []
        result = []

        for i in range(8):
            phase1.append(data[shuffle[i]])
            phase2.append(phase1[i] ^ self.magic_buf[i])
        for i in range(8):
            phase3.append(((phase2[i] >> 3) | (phase2[(i - 1 + 8) % 8] << 5)) & 0xff)
            result.append((0x100 + phase3[i] - self.ctmp[i]) & 0xff)

        return result

    def _parse(self, data):
        """
        Packet parsing
        """
        item = self._decode(data)
        r0 = item[0]
        r1 = item[1]
        r2 = item[2]
        r3 = item[3]
        checksum = (r0 + r1 + r2) & 0xff
        if (checksum == r3 and item[4] == 0x0d):
            w = (r1 << 8) + r2
            if (r0 == 0x42):  # Ambient Temperature
                w = w * 0.0625 - 273.15
                self._lock.acquire()
                self._temperature = w
                self._lock.release()
            elif (r0 == 0x50):  # Relative Concentration of CO2
                self._lock.acquire()
                self._concentration = w
                self._lock.release()
            else:
                pass

    def _release(self):
        """
        Releasing MT8057
        """
        usb.util.release_interface(self._dev, 0)
        if self._had_driver:
            self._dev.attach_kernel_driver(0)

class HumiditySensor(threading.Thread):
    """
    Class for Humidity sensor control
    """
    def __init__(self):
        """
        Class initialization
        """
        sensors = {
            0: None,
            11: Adafruit_DHT.DHT11,
            22: Adafruit_DHT.DHT22,
            2302: Adafruit_DHT.AM2302
        }

        self._sensor = sensors[int(thingspeak_config.get('sensor', 0))] # Type of Humidity sensor
        self._gpio = int(thingspeak_config.get('gpio', 17))     # GPIO for Humidity sensor
        
        if self._sensor == None:
            raise ValueError("Device wasn't found.")

        threading.Thread.__init__(self, name="dht")
        self._event_stop = threading.Event()
        self._lock = threading.Lock()
        self._humidity = None
        self._temperature = None

    def stop(self):
        """
        Stop data reading
        """
        self._event_stop.set()

    def run(self):
        """
        Loop data reading
        """
        while not self._event_stop.is_set():
            try:
                humidity, temperature = Adafruit_DHT.read_retry(self._sensor, self._gpio)
                if humidity is not None and temperature is not None and humidity <= 100:
                    self._humidity = humidity
                    self._temperature = temperature
            except BaseException as e:
                print('{} Humidity reading error: {}'.format(str(datetime.datetime.now()), str(e)))
            except:
                print('{} Humidity reading error.'.format(str(datetime.datetime.now())))

    def get_data(self):
        """
        Return last read data
        """
        self._lock.acquire()
        value = (self._humidity, self._temperature)
        self._lock.release()
        return value

def sendData(co2, temp, humidity, temp2):
    """
    Send data to Cloud
    """

    THINGSPEAKKEY = thingspeak_config.get('key', '')
    THINGSPEAKURL = thingspeak_config.get('url', '')

    values = {'api_key' : THINGSPEAKKEY, 'field1' : co2, 'field2' : temp, 'field3' : humidity, 'field4' : temp2}

    postdata = urllib.urlencode(values)
    req = urllib2.Request(THINGSPEAKURL, postdata)

    if debug:
        log = time.strftime("%d-%m-%Y,%H:%M:%S") + ","
        log = log + "{:.1f}ppm".format(co2) + ","
        log = log + "{:.2f}C".format(temp) + ","
        log = log + "{:.1f}%".format(humidity) + ","
        log = log + "{:.2f}C".format(temp2) + ","
    else:
        log = ''

    try:
        # Send data to Thingspeak
        response = urllib2.urlopen(req, None, 5)
        html_string = response.read()
        response.close()
        if debug:
            log = log + 'Update {}'.format(html_string)

    except (SystemExit, KeyboardInterrupt):
        raise # System Exit or Keyboard Interrupt
    except urllib2.HTTPError, e:
        log = log + 'Server could not fulfill the request. Error code: {}'.format(str(e.code))
    except urllib2.URLError, e:
        log = log + 'Failed to reach server. Reason: {}'.format(str(e.reason))
    except BaseException as e:
        log = log + 'Unknown error: {}'.format(str(e))

    print(log)

if __name__ == "__main__":
    """
    Main daemon function
    """

    def signal_handler(signum, frame):
        print('{} Signal SIGTERM was received.'.format(str(datetime.datetime.now())))
        sys.exit(0)

    print('{} CO2 daemon started.'.format(str(datetime.datetime.now())))

    LOGFILE = thingspeak_config.get('log', 'logCO2_ts.txt')

    try:
        signal.signal(signal.SIGTERM, signal_handler)

        t_mt8057 = mt8057()
        t_mt8057.start()

        print('{} MT8057 was initialized.'.format(str(datetime.datetime.now())))
    
        t_dht = HumiditySensor()
        t_dht.start()

        print('{} Humidity Sensor was initialized.'.format(str(datetime.datetime.now())))

        while True: # Infinite loop for data sending
            try:
                time.sleep(pause)

                current_time = str(datetime.datetime.now());

                (valueCO2, valueTemp) = t_mt8057.get_data()    # Data reading
                (valueHumidity, valueTemp2) = t_dht.get_data() # Data reading
                if debug:
                    print(current_time, valueCO2, valueTemp, valueHumidity, valueTemp2)

                sendData(valueCO2, valueTemp, valueHumidity, valueTemp2) # Send data to Cloud

                flog = open(LOGFILE,'a',0)
                flog.write('{},{},{},{},{}\n'.format(current_time, valueCO2, valueTemp, valueHumidity, valueTemp2))
                flog.close()
            except SystemExit: # System Exit, leave loop
                break
            except KeyboardInterrupt:
                # Leave loop only when KeyboardInterrupt was caught
                print('{} KeyboardInterrupt was caught.'.format(str(datetime.datetime.now())))
                break
            except IOError as e: # File error, don't leave loop
                print('I/O error: {}'.format(e.strerror))
            except:
                print('{} Unknown error in loop.'.format(str(datetime.datetime.now()))) # Don't leave loop

        t_mt8057.stop()
        t_mt8057.join()

        t_dht.stop()
        t_dht.join()
    except BaseException as e:
        print('{} Unknown error: {}'.format(str(datetime.datetime.now()), str(e)))
    except:
        print('{} Unknown error.'.format(str(datetime.datetime.now())))

    print('{} CO2 daemon stopped.'.format(str(datetime.datetime.now())))

    sys.exit(0)
