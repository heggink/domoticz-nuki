"""
<plugin key="NukiLock" name="Nuki Lock Plugin" author="heggink" version="1.0.5">
    <params>
        <param field="Port" label="Port" width="75px" required="true" default="8008"/>
        <param field="Mode1" label="Bridge IP" width="150px" required="true" default="192.168.1.123"/>
        <param field="Mode2" label="Bridge token" width="75px" required="true" default="abcdefgh"/>
        <param field="Mode4" label="Bridge port" width="75px" required="true" default="8080"/>
        <param field="Mode3" label="Poll interval (m)" width="75px" required="true" default="10"/>	
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
                <option label="Logging" value="File"/>
            </options>
        </param>
    </params>
</plugin>
"""

#  nuki python plugin
#
# Author: heggink, 2018
#
# this plugin provides domoticz HTTP support for the Nuki locks (www.nuki.io)
# it requires a Nuki bridge in order to function
# the Nuki bridge needs to placed in developer mode
# version control:
# 0.0.1:
#    reads state changes coming from the locks (ssued by app, manual, other)
#    read locks from the bridge on startup
#    create devices in domoticz for every non existing lock
#    handle state changes coming from the locks (app, manual, other) and update domoticz device
#    onCommand: execute device changes from domoticz that need to be executed by the lock
# todo:
#    onHeartbeat: heart beats in case the lock state gets out of sync with domoticz and update domoticz
# prerequisites:
#    Hardware needs to be set up per bridge, each bridge can contain multiple locks
#    setting up the bridge (incl developer mode to use the API assigning tokens and such)
#    adding lock(s) to the bridge
#
# changelog
#    1.0.1 fixed tab error on line 88
#    1.0.3 added bridge port 
#    1.0.4 multiple small fixes as per giejay's fork
#    1.0.5 catching success = false onheartbeat
#
import Domoticz
import json
import sys
import socket
import urllib.request
import urllib.error
from urllib.error import URLError, HTTPError

class BasePlugin:
    enabled = False
    httpServerConn = None
    httpServerConns = {}
    httpClientConn = None
    heartbeats = 0
    pollInterval = 0
    bridgeIP = ' '
    bridgeToken = ' '
    callbackPort = 0
    bridgePort = 0
    myIP = ' '
    numLocks = 0
    lockNames = []
    lockIds = []

#     PARAMETERS NEED TO GO HERE

    def __init__(self):
        return

#   on startup:
#   determine how many locks configured in the bridge
#   check if lock device(s) exist and create if not
#   check if callback exists for the lock(s) and create if not there
#   test the lock status for each lock and ensure that the domoticz lock device is the same

    def onStart(self):
        if Parameters["Mode6"] != "Normal":
            Domoticz.Debugging(1)
        DumpConfigToLog()
        self.callbackPort = Parameters["Port"]
        self.bridgeIP = Parameters["Mode1"]
        self.bridgeToken = Parameters["Mode2"]
        self.pollInterval = int(Parameters["Mode3"])
        self.bridgePort = Parameters["Mode4"]

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.myIP = s.getsockname()[0]
        s.close()
        Domoticz.Debug("My IP is " + self.myIP)
        Domoticz.Log("Nuki plugin started on IP " + self.myIP + " and port " + str(self.callbackPort))

        req = 'http://' + self.bridgeIP + ':' + self.bridgePort + '/list?token=' + self.bridgeToken
        Domoticz.Debug('REQUESTING ' + req)
#        resp = urllib.request.urlopen(req).read()

        try:
            resp = urllib.request.urlopen(req).read()
        except HTTPError as e:
            Domoticz.Error('NUKI HTTPError code: '+ str(e.code))
        except URLError as e:
            Domoticz.Error('NUKI  URLError Reason: '+ str(e.reason))
        else:
            strData = resp.decode("utf-8", "ignore")
            Domoticz.Debug("Lock list received " + strData)
            resp = json.loads(strData)
            num = len(resp)
            Domoticz.Debug("I count " + str(num) + " locks")
            self.numLocks = num

#	    create a lock device for every listed lock
#	    and update the lock state and battery immediately as listed in the response
            for i in range (num):
                if (i+1 not in Devices):
                    Domoticz.Device(Name=resp[i]["name"], Unit=i+1, TypeName="Switch", Switchtype=19, Used=1).Create()
                    Domoticz.Log("Lock " + resp[i]["name"] + " created.")
                else:
                    Domoticz.Debug("Lock " + resp[i]["name"] + " already exists.")

                self.lockNames.append(resp[i]["name"])
                self.lockIds.append(resp[i]["nukiId"])
                Domoticz.Debug("Lock batt " + str(resp[i]["lastKnownState"]["batteryCritical"]))
                Domoticz.Debug("Lock stateName " + resp[i]["lastKnownState"]["stateName"])
                Domoticz.Debug("Lock state " + str(resp[i]["lastKnownState"]["state"]))
		
                if (resp[i]["lastKnownState"]["batteryCritical"]):
                    batt = 0
                else:
                    batt = 255

                nval = -1
                sval = "Unknown"
                
                if (resp[i]["lastKnownState"]["state"] == 1):
                    sval = 'Locked'
                    nval = 1
                elif (resp[i]["lastKnownState"]["state"] == 3):
                    sval = 'Unlocked'
                    nval = 0
                Devices[i+1].Update(nValue=nval, sValue=str(sval), Description=str(resp[i]["nukiId"]), BatteryLevel=batt)

            Domoticz.Debug("Lock(s) created")
            DumpConfigToLog()
	
