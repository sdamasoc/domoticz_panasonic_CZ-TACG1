import json
import re
import requests
import Domoticz
import config
import urllib.parse
import os
import common
import time
from datetime import datetime
from html import unescape

power_pump = 0
power_tank = 0

# extracts a string from a regex
def extract_from_regex(string, regex):
    # regex = r"var deviceConf = eval\('\((.+?)\)'\);"
    match = re.search(regex, string)
    if match:
        return match.group(1).replace('\\"', '"').replace("'",'"')
    else:
        return None
    
def get_aquarea_token():
    # if token already exist reuse it
    if os.path.exists(config.aquarea_token_file_path):
        with open(config.aquarea_token_file_path, 'r') as token_file:
            token = token_file.read().strip()
            Domoticz.Log("Reusing existing aquarea token=" + token)
            return token
    # else 
    
    ### start auth calls ###
    # call 1
    Domoticz.Debug("# call 1")
    headers=get_headers()
    response = requests.post(url=f'{config.aquarea_url}/remote/v1/api/auth/login', headers=headers)
    cookies = response.cookies.get_dict()

    com_auth0_state = cookies.get('com.auth0.state', None)
    Domoticz.Debug(f'com_auth0_state: {com_auth0_state}')

    jsonResponse = json.loads(response.text)
    authorize_url = jsonResponse["authorizeUrl"] 
    Domoticz.Debug(f'authorize_url: {authorize_url}')

    # call 2
    Domoticz.Debug("# call 2")
    response = requests.get(url=authorize_url, allow_redirects=False)
    cookies = response.cookies.get_dict()

    location = response.headers["Location"]
    Domoticz.Debug(f'location: {location}')
    
    auth0_compat = cookies.get('auth0_compat', None)
    Domoticz.Debug(f'auth0_compat: {auth0_compat}')

    auth0 = cookies.get('auth0', None)
    Domoticz.Debug(f'auth0: {auth0}')

    did = cookies.get('did', None)
    Domoticz.Debug(f'did: {did}')

    didCompat = cookies.get('did_compat', None)
    Domoticz.Debug(f'didCompat: {didCompat}')

    # call 3
    Domoticz.Debug("# call 3")
    headers= {
        'Referer': config.aquarea_url,
        'Cookie': f'auth0={auth0}; auth0_compat={auth0_compat}; did={did}; did_compat={didCompat};',
    }
    response = requests.get(url=f'{config.authglb_url}{location}', headers=headers, allow_redirects=False)
    cookies = response.cookies.get_dict()
    csrf = cookies.get('_csrf', None)
    Domoticz.Debug(f'_csrf: {csrf}')

    clientId=get_param_from_url(location, "client")
    Domoticz.Debug(f'clientId: {clientId}')

    state=get_param_from_url(location, "state")
    Domoticz.Debug(f'state: {state}')

    # call 4
    Domoticz.Debug("# call 4")
    headers={
        'auth0-client': config.auth0_client,
        'accept': '*/*',
        'Content-Type': 'application/json;',
        'content-type': 'application/json' ,
        'referer': f'{config.authglb_url}{location}',
        'cookie': f'_csrf={csrf}; auth0={auth0}; auth0_compat={auth0_compat}; did={did}; did_compat={didCompat};',
    }
    data={
        "client_id": clientId,
        "redirect_uri": f"{config.aquarea_url}/authorizationCallback?lang=en",
        "tenant": "pdpauthglb-a1",
        "response_type": "code",
        "scope": "openid offline_access",
        "audience": f"{config.digital_panasonic_url}/{clientId}/api/v1/",
        "_csrf": csrf,
        "state": state,
        "_intstate": "deprecated",
        "username": f"{config.username}",
        "password": f"{config.password}",
        "lang": "en",
        "connection": "PanasonicID-Authentication",
      }
    response = requests.post(url=f'{config.authglb_url}/usernamepassword/login', headers=headers, json=data, allow_redirects=False)

    action_url = extract_action_url(response.text)
    form_data = extract_form_data(response.text)

    Domoticz.Debug(f"Action URL: {action_url}")
    Domoticz.Debug(f"Form Data: {form_data}")
    
    # call 5
    Domoticz.Debug("# call 5")
    headers['content-type']='application/x-www-form-urlencoded; charset=UTF-8'
    response = requests.post(url=action_url, headers=headers, data=urllib.parse.urlencode(form_data), allow_redirects=False)

    location = response.headers["Location"]
    Domoticz.Debug(f"location={location}")

    # call 6
    Domoticz.Debug("# call 6")
    headers={'cookie': f'_csrf={csrf}; auth0={auth0}; auth0_compat={auth0_compat}; did={did}; did_compat={didCompat};'}
    response = requests.get(url=f'{config.authglb_url}{location}', headers=headers, data=urllib.parse.urlencode(form_data), allow_redirects=False)

    cookies = response.cookies.get_dict()

    auth0_compat = cookies.get('auth0_compat', None)
    Domoticz.Debug(f'auth0_compat: {auth0_compat}')

    auth0 = cookies.get('auth0', None)
    Domoticz.Debug(f'auth0: {auth0}')

    location = response.headers["Location"]
    Domoticz.Debug(f"location={location}")

    # call 7
    Domoticz.Debug("# call 7")
    headers={
        'user-agent': 'curl/7.81.0',
        'accept': '*/*',
        'cookie': f'_csrf={csrf}; auth0={auth0}; auth0_compat={auth0_compat}; did={did}; did_compat={didCompat};'
    }
    response = requests.get(url=location, headers=headers, allow_redirects=False)

    cookies = response.cookies.get_dict()
    access_token = cookies.get('accessToken', None)
    ### end auth calls ###

    if not access_token:
        Domoticz.Log(f'Could not authenticate to Aquarea Smart Panasonic: {response.text}')
        return None
    else:
        Domoticz.Log(f"get_aquarea_token={access_token}")
        # save the token
        with open(config.aquarea_token_file_path, 'w') as token_file:
            token_file.write(access_token)
        return access_token

