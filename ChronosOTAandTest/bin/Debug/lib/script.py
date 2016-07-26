import time
import sys
import clr
clr.AddReferenceByName(r'Ulpbt')
import Ulpbt
import traceback
import Queue
import datetime
import random
from math import log,ceil
import System.Collections.Generic.List as List
import System.SByte
import System.ComponentModel
from threading import Thread, Lock, Event
from testerScriptCommon import *
from testerScriptServer import *
from testerScriptEngineClient import *
from hookscript import *
from protocol import Att
from protocol.Att import *
from protocol.Smp import *
from protocol.L2CapSignPkt import *
from protocol.Gatt import *
from modules.packetqueue import PacketQueue
import enum

try:
    clr.AddReference(r'MasterEmulator.dll')
except Exception, ex:
    print "Failed to import MasterEmulator.dll, %s" % ex

try:
    from dfu.dfu_transport_me import DfuTransportMe
    from nordicsemi.dfu.dfu_transport import DfuEvent
    from nordicsemi.dfu.dfu import Dfu
except Exception, ex:
    print "Failed to import dfu, %s" % ex


class AttErrorCode(enum.Enum):
    ## ERROR_RESPONSE codes
    INVALID_HANDLE                = Att.errorCode['INVALID_HANDLE']
    READ_NOT_PERMITTED            = Att.errorCode['READ_NOT_PERMITTED']
    WRITE_NOT_PERMITTED           = Att.errorCode['WRITE_NOT_PERMITTED']
    INVALID_PDU                   = Att.errorCode['INVALID_PDU']
    INSUFFICIENT_AUTHENTICATION   = Att.errorCode['INSUFFICIENT_AUTHENTICATION']
    REQUEST_NOT_SUPPORTED         = Att.errorCode['REQUEST_NOT_SUPPORTED']
    INVALID_OFFSET                = Att.errorCode['INVALID_OFFSET']
    INSUFFICIENT_AUTHORIZATION    = Att.errorCode['INSUFFICIENT_AUTHORIZATION']
    PREPARE_QUEUE_FULL            = Att.errorCode['PREPARE_QUEUE_FULL']
    ATTRIBUTE_NOT_FOUND           = Att.errorCode['ATTRIBUTE_NOT_FOUND']
    ATTRIBUTE_NOT_LONG            = Att.errorCode['ATTRIBUTE_NOT_LONG']
    INSUFFICIENT_ENC_KEY_SIZE     = Att.errorCode['INSUFFICIENT_ENC_KEY_SIZE']
    INVALID_ATTRIBUTE_VALUE_LEN   = Att.errorCode['INVALID_ATTRIBUTE_VALUE_LEN']
    UNLIKELY_ERROR                = Att.errorCode['UNLIKELY_ERROR']
    INSUFFICIENT_ENCRYPTION       = Att.errorCode['INSUFFICIENT_ENCRYPTION']
    UNSUPPORTED_GROUP_TYPE        = Att.errorCode['UNSUPPORTED_GROUP_TYPE']
    INSUFFICIENT_RESOURCES        = Att.errorCode['INSUFFICIENT_RESOURCES']
    APPLICATION_ERROR             = Att.errorCode['APPLICATION_ERROR_STRT']
    CCCD_IMPROPERLY_CONFIGURED    = Att.errorCode['CCCD_IMPROPERLY_CONFIGURED']
    PROCEDURE_ALREADY_IN_PROGRESS = Att.errorCode['PROCEDURE_ALREADY_IN_PROGRESS']
    APPLICATION_ERROR_END         = Att.errorCode['APPLICATION_ERROR_END']
    # proprietary command
    DEFERRAL_REQUIRED             = Att.errorCode['DEFERRAL_REQUIRED']

#Correct TesterScriptCommon packet IDs if driver is H4, since values are hardcoded to fit spi driver
tester = Tester(caller)
ftdiComm = FtdiComm(driver)
gattResponse = Ulpbt.GattResponse()
hciComm = HciComm(hci,ftdiComm)
dataComm = DataComm(bc)
att = AttCommands(AttComm(bc))
smp = SmpCommands(SmpComm(bc))
l2cap = L2CapCommands(L2CapComm(bc))
gatt = Gatt(tester, att)

if isinstance(driver, Ulpbt.HciH4Driver):
    tester.isDriverH4 = True

    Common.COMMAND_PACKET_ID = int(Ulpbt.HciH4PacketIndicator.HciCommandPacket)
    Common.DATA_PACKET_ID = int(Ulpbt.HciH4PacketIndicator.HciAclDataPacket)
    Common.EVENT_PACKET_ID = int(Ulpbt.HciH4PacketIndicator.HciEventPacket)

driver.HciEvent += tester.PacketEventHandler
driver.HciData += tester.PacketDataHandler
driver.HciDriverException += tester.ExceptionHandler

try:
    SERVICE_GROUP_UUID                  = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.PrimaryService.ToString()].Uuid16bit
    PRIMARY_SERVICE_GROUP_UUID          = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.PrimaryService.ToString()].Uuid16bit
    SECONDARY_SERVICE_GROUP_UUID        = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.SecondaryService.ToString()].Uuid16bit
    INCLUDE_UUID                        = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.Include.ToString()].Uuid16bit
    CHARACTERISTIC_DECLARATION          = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.CharacteristicDeclaration.ToString()].Uuid16bit
    CHARACTERISTIC_DESCRIPTION          = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.CharacteristicUserDescription.ToString()].Uuid16bit
    CLIENT_CHARACTERISTIC_CONFIGURATION = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.ClientCharacteristicConfiguration.ToString()].Uuid16bit
    SERVER_CHARACTERISTIC_CONFIGURATION = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.ServerCharacteristicConfiguration.ToString()].Uuid16bit
    CHARACTERISTIC_FORMAT               = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.CharacteristicFormat.ToString()].Uuid16bit
    AGGREGATE_FORMAT                    = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.CharacteristicAggregateFormat.ToString()].Uuid16bit
    ATTRIBUTE_PROFILE                   = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.GenericAttributeProfile.ToString()].Uuid16bit
    ATTRIBUTE_OPCODE_SUPPORTED          = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.AttributeOpcodesSupported.ToString()].Uuid16bit
    GENERIC_ACCESS_PROFILE              = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.GenericAccessProfile.ToString()].Uuid16bit
    DEVICE_NAME                         = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.DeviceName.ToString()].Uuid16bit
    APPEARANCE                          = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.Appearance.ToString()].Uuid16bit
    SLAVE_PREFFERED_CONN_PARAM          = Ulpbt.GattUuid.UuidByName[Ulpbt.GattUuidEnum.SlavePreferredConnectionParameters.ToString()].Uuid16bit
except Exception,ex:
    print str(traceback.extract_tb(sys.exc_info()[2]))
    print "Exception: " + str(ex)

Uuid.assignedNumbers = {
      'GAP'                     :GENERIC_ACCESS_PROFILE
    , 'DEVICE_NAME'             :DEVICE_NAME
    , 'APPEARANCE'              :APPEARANCE
    , 'PRIVACY_FLAG'            :0xFFF1
    , 'RECONN_ADDR'             :0xFFF2
    , 'CONNECTION_PARAMETERS'   :SLAVE_PREFFERED_CONN_PARAM
    , 'GATT'                    :ATTRIBUTE_PROFILE
    , 'SERVICE_CHANGED'         :0x0029
    , 'OPCODES_SUPPORTED'       :ATTRIBUTE_OPCODE_SUPPORTED
    , 'PRIMARY_SERVICE'         :PRIMARY_SERVICE_GROUP_UUID
    , 'SECONDARY_SERVICE'       :SECONDARY_SERVICE_GROUP_UUID
    , 'INCLUDE'                 :INCLUDE_UUID
    , 'CHARACTERISTIC'          :CHARACTERISTIC_DECLARATION
    , 'CHARACTERISTIC_EXT_PROP' :0x0015
    , 'CHARACTERISTIC_USER_DESC':CHARACTERISTIC_DESCRIPTION
    , 'CHARACTERISTIC_CLT_CFG'  :CLIENT_CHARACTERISTIC_CONFIGURATION
    , 'CHARACTERISTIC_SVR_CFG'  :SERVER_CHARACTERISTIC_CONFIGURATION
    , 'CHARACTERISTIC_FORMAT'   :CHARACTERISTIC_FORMAT
    , 'CHARACTERISTIC_AGG_FMT'  :AGGREGATE_FORMAT
}

client = testerScriptEngineClient(ftdiComm,hciComm,tester,smp,True)