#           check if callback exists and, if not, create
            req = 'http://' + self.bridgeIP + ':' + self.bridgePort + '/callback/list?token=' + self.bridgeToken
            Domoticz.Debug('checking callback ' + req)
            found = False
        
            try:
                resp = urllib.request.urlopen(req).read()
            except HTTPError as e:
                Domoticz.Error('NUKI HTTPError code: '+ str(e.code))
            except URLError as e:
                Domoticz.Error('NUKI  URLError Reason: '+ str(e.reason))
            else:
                strData = resp.decode("utf-8", "ignore")
                Domoticz.Debug("Callback list received " + strData)
                resp = json.loads(strData)
                urlNeeded = 'http://' + self.myIP + ':' + self.callbackPort
                num=len(resp["callbacks"])
                Domoticz.Debug("Found callbacks: " + str(num))
                if num > 0:
                    for i in range (num):
                        if resp["callbacks"][i]["url"] == urlNeeded:
                            Domoticz.Debug("Callback already installed")
                            found = True

            if not found:
#           create callback for the bridge (all lock changes reported on this callback)
                callback = 'http://' + self.bridgeIP + ':' + self.bridgePort + '/callback/add?url=http%3A%2F%2F' + self.myIP + '%3A' + self.callbackPort + '&token=' + self.bridgeToken
                Domoticz.Log('Installing callback ' + callback)

                try:
                    resp = urllib.request.urlopen(callback).read()
                except HTTPError as e:
                    Domoticz.Error('NUKI HTTPError code: '+ str(e.code))
                except URLError as e:
                    Domoticz.Error('NUKI  URLError Reason: '+ str(e.reason))
                else:
                    strData = resp.decode("utf-8", "ignore")
                    Domoticz.Debug("Callback response received " + strData)
                    resp = json.loads(strData)
                    if resp["success"]:
                        Domoticz.Log("Nuki Callback install succeeded")
                    else:
                        Domoticz.Error("Unable to register NUKI callback")

#	    now listen on the port for any state changes
            else:
                self.httpServerConn = Domoticz.Connection(Name="Server Connection", Transport="TCP/IP", Protocol="HTML", Port=Parameters["Port"])
                self.httpServerConn.Listen()

            Domoticz.Debug("Leaving on start")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Log("Connected successfully to: "+Connection.Address+":"+Connection.Port)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
        Domoticz.Log(str(Connection))
        if (Connection != self.httpClientConn):
            self.httpServerConns[Connection.Name] = Connection

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called for connection: " + Connection.Address + ":" + Connection.Port)
        strData = Data.decode("utf-8", "ignore")
        Domoticz.Debug("Lock message received " + strData)
        Response = strData[strData.index('{') :]
        Domoticz.Debug("JSON is " + Response)

        Response = json.loads(Response)

        lock_id = Response["nukiId"]
        foundlock = self.lockIds.index(lock_id)
        Domoticz.Debug("Found lock id " + str(foundlock))
        Domoticz.Debug("Found lock name " + self.lockNames[foundlock])
        if (Response["batteryCritical"]):
            batt = 10
        else:
            batt = 255

        Domoticz.Log(self.lockNames[foundlock] + " requests update: " + Response["stateName"])
        if (Response["state"] == 1):
            Domoticz.Debug(self.lockNames[foundlock] + " is LOCKED ")
            sval = 'Locked'
            nval = 1
            UpdateDevice(foundlock + 1, nval, sval, batt)
        elif (Response["state"] == 3):
            Domoticz.Debug(self.lockNames[foundlock] + " is UNLOCKED ")
            sval = 'Unlocked'
            nval = 0
            UpdateDevice(foundlock + 1, nval, sval, batt)
        elif (Response["state"] == 0):
            Domoticz.Error("Nuki lock" + self.lockNames[foundlock] + " UNCALIBRATED ")
        elif (Response["state"] == 254):
            Domoticz.Error("Nuki lock" + self.lockNames[foundlock] + " MOTOR BLOCKED ")
        else:
            Domoticz.Log("Nuki lock temporary state ignored" + Response["stateName"])

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        lockid = str(self.lockIds[Unit-1])
        lockname = self.lockNames[Unit-1]
        Domoticz.Log("Switch device " + lockid + " with name  " + lockname)

        if Command == 'On':
            action = 2
            sval = 'Locked'
            nval = 1
        else:
            action = 1
            sval = 'Unlocked'
            nval = 0

        Domoticz.Debug('setting action to ' + str(action))
        req = 'http://' + str(self.bridgeIP) + ':' + self.bridgePort + '/lockAction?nukiId=' + lockid + '&action=' + str(action) + '&token=' + str(self.bridgeToken)
        Domoticz.Debug('Executing lockaction ' + str(req))
        try:
            resp = urllib.request.urlopen(req).read()
        except HTTPError as e:
            Domoticz.Error('NUKI HTTPError code: '+ str(e.code))
        except URLError as e:
            Domoticz.Error('NUKI  URLError Reason: '+ str(e.reason))
        else:
            strData = resp.decode("utf-8", "ignore")
            Domoticz.Debug("Lock command response received " + strData)
            resp = json.loads(strData)
            if not resp["success"]:
                Domoticz.Error("Error switching lockstatus for lock " + lockname)
            else:
                UpdateDevice(Unit, nval, sval, 0)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called for connection '" + Connection.Name + "'.")
        Domoticz.Debug("Server Connections:")
        for x in self.httpServerConns:
            Domoticz.Debug("--> " + str(x) + "'.")
        if Connection.Name in self.httpServerConns:
            del self.httpServerConns[Connection.Name]

    def onHeartbeat(self):
        #   On timer:
        #   poll every lock on the bridge
        #   if status different:
        #    change the lock status
        self.heartbeats += 1
        Domoticz.Debug("onHeartbeat called " + str(self.heartbeats))
