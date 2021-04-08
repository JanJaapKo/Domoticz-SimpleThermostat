# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# Author: Jan-Jaap Kostelijk
#
# Domoticz plugin to a simple thermostat
#
"""
<plugin key="Domoticz-SimpleThermostat" name="Thermostat simple" author="Jan-Jaap Kostelijk" version="0.1.0" wikilink="https://github.com/JanJaapKo/DysonPureLink/wiki" externallink="https://github.com/JanJaapKo/DysonPureLink">
    <description>
        <h2>Sinple thermostat plugin</h2><br/>
        It reads the machine's states and sensors and it can control it via commands.<br/><br/>
        Used to control a heater binairy switch fro  external thermometer.
        <h2>Configuration</h2>
        MAin configuration is to connect the involved Domoticz Devcies. Look the IOdx's from Domoticz Device page (menu Setup -> Devices).<br/><br/>
        <ol>
            <li>The IP adress of the Domoticz instance that holds the thermometer and switch</li>
            <li>port number for the Domoticz instance</li>
            <li>Idx of the temperature setpoint</li>
            <li>Idx of the themometer (actual temperature)</li>
            <li>Idx os the switch that controls the heater</li>
            <li>refrsh period (interval for checking setpoint against actual)</li>
            <li>optional: log level</li>
        </ol>
        
    </description>
    <params>
        <param field="Address" label="Domoticz IP Address" required="true" default="127.0.0.1"/>
        <param field="Port" label="Domoticz Port" width="30px" required="true" default="8080"/>
        <param field="Mode3" label="Thermometer IDX" required="true" default="0"/>
        <param field="Mode4" label="Heater IDX" required="true" default="0"/>
        <param field="Mode2" label="Refresh interval" width="75px">
            <options>
                <option label="30s" value="3"/>
                <option label="1m" value="6"/>
                <option label="5m" value="30" default="true"/>
                <option label="10m" value="60"/>
                <option label="15m" value="90"/>
            </options>
        </param>
		<param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="Verbose" value="Verbose"/>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import json
#import urllib
#import urllib2
#import requests
from http import httpClient

class SimpleThermostatPlugin:
    #define class variables
    #plugin version
    enabled = False
    runCounter = 6
    ThermostatUnit = 1
    
    def __init__(self):
        self.httpClient = None
        self.connected = False

    def onStart(self):
        Domoticz.Debug("onStart called")
        #read out config parameters
        self.version = Parameters["Version"]
        self.version = "0.1.0"
        self.Thermometer = Parameters['Mode3']
        self.Heater = Parameters['Mode4']
        self.runCounter = int(Parameters['Mode2'])
        self.log_level = Parameters['Mode6']
        self.baseDeviceUrl = "{0}:{1}/json.htm?type=devices&rid=".format(Parameters["Address"].strip(),Parameters["Port"].strip())
        self.ThermometerUrl = self.baseDeviceUrl + self.Thermometer
        self.HeaterUrl = self.baseDeviceUrl + self.Heater
        
        if self.log_level == 'Debug':
            Domoticz.Debugging(2)
            DumpConfigToLog()
        if self.log_level == 'Verbose':
            Domoticz.Debugging(1+2+4+8+16+64)
            DumpConfigToLog()
                
        #PureLink needs polling, get from config
        Domoticz.Heartbeat(10)
        
        self.checkVersion(self.version)
        
        #create thermostat device
        if self.ThermostatUnit not in Devices:
            Domoticz.Device(Name='Heat target', Unit=self.ThermostatUnit, Type=242, Subtype=1).Create()
            
        #create connection to Domotic to fetch other device status
        self.httpClient = Domoticz.Connection(Name="JSON Connection", Transport="TCP/IP", Protocol="JSON", Address=Parameters["Address"], Port=Parameters["Port"])

        Domoticz.Debug("created some URLs: '{0}', '{1}'".format(self.ThermometerUrl,self.HeaterUrl))
        
    def onStop(self):
        Domoticz.Debug("onStop called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        if Unit == self.ThermostatUnit:
            UpdateDevice(self.ThermostatUnit, 0, Level)

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called: Connection '"+str(Connection)+"', Status: '"+str(Status)+"', Description: '"+Description+"'")
        #self.httpClient.onConnect(Connection, Status, Description)
        if Status == 0:
            self.connected = True
        else:
            self.connected = False

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called: Connection '"+str(Connection)+"'")
        self.connected = False
        #self.httpClient.onDisconnect(Connection)

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called: Connection '"+str(Connection)+"', Data: '"+str(Data)+"'")
        #self.httpClient.onMessage(Connection, Data)

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("onNotification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onHeartbeat(self):
        if self.myDevice != None:
            self.runCounter = self.runCounter - 1
            # self.pingCounter = self.pingCounter - 1
            # if self.pingCounter <= 0 and self.runCounter > 0:
                # self.httpClient.onHeartbeat()
                # self.pingCounter = int(int(Parameters['Mode2'])/2)
            if self.runCounter <= 0:
                Domoticz.Debug("DysonPureLink plugin: Poll unit")
                self.runCounter = int(Parameters['Mode2'])
                #self.pingCounter = int(int(Parameters['Mode2'])/2)
                topic, payload = self.myDevice.request_state()
                self.httpClient.Publish(topic, payload) #ask for update of current status
                
            else:
                Domoticz.Debug("Polling unit in " + str(self.runCounter) + " heartbeats.")
                self.httpClient.onHeartbeat()

    def onDeviceRemoved(self, unit):
        Domoticz.Log("onDeviceRemoved called for unit '" + str(unit) + "'")
    
    def updateDevices(self):
        """Update the defined devices from incoming mesage info"""
        #update the devices
        if self.state_data.oscillation is not None:
            UpdateDevice(self.fanOscillationUnit, self.state_data.oscillation.state, str(self.state_data.oscillation))
        if self.state_data.night_mode is not None:
            UpdateDevice(self.nightModeUnit, self.state_data.night_mode.state, str(self.state_data.night_mode))

        # Fan speed  
        if self.state_data.fan_speed is not None:
            f_rate = self.state_data.fan_speed
    
            if (f_rate == "AUTO"):
                nValueNew = 110
                sValueNew = "110" # Auto
            else:
                nValueNew = (int(f_rate))*10
                sValueNew = str((int(f_rate)) * 10)
            if self.state_data.fan_mode is not None:
                Domoticz.Debug("update fanspeed, state of FanMode: " + str(self.state_data.fan_mode))
                if self.state_data.fan_mode.state == 0:
                    nValueNew = 0
                    sValueNew = "0"
                    
            UpdateDevice(self.fanSpeedUnit, nValueNew, sValueNew)
        
        if self.state_data.fan_mode is not None:
            UpdateDevice(self.fanModeUnit, self.state_data.fan_mode.state, str((self.state_data.fan_mode.state+1)*10))
        if self.state_data.fan_state is not None:
            UpdateDevice(self.fanStateUnit, self.state_data.fan_state.state, str((self.state_data.fan_state.state+1)*10))
        if self.state_data.filter_life is not None:
            UpdateDevice(self.filterLifeUnit, self.state_data.filter_life, str(self.state_data.filter_life))
        if self.state_data.quality_target is not None:
            UpdateDevice(self.qualityTargetUnit, self.state_data.quality_target.state, str((self.state_data.quality_target.state+1)*10))
        if self.state_data.standby_monitoring is not None:
            UpdateDevice(self.standbyMonitoringUnit, self.state_data.standby_monitoring.state, str((self.state_data.standby_monitoring.state+1)*10))
        if self.state_data.fan_mode_auto is not None:
            UpdateDevice(self.fanModeAutoUnit, self.state_data.fan_mode_auto.state, str((self.state_data.fan_mode_auto.state+1)*10))
        if self.state_data.focus is not None:
            UpdateDevice(self.fanFocusUnit, self.state_data.focus.state, str(self.state_data.focus))
        if self.state_data.heat_mode is not None:
            UpdateDevice(self.heatModeUnit, self.state_data.heat_mode.state, str((self.state_data.heat_mode.state+1)*10))
        if self.state_data.heat_target is not None:
            UpdateDevice(self.heatTargetUnit, 0, str(self.state_data.heat_target))
        if self.state_data.heat_state is not None:
            UpdateDevice(self.heatStateUnit, self.state_data.heat_state.state, str((self.state_data.heat_state.state+1)*10))
        Domoticz.Debug("update StateData: " + str(self.state_data))


    def onhttpConnected(self):
        """connection to device established"""
        Domoticz.Debug("onhttpConnected called")
        Domoticz.Log("http connection established")
        self.httpClient.Subscribe([self.base_topic + '/status/current', self.base_topic + '/status/connection', self.base_topic + '/status/faults']) #subscribe to all topics on the machine
        topic, payload = self.myDevice.request_state()
        self.httpClient.Publish(topic, payload) #ask for update of current status

    def onhttpDisconnected(self):
        Domoticz.Debug("onhttpDisconnected")

    def onhttpSubscribed(self):
        Domoticz.Debug("onhttpSubscribed")
        
    def onhttpPublish(self, topic, message):
        Domoticz.Debug("http Publish: http message incoming: " + topic + " " + str(message))

        if (topic == self.base_topic + '/status/current'):
            #update of the machine's status
            if StateData.is_state_data(message):
                Domoticz.Debug("machine state or state change recieved")
                self.state_data = StateData(message)
                self.updateDevices()
            if SensorsData.is_sensors_data(message):
                Domoticz.Debug("sensor state recieved")
                self.sensor_data = SensorsData(message)
                self.updateSensors()

        if (topic == self.base_topic + '/status/connection'):
            #connection status received
            Domoticz.Debug("connection state recieved")

        if (topic == self.base_topic + '/status/software'):
            #connection status received
            Domoticz.Debug("software state recieved")
            
        if (topic == self.base_topic + '/status/summary'):
            #connection status received
            Domoticz.Debug("summary state recieved")

    def checkVersion(self, version):
        """checks actual version against stored version as 'Ma.Mi.Pa' and checks if updates needed"""
        #read version from stored configuration
        ConfVersion = getConfigItem("plugin version", "0.0.0")
        Domoticz.Log("Starting version: " + version )
        MaCurrent,MiCurrent,PaCurrent = version.split('.')
        MaConf,MiConf,PaConf = ConfVersion.split('.')
        Domoticz.Debug("checking versions: current '{0}', config '{1}'".format(version, ConfVersion))
        if int(MaConf) < int(MaCurrent):
            Domoticz.Log("Major version upgrade: {0} -> {1}".format(MaConf,MaCurrent))
            #add code to perform MAJOR upgrades
        elif int(MiConf) < int(MiCurrent):
            Domoticz.Log("Minor version upgrade: {0} -> {1}".format(MiConf,MiCurrent))
            #add code to perform MINOR upgrades
        elif int(PaConf) < int(PaCurrent):
            Domoticz.Log("Patch version upgrade: {0} -> {1}".format(PaConf,PaCurrent))
            #add code to perform PATCH upgrades, if any
        if ConfVersion != version:
            #store new version info
            self._setVersion(MaCurrent,MiCurrent,PaCurrent)
            
    def _setVersion(self, major, minor, patch):
        #set configs
        Domoticz.Debug("Setting version to {0}.{1}.{2}".format(major, minor, patch))
        setConfigItem(Key="MajorVersion", Value=major)
        setConfigItem(Key="MinorVersion", Value=minor)
        setConfigItem(Key="patchVersion", Value=patch)
        setConfigItem(Key="plugin version", Value="{0}.{1}.{2}".format(major, minor, patch))
                
# Configuration Helpers
def getConfigItem(Key=None, Default={}):
   Value = Default
   try:
       Config = Domoticz.Configuration()
       if (Key != None):
           Value = Config[Key] # only return requested key if there was one
       else:
           Value = Config      # return the whole configuration if no key
   except KeyError:
       Value = Default
   except Exception as inst:
       Domoticz.Error("Domoticz.Configuration read failed: '"+str(inst)+"'")
   return Value
   
def setConfigItem(Key=None, Value=None):
    Config = {}
    if type(Value) not in (str, int, float, bool, bytes, bytearray, list, dict):
        Domoticz.Error("A value is specified of a not allowed type: '" + str(type(Value)) + "'")
        return Config
    try:
       Config = Domoticz.Configuration()
       if (Key != None):
           Config[Key] = Value
       else:
           Config = Value  # set whole configuration if no key specified
       Config = Domoticz.Configuration(Config)
    except Exception as inst:
       Domoticz.Error("Domoticz.Configuration operation failed: '"+str(inst)+"'")
    return Config
       
def UpdateDevice(Unit, nValue, sValue, BatteryLevel=255, AlwaysUpdate=False):
    if Unit not in Devices: return
    if Devices[Unit].nValue != nValue\
        or Devices[Unit].sValue != sValue\
        or Devices[Unit].BatteryLevel != BatteryLevel\
        or AlwaysUpdate == True:

        Devices[Unit].Update(nValue, str(sValue), BatteryLevel=BatteryLevel)

        Domoticz.Debug("Update %s: nValue %s - sValue %s - BatteryLevel %s" % (
            Devices[Unit].Name,
            nValue,
            sValue,
            BatteryLevel
        ))
        
global _plugin
_plugin = SimpleThermostatPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def onDeviceRemoved(Unit):
    global _plugin
    _plugin.onDeviceRemoved(Unit)

    # Generic helper functions
def DumpConfigToLog():
    Domoticz.Debug("Parameter count: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "Parameter '" + x + "':'" + str(Parameters[x]) + "'")
    Configurations = getConfigItem()
    Domoticz.Debug("Configuration count: " + str(len(Configurations)))
    for x in Configurations:
        if Configurations[x] != "":
            Domoticz.Debug( "Configuration '" + x + "':'" + str(Configurations[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
    return