# load device
def load_device(retried=None):
    response = requests.post(
        url=f'{config.aquarea_url}/remote/a2wStatusDisplay',
        headers=get_headers(config.aquarea_token),
        data='Registration-ID',
    )
    # TODO handle "Logged out due to system error"
    # Domoticz.Log("load_device=" + response.text)
    if "const staticErrorMessage_XXXX_0998 = 'Logged out due to system error" in response.text:
        if retried:
            Domoticz.Error("Retries exausted")
        else:
            handle_token_expiration()
            return load_device(True)
    result = {
        "selectedDeviceId": extract_from_regex(response.text, r"var selectedDeviceId = '(.*)';"),
        "selectedDeviceName": extract_from_regex(response.text, r"var selectedDeviceName = '(.*)';"),
        "deviceConf": json.loads(extract_from_regex(response.text, r"var deviceConf = eval\('\((.*)\)'\);"))
    }
    Domoticz.Log(f"load_device={result}")
    return result

# load device details
def load_device_details(device_id):
    url=f'{config.aquarea_url}/remote/v1/api/devices/{device_id}?var.deviceDirect=1'
    headers=get_headers(config.aquarea_token)
    response = requests.get(url=url, headers=headers)
    Domoticz.Log(f"load_device_details={response.text}")
    return handle_response(response, lambda: load_device_details(device_id))