PROPERTIES_BROADCAST                = 0x01
PROPERTIES_READ                     = 0x02
PROPERTIES_WRITE_WITHOUT_RESPONSE   = 0x04
PROPERTIES_WRITE                    = 0x08
PROPERTIES_NOTIFY                   = 0x10
PROPERTIES_INDICATE                 = 0x20
PROPERTIES_AUTHENTICATED            = 0x40
PROPERTIES_EXTENDED_PROPERTIES      = 0x80


PERM_AUTHORIZATION      = 0x01
PERM_AUTHENTICATION     = 0x02
PERM_READ               = 0x04
PERM_WRITE              = 0x08

loop = True
ConnectionId = None
connected = False
RemoteHandleDict = {}
LocalHandleDict = {}
bondedDevices = {}
threadLock = Lock()
logLock = Lock()
testServer = None
connectionInfo = None

changedSettings = {}
DisconnectedCalled = False
holdConnection = False
tmpQueue = Queue.Queue(10)
tmpQueueEvent = Event()

class Notify:
    def __init__(self):
        self.Queue = Queue.Queue(20)
        try:
            tester.AddPacketRecipients(self.ReceivePacket)
        except Exception,ex:
            LogTraceback(ex)
            LogWrite("Exception: " + str(ex))
        self.ePacket = Event()
        self.backgroundWorker = System.ComponentModel.BackgroundWorker()
        self.backgroundWorker.RunWorkerCompleted += self.backgroundWorkerCompleted
        self.expectedPackets = [
                            SerialCommTypeMapping.ATT_NOTIFY_EVENTCODE,
                            hciComm.HCI_LL_CONNECTION_TERMINATION_EVENT,
                            hciComm.HCI_ENCRYPTION_CHANGE_EVENT,
                            hciComm.HCI_LL_CONNECTION_CREATED_EVENT,
                            SerialCommTypeMapping.SMP_REQUEST_EVENTCODE,
                            #SerialCommTypeMapping.ATT_COMMAND_EVENTCODE,
                            SerialCommTypeMapping.L2CAP_COMMAND_EVENTCODE
                            ]

    def backgroundWorkerCompleted(self, sender, arguments):
        if arguments.Error != None:
            LogWrite("Worker error: %s" % str(arguments.Error.Message))
        else:
            LogWrite("BackgroundWorker completed", debug="file")

    def ReceivePacket(self,packet):
        if packet.EventCode in self.expectedPackets:
            self.Queue.put(packet, True, Common.PACKET_QUEUE_TIMEOUT)
            self.ePacket.set()

    def run(self):
        global connected, connectionInfo, RemoteHandleDict
        self.running = True
        while self.running:
            try:
                if self.Queue.empty():
                    self.ePacket.wait()
                try:
                    ret = self.Queue.get(True, Common.PACKET_QUEUE_TIMEOUT)
                except Queue.Empty, ex:
                    LogTraceback(ex)
                    continue
                if isinstance(ret, AttHandleValueNotification):
                    handle = ret.Attributes.handle
                    value = ret.Attributes.value
                    if (connectionInfo != None) and (connectionInfo.PeerAddress in RemoteHandleDict):
                        if handle in RemoteHandleDict[connectionInfo.PeerAddress]:
                            RemoteHandleDict[connectionInfo.PeerAddress][handle]['DATA'] = value
                            gattResponse.AttributeUpdateNotification(ParseDictionary(handle, RemoteHandleDict[connectionInfo.PeerAddress][handle]))
                    LogWrite("Received a HandleValueNotification on handle %04X with value %s" % (handle,"".join("%02X" % el for el in value)))
                elif isinstance(ret, AttHandleValueIndication):
                    handle = ret.Attributes.handle
                    value = ret.Attributes.value
                    att.SendHandleValueConfirmation()
                    if (connectionInfo != None) and (connectionInfo.PeerAddress in RemoteHandleDict):
                        if handle in RemoteHandleDict[connectionInfo.PeerAddress]:
                            RemoteHandleDict[connectionInfo.PeerAddress][handle]['DATA'] = value
                            gattResponse.AttributeUpdateNotification(ParseDictionary(handle,RemoteHandleDict[connectionInfo.PeerAddress][handle]))
                    LogWrite("Received a HandleValueIndication on handle %04X with value %s" % (handle,"".join("%02X" % el for el in value)))
                elif ret.EventCode == hciComm.HCI_LL_CONNECTION_TERMINATION_EVENT:
                    LogWrite("Lost connection to device. Reason: %s" % (ret.ReasonAsString,))
                    connected = False
                    connectionInfo = None
                    gattResponse.StateChange(gattResponse.State.StateIdle)
                elif ret.EventCode == hciComm.HCI_ENCRYPTION_CHANGE_EVENT:
                    if ret.EncEnabled == 1:
                        state = "ON"
                    else:
                        state = "OFF"
                    LogWrite("Encryption change: Link encryption is %s" % state)
                elif isinstance(ret,SmpSecurityRequest):
                    LogWrite("Received Security Request, bonding requested: %s, mitm requested: %s" % (ret.Bonding, ret.Mitm))
                    connInfo = GetConnInfo()
                    while connInfo == None:
                        connInfo = GetConnInfo()
                    peerAddress = connectionInfo.PeerAddress
                    if peerAddress in bondedDevices:
                        device = bondedDevices[peerAddress]
                        ltk, ediv, rand =[None]*3
                        if 'LTK' in device:
                            ltk = device['LTK']
                        if 'EDIV' in device:
                            ediv = device['EDIV']
                        if 'RAND' in device:
                            rand = device['RAND']
                        client.StartEncryption(ltk, ediv, rand)
                    else:
                        securitySettings = {}
                        StartPairingProcedure(**securitySettings)
                #Processed in ServerUpdateCallbackHandler
                #elif isinstance(ret, AttWriteCommand) or isinstance(ret, AttWriteRequest):
                #    handle = ret.Attributes.handle
                #    value = ret.Attributes.value
                #    LocalHandleDict[handle]['DATA'] = value
                #    gattResponse.ServerAttributeUpdateNotification(ParseDictionary(handle, LocalHandleDict[handle]))
                elif isinstance(ret, L2CapConnectionParameterUpdateRequest):
                    self.processConnectionParameterUpdateRequest(ret)
                elif ret.EventCode == hciComm.HCI_LL_CONNECTION_CREATED_EVENT:
                    connInfo = GetConnInfo()
                    while connInfo == None:
                        connInfo = GetConnInfo()
                    peerAddress = connectionInfo.PeerAddress
                    if peerAddress in bondedDevices:
                        device = bondedDevices[peerAddress]
                        ltk, ediv, rand =[None]*3
                        if 'LTK' in device:
                            ltk = device['LTK']
                        if 'EDIV' in device:
                            ediv = device['EDIV']
                        if 'RAND' in device:
                            rand = device['RAND']
                        LogWrite("Starting encryption")
                        client.StartEncryption(ltk, ediv, rand)
                self.ePacket.clear()

            except Exception, ex:
                self.running = False
                LogTraceback(ex)
        LogWrite("Notify catcher terminated")

    def processConnectionParameterUpdateRequest(self, packet):
        LogWrite("Received Connection Parameter Update Request")
        identifier = int(packet.Identifier)
        intervalMinMs = float(packet.IntervalMin * 1.25)
        intervalMaxMs = float(packet.IntervalMax * 1.25)
        slaveLatency = int(packet.SlaveLatency)
        timeoutMs = int(packet.TimeoutMultiplier * 10)
        arguments = (identifier, intervalMinMs, intervalMaxMs, slaveLatency, timeoutMs)

        if not self.backgroundWorker.IsBusy:
            self.backgroundWorker.DoWork += self.callConnUpdateAsync
            LogWrite("launching connection update worker", debug="file")
            self.backgroundWorker.RunWorkerAsync(arguments)
        else:
            LogWrite("BackgroundWorker is busy. Operation aborted")

    def callConnUpdateAsync(self, sender, argument):
        try:
            parameters = argument.Argument
            (identifier, intervalMinMs, intervalMaxMs, slaveLatency, timeoutMs) = parameters
            gattResponse.ConnectionUpdateRequest(identifier, intervalMinMs, intervalMaxMs,
                                                 slaveLatency, timeoutMs)
        finally:
            self.backgroundWorker.DoWork -= self.callConnUpdateAsync

    def stop(self):
        self.running = False

def _isPendingWaitValid(*packetsToWaitFor):
    if connected:
        return True

    if SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE in packetsToWaitFor:
        return False
    elif SerialCommTypeMapping.SMP_RESPONSE_EVENTCODE in packetsToWaitFor:
        return False
    else:
        return True

