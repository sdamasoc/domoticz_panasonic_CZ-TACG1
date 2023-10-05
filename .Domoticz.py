import plugin

# Mock Domoticz.py

# change this values with your credentials
Parameters = {
        "Mode1": 60,
        "Mode2": "Debug",
        "Mode3": "1.17.0",
        "Address": "https://accsmart.panasonic.com",
        "Username": "<USERNAME>",
        "Password": "<PASSWORD>"
    }

Devices = {}

class Device:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def Create(self):
        print(f"Device created: {self.__dict__}")

    def Update(self, nValue, sValue):
        print(f"Device updated: nValue={nValue}, sValue={sValue}")


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