# load device details
def get_historic_data(device_id):
    url=f"{config.aquarea_url}/remote/v1/api/consumption/{device_id}?date={datetime.now().strftime('%Y-%m-%d')}&_={int(time.time())}"
    headers=get_headers(config.aquarea_token, device_id, device_id[6:16])
    response = requests.get(url=url, headers=headers)
    #Domoticz.Log(f"get_historic_data={response.text}")
    res=handle_response(response, lambda: get_historic_data(device_id))
    energyConsumption  = 0
    if 'dateData' in res:
        for date_data in res['dateData']:
            for data_set in date_data['dataSets']:
                if data_set['name'] == 'energyShowing':
                    for data in data_set['data']:
                        if data['name'] == 'Consume' and data['values']:
                            consume_data = data
    else:
        Domoticz.Error(f"No res['dateData'] found in get_historic_data !!!")
        Domoticz.Log(f"url={url}")
        Domoticz.Log(f"headers={headers}")
        Domoticz.Log(f"response={response.text}")
        return '-255;0' # return a dummy value to skip
    energyConsumption  += sum(value for value in consume_data['values'] if value is not None)
    energyConsumption  = int(energyConsumption  * 1000)

    last_hour=int(f"{datetime.now().strftime('%H')}")
    last_consumption_value = None
    if (last_hour-1) >=0:
        last_consumption_value = consume_data["values"][(last_hour-1)] 
    if not last_consumption_value and last_consumption_value != 0:
        Domoticz.Log(f"last_consumption_value for {device_id} return {last_consumption_value}, use -255")
        last_consumption_value = -255
    last_consumption_value = int(last_consumption_value * 1000)
    
    Domoticz.Log(f"get_historic_data for {device_id} = {last_consumption_value};{energyConsumption}")
    return f'{last_consumption_value};{energyConsumption}'

# call the api to update device parameter
def update_device_id(device_id, target, parameter_name, parameter_value):
    Domoticz.Log(f"updating DeviceId={device_id}, {parameter_name}={parameter_value}... (power_pump={power_pump}, power_tank={power_tank})")

    url=f'{config.aquarea_url}/remote/v1/api/devices/{device_id}'
    
    data={
        'status': [
            {
                'deviceGuid': device_id,
            }
        ]
    }
    if 'operationMode' in parameter_name:
        data['status'][0][f'{parameter_name}'] = parameter_value
    if target == 'zoneStatus':
        data['status'][0]['operationStatus'] = (power_tank or parameter_value)
        data['status'][0][f'{target}'] = [{'zoneId': 1, f'{parameter_name}': parameter_value}]
        data['status'][0]['operationMode'] = parameter_value
        
    if target == 'tankStatus':
        data['status'][0]['operationStatus'] = (power_pump or parameter_value)
        data['status'][0][f'{target}'] = [{f'{parameter_name}': parameter_value}]
    payload=json.dumps(data)
    headers=get_headers(config.aquarea_token, device_id)
    response = send_request("POST", url, headers=headers, data=payload)
    Domoticz.Log(f"updating device with payload={payload}")
    Domoticz.Log("update_device_id=" + response.text)
    # return handle_response(response, lambda: update_device_id(device_id, parameter_name, parameter_value))
    return

def get_headers(aquarea_token=None, device_id=None, device_gwid=None):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': config.aquarea_url,
        'Referer': f'{config.aquarea_url}',
        'X-APP-TYPE': '0',
        'X-APP-VERSION': config.api_version,
        'Accept': 'application/json; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15',
        'X-APP-NAME': 'Comfort Cloud',
        'X-CFC-API-KEY': '0',
        'X-APP-TIMESTAMP': common.get_timestamp(),
        'Registration-Id': '',
        'popup-screen-id': '1001',
    }
    if aquarea_token:
        headers['Cookie']=f'accessToken={config.aquarea_token};'
        headers['Referer']=f'{config.aquarea_url}/remote/a2wStatusDisplay'
        if device_id:
            headers['Cookie']=f'accessToken={config.aquarea_token}; selectedDeviceId={device_id};'
        if device_gwid:
            headers['Cookie']=f'selectedGwid={device_gwid}; selectedDeviceId={device_id}; deviceControlDate={int(time.time())}; accessToken={config.aquarea_token}; selectedDeviceId={device_id}; operationDeviceTop=2'
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
        "You have been logged out due to inactivity. Please log in again": handle_token_expiration,
        "New version app has been published": handle_api_version_update,
    }

    for error_text, handler in error_handlers.items():
        if error_text in response.text:
            handler()
            return retry_func()
        elif '"errorMessage":' in response.text:
            Domoticz.Error(f"error not handled in response {response.text} for retry_func={retry_func}")
    return json.loads(response.text)