def _assignWaitValidators():
    gatt.tst.isPendingWaitValid = _isPendingWaitValid
    tester.pktQueue.isPendingWaitValid = _isPendingWaitValid
    client.driver.isPendingWaitValid = _isPendingWaitValid


def SendConnectionUpdateResponse(identifier, response):
    if identifier < 1 or identifier > 0xFF:
        LogWrite("Invalid identifier")
        return

    if response not in [0x00, 0x01]:
        LogWrite("Invalid connection update response value")
        return

    l2cap.SendConnectionParameterUpdateResponse(identifier, response)
    LogWrite("ConnectionParameterUpdateResponse sent")

def UpdateConnParams(connIntervalMs, connLatency, connTimeoutMs):
    global ConnectionId
    if ConnectionId == None:
        LogWrite("Not connected")
        return

    tempPacketQueue = PacketQueue(QUEUE_LENGTH=200, LOG_FUNCTION=LogWrite)
    tempPacketQueue.isPendingWaitValid = _isPendingWaitValid
    tester.AddPacketRecipients(tempPacketQueue.AddToQueue)

    try:
        connectionId = ConnectionId
        hciComm.UpdateLLConnectionParameters(connectionId, connIntervalMs, connLatency, connTimeoutMs)

        statusEvent = tempPacketQueue.WaitFor(hciComm.HCI_COMMAND_STATUS_EVENT, T=1)
        if statusEvent == None:
            return False
        elif statusEvent.Status != 0:
            return False

        updatedEvent = tempPacketQueue.WaitFor(hciComm.HCI_LL_CONNECTION_PAR_UPDATE_COMPLETE_EVENT, T=10)
        if updatedEvent == None:
            return False
        elif updatedEvent.Status != 0:
            return False
        else:
            LogWrite("Connection Parameters Updated. ConnInterval:%sms, SlaveLatency:%s, SupervisionTimeout:%sms" % (connIntervalMs, connLatency, connTimeoutMs))
            return True
    finally:
        tester.RemovePacketRecipient(tempPacketQueue.AddToQueue)
        tempPacketQueue = None

def UpdateChannelMap(channelMap):
    global ConnectionId
    if ConnectionId == None:
        LogWrite("Not connected")
        return

    tempPacketQueue = PacketQueue(QUEUE_LENGTH=200, LOG_FUNCTION=LogWrite)
    tempPacketQueue.isPendingWaitValid = _isPendingWaitValid
    tester.AddPacketRecipients(tempPacketQueue.AddToQueue)

    try:
        connectionId = ConnectionId
        hciComm.SetHostChannelClassification(channelMap)

        updatedEvent = tempPacketQueue.WaitFor(hciComm.HCI_COMMAND_COMPLETE_EVENT,
                                               CMD_OPCODE=hciComm.BTLE_CMD_LE_SET_HOST_CHANNEL_CLASSIFICATION,
                                               T=5)
        if updatedEvent == None:
            return False
        elif updatedEvent.Status != 0:
            return False
        else:
            LogWrite("Channel Map Updated.")
            return True
    finally:
        tester.RemovePacketRecipient(tempPacketQueue.AddToQueue)
        tempPacketQueue = None

def GetConnInfo():
    return connectionInfo

def StartServer():
    global testServer
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    LogWrite("Starting Server", debug="file")
    testServer = testerScriptServer(tester,att,dataBase=LocalHandleDict,logFunc=LogWrite)
    testServer.SetServerUpdatedCallback(serverUpdatedCallbackHandler)
    testServer.SetServerExecuteWriteCallback(serverExecuteWriteCallbackHandler)
    testServer.start()
    gattResponse.StateChange(gattResponse.State.StateServerRunning)
    gattResponse.StateChange(gattResponse.State.StateScriptReady)

def StopServer():
    global testServer
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    if testServer != None:
        testServer.stop()
        while testServer.isAlive():
            LogWrite("Waiting for server to terminate", debug="file")
            tester.Sleep(0.5)
    gattResponse.StateChange(gattResponse.State.StateServerNotRunning)
    gattResponse.StateChange(gattResponse.State.StateScriptReady)

def serverUpdatedCallbackHandler(handle, value, packetType=None):
    LocalHandleDict[handle]['DATA'] = value
    gattResponse.ServerAttributeUpdateNotification(ParseDictionary(handle, LocalHandleDict[handle]))

def serverExecuteWriteCallbackHandler(handleValueCollection, numberOfDeferred):
    for (handle, value) in handleValueCollection.iteritems():
        LocalHandleDict[handle]['DATA'] = value
        gattResponse.ServerAttributeUpdateNotification(ParseDictionary(handle, LocalHandleDict[handle]))

def StartHookscript():
    global hookServer
    LogWrite("Starting Hookscript")
    hookServer = HookscriptServer(tester, att, logFunc=LogWrite)
    hookServer.start()

def StopHookscript():
    global hookServer
    LogWrite("Stopping Hookscript")
    if hookServer != None:
        hookServer.stop()
        while hookServer.isAlive():
            tester.Sleep(0.5)

def ScriptLoop():
    try:
        global loop
        notify = Notify()
        notify.run()
        while loop:
            time.sleep(0.5)
        notify.stop()
        if testServer.isAlive():
            testServer.stop()
            while testServer.isAlive():
                time.sleep(0.01)

    except Exception,ex:
        LogTraceback(ex)
        LogWrite("Exception: " + str(ex))

def DisconnectFromDevice():
    global gattResponse
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    if Disconnect():
        gattResponse.StateChange(gattResponse.State.StateIdle)
        LogWrite("Disconnected")
    else:
        LogWrite("Could not disconnect")
    gattResponse.StateChange(gattResponse.State.StateScriptReady)

def SetSettings(**settings):
    global changedSettings
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    changedSettings = {}
    for key,value in settings.iteritems():
        if key in defaultSettings:
            changedSettings[key] = value
    gattResponse.StateChange(gattResponse.State.StateScriptReady)


def reverseHexAddressByteOrder(address):
    newAddress = ''
    byteList = []
    for i in xrange(0, len(address), 2):
        byteList.append(address[i:i+2])

    byteList.reverse()
    newAddress += ''.join(byteList)
    return newAddress

def ConnectToDevice(**parameters):
    global gattResponse
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    try:
        MSBAddress = reverseHexAddressByteOrder(parameters['peerAddress'])
        if Connect(**parameters):
            LogWrite("Connected to %s" % MSBAddress)
        else:
            LogWrite("Could not connect to %s" % MSBAddress)
    except Exception,ex:
        LogTraceback(ex)
        LogWrite("Exception: %s" % ex)
    gattResponse.StateChange(gattResponse.State.StateScriptReady)

def GetDeviceInfo(**parameters):
    global connected, bondedDevices
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    disconnect = False
    try:
        if not connected:
            disconnect = True
            MSBAddress = reverseHexAddressByteOrder(parameters['peerAddress'])
            if Connect(**parameters):
                LogWrite("Connected to address: %s" % MSBAddress)
            else:
                if 'peerAddress' in parameters:
                    LogWrite("Failed to connect to address: %s" % MSBAddress)
                else:
                    LogWrite("Failed to connect, no address provided")
        if connected:
            discoverServices()
    except Exception,ex:
        LogTraceback(ex)
        LogWrite("Exception: %s" % ex)
    gattResponse.StateChange(gattResponse.State.StateScriptReady)


def Connect(**parameters):
    global ConnectionId, connected, connectionInfo, DisconnectedCalled, RemoteHandleDict
    DisconnectedCalled = False
    for key,value in changedSettings.iteritems():
        if key not in parameters:
            parameters[key] = value

    gattResponse.StateChange(gattResponse.State.StateConnecting)
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    retval = client.ConnectTo(connSettings = parameters)
    if (retval != None):
        gattResponse.StateChange(gattResponse.State.StateConnected)
        gattResponse.StateChange(gattResponse.State.StateScriptBusy)
        ConnectionId = retval.ConnectionId
        att.driver.setConnID(ConnectionId)
        smp.driver.setConnID(ConnectionId)
        l2cap.driver.setConnID(ConnectionId)

        connected = True
        connectionInfo = retval
        LogWrite("----------------------------")
        LogWrite("Connected to device")
        LogWrite("Role: %d" % retval.Role)
        LogWrite("PeerAddressType: %d" % retval.PeerAddressType)
        LogWrite("PeerAddress (MSB): %s" % retval.PeerAddress)
        LogWrite("Connection Interval: %sms" % (retval.ConnectionInterval*1.25))
        LogWrite("Connection Latency: %d" % retval.ConnectionLatency)
        LogWrite("Supervision Timeout: %dms" % (retval.SupervisionTimeout*10))
        LogWrite("Clock Accuracy: (%d)" % retval.ClockAccuracy)
        LogWrite("----------------------------")
        if retval.PeerAddress in bondedDevices:
            if retval.PeerAddress in RemoteHandleDict:
                gattResponse.ServiceDiscoveryResponse(RemoteHandleDict[retval.PeerAddress]['ServiceObject'])
        return True
    return False

