import os
import requests
import json
import Domoticz
from datetime import datetime
import config
import common

############################
# Generic helper functions #
############################

# call the api to get a token
def get_token():
    # if token already exist reuse it
    if os.path.exists(config.token_file_path):
        with open(config.token_file_path, 'r') as token_file:
            token = token_file.read().strip()
            Domoticz.Log("Reusing existing accsmart token=" + token)
            return token
    # else    
    url = config.accsmart_url + "/auth/login"

    payload = json.dumps({
        "language": 0,
        "loginId": config.username,
        "password": config.password
    })
    headers=get_headers(with_token=False)
    response = send_request("POST", url, headers=headers, data=payload)
    Domoticz.Log("get_token=" + response.text)
    res = json.loads(response.text)
    token = res["uToken"] 
    # save the token
    with open(config.token_file_path, 'w') as token_file:
        token_file.write(token)
    return token


# call the api to get device list
def get_devices():
    url = config.accsmart_url + "/device/group/"

    headers = get_headers()
    response = send_request("GET", url, headers=headers)
    Domoticz.Log("get_devices=" + response.text)
    return handle_response(response, lambda: get_devices())

# call the api to get device infos
def get_device_by_id(device_id):
    url = config.accsmart_url + "/deviceStatus/now/" + device_id

    headers = get_headers()
    response = send_request("GET", url, headers=headers)
    Domoticz.Log("get_device_by_id=" + response.text)
    return handle_response(response, lambda: get_device_by_id(device_id))

# call the api to get device historic data
def get_historic_data(device_id):
    url = config.accsmart_url + "/deviceHistoryData"
    payload = json.dumps({
        "dataMode": 0,
        "date": common.get_date(),
        "deviceGuid": device_id,
        "osTimezone": "+01:00"
    })
    headers = get_headers()
    response = send_request("POST", url, headers=headers, data=payload)
    #Domoticz.Log("get_historic_data=" + response.text)
    res = handle_response(response, lambda: get_historic_data(device_id))
    kWh = res["energyConsumption"]
    return kWh

# call the api to update device parameter
def update_device_id(device_id, parameter_name, parameter_value):
    Domoticz.Log("updating DeviceId=" + device_id + ", " + parameter_name + "=" + str(parameter_value) + "...")

    url = config.accsmart_url + "/deviceStatus/control/"
    
    payload = json.dumps({
        "deviceGuid": device_id,
        "parameters": {parameter_name: parameter_value}
    })
    headers = get_headers()
    response = send_request("POST", url, headers=headers, data=payload)
    Domoticz.Log("update_device_id=" + response.text)
    return handle_response(response, lambda: update_device_id(device_id, parameter_name, parameter_value))

def get_headers(with_token=True):
    headers = {
        'X-APP-TYPE': '0',
        'X-APP-VERSION': config.api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'User-Agent': 'G-RAC',
        'X-APP-NAME': 'Comfort Cloud',
        'X-CFC-API-KEY': '0',
        'X-APP-TIMESTAMP': common.get_timestamp()
    }
    if with_token:
        headers['X-User-Authorization']= config.token
    return headers

def send_request(method, url, headers=None, data=None):
    try:
        response = requests.request(method, url, headers=headers, data=data)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        #Domoticz.Error(f"Request failed: {e}")
        return response

def handle_response(response, retry_func):
    if response is None:
        return None

    error_handlers = {
        "Token expires": handle_token_expiration,
        "New version app has been published": handle_api_version_update,
    }

    for error_text, handler in error_handlers.items():
        if error_text in response.text:
            handler()
            return retry_func()

    return json.loads(response.text)

def handle_token_expiration():
    Domoticz.Log("Token is expired, get a new token")
    # if token file exists delete it
    if os.path.exists(config.token_file_path):
        os.remove(config.token_file_path)
    config.token = get_token()

def handle_api_version_update():
    Domoticz.Log("New version app has been published")
    # if api_version_file_path file exists delete it
    if os.path.exists(config.api_version_file_path):
        os.remove(config.api_version_file_path)
    config.api_version = common.get_app_version()

