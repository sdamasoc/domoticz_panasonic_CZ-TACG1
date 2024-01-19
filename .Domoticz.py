import plugin

# Mock Domoticz.py

# change this values with your credentials
Parameters = {
        "Mode1": 60,
        "Mode2": "Debug",
        "Mode3": "1.20.0",
        "Username": "<YOUR_USERNAME>",
        "Password": "<YOUR_PASSWORD>"
    }

Devices = {}

class Device:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.__dict__['sValue']=""
        self.__dict__['nValue']=""

    def Create(self):
        print(f"Device created: {self.__dict__}")
        Devices[self.__dict__['Unit']] = self

    def Update(self, nValue, sValue):
        print(f"Device {self.__dict__['Name']} updated: nValue={nValue}, sValue={sValue}")


@staticmethod
def Log(message):
    print(f"Log: {message}")

@staticmethod
def Debug(message):
    print(f"Debug: {message}")

@staticmethod
def Error(message):
    print(f"Error: {message}")

def Debugging(level):
    return
