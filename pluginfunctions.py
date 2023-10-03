import requests
import json
import Domoticz
from datetime import datetime
import config

############################
# Generic helper functions #
############################

# get current timestamp
def get_timestamp():
    return f"'{datetime.now().strftime('%Y%m%d %H:%M:%S')}'"

# call app store to get latest version
def get_app_version():
    version = config.api_version
    try:
        Domoticz.Log("Getting latest Comfort Cloud version from the App Store...")
        response = requests.request("GET", config.appstore_url)
        response.raise_for_status()  # Vérifiez si la requête a réussi; sinon, une exception est levée

        html_string = response.text
        start_str = 'class="l-column small-6 medium-12 whats-new__latest__version">Version '
        end_str = '</p>'

        start_pos = html_string.find(start_str)
        if start_pos != -1:
            start_pos += len(start_str)
            end_pos = html_string.find(end_str, start_pos)
            if end_pos != -1:
                version = html_string[start_pos:end_pos]
                Domoticz.Log("get_app_version=" + version)

    except requests.RequestException as e:
        Domoticz.Error(f"Failed to get the latest Comfort Cloud version: {e}")

    except Exception as e:
        Domoticz.Error(f"An unexpected error occurred: {e}")

    return version



# call the api to get a token
def get_token():
    url = config.address + "/auth/login"

    payload = json.dumps({
        "language": 0,
        "loginId": config.username,
        "password": config.password
    })
    headers = {
        'X-APP-TYPE': '0',
        'X-APP-VERSION': config.api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'User-Agent': 'G-RAC',
        'X-APP-NAME': 'Comfort Cloud',
        'X-CFC-API-KEY': '0',
        'X-APP-TIMESTAMP': get_timestamp()
    }
    response = send_request("POST", url, headers=headers, data=payload)
    Domoticz.Log("get_token=" + response.text)
    res = json.loads(response.text)
    return res["uToken"]


# call the api to get device list
def get_devices():
    url = config.address + "/device/group/"

    headers = get_headers()
    response = send_request("GET", url, headers=headers)
    #Domoticz.Log("get_devices=" + response.text)
    return handle_response(response, get_devices)

# call the api to get device infos
def get_device_by_id(device_id):
    url = config.address + "/deviceStatus/now/" + device_id

    headers = get_headers()
    response = send_request("GET", url, headers=headers)
    Domoticz.Log("get_device_by_id=" + response.text)
    return handle_response(response, lambda: get_device_by_id(device_id))

# call the api to update device parameter
def update_device_id(device_id, parameter_name, parameter_value):
    Domoticz.Log("updating DeviceId=" + device_id + ", " + parameter_name + "=" + str(parameter_value) + "...")

    url = config.address + "/deviceStatus/control/"
    
    payload = json.dumps({
        "deviceGuid": device_id,
        "parameters": {parameter_name: parameter_value}
    })
    headers = get_headers()
    response = send_request("POST", url, headers=headers, data=payload)
    Domoticz.Log("update_device_id=" + response.text)
    return handle_response(response, lambda: update_device_id(device_id, parameter_name, parameter_value))

def get_headers():
    return {
        'X-APP-TYPE': '0',
        'X-APP-VERSION': config.api_version,
        'Accept': 'application/json; charset=UTF-8',
        'Content-Type': 'application/json',
        'X-User-Authorization': config.token,
        'User-Agent': 'G-RAC',
        'X-APP-NAME': 'Comfort Cloud',
        'X-CFC-API-KEY': '0',
        'X-APP-TIMESTAMP': get_timestamp()
    }

def send_request(method, url, headers=None, data=None):
    try:
        response = requests.request(method, url, headers=headers, data=data)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        #Domoticz.Error(f"Request failed: {e}")
        return response

def handle_response(response, retry_func):
    Domoticz.Debug(f'{retry_func.__name__} = {response.text}')

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
    config.token = get_token()

def handle_api_version_update():
    config.api_version = get_app_version()

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