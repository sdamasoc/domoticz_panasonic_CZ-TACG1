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
        <param field="Address" label="IP Address" width="200px" required="true" default="https://accsmart.panasonic.com"/>
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
from pluginfunctions import dump_config_to_log, dump_http_response_to_log, get_devices, get_device_by_id, update_device_id, get_app_version
import config

# set config parameters
config.update_interval = int(Parameters["Mode1"])
config.debug_level = Parameters["Mode2"]
config.api_version = Parameters["Mode3"]
config.address = Parameters["Address"]
config.username = Parameters["Username"]
config.password = Parameters["Password"]
config.devices = Devices

class PanasonicCZTACG1Plugin:
    enabled = True
    powerOn = 0
    last_update = 0

    def __init__(self):
        return

    def onStart(self):
        Domoticz.Debug("onStart called")
        # 1st try to get last version of the plugin
        config.api_version = get_app_version()

        if config.debug_level == "Debug":
            # 0: None. All Python and framework debugging is disabled.
            # 1: All. Very verbose log from plugin framework and plugin debug messages.
            # 2: Mask value. Shows messages from Plugin Domoticz.Debug() calls only.
            # https://www.domoticz.com/wiki/Developing_a_Python_plugin#C.2B.2B_Callable_API 
            Domoticz.Debugging(2)

        # get devices list
        panasonic_devices = get_devices()

        # loop found devices to create then in domoticz
        nbdevices = len(config.devices)  # (nbdevices:=nbdevices+1) = ++nbdevices

        for group in panasonic_devices['groupList']:
            groupname = group['groupName']
            for device in group['deviceList']:
                devicename = device['deviceName']
                deviceid = device['deviceGuid']

                exist = False
                for x in config.devices:
                    Domoticz.Debug("x="+str(x)+",DeviceID="+ config.devices[x].DeviceID + ", Name="+config.devices[x].Name + "Dump=" + str(config.devices[x]));
                    # check if there's an unitId > nbdevices
                    if (x > nbdevices):
                        nbdevices = x
                    # check if device already exist in Domoticz
                    if (deviceid == config.devices[x].DeviceID):
                        exist = True

                if exist :
                    Domoticz.Log("Device " + devicename + " already exists in domoticz (DeviceID=" + deviceid + ").")
                else :
                    Domoticz.Log("Creating device " + devicename + ", DeviceID=" + deviceid + ", Unit="+ str(nbdevices) +".")
                    # TODO check if device is support before creation ("airSwingLR":true,"nanoe":false,"autoMode":true,"autoSwingUD":false,"ecoNavi":false,...)
                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Power]", Unit=nbdevices, Image=16,
                                    TypeName="Switch", Used=1, DeviceID=deviceid).Create()

                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Room Temp]", Unit=nbdevices,
                                    TypeName="Temperature", Used=1, DeviceID=deviceid).Create()

                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Outdoor Temp]", Unit=nbdevices,
                                    TypeName="Temperature", Used=1, DeviceID=deviceid).Create()

                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Target temp]", Unit=nbdevices, Type=242,
                                    Subtype=1, Image=16, Used=1, DeviceID=deviceid).Create()

                    # operationMode
                    Options = {"LevelActions": "|||||", "LevelNames": "|Auto|Dry|Cool|Heat|Fan",
                               "LevelOffHidden": "true", "SelectorStyle": "1"}
                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Mode]", Unit=nbdevices,
                                    TypeName="Selector Switch", Image=16, Options=Options, Used=1,
                                    DeviceID=deviceid).Create()

                    # fanSpeed
                    Options = {"LevelActions": "|||||||", "LevelNames": "|Auto|Low|LowMid|Mid|HighMid|High",
                               "LevelOffHidden": "true", "SelectorStyle": "1"}
                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Fan Speed]", Unit=nbdevices,
                                    TypeName="Selector Switch", Image=7, Options=Options, Used=1,
                                    DeviceID=deviceid).Create()
                    # ecoMode
                    Options = {"LevelActions": "|||||||", "LevelNames": "|Auto|Powerful|Quiet",
                               "LevelOffHidden": "true", "SelectorStyle": "1"}
                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Eco Mode]", Unit=nbdevices,
                                    TypeName="Selector Switch", Image=7, Options=Options, Used=1,
                                    DeviceID=deviceid).Create()

                    # airSwingUD => 0,3,2,4,1 (weird)
                    Options = {"LevelActions": "|||||||", "LevelNames": "Up|Down|Mid|UpMid|DownMid",
                               "LevelOffHidden": "true", "SelectorStyle": "1"}
                    nbdevices = nbdevices + 1
                    Domoticz.Device(Name=devicename + "[Air Swing]", Unit=nbdevices,
                                    TypeName="Selector Switch", Image=7, Options=Options, Used=1,
                                    DeviceID=deviceid).Create()

                    # TODO add other switches?

                    Domoticz.Log("Device " + devicename + " created (DeviceID=" + deviceid + ").")

        onHeartbeat()
        dump_config_to_log()

        Domoticz.Debug("onStart end")

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called, Status=" + str(Status))

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        dump_http_response_to_log(Data)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("Command received for device Name=" + config.devices[Unit].Name + "(deviceId=" + config.devices[
            Unit].DeviceID + ") U=" + str(Unit) + " C=" + str(Command) + " L=" + str(Level) + " H=" + str(Hue))

        if (Command == "On"):
            update_device_id(config.devices[Unit].DeviceID, "operate", 1)
            config.devices[Unit].Update(nValue=1, sValue="100")
            self.powerOn = 1
        elif (Command == "Off"):
            update_device_id(config.devices[Unit].DeviceID, "operate", 0)
            config.devices[Unit].Update(nValue=0, sValue="0")
            self.powerOn = 0
        elif (Command == "Set Level"):
            if (config.devices[Unit].nValue != self.powerOn or (config.devices[Unit].sValue != Level) and Level != "--"):
                if ("[Target temp]" in config.devices[Unit].Name):
                    update_device_id(config.devices[Unit].DeviceID, "temperatureSet", float(Level))
                if ("[Mode]" in config.devices[Unit].Name):
                    operationmode = (Level / 10) - 1
                    update_device_id(config.devices[Unit].DeviceID, "operationMode", int(operationmode))
                elif ("[Fan Speed]" in config.devices[Unit].Name):
                    fanspeed = (Level / 10) - 1
                    update_device_id(config.devices[Unit].DeviceID, "fanSpeed", int(fanspeed))
                elif ("[Eco Mode]" in config.devices[Unit].Name):
                    ecomode = (Level / 10) - 1
                    update_device_id(config.devices[Unit].DeviceID, "ecoMode", int(ecomode))
                elif ("[Air Swing]" in config.devices[Unit].Name):
                    airswing = (Level / 10) - 1
                    update_device_id(config.devices[Unit].DeviceID, "airSwingUD", int(airswing))
                config.devices[Unit].Update(nValue=self.powerOn, sValue=str(Level))

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
        deviceid = None
        devicejson = None
        power = 0
        value = "----"
        for x in config.devices:
            if (deviceid != config.devices[x].DeviceID):
                deviceid = config.devices[x].DeviceID
                devicejson = get_device_by_id(deviceid)
            if (devicejson.get('parameters') is None):
                # the device is offline
                Domoticz.Log("The device " + deviceid + " return an error (code=" + str(devicejson.get('code')) + ", message=" + str(devicejson.get('message')) + ")")
                continue
            if ("[Target temp]" in config.devices[x].Name):
                value = str(float(devicejson['parameters']['temperatureSet']))
            elif ("[Room Temp]" in config.devices[x].Name):
                value = str(float(devicejson['parameters']['insideTemperature']))
            elif ("[Outdoor Temp]" in config.devices[x].Name):
                if (float(devicejson['parameters']['outTemperature']) > 100):
                    value = "--"
                else:
                    value = str(float(devicejson['parameters']['outTemperature']))
            elif ("[Power]" in config.devices[x].Name):
                power = int(devicejson['parameters']['operate'])
                value = str(power * 100)
            elif ("[Mode]" in config.devices[x].Name):
                operationmode = int(devicejson['parameters']['operationMode'])
                value = str((operationmode + 1) * 10)
            elif ("[Fan Speed]" in config.devices[x].Name):
                fanspeed = int(devicejson['parameters']['fanSpeed'])
                value = str((fanspeed + 1) * 10)
            elif ("[Eco Mode]" in config.devices[x].Name):
                ecomode = int(devicejson['parameters']['ecoMode'])
                value = str((ecomode + 1) * 10)
            elif ("[Air Swing]" in config.devices[x].Name):
                airswing = int(devicejson['parameters']['airSwingUD'])
                value = str((airswing + 1) * 10)

            # update value only if value has changed
            if (config.devices[x].sValue != value):
                config.devices[x].Update(nValue=power, sValue=value)

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