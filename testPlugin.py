import requests
import json
import time
from datetime import date

# global var token
token = None
Parameters = {"Mode3": "1.15.1", "Address": "https://accsmart.panasonic.com", "Username" : "XXXXXXX", "Password":"YYYYYYY"}


class PanasonicCZTACG1Plugin:
    enabled = True
    powerOn = 0
    last_update = 0

    def onStart(self):
        print("onStart called")

        # get devices list
        panasonic_devices = getDevices()

        # loop found devices to create then in domoticz
        nbdevices = 0  # (nbdevices:=nbdevices+1) = ++nbdevices
        for group in panasonic_devices['groupList']:
            groupname = group['groupName']
            for device in group['deviceList']:
                devicename = device['deviceName']
                deviceid = device['deviceGuid']
                print("Device " + devicename + " found (DeviceID=" + deviceid + ").")

        print("onStart end")



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
    print("getToken=" + response.text)
    res = json.loads(response.text)
    return res["uToken"]


# call the api to get device list
def getDevices():
    global token
    api_version = Parameters["Mode3"]
    url = Parameters["Address"] + "/device/group/"
    payload = ""
    headers = {
        'X-APP-TYPE':'0',
        'X-APP-VERSION': api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    for key, value in headers.items():
        print('header=',key,':',value)
    response = requests.request("GET", url, headers=headers, data=payload)
    print("getDevices=" + response.text)
    if ("Token expires" in response.text):
        print("Token is expired, renew!")
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
        'X-APP-TYPE': '1',
        'X-APP-VERSION': api_version,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    print("getDeviceById=" + response.text)
    if ("Token expires" in response.text):
        token = getToken()
        return getDeviceById(deviceid)
    else:
        return json.loads(response.text)


# call the api to update device parameter
def updateDeviceId(deviceid, parameterName, parameterValue):
    global token
    api_version = Parameters["Mode3"]
    print("updating DeviceId=" + deviceid + ", " + parameterName + "=" + str(parameterValue) + "...")
    url = Parameters["Address"] + "/deviceStatus/control/"
    payload = "{\"deviceGuid\": \"" + deviceid + "\", \"parameters\": { \"" + parameterName + "\": " + str(
        parameterValue) + " }}"
    headers = {
        'X-APP-TYPE': '1',
        'X-APP-VERSION': api_version,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-User-Authorization': token,
        'User-Agent': 'G-RAC'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    print("updateDeviceId=" + response.text)
    if ("Token expires" in response.text):
        token = getToken()
        return updateDeviceId(deviceid, parameterName, parameterValue)
    else:
        return json.loads(response.text)


# dumps the http response to the log
def DumpHTTPResponseToLog(httpResp, level=0):
    if (level == 0): print("HTTP Details (" + str(len(httpResp)) + "):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                print(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                print(indentStr + ">'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level + 1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            print(indentStr + "['" + x + "']")
    else:
        print(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")


########################
# End helper functions #
########################

# start test calls
p1 = PanasonicCZTACG1Plugin()
p1.onStart()
