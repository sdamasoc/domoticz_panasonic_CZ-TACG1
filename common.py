import Domoticz
import requests
import config
import os
import requests
import Domoticz
from datetime import datetime
import config

# get current timestamp
def get_timestamp():
    return f"'{datetime.now().strftime('%Y%m%d %H:%M:%S')}'"

# call app store to get latest version
def get_app_version():
    version = config.api_version
    # if api_version_file_path already exist reuse it
    if os.path.exists(config.api_version_file_path):
        with open(config.api_version_file_path, 'r') as version_file:
            version = version_file.read().strip()
            Domoticz.Log("Reusing existing api_version=" + version)
            return version
    # else    
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

        # save the token
        with open(config.api_version_file_path, 'w') as version_file:
            version_file.write(version)

    except requests.RequestException as e:
        Domoticz.Error(f"Failed to get the latest Comfort Cloud version: {e}")

    except Exception as e:
        Domoticz.Error(f"An unexpected error occurred: {e}")

    return version