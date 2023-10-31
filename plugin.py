# Panasonic CZ-TACG1 Python Plugin for Domoticz
#
# Author: sdamasoc
#
"""
<plugin key="CZ-TACG1" name="Panasonic Airco (CZ-TACG1)" author="sdamasoc" version="2.0.0" externallink="https://www.panasonic.com/global/hvac/air-conditioning/connectivity/comfort-cloud/home-owner.html">
    <description>
        <h2>Panasonic Cloud Control Plugin</h2><br/>
        This is a Domoticz python plugin to communicate through Panasonic Cloud Comfort API.
        <h3>Configuration</h3>
        <p>Just enter your Panasonic Cloud Comfort username and password and everything will be detected automatically.</p>
        <p>You can also configure the update interval to not overload http requests.</p>
        <p>The API version can also be given when an API update is available.</p>
    </description>
    <params>
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default=""/>
        <param field="Mode1" label="Update every x seconds" width="75px">
            <options>
                <option label="30" value="30" />
                <option label="60" value="60" default="true" />
                <option label="90" value="90" />
                <option label="120" value="120" />
                <option label="150" value="150" />
                <option label="180" value="180" />
                <option label="210" value="210" />
                <option label="240" value="240" />
            </options>
        </param>
        <param field="Mode2" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
        <param field="Mode3" label="API Version" width="60px" required="true" default="1.19.0"/>
    </params>
</plugin>
"""
import Domoticz
import time
import accsmart
import aquarea
import config
import common
import os
# to test locally uncomment this line, rename .Domoticz.py to Domoticz.py and set your cvredentials in Domoticz.py
# from Domoticz import Parameters, Devices

class PanasonicCZTACG1Plugin:
    enabled = True
    powerOn = 0
    last_update = 0

    def __init__(self):
        return

    def onStart(self):
        # set config parameters
        config.update_interval = int(Parameters["Mode1"])
        config.debug_level = Parameters["Mode2"]
        config.api_version = Parameters["Mode3"]
        config.username = Parameters["Username"]
        config.password = Parameters["Password"]
        config.devices = Devices

        Domoticz.Debug("onStart called")
        # 1st try to get last version of the plugin
        config.api_version = common.get_app_version()
        config.token = accsmart.get_token()
        config.aquarea_token = aquarea.get_aquarea_token()

        if config.debug_level == "Debug":
            # 0: None. All Python and framework debugging is disabled.
            # 1: All. Very verbose log from plugin framework and plugin debug messages.
            # 2: Mask value. Shows messages from Plugin Domoticz.Debug() calls only.
            # https://www.domoticz.com/wiki/Developing_a_Python_plugin#C.2B.2B_Callable_API 
            Domoticz.Debugging(2)

        # get devices list
        panasonic_devices = accsmart.get_devices()

        # loop found devices to create then in domoticz
        nbdevices = len(config.devices)  # (nbdevices:=nbdevices+1) = ++nbdevices

        for group in panasonic_devices['groupList']:
            groupname = group['groupName']
            for device in group['deviceList']:
                devicename = device['deviceName']
                deviceid = device['deviceGuid']
                deviceType = device['deviceType']

                exist = False
                for x in config.devices:
                    # Domoticz.Debug("x="+str(x)+",DeviceID="+ config.devices[x].DeviceID + ", Name="+config.devices[x].Name + "Dump=" + str(config.devices[x]));
                    # check if there's an unitId > nbdevices
                    if (x > nbdevices):
                        nbdevices = x
                    # check if device already exist in Domoticz
                    if (devicename in config.devices[x].Name):
                        exist = True

                if exist :
                    Domoticz.Log("Device " + devicename + " already exists in domoticz (DeviceID=" + deviceid + ").")
                elif(deviceType == "2"):
                    Domoticz.Log("Aquarea devices (deviceType=" + deviceType + ") IS IN ALPHA MODE") 
                    aquarea.add_device(devicename, nbdevices)
                else :
                    accsmart.add_device(devicename, deviceid, nbdevices)

        onHeartbeat()
        #dump_config_to_log()

        Domoticz.Debug("onStart end")

    def onStop(self):
        Domoticz.Debug("onStop called")
        if os.path.exists(config.token_file_path):
            os.remove(config.token_file_path)
        if os.path.exists(config.aquarea_token_file_path):
            os.remove(config.aquarea_token_file_path)
        if os.path.exists(config.api_version_file_path):
            os.remove(config.api_version_file_path)
        Domoticz.Debug("onStop end")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called, Status=" + str(Status))

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        accsmart.dump_http_response_to_log(Data)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("Command received for device Name=" + config.devices[Unit].Name + "(deviceId=" + config.devices[
            Unit].DeviceID + ") U=" + str(Unit) + " C=" + str(Command) + " L=" + str(Level) + " H=" + str(Hue))

        if len(config.devices[Unit].DeviceID) < 20:
            # handle accsmart
            accsmart.update_accsmart(self, Command, Level, config.devices[Unit])
        else:
            # handle aquarea
            aquarea.update_aquarea(self, Command, Level, config.devices[Unit])


    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(
            Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("Connection " + Connection.Name + " closed.")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat started...")
        update_interval = config.update_interval
        Domoticz.Debug("interval since last update = " + str(time.time() - self.last_update) + ", update_interval = " + str(update_interval))
        if time.time() - self.last_update < update_interval:
            Domoticz.Debug("update interval not reached")
            return
        previous_id = None
        deviceid = None
        devicejson = None
        for x in config.devices:
            deviceid = config.devices[x].DeviceID
            if len(deviceid) < 70:
                if previous_id != deviceid:
                    deviceid = config.devices[x].DeviceID
                    devicejson = accsmart.get_device_by_id(deviceid)
                if (devicejson.get('parameters') is None):
                    # the device is offline
                    Domoticz.Log("The device " + deviceid + " return an error (code=" + str(devicejson.get('code')) + ", message=" + str(devicejson.get('message')) + ")")
                    continue
                accsmart.handle_accsmart(config.devices[x], devicejson)
            else:
                if previous_id != deviceid:
                    deviceid = config.devices[x].DeviceID
                    devicejson = aquarea.load_device_details(deviceid)
                aquarea.handle_aquarea(config.devices[x], devicejson)
            previous_id = deviceid



        # Domoticz.Debug("Device ID:       '" + str(config.devices[x].ID) + "'")
        # Domoticz.Debug("Device Name:     '" + config.devices[x].Name + "'")
        # Domoticz.Debug("Device nValue:    " + str(config.devices[x].nValue))
        # Domoticz.Debug("Device sValue:   '" + config.devices[x].sValue + "'")
        # Domoticz.Debug("Device LastLevel: " + str(config.devices[x].LastLevel))
        self.last_update = time.time()
        Domoticz.Debug("onHeartbeat ended.")


global _plugin
_plugin = PanasonicCZTACG1Plugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Dumps the config to debug log
def dump_config_to_log():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(config.devices)))
    for x in config.devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(config.devices[x]))
        Domoticz.Debug("Device ID:       '" + str(config.devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + config.devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(config.devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + config.devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(config.devices[x].LastLevel))
    return