# Panasonic CZ-TACG1 Python Plugin for Domoticz
#
# Author: sdamasoc
#
"""
<plugin key="CZ-TACG1" name="Panasonic Airco (CZ-TACG1)" author="sdamasoc" version="1.0.0" externallink="https://aircon.panasonic.com/connectivity/consumer/comfort_cloud_app.html">
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="https://accsmart.panasonic.com"/>
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default=""/>
        <param field="Mode1" label="Update every x seconds" width="75px">
            <options>
                <option label="30" value="3" />
                <option label="60" value="6" default="true" />
                <option label="90" value="9" />
                <option label="120" value="12" />
                <option label="150" value="15" />
                <option label="180" value="18" />
                <option label="210" value="21" />
                <option label="240" value="24" />
            </options>
        </param>
        <param field="Mode2" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
        
    </params>
</plugin>
"""
import requests
import json
import Domoticz
from datetime import datetime

# global var token
token = None


class PanasonicCZTACG1Plugin:
    enabled = True
    powerOn = 0

    def __init__(self):
        return

    def onStart(self):
        Domoticz.Log("onStart called")

        if Parameters["Mode2"] == "Debug":
            Domoticz.Debugging(1)

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

                    # get device infos
                    devicejson = getDeviceById(deviceid)

                    Domoticz.Device(Name=devicename + "[Power]", Unit=(nbdevices := nbdevices + 1), Image=16,
                                    TypeName="Switch", Used=1, DeviceID=deviceid).Create()

                    Domoticz.Device(Name=devicename + "[Room Temp]", Unit=(nbdevices := nbdevices + 1),
                                    TypeName="Temperature", Used=1, DeviceID=deviceid).Create()

                    Domoticz.Device(Name=devicename + "[Outdoor Temp]", Unit=(nbdevices := nbdevices + 1),
                                    TypeName="Temperature", Used=1, DeviceID=deviceid).Create()

                    Domoticz.Device(Name=devicename + "[Target temp]", Unit=(nbdevices := nbdevices + 1), Type=242,
                                    Subtype=1, Image=16, Used=1, DeviceID=deviceid).Create()

                    # operationMode
                    Options = {"LevelActions": "|||||", "LevelNames": "|Auto|Dry|Cool|Heat|Fan",
                               "LevelOffHidden": "true", "SelectorStyle": "1"}
                    Domoticz.Device(Name=devicename + "[Mode]", Unit=(nbdevices := nbdevices + 1),
                                    TypeName="Selector Switch", Image=16, Options=Options, Used=1,
                                    DeviceID=deviceid).Create()

                    # fanSpeed
                    Options = {"LevelActions": "|||||||", "LevelNames": "|Auto|Low|LowMid|Mid|HighMid|High",
                               "LevelOffHidden": "true", "SelectorStyle": "1"}
                    Domoticz.Device(Name=devicename + "[Fan Speed]", Unit=(nbdevices := nbdevices + 1),
                                    TypeName="Selector Switch", Image=7, Options=Options, Used=1,
                                    DeviceID=deviceid).Create()

                    # TODO add other switches?

                    Domoticz.Log("Device " + devicename + " created (DeviceID=" + deviceid + ").")

        onHeartbeat()
        DumpConfigToLog()

        Domoticz.Heartbeat(int(Parameters["Mode1"]))

        Domoticz.Log("onStart end")

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called, Status=" + str(Status))

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")
        DumpHTTPResponseToLog(Data)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("Command received for device Name=" + Devices[Unit].Name + "(deviceId=" + Devices[
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
                Devices[Unit].Update(nValue=self.powerOn, sValue=str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(
            Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("Connection " + Connection.Name + " closed.")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat started...")
        deviceid = None
        devicejson = None
        power = 0
        for x in Devices:
            if (deviceid != Devices[x].DeviceID):
                deviceid = Devices[x].DeviceID
                devicejson = getDeviceById(deviceid)
            if ("[Target temp]" in Devices[x].Name):
                value = str(float(devicejson['parameters']['temperatureSet']))
            elif ("[Room Temp]" in Devices[x].Name):
                value = str(float(devicejson['parameters']['insideTemperature']))
            elif ("[Outdoor Temp]" in Devices[x].Name):
                if (float(devicejson['parameters']['outTemperature']) > 50):
                    value = "--"
                else:
                    value = str(float(devicejson['parameters']['outTemperature']))
            elif ("[Power]" in Devices[x].Name):
                power = int(devicejson['parameters']['operate'])
                value = str(power * 100)

            elif ("[Mode]" in Devices[x].Name):
                operationmode = int(devicejson['parameters']['operationMode'])
                value = str(((operationmode + 1) * 10))
            elif ("[Fan Speed]" in Devices[x].Name):
                fanspeed = int(devicejson['parameters']['fanSpeed'])
                value = str(((fanspeed + 1) * 10))

            # update value only if value has changed
            if (Devices[x].sValue != value):
                Devices[x].Update(nValue=power, sValue=value)

        # Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        # Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        # Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        # Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        # Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
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
    url = Parameters["Address"] + "/auth/login"
    payload = "{\"language\": 0,\"loginId\": \"" + Parameters["Username"] + "\",\"password\": \"" + Parameters[
        "Password"] + "\"}"
    headers = {
        'X-APP-TYPE': '1',
        'X-APP-VERSION': '1.10.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'G-RAC'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    Domoticz.Debug("getToken=" + response.text)
    res = json.loads(response.text)
    return res["uToken"]

# call the api to get device list
def getDevices():
    global token
    url = Parameters["Address"] + "/device/group/"
    payload = ""
    headers = {
        'X-APP-TYPE': '1',
        'X-APP-VERSION': '1.10.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    Domoticz.Debug("getDevices=" + response.text)
    if ("Token expires" in response.text):
        token = getToken()
        return getDevices()
    else:
        return json.loads(response.text)
    return json.loads(response.text)

# call the api to get device infos
def getDeviceById(deviceid):
    global token
    url = Parameters["Address"] + "/deviceStatus/now/" + deviceid
    payload = ""
    headers = {
        'X-APP-TYPE': '1',
        'X-APP-VERSION': '1.10.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    Domoticz.Debug("getDeviceById=" + response.text)
    if ("Token expires" in response.text):
        token = getToken()
        return getDeviceById(deviceid)
    else:
        return json.loads(response.text)

# call the api to update device parameter
def updateDeviceId(deviceid, parameterName, parameterValue):
    global token
    Domoticz.Log("updating DeviceId=" + deviceid + ", " + parameterName + "=" + str(parameterValue) + "...")
    url = Parameters["Address"] + "/deviceStatus/control/"
    payload = "{\"deviceGuid\": \"" + deviceid + "\", \"parameters\": { \"" + parameterName + "\": " + str(
        parameterValue) + " }}"
    headers = {
        'X-APP-TYPE': '1',
        'X-APP-VERSION': '1.10.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    Domoticz.Debug("updateDeviceId=" + response.text)
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