def Disconnect():
    global ConnectionId, connected, connectionInfo, DisconnectedCalled
    if ConnectionId == None:
        raise Exception("ConnectionID is None!")
    if holdConnection == True:
        LogWrite("Cannot close connection due to another procedure is under process")
        DisconnectedCalled = True
        return False
    hciComm.TerminateLLConnection(ConnectionId)
    retval = tester.WaitFor(hciComm.HCI_LL_CONNECTION_TERMINATION_EVENT, T=5)
    connectionInfo = None
    if retval != None and retval.EventCode == hciComm.HCI_LL_CONNECTION_TERMINATION_EVENT:
        connected = False
        return True
    else:
        return False

def TempPacketReceiver(packet):
    global tmpQueue, tmpQueueEvent
    tmpQueue.put(packet)
    tmpQueueEvent.set()

def WaitForTmpQueue(*eventCodes, **args):
    global tmpQueue, tmpQueueEvent
    for el in ['T','timeout']:
        if el in args:
            T = args[el]
            break
        else:
            T = 30

    startTime = datetime.datetime.now()
    while True:
        if (datetime.datetime.now()-startTime) > datetime.timedelta(0,T):
            return None
        if tmpQueue.empty():
            tmpQueueEvent.wait(0.5)
        if not tmpQueueEvent.isSet() and tmpQueue.empty():
            continue
        pkt = tmpQueue.get()
        tmpQueueEvent.clear()
        if len(eventCodes) == 0:
            return pkt
        elif pkt.EventCode in eventCodes:
            return pkt
        else:
            continue

def ReadRssi():
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)

    try:
        readRssi()
    finally:
        gattResponse.StateChange(gattResponse.State.StateScriptReady)

def readRssi():
    global ConnectionId
    hciComm.ReadRssi(ConnectionId)
    cmdEvent = tester.WaitFor(hciComm.HCI_COMMAND_COMPLETE_EVENT,
                                CMD_OPCODE=hciComm.BTLE_CMD_READ_RSSI,
                                T=5)
    if cmdEvent != None:
        LogWrite("RSSI: %i" % System.SByte(cmdEvent.Rssi))
    else:
        LogWrite("ReadRssi failed")

def StartEncryption():
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    encryptLink()
    gattResponse.StateChange(gattResponse.State.StateScriptReady)

def encryptLink():
    global bondedDevices, holdConnection
    #LogWrite("Encrypt Link has been called")
    connInfo = GetConnInfo()
    if connInfo == None:
        LogWrite("Error: No connection")
        return False
    if not connInfo.PeerAddress in bondedDevices:
        LogWrite("Error: Not bonded")
        return False

    device = bondedDevices[connInfo.PeerAddress]
    ltk, ediv, rand =[None]*3
    if 'LTK' in device:
        ltk = device['LTK']
    if 'EDIV' in device:
        ediv = device['EDIV']
    if 'RAND' in device:
        rand = device['RAND']

    try:
        client.StartEncryption(ltk, ediv, rand)
    except Exception,msg:
        LogTraceback(ex)
        LogWrite("Exception: " + str(msg))

    return True

def StartPairingProcedure(**securitySettings):
    global bondedDevices, holdConnection, DisconnectedCalled
    retval = client.RunPairingSequence(**securitySettings)
    if retval in [None, False] or isinstance(retval, SmpPairingFailed):
        LogWrite("Pairing procedure failed")
        return False
    else:
        connInfo = GetConnInfo()
        if connInfo == None:
            LogWrite("Error: No connection")
            return False

        bondedDevices[connInfo.PeerAddress] = retval
    return retval

def BondToDevice(*args,**argv):
    global connected, bondedDevices
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    try:
        if not connected:
            connectSuccess = Connect(*args,**argv)
            if not connectSuccess:
                return False

        connInfo = GetConnInfo()
        if connInfo == None:
            LogWrite("Error: No connection")
            return False

        if connInfo.PeerAddress in bondedDevices:
            LogWrite("Bond already exists with %s" % argv['peerAddress'])
            return False

        ioCapabilities = gattResponse.IoCapabilitiesRequest()
        argv.update({'IO': ioCapabilities})
        oobKeyPresent = gattResponse.OobKeyPresent()
        argv.update({'OOB': oobKeyPresent})
        retval = StartPairingProcedure(**argv)
        if retval in [False, None]:
            return False
        elif retval['ReceivedPairingFailed'] != None:
            return False

        if not connected:
            return False

        if client.PairingPaused:
            retval['TK'] = _getKey(client.PairingPaused)
            if retval['TK'] != None:
                negotiatedSecurity = _getNegotiatedSecurity(client.PairingPaused)
                retval = client.ContinuePairingSequence(retval)
            else:
                return False
        else:
            negotiatedSecurity = "JustWorks"

        if retval['ReceivedPairingFailed'] != None:
            return False

        wbAddress = Ulpbt.WbDeviceAddress.CreateAddress(argv['peerAddress'])
        gattResponse.BondingCompleteResponse(wbAddress)
    except Exception, ex:
        LogTraceback(ex)
    finally:
        gattResponse.StateChange(gattResponse.State.StateScriptReady)

    return True

def _getKey(pairingPausedValue):
    key = None
    if pairingPausedValue in ['RespKey', 'Both']:
        try:
            key = _getPasskey()
        except KeyRequestFailedException, ex:
            packet = SmpPairingFailed(protocol.Smp.errorCodes['Passkey Entry Failed'])
            smp.driver.Write(packet)

    elif pairingPausedValue in ['InitKey']:
        generatedPasskey = _generateRandomPasskey()
        LogWrite("Generated passkey: %06d" % generatedPasskey, debug="file")
        gattResponse.DisplayPasskey(generatedPasskey)
        key = _convertKeyToList(generatedPasskey)

    elif pairingPausedValue in ['OobKey']:
        try:
            key = _getOobKey()
        except KeyRequestFailedException, ex:
            packet = SmpPairingFailed(protocol.Smp.errorCodes['OOB Not Available'])
            smp.driver.Write(packet)
    else:
        LogWrite("Invalid pairingPaused value: %s" % pairingPausedValue)

    return key

def _getNegotiatedSecurity(pairingPausedValue):
    negotiatedSecurity = ""
    if pairingPausedValue in ['RespKey', 'Both']:
        negotiatedSecurity = "Passkey"

    elif pairingPausedValue in ['InitKey']:
        negotiatedSecurity = "Passkey"

    elif pairingPausedValue in ['OobKey']:
        negotiatedSecurity = "OutOfBand"

    return negotiatedSecurity

class KeyRequestFailedException(Exception):
    pass

def _getPasskey():
    keyParameter = {'key':None, 'reject':False}
    keyParameter['key'] = gattResponse.PasskeyRequest()
    key = keyParameter['key']
    if keyParameter['reject'] == True:
        key = 0
    elif key == None:
        raise Exception("Did not receive passkey")
    if type(key) != int:
        raise Exception("Passkey must be of type int")
    if key < 0:
        raise KeyRequestFailedException("Passkey entry aborted")
    if key < 0 or key > 999999:
        raise Exception("Invalid key value. Must be between 0 and 999999.")
    keyList = _convertKeyToList(key)
    return keyList

def _getOobKey():
    keyParameter = {'key':None, 'reject':False}
    keyParameter['key'] = gattResponse.OobKeyRequest()
    key = keyParameter['key']
    # Manually entered OOB key:
    #key = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xA, 0xB, 0xC, 0xD, 0xE, 0xF]
    if isinstance(key, System.Array[System.Byte]):
        key = [int(value) for value in key]
    if keyParameter['reject'] == True:
        key = []
    elif key == None:
        raise Exception("Did not receive OOB key")
    if type(key) not in [list, tuple]:
        raise Exception("OOB key must be of type list or tuple")
    if len(key) == 0:
        key = _padKeyLength(key)
    elif len(key) != 16:
        raise Exception("Invalid length of OOB key. Must be 16.")
    return key