#	heartbeat is every 10 seconds, pollinterval is in minutes 
        if (self.heartbeats / 6) >= self.pollInterval:
            self.heartbeats = 0
            Domoticz.Log("onHeartbeat check locks")
            for i in range (self.numLocks):
                nukiId = self.lockIds[i]
                req = 'http://' + self.bridgeIP + ':' + self.bridgePort + '/lockState&nukiId=' + str(nukiId) + '&token=' + self.bridgeToken
                Domoticz.Debug('Checking lockstatus ' + req)
                try:
                    resp = urllib.request.urlopen(req).read()
                except HTTPError as e:
                    Domoticz.Error('NUKI HTTPError code: '+ str(e.code))
                except URLError as e:
                    Domoticz.Error('NUKI  URLError Reason: '+ str(e.reason))
                else:
                    strData = resp.decode("utf-8", "ignore")
                    Domoticz.Debug("Lock status received " + strData)
                    resp = json.loads(strData)

                    if (resp["success"]):
                        if (resp["batteryCritical"]):
                            batt = 10
                        else:
                            batt = 255

                        if (resp["state"] == 1):
                            Domoticz.Debug(self.lockNames[i] + " is LOCKED ")
                            sval = 'Locked'
                            nval = 1
                            UpdateDevice(i + 1, nval, sval, batt)
                        elif (resp["state"] == 3):
                            Domoticz.Debug(self.lockNames[i] + " is UNLOCKED ")
                            sval = 'Unlocked'
                            nval = 0
                            UpdateDevice(i + 1, nval, sval, batt)
                        elif (resp["state"] == 0):
                            Domoticz.Error("Nuki lock" + self.lockNames[i] + " UNCALIBRATED ")
                        elif (resp["state"] == 254):
                            Domoticz.Error("Nuki lock" + self.lockNames[i] + " MOTOR BLOCKED ")
                        else:
                            Domoticz.Log("Nuki lock temporary state ignored" + resp["stateName"])
                    else:
                        Domoticz.Log("Nuki lock false response received")

global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def LogMessage(Message):
    if Parameters["Mode6"] != "Normal":
        Domoticz.Log(Message)
    elif Parameters["Mode6"] != "Debug":
        Domoticz.Debug(Message)
    else:
        f = open("http.html", "w")
        f.write(Message)
        f.close()


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


def DumpJSONResponseToLog(jsonmsg):
    if isinstance(jsonmsg, dict):
        Domoticz.Log("HTTP Details (" + str(len(jsonmsg)) + "):")
        for x in jsonmsg:
            if isinstance(jsonmsg[x], dict):
                Domoticz.Log("--->'" + x + " (" + str(len(jsonmsg[x])) + "):")
                for y in jsonmsg[x]:
                    Domoticz.Log("------->'" + y + "':'" + str(jsonmsg[x][y]) + "'")
            else:
                Domoticz.Log("--->'" + x + "':'" + str(jsonmsg[x]) + "'")

def UpdateDevice(Unit, nValue, sValue, batt):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    Domoticz.Debug("UpdateDevice called with " + str(Unit) + ' ' + str(nValue) + ' ' + str(sValue) + ' ' + str(batt))
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            if batt == 0:
#               if there are no battery data then do not update
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            else:
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue), BatteryLevel=batt)
            Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return
