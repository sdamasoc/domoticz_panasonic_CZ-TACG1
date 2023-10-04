from datetime import datetime
from pluginfunctions import get_devices, get_device_by_id, get_app_version, get_token
import config

# change this values with your credentials
config.username = "<YOUR_PANASONIC_USER>"
config.password = "<YOUR_PANASONIC_PWD>"

# test config parameters
config.update_interval = 60
config.debug_level = "Debug"
config.api_version = "1.17.0"
config.address = "https://accsmart.panasonic.com"
config.devices = {}


########################


class PanasonicCZTACG1Plugin:
    enabled = True
    powerOn = 0
    last_update = 0

    def onStart(self):
        print("onStart called")
        # 1st try to get last version of the plugin
        config.api_version = get_app_version()
        config.token = get_token()

        # get devices list
        panasonic_devices = get_devices()

        # loop found devices to create then in domoticz
        nbdevices = 0  # (nbdevices:=nbdevices+1) = ++nbdevices
        for group in panasonic_devices['groupList']:
            groupname = group['groupName']
            for device in group['deviceList']:
                devicename = device['deviceName']
                deviceid = device['deviceGuid']
                get_device_by_id(deviceid)
                print("Device " + devicename + " found (DeviceID=" + deviceid + ").")

        print("onStart end")

# start test calls
p1 = PanasonicCZTACG1Plugin()
p1.onStart()