def handle_token_expiration():
    Domoticz.Log("Token is expired, get a new token")
    # if token file exists delete it
    if os.path.exists(config.aquarea_token_file_path):
        os.remove(config.aquarea_token_file_path)
    config.aquarea_token = get_aquarea_token()

def handle_api_version_update():
    Domoticz.Log("New version app has been published")
    # if api_version_file_path file exists delete it
    if os.path.exists(config.api_version_file_path):
        os.remove(config.api_version_file_path)
    config.api_version = common.get_app_version()



def add_device(devicename, nbdevices):
    # aquarea has a special token
    config.aquarea_token = get_aquarea_token()
    # load the device
    device=load_device()

    deviceConf=device['deviceConf']
    selectedDeviceId=device['selectedDeviceId']

    Domoticz.Log(f"Creating aquarea devices for {devicename}, DeviceID={selectedDeviceId}, Unit={nbdevices}...")

    if deviceConf['configration']:
        for zone in deviceConf['configration'][0]['zoneInfo']:
            zoneId=zone['zoneId']
            zoneName=zone['zoneName']
            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Pump Power]", Unit=nbdevices, Image=16, TypeName="Switch", Used=1, DeviceID=selectedDeviceId).Create()

            # operationMode
            Options = {"LevelActions": "|||", "LevelNames": "|Heat|Cool|Auto", "LevelOffHidden": "true", "SelectorStyle": "1"}
            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Mode]", Unit=nbdevices, TypeName="Selector Switch", Image=16, Options=Options, Used=1, DeviceID=selectedDeviceId).Create()

            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Pump Heat Temp]", Unit=nbdevices, Type=242, Subtype=1, Image=16, Used=1, DeviceID=selectedDeviceId).Create()

            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Pump Temp Now]", Unit=nbdevices, TypeName="Temperature", Used=1, DeviceID=selectedDeviceId).Create()

            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Outdoor Temp]", Unit=nbdevices, TypeName="Temperature", Used=1, DeviceID=selectedDeviceId).Create()

            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Tank Power]", Unit=nbdevices, Image=11, TypeName="Switch", Used=1, DeviceID=selectedDeviceId).Create()
            
            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Tank Heat temp]", Unit=nbdevices, Type=242, Subtype=1, Image=16, Used=1, DeviceID=selectedDeviceId).Create()

            nbdevices = nbdevices + 1
            Domoticz.Device(Name=devicename + "[Tank Temp Now]", Unit=nbdevices, TypeName="Temperature", Used=1, DeviceID=selectedDeviceId).Create()
    
            # energyConsumption
            nbdevices = nbdevices + 1
            #Use Options={'EnergyMeterMode': '1' } to set energyMeterMode to "Calculated". Default is "From Device"
            Options={'EnergyMeterMode': '0' }            
            Domoticz.Device(Name=devicename + "[Energy]", Unit=nbdevices, TypeName="kWh", Options=Options, Used=1, DeviceID=selectedDeviceId).Create()

            Domoticz.Log(f"Device " + devicename + " created (DeviceID={selectedDeviceId}).")
    else:
        Domoticz.Log(f"Device {devicename} is not responding")