def _convertKeyToList(key):
    keyTmp = int(key)
    keyList = [int("%02X" % (0xFF & (keyTmp >> i)),16) for i in range((3-1)*8,-1,-8)]
    paddedKey = _padKeyLength(keyList)
    return paddedKey

def _padKeyLength(keyList):
    keyLength = len(keyList)
    keyPaddingLength = 16 - keyLength
    paddedKey = [0]*keyPaddingLength
    paddedKey.extend(keyList)
    return paddedKey

def _generateRandomPasskey():
    minValue = 1
    maxValue = 999999
    passkey = random.randint(minValue, maxValue)
    return passkey

def CopyRemoteDB():
    global connected
    handleDict = {}
    allHandles = False
    starthdl = 0x0001; endhdl = 0xFFFF
    LogWrite("Starting a Read Information Request on the whole remote DB")
    while True:
        if not connected:
            LogWrite("Lost connection before service discovery were complete")
            return None
        if starthdl == 0:
            break
        att.SendFindInformationRequest(startHdl=starthdl,endHdl=endhdl)
        ret = tester.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE,T=5)
        if ret == None:
            break
        if isinstance(ret,AttFindInformationResponse):
            for attpkt in ret.Attributes:
                handleDict[attpkt.handle] = {'UUID':attpkt.uuid}
            starthdl = ret.Attributes[-1].handle + 1
        else:
            break
    return handleDict

def discoverServices():
    try:
        handleDict = CopyRemoteDB()
        discoverAllHandles(handleDict)
        requestAllAttributeData(handleDict)

        connInfo = GetConnInfo()
        gattResponse.ServiceDiscoveryCompleteResponse()
        LogWrite("Service Discovery complete")
    except Exception, ex:
        LogTraceback(ex)

def discoverAllHandles(handleDict):
    global RemoteHandleDict, connected
    connInfo = GetConnInfo()
    services = List[Ulpbt.GattServiceGroup]()
    service = None
    charDec = None
    attribute = None

    LogWrite("Discovering all attribute UUIDs")
    connectionError = "Lost connection before service discovery was complete"

    for handle in sorted(handleDict.iterkeys()):
        if not connected:
            raise Exception(connectionError)

        LogWrite("Handle: 0x%04X, UUID: 0x%04X" % (handle, handleDict[handle]['UUID']))

        object = ParseDictionary(handle,handleDict[handle])
        if object == None:
            continue

        object.IsUnpopulated = True

        if isinstance(object,Ulpbt.GattServiceGroup):
            LogWrite("Received a Service group UUID")
            if service != None:
                if charDec != None:
                    service.AddCharacteristicGroup(charDec)
                    charDec = None
                services.Add(service)
            service = object

        elif service != None:
            if isinstance(object, Ulpbt.GattInclude):
                LogWrite("Received an Included Service Group UUID")
                service.AddGroupAttribute(object)
            elif isinstance(object,Ulpbt.GattCharacteristicGroup):
                LogWrite("Received a Characteristic Group group UUID")
                if charDec != None:
                    service.AddCharacteristicGroup(charDec)
                charDec = object
            elif charDec != None:
                LogWrite("Received a Characteristic Group group attribute")
                charDec.AddCharacteristic(object)
            else:
                LogWrite("Received a Service Group group attribute")
                service.AddGroupAttribute(object)
        else:
            # Need to add an error that no attribute can be added if there is no service group
            LogWrite("Could not add received handle to any group")

    if service != None:
        if charDec != None:
            service.AddCharacteristicGroup(charDec)
        services.Add(service)

    if not connected:
        raise Exception(connectionError)

    gattResponse.ServiceDiscoveryResponse(services)

    if not connected:
        raise Exception(connectionError)

    RemoteHandleDict[connInfo.PeerAddress] = handleDict
    RemoteHandleDict[connInfo.PeerAddress]['ServiceObject'] = services

def requestAllAttributeData(handleDict):
    global connected
    connectionError = "Lost connection before service discovery was complete"

    if not connected:
        raise Exception(connectionError)

    LogWrite("Discovering all attribute values")
    for handle in sorted(handleDict.iterkeys()):
        if type(handle) != int:
            continue
        if not connected:
            break
        _readAttributeValue(handle)

def progress_changed(progress=0, log_message="", done=False):
    gattResponse.ProgressChange(progress, log_message, done)

def BleProgram(emulatorId, devAddress, dfuZipFile, baudRate):
    import logging
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(stream_handler)

    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    gattResponse.ProgressChange(0, "Starting...")

    global deviceAddress
    own_address = deviceAddress

    try:
        LTK = bondedDevices[devAddress]['LTK']
        RAND = bondedDevices[devAddress]['RAND']
        EDIV = bondedDevices[devAddress]['EDIV']

        bondInfo = (LTK, RAND, EDIV)
    except Exception, ex:
        bondInfo = None

    try:
        dfu_backend = DfuTransportMe(devAddress.upper(), baudRate, emulatorId, own_address, bondInfo)
        dfu_backend.register_events_callback(DfuEvent.PROGRESS_EVENT, progress_changed)
        dfu = Dfu(dfuZipFile, dfu_backend)

        # Transmit the hex image to peer device.
        dfu.dfu_send_images()

        gattResponse.ProgressChange(100, "Done", True)
        gattResponse.StateChange(gattResponse.State.StateScriptReady)
        return
    except Exception, ex:
        LogWrite(ex)

    gattResponse.ProgressChange(0, "Error during firmware upload. %s" % ex, True)
    dfu_backend.close()
    gattResponse.StateChange(gattResponse.State.StateScriptReady)


def EnableServices(cccdPairs):
    for handle, cccdValue in cccdPairs.iteritems():
        SetClientConfiguration(handle, cccdValue)

def DisableServices(cccdPairs):
    for handle, cccdValue in cccdPairs.iteritems():
        cccdValue = 0 #Disable cccd
        SetClientConfiguration(handle, cccdValue)

def SetClientConfiguration(handle, cccdValue):
    global RemoteHandleDict, connected
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)

    if not connected:
        LogWrite("Not connected")
        gattResponse.StateChange(gattResponse.State.StateScriptReady)
        return

    try:
        connInfo = GetConnInfo()
        if connInfo == None:
            LogWrite("Error: No connection")
            return False

        handleDict = RemoteHandleDict[connInfo.PeerAddress]
        Content = [cccdValue, 0x00]

        att.SendWriteRequest(handle,Content)
        ret = tester.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE,T=5)
        didReceiveError = False

        if isinstance(ret,AttWriteResponse):
            handleDict[handle]['DATA'] = Content
            LogWrite("Updated handle %04X with value %s" % (handle,handleDict[handle]['DATA']))
            gattResponse.AttributeUpdateNotification(ParseDictionary(handle,handleDict[handle]))
        elif isinstance(ret,AttErrorResponse):
            didReceiveError = True
            if ret.ErrorCode == AttCommands.WRITE_NOT_PERMITTED:
                handleDict[handle]['W_PERM'] = "no"
            elif ret.ErrorCode == AttCommands.INSUFFICIENT_AUTHENTICATION:
                handleDict[handle]['W_PERM'] = "aut"
            LogWrite("Could not update handle %04X with a new value" % handle)
            errorString = parseAttError(ret.ErrorCode)
            LogWrite("Received error response: %s, handle: 0x%04X" % (errorString, handle))

    except Exception, ex:
        LogTraceback(ex)

    if (connInfo.PeerAddress in RemoteHandleDict) and not didReceiveError:
        serviceObject = RemoteHandleDict[connInfo.PeerAddress]['ServiceObject']
        updateCccdValueInServiceObject(handle, cccdValue, serviceObject)

    gattResponse.StateChange(gattResponse.State.StateScriptReady)

def parseAttError(errorCode):
    if AttErrorCode.containsvalue(errorCode):
        errorString = AttErrorCode.getname(errorCode)
    else:
        errorString = "0x%02X" % errorCode
    return errorString

def updateCccdValueInServiceObject(handle, cccdValue, serviceObject):
    for service in serviceObject:
        for characteristic in service.GetCharacteristicGroups():
            for charAttr in characteristic.GetCharacteristicAttributes():
                if charAttr.Handle == handle:
                    if isinstance(charAttr, Ulpbt.GattClientCharacteristicConfiguration):
                        charAttr.CharacteristicConfigurationBits = cccdValue
                        LogWrite("Successfully updated the store value of CCCD")
                        return

