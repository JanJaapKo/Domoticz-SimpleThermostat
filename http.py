# Based on https://github.com/emontnemery/domoticz_mqtt_discovery
try:
	import Domoticz
	debug = False
except ImportError:
	import fakeDomoticz as Domoticz
	debug = True
import time
import json

class httpClient:
    Address = ""
    Port = ""
    httpConn = None
    isConnected = False
    httpConnectedCb = None
    httpDisconnectedCb = None
    httpPublishCb = None

    def __init__(self, destination, port, clientId, httpConnectedCb, httpDisconnectedCb, httpPublishCb, httpSubackCb):
        #Domoticz.Debug("httpClient::__init__")
        
        self.address = destination
        self.port = port
        self.client_id = clientId if clientId != "" else 'Domoticz_'+str(int(time.time()))
        self.httpConnectedCb = httpConnectedCb
        self.httpDisconnectedCb = httpDisconnectedCb
        self.httpPublishCb = httpPublishCb
        self.httpSubackCb = httpSubackCb
        self.Open()

    def __str__(self):
        #Domoticz.Debug("httpClient::__str__")
        if (self.httpConn != None):
            return str(self.httpConn)
        else:
            return "None"

    def Open(self):
        Domoticz.Debug("httpClient::Open")
        if (self.httpConn != None):
            self.Close()
        self.isConnected = False

        protocol = "MQTTS" if self.port == "8883" else "MQTT"

        Domoticz.Debug("httpClient::Open: setup Domoticz connection object with protocol: '"+protocol+"'")
        self.httpConn = Domoticz.Connection(Name=self.address, Transport="TCP/IP", Protocol=protocol, Address=self.address, Port=self.port)
        Domoticz.Debug("httpClient::Open: open connection")
        self.httpConn.Connect()

    def Connect(self):
        Domoticz.Debug("httpClient::Connect")
        if (self.httpConn == None):
            self.Open()
        else:
            Domoticz.Debug("httpClient::http CONNECT ID: '" + self.client_id + "'")
            self.httpConn.Send({'Verb': 'CONNECT', 'ID': self.client_id})

    def Ping(self):
        #Domoticz.Debug("httpClient::Ping")
        if (self.httpConn == None or not self.isConnected):
            self.Open()
        else:
            self.httpConn.Send({'Verb': 'PING'})

    def Publish(self, topic, payload, retain = 0):
        Domoticz.Debug("httpClient::Publish " + topic + " (" + payload + ")")
        if (self.httpConn == None or not self.isConnected):
            self.Open()
        else:
            self.httpConn.Send({"Verb": "PUBLISH", "Topic": topic, "Payload": bytearray(payload, "utf-8"), "Retain": retain})

    def Subscribe(self, topics):
        Domoticz.Debug("httpClient::Subscribe to topics: " + str(topics))
        subscriptionlist = []
        for topic in topics:
            subscriptionlist.append({'Topic':topic, 'QoS':0})
        if (self.httpConn == None or not self.isConnected):
            self.Open()
        else:
            self.httpConn.Send({'Verb': 'SUBSCRIBE', 'Topics': subscriptionlist})

    def Close(self):
        Domoticz.Debug("httpClient::Close")
        #TODO: Disconnect from server
        self.httpConn = None
        self.isConnected = False

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("httpClient::onConnect")
        if (Status == 0):
            Domoticz.Debug("httpClient::http connected successfully.")
            self.Connect()
        else:
            Domoticz.Log("httpClient::Failed to connect to: " + Connection.Address + ":" + Connection.Port + ", Description: " + Description)

    def onDisconnect(self, Connection):
        Domoticz.Debug("httpClient::onDisonnect Disconnected from: " + Connection.Address+":" + Connection.Port)
        self.Close()
        # TODO: Reconnect?
        if self.httpDisconnectedCb != None:
            self.httpDisconnectedCb()

    def onHeartbeat(self):
        #Domoticz.Debug("httpClient::onHeartbeat")
        if self.httpConn is None or (not self.httpConn.Connecting() and not self.httpConn.Connected() or not self.isConnected):
            Domoticz.Debug("httpClient::Reconnecting")
            self.Open()
        else:
            self.Ping()

    def onMessage(self, Connection, Data):
        #Domoticz.Debug("httpClient::onMessage")
        topic = ''
        if 'Topic' in Data:
            topic = Data['Topic']
        payloadStr = ''
        if 'Payload' in Data:
            payloadStr = Data['Payload'].decode('utf8','replace')
            payloadStr = str(payloadStr.encode('unicode_escape'))

        Domoticz.Debug("httpClient::onMessage Topic '"+topic+"', Data[Verb]: '"+Data['Verb']+"'")
        if Data['Verb'] == "CONNACK":
            self.isConnected = True
            if self.httpConnectedCb != None:
                self.httpConnectedCb()

        if Data['Verb'] == "SUBACK":
            if self.httpSubackCb != None:
                self.httpSubackCb()

        if Data['Verb'] == "PUBLISH":
            if self.httpPublishCb != None:
                rawmessage = Data['Payload'].decode('utf8')
                message = ""

                try:
                    message = json.loads(rawmessage)
                except ValueError:
                    message = rawmessage
                    
                self.httpPublishCb(topic, message)
