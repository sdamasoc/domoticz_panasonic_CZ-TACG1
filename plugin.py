# Panasonic CZ-TACG1 Python Plugin for Domoticz
#
# Author: sdamasoc
#
"""
<plugin key="CZ-TACG1" name="Panasonic Airco (CZ-TACG1)" author="sdamasoc" version="1.1.0" externallink="https://aircon.panasonic.com/connectivity/consumer/comfort_cloud_app.html">
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
        <param field="Mode3" label="API Version" width="60px" required="true" default="1.15.1"/>
    </params>
</plugin>
"""
import requests
import json
import Domoticz
import time
from datetime import date

# global var token
token = None



class PanasonicCZTACG1Plugin:
    enabled = True
    powerOn = 0
    last_update = 0

    def __init__(self):
        return

    def onStart(self):
        Domoticz.Debug("onStart called")

        if Parameters["Mode2"] == "Debug":
            # 0: None. All Python and framework debugging is disabled.
            # 1: All. Very verbose log from plugin framework and plugin debug messages.
            # 2: Mask value. Shows messages from Plugin Domoticz.Debug() calls only.
            # https://www.domoticz.com/wiki/Developing_a_Python_plugin#C.2B.2B_Callable_API 
            Domoticz.Debugging(2)

        # get devices list
        panasonic_devices = getDevices()

        # loop found devices to create then in domoticz
        nbdevices = 0  # (nbdevices:=nbdevices+1) = ++nbdevices
        if (len(Devices) == 0):
            for group in panasonic_devices['groupList']:
                groupname = group['groupName']
                for device in group['deviceList']:
                    devicename = device['deviceName']
                    deviceid = device['deviceGuid']

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
        DumpConfigToLog()

        Domoticz.Debug("onStart end")

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called, Status=" + str(Status))

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        DumpHTTPResponseToLog(Data)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("Command received for device Name=" + Devices[Unit].Name + "(deviceId=" + Devices[
            Unit].DeviceID + ") U=" + str(Unit) + " C=" + str(Command) + " L=" + str(Level) + " H=" + str(Hue))

        if (Command == "On"):
            updateDeviceId(Devices[Unit].DeviceID, "operate", 1)
            Devices[Unit].Update(nValue=1, sValue="100")
            self.powerOn = 1
        elif (Command == "Off"):
            updateDeviceId(Devices[Unit].DeviceID, "operate", 0)
            Devices[Unit].Update(nValue=0, sValue="0")
            self.powerOn = 0
        elif (Command == "Set Level"):
            if (Devices[Unit].nValue != self.powerOn or (Devices[Unit].sValue != Level) and Level != "--"):
                if ("[Target temp]" in Devices[Unit].Name):
                    updateDeviceId(Devices[Unit].DeviceID, "temperatureSet", float(Level))
                if ("[Mode]" in Devices[Unit].Name):
                    operationmode = (Level / 10) - 1
                    updateDeviceId(Devices[Unit].DeviceID, "operationMode", int(operationmode))
                elif ("[Fan Speed]" in Devices[Unit].Name):
                    fanspeed = (Level / 10) - 1
                    updateDeviceId(Devices[Unit].DeviceID, "fanSpeed", int(fanspeed))
                elif ("[Eco Mode]" in Devices[Unit].Name):
                    ecomode = (Level / 10) - 1
                    updateDeviceId(Devices[Unit].DeviceID, "ecoMode", int(ecomode))
                elif ("[Air Swing]" in Devices[Unit].Name):
                    airswing = (Level / 10) - 1
                    updateDeviceId(Devices[Unit].DeviceID, "airSwingUD", int(airswing))
                Devices[Unit].Update(nValue=self.powerOn, sValue=str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(
            Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("Connection " + Connection.Name + " closed.")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat started...")
        update_interval = int(Parameters["Mode1"])
        Domoticz.Debug("interval since last update = " + str(time.time() - self.last_update) + ", update_interval = " + str(update_interval))
        if time.time() - self.last_update < update_interval:
            Domoticz.Debug("update interval not reached")
            return
        deviceid = None
        devicejson = None
        power = 0
        for x in Devices:
            if (deviceid != Devices[x].DeviceID):
                deviceid = Devices[x].DeviceID
                devicejson = getDeviceById(deviceid)
            if (devicejson.get('parameters') is None):
                # the device is offline
                Domoticz.Log("The device " + deviceid + " return an error (code=" + str(devicejson.get('code')) + ", message=" + str(devicejson.get('message')) + ")")
                continue
            if ("[Target temp]" in Devices[x].Name):
                value = str(float(devicejson['parameters']['temperatureSet']))
            elif ("[Room Temp]" in Devices[x].Name):
                value = str(float(devicejson['parameters']['insideTemperature']))
            elif ("[Outdoor Temp]" in Devices[x].Name):
                if (float(devicejson['parameters']['outTemperature']) > 100):
                    value = "--"
                else:
                    value = str(float(devicejson['parameters']['outTemperature']))
            elif ("[Power]" in Devices[x].Name):
                power = int(devicejson['parameters']['operate'])
                value = str(power * 100)
            elif ("[Mode]" in Devices[x].Name):
                operationmode = int(devicejson['parameters']['operationMode'])
                value = str((operationmode + 1) * 10)
            elif ("[Fan Speed]" in Devices[x].Name):
                fanspeed = int(devicejson['parameters']['fanSpeed'])
                value = str((fanspeed + 1) * 10)
            elif ("[Eco Mode]" in Devices[x].Name):
                ecomode = int(devicejson['parameters']['ecoMode'])
                value = str((ecomode + 1) * 10)
            elif ("[Air Swing]" in Devices[x].Name):
                airswing = int(devicejson['parameters']['airSwingUD'])
                value = str((airswing + 1) * 10)

            # update value only if value has changed
            if (Devices[x].sValue != value):
                Devices[x].Update(nValue=power, sValue=value)

        # Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        # Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        # Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        # Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        # Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
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


############################
# Generic helper functions #
############################

# call the api to get a token
def getToken():
    api_version = Parameters["Mode3"]
    url = Parameters["Address"] + "/auth/login"
    payload = "{\"language\": 0,\"loginId\": \"" + Parameters["Username"] + "\",\"password\": \"" + Parameters[
        "Password"] + "\"}"
    headers = {
        'X-APP-TYPE': '0',
        'X-APP-VERSION': api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'User-Agent': 'G-RAC'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    Domoticz.Log("getToken=" + response.text)
    res = json.loads(response.text)
    return res["uToken"]


# call the api to get device list
def getDevices():
    global token
    api_version = Parameters["Mode3"]
    url = Parameters["Address"] + "/device/group/"
    payload = ""
    headers = {
        'X-APP-TYPE': '0',
        'X-APP-VERSION': api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    Domoticz.Log("getDevices=" + response.text)
    if ("Token expires" in response.text):
        token = getToken()
        return getDevices()
    else:
        return json.loads(response.text)
    return json.loads(response.text)


# call the api to get device infos
def getDeviceById(deviceid):
    global token
    api_version = Parameters["Mode3"]
    url = Parameters["Address"] + "/deviceStatus/now/" + deviceid
    payload = ""
    headers = {
        'X-APP-TYPE': '0',
        'X-APP-VERSION': api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    Domoticz.Log("getDeviceById=" + response.text)
    if ("Token expires" in response.text):
        token = getToken()
        return getDeviceById(deviceid)
    else:
        return json.loads(response.text)


# call the api to update device parameter
def updateDeviceId(deviceid, parameterName, parameterValue):
    global token
    api_version = Parameters["Mode3"]
    Domoticz.Log("updating DeviceId=" + deviceid + ", " + parameterName + "=" + str(parameterValue) + "...")
    url = Parameters["Address"] + "/deviceStatus/control/"
    payload = "{\"deviceGuid\": \"" + deviceid + "\", \"parameters\": { \"" + parameterName + "\": " + str(
        parameterValue) + " }}"
    headers = {
        'X-APP-TYPE': '0',
        'X-APP-VERSION': api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    Domoticz.Log("updateDeviceId=" + response.text)
    if ("Token expires" in response.text):
        token = getToken()
        return updateDeviceId(deviceid, parameterName, parameterValue)
    else:
        return json.loads(response.text)


# dumps the http response to the log
def DumpHTTPResponseToLog(httpResp, level=0):
    if (level == 0): Domoticz.Debug("HTTP Details (" + str(len(httpResp)) + "):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + ">'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level + 1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")


# Dumps the config to debug log
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

########################
# End helper functions #
########################