# dumps the http response to the log
def dump_http_response_to_log(httpResp, level=0):
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
                dump_http_response_to_log(httpResp[x], level + 1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")


########################
# End helper functions #
########################

def add_device(devicename, deviceid, nbdevices):
    Domoticz.Log(f"Creating accsmart devices for {devicename}, DeviceID={deviceid}, Unit={nbdevices}...")
    # TODO check if device is support before creation ("airSwingLR":true,"nanoe":false,"autoMode":true,"autoSwingUD":false,"ecoNavi":false,...)
    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Power]", Unit=nbdevices, Image=16, TypeName="Switch", Used=1, DeviceID=deviceid).Create()

    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Room Temp]", Unit=nbdevices, TypeName="Temperature", Used=1, DeviceID=deviceid).Create()

    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Outdoor Temp]", Unit=nbdevices, TypeName="Temperature", Used=1, DeviceID=deviceid).Create()

    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Target temp]", Unit=nbdevices, Type=242, Subtype=1, Image=16, Used=1, DeviceID=deviceid).Create()

    # operationMode
    Options = {"LevelActions": "|||||", "LevelNames": "|Auto|Dry|Cool|Heat|Fan", "LevelOffHidden": "true", "SelectorStyle": "1"}
    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Mode]", Unit=nbdevices, TypeName="Selector Switch", Image=16, Options=Options, Used=1, DeviceID=deviceid).Create()

    # fanSpeed
    Options = {"LevelActions": "|||||||", "LevelNames": "|Auto|Low|LowMid|Mid|HighMid|High", "LevelOffHidden": "true", "SelectorStyle": "1"}
    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Fan Speed]", Unit=nbdevices, TypeName="Selector Switch", Image=7, Options=Options, Used=1, DeviceID=deviceid).Create()
    # ecoMode
    Options = {"LevelActions": "|||||||", "LevelNames": "|Auto|Powerful|Quiet", "LevelOffHidden": "true", "SelectorStyle": "1"}
    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Eco Mode]", Unit=nbdevices, TypeName="Selector Switch", Image=7, Options=Options, Used=1, DeviceID=deviceid).Create()

    # airSwingUD => 0,3,2,4,1 (weird)
    Options = {"LevelActions": "|||||||", "LevelNames": "Up|Down|Mid|UpMid|DownMid", "LevelOffHidden": "true", "SelectorStyle": "1"}
    nbdevices = nbdevices + 1
    Domoticz.Device(Name=devicename + "[Air Swing]", Unit=nbdevices, TypeName="Selector Switch", Image=7, Options=Options, Used=1, DeviceID=deviceid).Create()
    
    # energyConsumption
    nbdevices = nbdevices + 1
    Options={'EnergyMeterMode': '1' }    
    Domoticz.Device(Name=devicename + "[kWh]", Unit=nbdevices, TypeName="kWh", Used=1, Options=Options, DeviceID=deviceid).Create()

    # TODO add other switches?

    Domoticz.Log("Device " + devicename + " created (DeviceID=" + deviceid + ").")



def handle_accsmart(device, devicejson):
    power = 0
    value = "----"
    if ("[Target temp]" in device.Name):
        value = str(float(devicejson['parameters']['temperatureSet']))
    elif ("[Room Temp]" in device.Name):
        value = str(float(devicejson['parameters']['insideTemperature']))
    elif ("[Outdoor Temp]" in device.Name):
        if (float(devicejson['parameters']['outTemperature']) > 100):
            value = "--"
        else:
            value = str(float(devicejson['parameters']['outTemperature']))
    elif ("[Power]" in device.Name):
        power = int(devicejson['parameters']['operate'])
        value = str(power * 100)
    elif ("[Mode]" in device.Name):
        operationmode = int(devicejson['parameters']['operationMode'])
        value = str((operationmode + 1) * 10)
    elif ("[Fan Speed]" in device.Name):
        fanspeed = int(devicejson['parameters']['fanSpeed'])
        value = str((fanspeed + 1) * 10)
    elif ("[Eco Mode]" in device.Name):
        ecomode = int(devicejson['parameters']['ecoMode'])
        value = str((ecomode + 1) * 10)
    elif ("[Air Swing]" in device.Name):
        airswing = int(devicejson['parameters']['airSwingUD'])
        value = str((airswing + 1) * 10)
    elif ("[kWh]" in device.Name):
        kWh = get_historic_data(device.DeviceID)*1000 # historic data is in kWh, domoticz wants W
        value = f'{str(float(kWh))};{str(float(kWh))}'

    # update value only if value has changed
    if (device.sValue != value):
        device.Update(nValue=power, sValue=value)



def update_accsmart(p, Command, Level, device):
    if (Command == "On"):
        update_device_id(device.DeviceID, "operate", 1)
        device.Update(nValue=1, sValue="100")
        p.powerOn = 1
    elif (Command == "Off"):
        update_device_id(device.DeviceID, "operate", 0)
        device.Update(nValue=0, sValue="0")
        p.powerOn = 0
    elif (Command == "Set Level"):
        if (device.nValue != p.powerOn or (device.sValue != Level) and Level != "--"):
            if ("[Target temp]" in device.Name):
                update_device_id(device.DeviceID, "temperatureSet", float(Level))
            if ("[Mode]" in device.Name):
                operationmode = (Level / 10) - 1
                update_device_id(device.DeviceID, "operationMode", int(operationmode))
            elif ("[Fan Speed]" in device.Name):
                fanspeed = (Level / 10) - 1
                update_device_id(device.DeviceID, "fanSpeed", int(fanspeed))
            elif ("[Eco Mode]" in device.Name):
                ecomode = (Level / 10) - 1
                update_device_id(device.DeviceID, "ecoMode", int(ecomode))
            elif ("[Air Swing]" in device.Name):
                airswing = (Level / 10) - 1
                update_device_id(device.DeviceID, "airSwingUD", int(airswing))
            device.Update(nValue=p.powerOn, sValue=str(Level))