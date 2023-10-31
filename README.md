[![CodeQL](https://github.com/sdamasoc/domoticz_panasonic_CZ-TACG1/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/sdamasoc/domoticz_panasonic_CZ-TACG1/actions/workflows/codeql-analysis.yml)

# Domoticz python plugin for Panasonic CZ-TACG1 wifi adapter
A Python plugin for Domoticz to communicate with Panasonic Cloud Comfort.
It was designed for CZ-TACG1 WiFi adapter but should work with all Panasonic Cloud Comfort devices.

# Getting started
If you don't have git:
```
sudo apt-get update
sudo apt-get install git
```
Goto to the plugins directory of your domoticz installation folder and clone this repository:
```
cd domoticz/plugins
git clone https://github.com/sdamasoc/domoticz_panasonic_CZ-TACG1.git domoticz_panasonic_CZ-TACG1
```
So in this case the directory structure should now be: domoticz/plugins/domoticz_panasonic_CZ-TACG1/plugin.py

Next, you need to restart Domoticz so that it will find the plugin:
```
 sudo systemctl restart domoticz.service
```
or
```
sudo service domoticz.sh restart
```
From here the plugin should be able to be set-up from the Domoticz interface. Go to the hardware page and look in the dropdown, you should find "Panasonic Airco (CZ-TACG1)"

Then, fill your email, password and click on "Add"

If you run Linux and the plugin does not show up in the hardware list, you may have to make the plugin.py file executable. Go to the directory and execute the command:
```
 chmod +x domoticz_panasonic_CZ-TACG1/plugin.py
```

https://www.domoticz.com/wiki/Using_Python_plugins

# Requirements
- This plugin requires python v3.8 (or greater)
- It uses python requests and simplejson modules to send and receive json content to panasonic cloud. If you don't have them execute `pip3 install requests` and `pip3 install simplejson` as root to install.

- You need a panasonic id associated with your devices to be able to use this plugin:
1. Create a new panasonic account here: [Panasonic ID Registration](https://csapl.pcpf.panasonic.com/Account/Register001?lang=en)
2. Verify email using the link sent to the email id specified
3. Sign into the Panasonic Comfort Cloud app on your smart device using the newly created Panasonic ID
4. Agree to the terms and conditions displayed in app
5. Agree to the privacy notice displayed in app
6. You should now be on the home screen of the App
7. Click the "+" button
8. Choose "Air Conditioner"
9. Use the device ID from the original device package
10. Enter the device password you used when originally setting up the device
11. In step 3: Enter a name for the aircon
12. Click Send Request
13. Log out of the app
14. Sign in with the original email account in the Panasonic Comfort Cloud App
15. Click the Device you've requested sharing for
16. Click the hamburger menu and expand the "Owner" menu item, click "User list"
17. You should now see an id with a waiting approval status
18. Click the "Waiting Approval" button
19. Select the "Allow both monitoring and controlling air conditioner" permission
20. Confirm
21. The waiting for approval button should have disappeared and replaced with a blue check icon
22. Use the newly created id in the homekit accessory configuration

(instructions copied from codyc1515: https://github.com/codyc1515/homebridge-panasonic-air-conditioner/)

Aquarea support inspired by: https://github.com/Hernas/homebridge-panasonic-heat-pump 

# Compatibility
This script was tested with:
* Domoticz Version: 2023.2
* Python Version: 3.10.12
* Ubuntu: 22.04.3 LTS 

# To test this plugin outside Domoticz
1. In plugin.py uncomment line: `from Domoticz import Parameters, Devices`
2. Rename .Domoticz.py to Domoticz.py
3. Put your credentials in Domoticz.py
4. Run testPlugin.py: `python testPlugin.py`