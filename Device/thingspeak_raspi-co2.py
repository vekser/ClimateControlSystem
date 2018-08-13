import sys, traceback
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
import json
import socket
import Adafruit_DHT
import sqlite3

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'thingspeak_config.ini'))
thingspeak_config = config['thingspeak.com']

debug = thingspeak_config.getboolean('debug', False) # Loging data sending to console
pause = int(thingspeak_config.get('pause', 30))      # Pause between data sending (seconds)

cache = None

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except (SystemExit, KeyboardInterrupt):
        raise # System Exit or Keyboard Interrupt
    except BaseException as e:
        print('{} Error: {}'.format(str(datetime.datetime.now()), str(e)))
        return ''

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
                raise SystemExit
            except:
                print('{} USB reading error.'.format(str(datetime.datetime.now())))
                raise SystemExit
        self._release()
        print('{} MT8057 was stopped.'.format(str(datetime.datetime.now())))

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
                raise SystemExit
            except:
                print('{} Humidity reading error.'.format(str(datetime.datetime.now())))
                raise SystemExit
        print('{} Humidity sensor was stopped.'.format(str(datetime.datetime.now())))

    def get_data(self):
        """
        Return last read data
        """
        self._lock.acquire()
        value = (self._humidity, self._temperature)
        self._lock.release()
        return value

class Cache():
    """
    Class for cache
    """
    def __init__(self):
        """
        Class initialization
        """
        self._db = None
        self._cursor = None
        self._cache_data = []
        self._sent_id = set()
        self._limit = int(thingspeak_config.get('max_bulk_size', 960))
        if not self._limit or self._limit <= 0:
            self._limit = 960
        try:
            self._db = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'thingspeak_cache.sqlite')) # Sqlite DB initialization
            if self._db:
                self._cursor = self._db.cursor()
                self._cursor.execute('''CREATE TABLE IF NOT EXISTS cache(
                                    id INTEGER PRIMARY KEY NOT NULL,
                                    timestamp DATE,
                                    co2 REAL,
                                    temp REAL,
                                    humidity REAL,
                                    temp2 REAL)
                ''')
                self._db.commit()
                print('{} DB for cache was initialized.'.format(str(datetime.datetime.now())))
        except BaseException as e:
            print('{} DB error: {}'.format(str(datetime.datetime.now()), str(e)))

    def __del__(self):
        if self._db:
            self._db.close()

    def append(self, current_time, co2, temp, humidity, temp2):
        if self._cursor:
            try:
                self._cursor.execute(
                    '''INSERT OR REPLACE INTO cache(timestamp, co2, temp, humidity, temp2) 
                       VALUES(:timestamp, :co2, :temp, :humidity, :temp2)''',
                    {"timestamp": current_time, 'co2': co2, 'temp': temp, 'humidity': humidity, 'temp2': temp2}
                )
                self._db.commit()
            except BaseException as e:
                print('{} DB error: {}'.format(str(datetime.datetime.now()), str(e)))
        else:
            data = {"created_at" : current_time, 'field1' : co2, 'field2' : temp, 'field3' : humidity, 'field4' : temp2, 'status' : ''}
            if len(self._cache_data) >= self._limit:
                del self._cache_data[0]
            self._cache_data.append(data)

    def get_cache(self):
        if self._cursor:
            self._cache_data = []
            try:
                self._cursor.execute('SELECT * FROM cache ORDER BY datetime(timestamp) DESC LIMIT :limit', {"limit": self._limit})
                results = self._cursor.fetchall()
                if results:
                    for result in results:
                        data = {
                            "created_at": result[1],
                            'field1': result[2],
                            'field2': result[3],
                            'field3': result[4],
                            'field4' : result[5]
                        }
                        self._cache_data.append(data)
                        self._sent_id.add(result[0])
            except BaseException as e:
                print('{} DB error: {}'.format(str(datetime.datetime.now()), str(e)))
        return self._cache_data

    def clear_cache(self):
        if self._cache_data:
            if self._cursor:
                try:
                    if self._sent_id:
                        sql = 'DELETE FROM cache WHERE id IN ({})'.format(",".join(['?'] * len(self._sent_id)))
                        self._cursor.execute(sql, list(self._sent_id))
                        self._db.commit()
                        self._sent_id = set()
                except BaseException as e:
                    print('{} DB error: {}'.format(str(datetime.datetime.now()), str(e)))
            else:
                del self._cache_data[:]