def formatDictionary(dictionary):
    outputList = []
    for key, value in dictionary.iteritems():
        output = ""
        output += "%s: " % key
        if type(value) is dict:
            for subkey, subvalue in value.iteritems():
                output += "%s:" % subkey
                if type(subvalue) is list:
                    listRepr = []
                    for el in subvalue:
                        if type(el) in [int, long]:
                            listRepr.append("%X" % el)
                        else:
                            listRepr.append(str(el))
                    output += "0x["
                    output += ", ".join(listRepr)
                    output += "]"
                else:
                    if type(subvalue) in [int, long]:
                        output += "0x%X " % subvalue
                    else:
                        output += "%s " % str(subvalue)
        else:
            output += str(value)
        outputList.append(output)
    endOutput = "\r\n".join(outputList)
    return endOutput

def CreateServerFromObject():
    global LocalHandleDict,gattResponse
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    handle = 0x0001
    handleDict = {}
    try:
        gattObject = Ulpbt.GattResponse.GattServerObject
        for service in gattObject:
            handle = processGattObjectService(service, handleDict, handle)
        formattedDict = formatDictionary(handleDict)
        LogWrite("Successfully parsed the server setup: \r\n%s" % formattedDict, debug="file")

    except Exception, ex:
        LogTraceback(ex)
    gattResponse.CreateDatabaseResponse(gattObject)
    LocalHandleDict = handleDict
    gattResponse.StateChange(gattResponse.State.StateScriptReady)

def getUuidAsList(btuuid):
    if btuuid.HasBtBase():
        uuid16AsList = [btuuid.Uuid16bit & 0xFF,(btuuid.Uuid16bit >> 8) & 0xFF]
        return uuid16AsList
    else:
        uuid128AsList = [int(el) for el in btuuid.Uuid128bit]
        return uuid128AsList

def getUuidAsNumeral(btuuid):
    if btuuid.HasBtBase():
        uuid16AsNumeral = int(btuuid.Uuid16bit)
        return uuid16AsNumeral
    else:
        uuid128AsNumeral = int(btuuid.Uuid128bitHexString, 16)
        return uuid128AsNumeral

def processGattObjectService(service, handleDict, handle):
    data = getUuidAsList(service.ServiceGroupUuid)
    handleDict[handle] = {'UUID':getUuidAsNumeral(service.UUID),'DATA':data,'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'INDICATE':"no"}
    service.Handle = handle
    handle += 1
    characteristicList = service.GetCharacteristicGroups()
    for characteristic in characteristicList:
        handleDict[handle] = {'UUID':getUuidAsNumeral(characteristic.UUID), 'R_PERM':"yes", 'W_PERM':"no", 'NOTIFY':"no", 'INDICATE':"no"}
        characteristic.Handle = handle
        handle += 1

        charAttribList = characteristic.GetCharacteristicAttributes()
        for charAttr in charAttribList:
            w_perm = "no"
            r_perm = "no"
            notify = "no"
            indicate = "no"

            if isinstance(charAttr,Ulpbt.GattCharacteristicValue):
                data = charAttr.Value
                if characteristic.CharacteristicProperties & PROPERTIES_READ:
                    r_perm = "yes"
                if characteristic.CharacteristicProperties & (PROPERTIES_WRITE | PROPERTIES_WRITE_WITHOUT_RESPONSE):
                    w_perm = "yes"
                if characteristic.CharacteristicProperties & PROPERTIES_AUTHENTICATED:
                    w_perm = "aut"
                if characteristic.CharacteristicProperties & PROPERTIES_NOTIFY:
                    notify = "yes"
                if characteristic.CharacteristicProperties & PROPERTIES_INDICATE:
                    indicate = "yes"
                tempHandle  = handle
                tempUuid    = charAttr.UUID
            elif isinstance(charAttr,Ulpbt.GattCharacteristicFormat):
                data = [charAttr.Format & 0xFF,
                        charAttr.Exponent & 0xFF,
                        charAttr.Unit & 0xFF, (charAttr.Unit >> 8) & 0xFF,
                        charAttr.NameSpace & 0xFF,
                        charAttr.Description & 0xFF, (charAttr.Description >> 8) & 0xFF]
                r_perm = "yes"
            elif isinstance(charAttr,Ulpbt.GattClientCharacteristicConfiguration):
                w_perm = "yes"
                r_perm = "yes"
            else:
                #if characteristic.CharacteristicProperties & FEATURE_WRITEABLE_AUXILARIES:
                #    w_perm = "yes"
                data = charAttr.Value
            if (data != None):
                data = [int(dataEl) for dataEl in data]
            else:
                data = []
            handleDict[handle] = {'UUID':getUuidAsNumeral(charAttr.UUID),'DATA':data,'R_PERM':r_perm,'W_PERM':w_perm,'NOTIFY':notify,'INDICATE':indicate}
            charAttr.Handle = handle
            handle += 1
        characteristic.CharacteristicHandle = tempHandle
        characteristic.CharacteristicUuid   = tempUuid
        charData = [characteristic.CharacteristicProperties & 0xFF, tempHandle & 0xFF, (tempHandle >> 8) & 0xFF] + getUuidAsList(characteristic.CharacteristicUuid)
        handleDict[characteristic.Handle]['DATA'] = charData
    return handle

def createGattObject(data, uuid16):
    gattObject = None
    if uuid16 == PRIMARY_SERVICE_GROUP_UUID:
        gattObject = Ulpbt.GattPrimaryService()

    elif uuid16 == SECONDARY_SERVICE_GROUP_UUID:
        gattObject = Ulpbt.GattSecondaryService()

    elif uuid16 == INCLUDE_UUID:
        gattObject = Ulpbt.GattInclude()

    elif uuid16 == CHARACTERISTIC_DECLARATION:
        gattObject = Ulpbt.GattCharacteristicGroup()

    elif uuid16 == CHARACTERISTIC_DESCRIPTION:
        gattObject = Ulpbt.GattCharacteristicUserDescription()

    elif uuid16 == CLIENT_CHARACTERISTIC_CONFIGURATION:
        gattObject = Ulpbt.GattClientCharacteristicConfiguration()

    elif uuid16 == SERVER_CHARACTERISTIC_CONFIGURATION:
        gattObject = Ulpbt.GattServerCharacteristicConfiguration()

    elif uuid16 == CHARACTERISTIC_FORMAT:
        gattObject = Ulpbt.GattCharacteristicFormat()

    elif uuid16 == AGGREGATE_FORMAT:
        gattObject = Ulpbt.GattCharacteristicAggregateFormat()

    elif uuid16 == ATTRIBUTE_OPCODE_SUPPORTED:
        gattObject = Ulpbt.GattAttOpcodesSupported()

    elif uuid16 == DEVICE_NAME:
        gattObject = Ulpbt.GattGapDeviceName()

    elif uuid16 == APPEARANCE:
        gattObject = Ulpbt.GattGapAppearance()

    elif uuid16 == SLAVE_PREFFERED_CONN_PARAM:
        gattObject = Ulpbt.GattGapSlavePreferredSlaveConnParams()

    else:
        # Unknown UUID
        pass

    return gattObject

def populateGattObject(gattObject, data, uuid16):
    if uuid16 == PRIMARY_SERVICE_GROUP_UUID:
        if len(data) < 2:
            return False
        elif len(data) == 2:
            temp = (data[1] << 8) | data[0]
            gattObject.ServiceGroupUuid = Ulpbt.BtUuid(temp)
        elif len(data) > 2:
            temp = System.Array[System.Byte](data)
            gattObject.ServiceGroupUuid = Ulpbt.BtUuid(temp)

    elif uuid16 == SECONDARY_SERVICE_GROUP_UUID:
        if len(data) < 2:
            return False
        elif len(data) == 2:
            temp = (data[1] << 8) | data[0]
            gattObject.ServiceGroupUuid = Ulpbt.BtUuid(temp)
        elif len(data) > 2:
            temp = System.Array[System.Byte](data)
            gattObject.ServiceGroupUuid = Ulpbt.BtUuid(temp)

    elif uuid16 == INCLUDE_UUID:
        if len(data) >= 4:
            gattObject.IncludedServiceAttributeHandle = (data[1] << 8) | data[0]
            gattObject.EndGroupHandle = (data[3] << 8) | data[2]
        if len(data) > 4:
            gattObject.ServiceUuid = (data[5] << 8) | data[4]

    elif uuid16 == CHARACTERISTIC_DECLARATION:
        if len(data) < 3:
            return False

        gattObject.CharacteristicProperties = data[0]
        gattObject.CharacteristicHandle = (data[2] << 8) | data[1]
        charUuid = data[3:]
        if len(charUuid) == 2:
            gattObject.CharacteristicUuid = Ulpbt.BtUuid((charUuid[1] << 8) | charUuid[0])
        elif len(charUuid) > 2:
            gattObject.CharacteristicUuid = Ulpbt.BtUuid(System.Array[System.Byte](charUuid))

    elif uuid16 == CHARACTERISTIC_DESCRIPTION:
        gattObject.UserDescription = "".join("%s" % chr(el) for el in data)

    elif uuid16 == CLIENT_CHARACTERISTIC_CONFIGURATION:
        if len(data) < 2:
            return False

        gattObject.CharacteristicConfigurationBits = (data[1] << 8) | data[0]

    elif uuid16 == SERVER_CHARACTERISTIC_CONFIGURATION:
        if len(data) < 2:
            return False

        gattObject.CharacteristicConfigurationBits = (data[1] << 8) | data[0]

    elif uuid16 == CHARACTERISTIC_FORMAT:
        if len(data) < 7:
            return False

        gattObject.Format = data[0]
        gattObject.Exponent = System.SByte(data[1])
        gattObject.Unit = (data[3] << 8) | data[2]
        gattObject.NameSpace = data[4]
        gattObject.Description = (data[6] << 8) | data[5]

    elif uuid16 == AGGREGATE_FORMAT:
        for i in range(0,len(data),2):
            formatHandle = System.UInt16((data[i+1] << 8) | data[i])
            gattObject.AddFormatHandle(formatHandle)

    elif uuid16 == ATTRIBUTE_OPCODE_SUPPORTED:
        temp = 0
        data.reverse()
        for i in range(len(data)):
            temp = temp << 8 | data[i]
        gattObject.OpcodesSupported = temp

    elif uuid16 == DEVICE_NAME:
        gattObject.DeviceName = "".join("%s" % chr(el) for el in data)

    elif uuid16 == APPEARANCE:
        if len(data) < 2:
            return False

        gattObject.Appearance = (data[1] << 8) | data[0]

    elif uuid16 == SLAVE_PREFFERED_CONN_PARAM:
        length = len(data)
        if length <= 2:
            return False
        if length >= 2:
            gattObject.MinimumConnectionInterval = data[0] | data[1] << 8
        if length >= 4:
            gattObject.MaximumConnectionInterval = data[2] | data[3] << 8
        if length >= 6:
            gattObject.SlaveLatency = data[4] | data[5] << 8
        if length >= 8:
            gattObject.SupervisionTimeoutMultiplier = data[6] | data[7] << 8

    #If the method hasn't return by now, there have been no errors.
    return True

def ParseDictionary(handle,lookupDict):
    uuid = lookupDict['UUID']

    maxUshortValue = 0xFFFF
    if int(uuid) > maxUshortValue:
        converted128bitNum = "%032X" % int(uuid)
        btuuid = Ulpbt.BtUuid(converted128bitNum)
    else:
        btuuid = Ulpbt.BtUuid(uuid)

    if 'DATA' in lookupDict:
        data = lookupDict['DATA']
    else:
        data = None

    gattObject = None
    parseSuccess = True

    if btuuid.HasBtBase():
        uuid16 = int(btuuid.Uuid16bit)
        gattObject = createGattObject(data, uuid16)
        if data != None:
            parseSuccess = populateGattObject(gattObject, data, uuid16)

    if gattObject == None:
        gattObject = Ulpbt.GattCharacteristicValue()  # CharacteristicValue here means value or descriptor

    if data != None:
        gattObject.Value = System.Array[System.Byte](data)

    gattObject.UUID = btuuid
    gattObject.Handle = handle

    if not parseSuccess:
        LogWrite("Warning: Value for handle 0x%04X is too short, cannot parse successfully." % handle)

    return gattObject

def ReadAttributeValue(handle):
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    try:
        _readAttributeValue(handle)
    except Exception,ex:
        LogTraceback(ex)
    finally:
        gattResponse.StateChange(gattResponse.State.StateScriptReady)

def _readAttributeValue(handle):
    global RemoteHandleDict
    connInfo = GetConnInfo()
    handleDict = RemoteHandleDict[connInfo.PeerAddress]
    att.SendReadRequest(handle)
    value = None
    retval = tester.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE,
                            TYPE=[AttReadResponse, AttErrorResponse],
                            T=10)

    if connInfo == None:
        LogWrite("Not connected")
        return False

    if retval == None:
        LogWrite("No response received for ReadRequest on handle 0x%04X. Disconnecting.." % handle)
        Disconnect()
        raise Exception("Service discovery aborted, connection terminated.")

    if isinstance(retval, AttReadResponse):
        value = retval.Attributes.value
        valueHex = "-".join(["%02X" % val for val in value])
        LogWrite("Received Read Response, handle: 0x%04X, value (0x): %s" % (handle, valueHex))
        handleDict[handle]['DATA'] = value
        gattResponse.AttributeUpdateNotification(ParseDictionary(handle, handleDict[handle]))

    elif isinstance(retval, AttErrorResponse):
        errorString = parseAttError(retval.ErrorCode)
        LogWrite("Received Error Response: %s, handle: 0x%04X" % (errorString, handle))
        if retval.ErrorCode == AttCommands.READ_NOT_PERMITTED:
            handleDict[handle].update({'R_PERM':"no"})
        elif retval.ErrorCode == AttCommands.INSUFFICIENT_AUTHENTICATION:
            handleDict[handle].update({'R_PERM':"aut"})
    else:
        LogWrite("Received an unexpected ATT packet: %r: %s" % (retval, retval))

    return True

