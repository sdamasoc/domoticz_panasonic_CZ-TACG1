import os
import requests
import json
import Domoticz
from datetime import datetime
import config
import common

from pcomfortcloud import ApiClient
from pcomfortcloud import constants
import pcomfortcloud

############################
# Generic helper functions #
############################

# call the api to get a token
def get_client():
    client = ApiClient(config.username, config.password)
    client.start_session()
    client.get_devices()
    return client

# call the api to get device infos
def get_device_by_id(device_id):
    #todo: use client api
    #device_hash_guid=get_device_hash_guid(device_id)
    #json_response=config.client.get_device(device_hash_guid)
    json_response = config.client.execute_get(config.client._get_device_status_url(device_id), "get_device", 200)
    Domoticz.Debug(f"in get_device_by_id, json_response={json_response}")
    return json_response

# call the api to get device historic data
def get_historic_data(device_id):
    # TODO: implement this with new API
    # config.client.history(...)
    last_consumption_value = 0
    energyConsumption = 0
    Domoticz.Log("get_historic_data is not implemented with new API")
    Domoticz.Log(f"get_historic_data for {device_id}  = {last_consumption_value};{energyConsumption}")
    return f'{last_consumption_value};{energyConsumption}'

# call the api to update device parameter
def update_device_id(device_id, parameter_name, parameter_value):
    device_hash_guid=get_device_hash_guid(device_id)
    Domoticz.Log(f"updating DeviceId={device_id}, device_hash_guid={device_hash_guid}, {parameter_name}={parameter_value}...")
    payload= {parameter_name: parameter_value}
    res=config.client.set_device(device_hash_guid, **payload)
    print(f'result of set_device={res}')   
    #Domoticz.Log(f"payload={payload} url={config.client._get_device_status_control_url()}")
    #response = config.client.execute_post(config.client._get_device_status_control_url(), payload, "set_device", 200)

    Domoticz.Log(f"update_device_id={res}")
    return res

def handle_response(response, retry_func):
    if response is None:
        return None

    error_handlers = {
        "New version app has been published": handle_api_version_update,
    }

    for error_text, handler in error_handlers.items():
        if error_text in response.text:
            handler()
            return retry_func()
        elif '"errorMessage":' in response.text:
            Domoticz.Error(f"error not handled in response {response.text} for retry_func={retry_func}")

    return json.loads(response.text)

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
    #Use Options={'EnergyMeterMode': '1' } to set energyMeterMode to "Calculated". Default is "From Device"
    Options={'EnergyMeterMode': '0' }
    Domoticz.Device(Name=devicename + "[Energy]", Unit=nbdevices, TypeName="kWh", Options=Options, Used=1, DeviceID=deviceid).Create()

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
    elif ("[Energy]" in device.Name):
        value = get_historic_data(device.DeviceID) # historic data is in kWh, domoticz wants W
        if value.startswith('-255'):
            Domoticz.Log(f"keep previous value of get_historic_data for {device.DeviceID} = {device.sValue}")
            value = device.sValue  # keep previous value

    # update value only if value has changed
    if (device.sValue != value):
        device.Update(nValue=power, sValue=value)



def update_accsmart(p, Command, Level, device):
    if (Command == "On"):
        update_device_id(device.DeviceID, "power", pcomfortcloud.constants.Power.On)
        device.Update(nValue=1, sValue="100")
        p.powerOn = 1
    elif (Command == "Off"):
        update_device_id(device.DeviceID, "power", pcomfortcloud.constants.Power.Off)
        device.Update(nValue=0, sValue="0")
        p.powerOn = 0
    elif (Command == "Set Level"):
        if (device.nValue != p.powerOn or (device.sValue != Level) and Level != "--"):
            if ("[Target temp]" in device.Name):
                update_device_id(device.DeviceID, "temperature", float(Level))
            if ("[Mode]" in device.Name):
                operationmode = (Level / 10) - 1
                update_device_id(device.DeviceID, "mode", int(operationmode))
            elif ("[Fan Speed]" in device.Name):
                fanspeed = (Level / 10) - 1
                update_device_id(device.DeviceID, "fanSpeed", int(fanspeed))
            elif ("[Eco Mode]" in device.Name):
                ecomode = (Level / 10) - 1
                update_device_id(device.DeviceID, "eco", int(ecomode))
            elif ("[Air Swing]" in device.Name):
                airswing = (Level / 10) - 1
                update_device_id(device.DeviceID, "airSwingVertical", int(airswing))
            device.Update(nValue=p.powerOn, sValue=str(Level))

def get_device_hash_guid(device_id):
    for key, value in config.client._device_indexer.items():
        if value == device_id:
            matching_key = key
            break
    return matching_key