def handle_aquarea(device, devicejson):
    global power_pump
    global power_tank
    value = "----"
    if ("[Pump Power]" in device.Name):
        power_pump = int(devicejson['status'][0]['zoneStatus'][0]['operationStatus'])
        value = str(power_pump * 100)
    elif ("[Mode]" in device.Name):
        operationmode = int(devicejson['status'][0]['operationMode'])
        value = str(operationmode * 10)
    elif ("[Pump Heat Temp]" in device.Name):
        value = get_str_of_float(devicejson['status'][0]['zoneStatus'][0]['heatSet'])
    elif ("[Pump Temp Now]" in device.Name):
        value = get_str_of_float(devicejson['status'][0]['zoneStatus'][0]['temparatureNow'])
    elif ("[Outdoor Temp]" in device.Name):
        value = get_str_of_float(devicejson['status'][0]['outdoorNow'])
    elif ("[Tank Power]" in device.Name):
        power_tank = int(devicejson['status'][0]['tankStatus'][0]['operationStatus'])
        value = str(power_tank * 100)
    elif ("[Tank Heat temp]" in device.Name):
        value = get_str_of_float(devicejson['status'][0]['tankStatus'][0]['heatSet'])
    elif ("[Tank Temp Now]" in device.Name):
        value = get_str_of_float(devicejson['status'][0]['tankStatus'][0]['temparatureNow'])
    elif ("[Energy]" in device.Name):
        value = get_historic_data(device.DeviceID) # historic data is in kWh, domoticz wants W
        if value.startswith('-255'):
            Domoticz.Log(f"keep previous value of get_historic_data for {device.DeviceID} = {device.sValue}")
            value = device.sValue  # keep previous value

    #Domoticz.Debug(f"Device ID: {device.DeviceID}, Name: {device.Name}, value: {value}")
    # update value only if value has changed
    if device.sValue != str(value):
        nValue = power_pump
        if "Tank" in device.Name:
            nValue = power_tank
        device.Update(nValue=nValue, sValue=str(value))

def get_str_of_float(value):
    if (value):
        return str(float(value))
    else:
        return "----"

def update_aquarea(p, Command, Level, device):
    if (Command == "On"):
        if ("[Pump Power]" in device.Name):
            update_device_id(device.DeviceID, "zoneStatus", "operationStatus", 1)
        elif ("[Tank Power]" in device.Name):
            update_device_id(device.DeviceID, "tankStatus", "operationStatus", 1)
        device.Update(nValue=1, sValue="100")
        p.powerOn = 1
    elif (Command == "Off"):
        if ("[Pump Power]" in device.Name):
            update_device_id(device.DeviceID, "zoneStatus", "operationStatus", 0)
        elif ("[Tank Power]" in device.Name):
            update_device_id(device.DeviceID, "tankStatus", "operationStatus", 0)
        device.Update(nValue=0, sValue="0")
        p.powerOn = 0
    elif (Command == "Set Level"):
        if (device.nValue != p.powerOn or (device.sValue != Level) and Level != "--"):
            if ("[Mode]" in device.Name):
                update_device_id(device.DeviceID, None, "operationMode", mapModeLevel(Level))
            if ("[Pump Heat Temp]" in device.Name):
                update_device_id(device.DeviceID, "zoneStatus", "heatSet", float(Level))
            elif ("[Tank Heat temp]" in device.Name):
                update_device_id(device.DeviceID, "tankStatus", "heatSet", float(Level))
            device.Update(nValue=p.powerOn, sValue=str(Level))

def mapModeLevel(Level):
    # strange but in update mode 2=HEAT, 3=COLD, 8=AUTO
    if Level == 10: 
        return 2 # 2=> set HEAT
    elif Level == 20:
        return 3 # 3=> set COLD
    elif Level == 30: 
        return 8 # 8=> set AUTO

def get_param_from_url(url, param_name):
    return [i.split("=")[-1] for i in url.split("?", 1)[-1].split("&") if i.startswith(param_name + "=")][0]

def extract_action_url(data):
    action_url_match = re.search(r'action="(.+?)"', data, re.IGNORECASE)
    action_url = action_url_match.group(1) if action_url_match else None
    return action_url

def extract_form_data(data):
    inputs = re.findall(r'<input([^>]+?)>', data, re.IGNORECASE) or []

    # Créer le dictionnaire pour stocker les données du formulaire
    form_data = {}

    for input_tag in inputs:
        name_match = re.search(r'name="(.+?)"', input_tag, re.IGNORECASE)
        value_match = re.search(r'value="(.+?)"', input_tag, re.IGNORECASE)
        
        if name_match and value_match:
            name = name_match.group(1)
            value = unescape(value_match.group(1))
            form_data[name] = value
    return form_data