def ReadLongAttributeValue(handle):
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    offset = 0
    try:
        connInfo = GetConnInfo()
        value = []
        while True:
            att.SendReadBlobRequest(handle, offset)
            retval = tester.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE,
                                    TYPE=[AttReadBlobResponse, AttErrorResponse],
                                    T=30)
            if retval == None:
                LogWrite("No response received for ReadBlobRequest on handle 0x%04X" % handle)
                break
            if isinstance(retval, AttReadBlobResponse):
                valueTemp = retval.Attributes.value
                valueHex = "-".join(["%02X" % val for val in valueTemp])
                LogWrite("Received Read Blob Response, offset %s, value (0x): %s" % (offset, valueHex))
                value[offset:] = retval.Attributes.value
                length = len(retval.Attributes.value)
                if length == ATT_MTU-1:
                    offset += length
                else:
                    RemoteHandleDict[connInfo.PeerAddress][handle]['DATA'] = value
                    gattResponse.AttributeUpdateNotification(ParseDictionary(handle, RemoteHandleDict[connInfo.PeerAddress][handle]))
                    break
            elif isinstance(retval, AttErrorResponse):
                errorString = parseAttError(retval.ErrorCode)
                LogWrite("Received error response: %s, handle: 0x%04X" % (errorString, handle))
                break
            else:
                LogWrite("Received an unexpected ATT packet: %r: %s" % (retval,retval))
                break
    except Exception,ex:
        LogTraceback(ex)

    gattResponse.StateChange(gattResponse.State.StateScriptReady)

LONG_WRITE_MODE = 1
def UpdateAttributeValue(mode=None):
    global RemoteHandleDict, connected
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)
    try:
        content = []
        updateObj = Ulpbt.GattResponse.GattAttributeUpdateObject
        if updateObj.valueIsText:
            strData = "".join("%s" % chr(el) for el in updateObj.Value)
        else:
            strData = "".join("%02X" % int(el) for el in updateObj.Value)

        content = [int(el) for el in updateObj.Value]
        if not connected:
            return

        handle = updateObj.Handle

        if mode == LONG_WRITE_MODE:
            _attributeLongWrite(handle, content)
            return

        elif isCharacteristicValue(handle):
            _attributeCharacteristicWrite(handle, content)
        else:  # must be characteristic descriptor
            _attributeDescriptorWrite(handle, content)

    except Exception, ex:
        LogTraceback(ex)
    finally:
        gattResponse.StateChange(gattResponse.State.StateScriptReady)

def isCharacteristicValue(handle):
    connInfo = GetConnInfo()
    uuid = RemoteHandleDict[connInfo.PeerAddress][handle-1]['UUID']
    if uuid == CHARACTERISTIC_DECLARATION:
        return True
    return False