def sendData(current_time, co2, temp, humidity, temp2):
    """
    Send data to Cloud
    """
    if not hasattr(sendData, "_send_error_cnt"):
        sendData._send_error_cnt = 0

    THINGSPEAKKEY = thingspeak_config.get('key', '')
    THINGSPEAKURL = thingspeak_config.get('url', '')
    THINGSPEAKBULKURL = thingspeak_config.get('bulk_url', '')

    if not THINGSPEAKKEY:
        print('{} Key for thingspeak.com not found.'.format(str(datetime.datetime.now())))
        sys.exit(0)

    if not co2 or not temp or not humidity or not temp2:
        print('{} Found None value, don\'t send.'.format(str(datetime.datetime.now())))
        return sendData._send_error_cnt

    req = None
    if THINGSPEAKBULKURL and cache:
        req = urllib2.Request(THINGSPEAKBULKURL)
        req.add_header('Content-Type', 'application/json')

        cache.append(current_time, co2, temp, humidity, temp2)
        cache_data = []

        ip = get_ip_address()
        if not ip:
            sendData._send_error_cnt += 1
            return sendData._send_error_cnt
        else:
            for data in cache.get_cache():
                data['status'] = ip
                cache_data.append(data)

        if not cache_data:
            return sendData._send_error_cnt

        values = {"write_api_key" : THINGSPEAKKEY, "updates" : cache_data}
        postdata = json.dumps(values)

    elif THINGSPEAKURL:
        values = {'api_key' : THINGSPEAKKEY, 'created_at' : current_time, 'field1' : co2, 'field2' : temp, 'field3' : humidity, 'field4' : temp2, 'status' : get_ip_address()}
        postdata = urllib.urlencode(values)

        req = urllib2.Request(THINGSPEAKURL)
    else:
        print('{} Correct url for thingspeak.com not found.'.format(str(datetime.datetime.now())))
        sys.exit(0)

    if debug:
        print('{} {}'.format(str(datetime.datetime.now()), postdata))

    try:
        # Send data to Thingspeak
        response = urllib2.urlopen(req, postdata, 5)
        html_string = response.read()
        response.close()
        if debug:
            print('{} Update: {}'.format(str(datetime.datetime.now()), html_string))
        if THINGSPEAKBULKURL and cache:
            cache.clear_cache()
        sendData._send_error_cnt = 0
    except (SystemExit, KeyboardInterrupt):
        raise # System Exit or Keyboard Interrupt
    except urllib2.HTTPError as e:
        sendData._send_error_cnt += 1
        print('{} Server could not fulfill the request. Error: {}'.format(str(datetime.datetime.now()), str(e)))
    except urllib2.URLError as e:
        sendData._send_error_cnt += 1
        print('{} Failed to reach server. Error: {}'.format(str(datetime.datetime.now()), str(e)))
    except BaseException as e:
        sendData._send_error_cnt += 1
        print('{} Unknown error: {}'.format(str(datetime.datetime.now()), str(e)))
    return sendData._send_error_cnt

if __name__ == "__main__":
    """
    Main daemon function
    """

    def signal_handler(signum, frame):
        print('{} Signal SIGTERM was received.'.format(str(datetime.datetime.now())))
        sys.exit(0)

    print('{} CO2 daemon started.'.format(str(datetime.datetime.now())))

    LOGFILE = thingspeak_config.get('log', '')
    ERROR_LIMIT = int(thingspeak_config.get('error_limit', 120)) # Limit of continuous data sending errors

    send_error_cnt = 0

    t_mt8057 = None
    t_dht = None
    try:
        signal.signal(signal.SIGTERM, signal_handler)

        t_mt8057 = mt8057()
        t_mt8057.start()

        print('{} MT8057 was initialized.'.format(str(datetime.datetime.now())))

        t_dht = HumiditySensor()
        t_dht.start()

        print('{} Humidity Sensor was initialized.'.format(str(datetime.datetime.now())))

        cache = Cache()
        print('{} Cache was initialized.'.format(str(datetime.datetime.now())))

        while True: # Infinite loop for data sending
            start_loop = time.time()
            try:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime());

                (valueCO2, valueTemp) = t_mt8057.get_data()    # Data reading
                (valueHumidity, valueTemp2) = t_dht.get_data() # Data reading
                if debug:
                    print("{} sendData({},{},{},{},{})".format(str(datetime.datetime.now()), current_time, valueCO2, valueTemp, valueHumidity, valueTemp2))

                send_error_cnt = sendData(current_time, valueCO2, valueTemp, valueHumidity, valueTemp2) # Send data to Cloud

                if LOGFILE:
                    flog = open(LOGFILE,'a',0)
                    flog.write('{},{},{},{},{}\n'.format(current_time, valueCO2, valueTemp, valueHumidity, valueTemp2))
                    flog.close()
                    
                if send_error_cnt >= ERROR_LIMIT:
                    break
            except SystemExit: # System Exit, leave loop
                break
            except KeyboardInterrupt:
                # Leave loop only when KeyboardInterrupt was caught
                print('{} KeyboardInterrupt was caught.'.format(str(datetime.datetime.now())))
                break
            except IOError as e: # File error, don't leave loop
                print('{} I/O error: {}'.format(str(datetime.datetime.now()), str(e)))
            except:
                print('{} Unknown error in loop.'.format(str(datetime.datetime.now()))) # Don't leave loop
                traceback.print_exc()
            end_loop = time.time()
            loop_duration = end_loop - start_loop
            if loop_duration < pause:
                time.sleep(pause - (end_loop - start_loop))

    except KeyboardInterrupt:
        print('{} KeyboardInterrupt was caught.'.format(str(datetime.datetime.now())))
    except SystemExit: # System Exit
        pass
    except BaseException as e:
        print('{} Unknown error: {}'.format(str(datetime.datetime.now()), str(e)))
        traceback.print_exc()
    except:
        print('{} Unknown error.'.format(str(datetime.datetime.now())))
        traceback.print_exc()
    finally:
        if t_mt8057:
            print('{} MT8057 is stopping...'.format(str(datetime.datetime.now())))
            t_mt8057.stop()
            t_mt8057.join()

        if t_dht:
            print('{} Humidity Sensor is stopping...'.format(str(datetime.datetime.now())))
            t_dht.stop()
            t_dht.join()

    print('{} CO2 daemon stopped.'.format(str(datetime.datetime.now())))
    if send_error_cnt >= ERROR_LIMIT:
        print('{} System reboot...'.format(str(datetime.datetime.now())))
        os.system("sudo reboot")
