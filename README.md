# domoticz-nuki
python plugin for the nuki locks
## BETA BETA BETA
## Prerequisites
This plugin requires python modules json and urllib
It also requires all the locks to be assigned to the bridge
and for the bridge to be put in developer mode in order to use the HTTP API

## Installation
cd ~/domoticz/plugins
git clone https://github.com/heggink/domoticz-nuki
sudo service domoticz.sh restart
Then create a hardware device for each bridge
# Multiple bridges REQUIRE SEPARATE PORTS!!!
If not then the messages from one bridge will be sent to the plugin of the other and vice versa

Once started, the plugin will
- create lock devices for all locks configured in the bridge
- create a callback in the bridge that sends lock status update messages to the plugin
- polls all the configured locks at the poll interval specified
# PLS NOTE that nuki locks drain batteries fast if polling is set too low
Since the lock status is updated on start and the lock shouldn't get out of sync as long as the plugin runs
a short polling time should not be required at all
Alternatively, swap the batteries for a (hacked) power supply

## Parameters
| Parameter | Description |
| :--- | :--- |
| **Port** | free port on your system for the bridge to send status messages to (default 8008) |
| **Bridge IP** | IP address of the Nuki Bridge |
| **Bridge token** | Token configired when putting the bridge in developer mode |
| **Poll interval in minutes** | Polling time in minutes for the plugin to check lock status |
## Devices
| Name | Description |
| :--- | :--- |
| **Lock device** | For each lock configured in the bridge |

## To do
1) Delete the callback on deletion of the device
Currently, all callbacks need to be removed manually: http://[IP OF THE BRIDGE]:8080/callback/remove?id=[ID CREATED BY THE PLUGIN]&token=[TOKEN]
Callbacks can be easily listed: http://[IP OF THE BRIDGE]:8080/callback/list?token=[TOKEN]
# Please note that a max of 3 callbacks is allowed
This should allow you to install this next to any existing scripts to test
