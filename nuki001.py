"""
<plugin key="NukiLock" name="Nuki Lock Plugin" author="heggink" version="0.0.1">
    <params>
        <param field="Port" label="Port" width="30px" required="true" default="8008"/>
        <param field="Mode1" label="Bridge IP" width="150px" required="true" default="http://<bridge ip>/"/>
        <param field="Mode2" label="Bridge token" width="75px" required="true" default="abcdefgh"/>
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
# todo:
#    read locks from the bridge on startup
#    create devices in domoticz for every non existing lock
#    handles state changes coming from the locks (app, manual, other) and update domoticz device
#    execute device changes from domoticz that need to be executed by the lock
#    heart beats in case the lock state gets out of sync with domoticz and update domoticz
# prerequisites:
#    Hardware needs to be set up per bridge, each bridge can contain multiple locks
#    setting up the bridge (incl developer mode to use the API assigning tokens and such)
#    adding lock(s) to the bridge
#
import Domoticz

class BasePlugin:
    enabled = False
    httpServerConn = None
    httpServerConns = {}
    httpClientConn = None
    heartbeats = 0

#     PARAMETERS NEED TO GO HERE

    def __init__(self):
        return

#   on startup:
#   determine how many locks configured in the bridge
#   check if lock device(s) exist and create if not
#   check if callback exists for the lock(s) and create if not there
#   test the lock status for each lock and ensure that the lock device is the same

    def onStart(self):
        if Parameters["Mode6"] != "Normal":
            Domoticz.Debugging(1)
        DumpConfigToLog()

        self.httpServerConn = Domoticz.Connection(Name="Server Connection", Transport="TCP/IP", Protocol="JSON",
                                                  Port=Parameters["Port"])
        self.httpServerConn.Listen()
        Domoticz.Log("Leaving on start")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Log("Connected successfully to: " + Connection.Address + ":" + Connection.Port)
        else:
            Domoticz.Log("Failed to connect (" + str(
                Status) + ") to: " + Connection.Address + ":" + Connection.Port + " with error: " + Description)
        Domoticz.Log(str(Connection))
        if (Connection != self.httpClientConn):
            self.httpServerConns[Connection.Name] = Connection

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called for connection: " + Connection.Address + ":" + Connection.Port)

        strData = Data.decode("utf-8", "ignore")
        Domoticz.Debug("Lock message received" + strData)
        Response = json.loads(strData)

#   if Response["state"] == "Locked":
#       log status message
#       if lockstatus != locked then
#       change the lock status to "Locked"
#   elif Response["state"] == "Unlocked":
#       log status message
#       if lockstatus != Unlocked then
#       change the lock status to "Unlocked"
#
#   elif Response["state"] == "uncalibrated" or Response["state"] == "motor blocked"
#       log status message log an error
#
#   "unlocking" "locking" "unlatching" "unlatched" "unlocked (lock ‘n’ go)"
#       log status message do nothing
#

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for connection '" + Connection.Name + "'.")
        Domoticz.Log("Server Connections:")
        for x in self.httpServerConns:
            Domoticz.Log("--> " + str(x) + "'.")
        if Connection.Name in self.httpServerConns:
            del self.httpServerConns[Connection.Name]

    def onHeartbeat(self):
        #   On timer:
        #   poll every lock on the bridge
        #   if status different:
        #    change the lock status
#        if (self.httpClientConn == None or self.httpClientConn.Connected() != True):
#            self.httpClientConn = Domoticz.Connection(Name="Client Connection", Transport="TCP/IP", Protocol="JSON",
#                                                      Address="127.0.0.1", Port=Parameters["Port"])
#            self.httpClientConn.Connect()
#            self.heartbeats = 0
#        else:
#            if (self.heartbeats == 1):
#                self.httpClientConn.Send({"Verb": "GET", "URL": "/page.html", "Headers": {"Connection": "keep-alive",
#                                                                                          "Accept": "Content-Type: text/html; charset=UTF-8"}})
#            elif (self.heartbeats == 2):
#                postData = "param1=value&param2=other+value"
#                self.httpClientConn.Send(
#                    {'Verb': 'POST', 'URL': '/MediaRenderer/AVTransport/Control', 'Data': postData})
#            elif (self.heartbeats == 3) and (Parameters["Mode6"] != "File"):
#                self.httpClientConn.Disconnect()
        self.heartbeats += 1

#On device:
#    case device status in:
#    "Locked":
#        log status message
#        send the lock a LOCK command.
#		If it's locked already then no harm done and no response will be received
#		If it's unlocked then it will lock causing it to send an lock confirmation
#		Onmessage will receive and notice the lock is locked alread so action needed
#
#    "Unlocked":
#        log status message
#        send the lock an UNLOCK command.
#		If it's unlocked already then no harm done and no response will be received
#		If it's locked then it will lock causing it to send an unlock confirmation
#		Onmessage will receive and notice the lock is unlocked alread so action needed

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

def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return