def _attributeLongWrite(handle, content):
    global RemoteHandleDict
    connInfo = GetConnInfo()
    uuid = RemoteHandleDict[connInfo.PeerAddress][handle]['UUID']
    properties  = Gatt.CHARACTERISTICPROPERTIES['Write']
    properties |= Gatt.CHARACTERISTICPROPERTIES['Write Without Response']
    characteristic = GattCharacteristic(0, properties, handle, uuid)

    LogWrite("Sending Prepare/Execute Write Request, handle 0x%04X, value %s" % (handle, content))

    ret = gatt.WriteLongCharacteristicValues(characteristic, content, timeout=5)
    tester.pktQueue.emptyQueue()

    if isinstance(ret, AttErrorResponse):
        if ret.ErrorCode == AttCommands.WRITE_NOT_PERMITTED:
            RemoteHandleDict[connInfo.PeerAddress][handle]['W_PERM'] = "no"
        elif ret.ErrorCode == AttCommands.INSUFFICIENT_AUTHENTICATION:
            RemoteHandleDict[connInfo.PeerAddress][handle]['W_PERM'] = "aut"
        errorString = parseAttError(ret.ErrorCode)
        LogWrite("Could not update handle 0x%04X with new value. Error code: %s" % (handle, errorString))
        return
    elif ret == False:
        LogWrite("Error. Did not receive response for Prepare/Execute Write Request, handle 0x%04X." % handle)
        return

    RemoteHandleDict[connInfo.PeerAddress][handle]['DATA'] = content
    LogWrite("Updated handle %04X with value %s" % (handle, content))
    gattResponse.AttributeUpdateNotification(ParseDictionary(handle, RemoteHandleDict[connInfo.PeerAddress][handle]))

def _attributeCharacteristicWrite(handle, content):
    connInfo = GetConnInfo()
    properties = RemoteHandleDict[connInfo.PeerAddress][handle-1]['DATA'][0]
    if properties & PROPERTIES_WRITE:
        _sendWriteRequest(handle, content)
    elif properties & PROPERTIES_WRITE_WITHOUT_RESPONSE:
        _sendWriteCommand(handle, content)
    else:
        _sendWriteRequest(handle, content)

def _attributeDescriptorWrite(handle, content):
    _sendWriteRequest(handle, content)

def _sendWriteCommand(handle, content):
    global RemoteHandleDict
    connInfo = GetConnInfo()
    att.SendWriteCommand(handle, content)
    LogWrite("WriteCommand sent to handle 0x%04X with value %s" % (handle, content))
    RemoteHandleDict[connInfo.PeerAddress][handle]['DATA'] = content
    gattResponse.AttributeUpdateNotification(ParseDictionary(handle,RemoteHandleDict[connInfo.PeerAddress][handle]))

def _sendWriteRequest(handle, content):
    global RemoteHandleDict
    connInfo = GetConnInfo()
    LogWrite("WriteRequest sent to handle 0x%04X with value %s" % (handle, content))
    att.SendWriteRequest(handle,content)
    ret = tester.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE,
                         TYPE=[AttWriteResponse, AttErrorResponse], T=5)
    if isinstance(ret, AttWriteResponse):
        RemoteHandleDict[connInfo.PeerAddress][handle]['DATA'] = content
        LogWrite("Updated handle %04X with value %s" % (handle,RemoteHandleDict[connInfo.PeerAddress][handle]['DATA']))
        gattResponse.AttributeUpdateNotification(ParseDictionary(handle,RemoteHandleDict[connInfo.PeerAddress][handle]))
    elif isinstance(ret, AttErrorResponse):
        if ret.ErrorCode == AttCommands.WRITE_NOT_PERMITTED:
            RemoteHandleDict[connInfo.PeerAddress][handle]['W_PERM'] = "no"
        elif ret.ErrorCode == AttCommands.INSUFFICIENT_AUTHENTICATION:
            RemoteHandleDict[connInfo.PeerAddress][handle]['W_PERM'] = "aut"
        errorString = parseAttError(ret.ErrorCode)
        LogWrite("Could not update handle 0x%04X with new value. Error code: %s" % (handle, errorString))

def UpdateServerAttributeValue():
    global LocalHandleDict
    gattResponse.StateChange(gattResponse.State.StateScriptBusy)

    try:
        if testServer.isAlive():
            LocalHandleDict = testServer.GetServerDb()
        else:
            LogWrite("Server is not running")
            return

        Content = []
        updateObj = Ulpbt.GattResponse.GattAttributeUpdateObject
        handle = updateObj.Handle
        #strData = "".join("%02X" % int(el) for el in updateObj.Value)
        Content = [int(el) for el in updateObj.Value]
        if not handle in LocalHandleDict:
            LogWrite("Handle %s was not found in local server setup: %s" % (handle, LocalHandleDict))
            return

        LocalHandleDict[handle]['DATA'] = Content
        gattResponse.ServerAttributeUpdateNotification(ParseDictionary(handle,LocalHandleDict[handle]))

        testServer.UpdateServerDb(LocalHandleDict)
        if not connected:
            return

        if 'NOTIFY' in LocalHandleDict[handle] and LocalHandleDict[handle]['NOTIFY'] == 'yes':
            att.SendHandleValueNotification(handle, Content)
            LogWrite("Sent handle value notification on handle 0x%04X" % handle)
        elif 'INDICATE' in LocalHandleDict[handle] and LocalHandleDict[handle]['INDICATE'] == 'yes':
            att.SendHandleValueIndication(handle, Content)
            LogWrite("Sent handle value indication on handle 0x%04X" % handle)

    except Exception, ex:
        LogTraceback(ex)
    finally:
        gattResponse.StateChange(gattResponse.State.StateScriptReady)

def GetListOfBondedDevices():
    wbList = List[Ulpbt.WbDeviceAddress]()
    for address in bondedDevices:
        wbList.Add(Ulpbt.WbDeviceAddress.CreateAddress(address))
    gattResponse.BondedDevicesResponse(wbList)

def DeleteDiscoveredDevices():
    global RemoteHandleDict
    RemoteHandleDict = {}

def ClearListOfBondedDevices():
    global bondedDevices
    bondedDevices = {}
    DeleteDiscoveredDevices()

def GetVersionInfo():
    versionInfo = None
    try:
        cmd = hci.NrfBuildGetVersionInfo()
        ftdiComm.WriteCmd(cmd.GetPacket())
        cmdEvent = tester.WaitFor(hciComm.HCI_COMMAND_COMPLETE_EVENT,
                                  CMD_OPCODE=hciComm.NRF_CMD_GET_VERSION_INFO,
                                  T=1)
        if cmdEvent != None:
            versionInfo = cmdEvent.GetVersionInfo()
            validateVersionInfo(versionInfo)
            LogWrite("Master emulator firmware version: %s" % versionInfo)
        else:
            raise Exception("No response from master emulator")
    except Exception, ex:
       LogWrite("Could not read controller version info. %s" % (ex,), debug="file")
    return versionInfo

def validateVersionInfo(versionInfo):
    try:
        testMessage = ", ".join(str(el) for el in versionInfo) #Parsing string to see if it's printable
    except:
        raise Exception("Please upgrade master emulator firmware")

def GetPublicDeviceAddress():
    deviceAddress = None
    try:
        cmd = hci.HciBuildHciReadPublicDeviceAddress()
        ftdiComm.WriteCmd(cmd.GetPacket())
        cmdEvent = tester.WaitFor(hciComm.HCI_COMMAND_COMPLETE_EVENT,
                                  CMD_OPCODE=hciComm.BTLE_CMD_LE_READ_BD_ADDR,
                                  T=1)
        if cmdEvent != None:
            deviceAddress = cmdEvent.GetPublicDeviceAddress().ToString()
            LogWrite("Device address: 0x%s" % deviceAddress, debug="file")
        else:
            raise Exception("No response from master emulator")
    except Exception, ex:
        LogWrite("Could not read public device address: %s" % ex, debug="file")
    return deviceAddress

def LogTraceback(ex):
    LogWrite("%s" % str(ex))
    stacktrace = traceback.extract_tb(sys.exc_info()[2])
    stacktraceFormatted = "\n\t".join(str(el) for el in stacktrace)
    LogWrite(stacktraceFormatted, debug="file")

def LogWrite(*args,**argv):
    try:
        message = ", ".join(str(el) for el in args)
    except Exception, ex:
        gattResponse.LogMessage("Exception: Can't convert log message to string")
        Common.LogWrite(ex)
        stacktrace = traceback.extract_tb(sys.exc_info()[2])
        Common.LogWrite(str(stacktrace), debug="file")
        return
    if 'debug' not in argv:
        try:
            gattResponse.LogMessage(message)
        except:
            pass
    Common.LogWrite(message)

##############

_assignWaitValidators()
deviceAddress = GetPublicDeviceAddress()
#GetVersionInfo()

if deviceAddress != None:
    LogWrite("Ready")
else:
    LogWrite("No response from master emulator.")

gattResponse.StateChange(gattResponse.State.StateScriptReady)

ScriptLoop() #Start the spi application loop
