import sys
import masteremulator
import System
import testerScriptCommon
import time
import traceback
import threading
import pipesetup
import protocol.Att
import protocol.Smp

def logMessageEventHandler(*args):
    print "LOG: %s" % args[0]

def dataCreditEventHandler(*args):
    #print "Data credit event"
    pass

def dataReceivedEventHandler(*args):
    global master
    pipeNumber = args[0]
    data = args[1]
    print "Data received: %s" % (data[0], )
    # if pipeNumber == 2:
        # master.SendDataAck(pipeNumber)

def connectedEventHandler(*args):
    print "Connected event"

def disconnectedEventHandler(*args):
    print "Disconnected event. Reason: %s" % masteremulator._DisconnectReasonCodes.getname(args[0])

def dataAckEventHandler(*args):
    print "Data ack received"

def connectionUpdateRequestEventHandler(*args):
    print "ConnectionUpdateRequest event received: %s" % (args, )
    (identifier, intervalMinMs, intervalMaxMs, slaveLatency, timeoutMs) = args
    response = masteremulator._ConnectionUpdateResponseCode.ACCEPTED
    master.SendConnectionUpdateResponse(identifier, response)

def securityRequestEventHandler(bonding, mitm):
    print "SecurityRequestEvent received. Bonding: %s, Mitm: %s" % (bonding, mitm)

def keyRequestEventHandler(keyType, keyParameter, *args):
    print "KeyRequestEvent received. KeyType: %s" % keyType
    keyString = "123456"
    print "Key: %s" % keyParameter.key

def displayPasskeyEventHandler(passkey, *args):
    print "DiplayPasskeyEvent received. Passkey: %s" % passkey

def pipeError(*args):
    print "Pipe error event"

def dataRequestedEventHandler(pipeNumber, data, *args):
    print "DataRequestedEvent received on pipe %s with data %s" % (pipeNumber, data)
    errorCode = 0x00
    return (data, errorCode)

def deviceDiscoveredEventHandler(device, *args):
    print "DeviceDiscoveredEvent received: %s" % (device, )

master = masteremulator.MasterAPI()
master.DataReceivedEvent = dataReceivedEventHandler
master.DataRequestedEvent = dataRequestedEventHandler
master.DeviceDiscoveredEvent = deviceDiscoveredEventHandler
master.ConnectedEvent = connectedEventHandler
master.DisconnectedEvent = disconnectedEventHandler
master.DataAckEvent = dataAckEventHandler
master.LogMessageEvent = logMessageEventHandler
master.ConnectionUpdateRequestEvent = connectionUpdateRequestEventHandler
master.SecurityRequestEvent = securityRequestEventHandler
master.KeyRequestEvent = keyRequestEventHandler
master.DisplayPasskeyEvent = displayPasskeyEventHandler

usbDevs = master.EnumerateUsb()
master.Open(usbDevs[0])
assert(master.IsOpen())
master.tester.LogWrite = master._logWrite
master.Run()
assert(master.IsRunning())


payloadList = [0]*10
for i in xrange(0, len(payloadList)):
    payloadList[i] = [i] * 40

def threadFunc(arg1, arg2):
    while True:
        print ""
        print "-" * 10
        print time.clock()
        for i in xrange(0, len(payloadList)):
            master.packetProcessor.sendDataReceivedEvent(0, payloadList[i])
            time.sleep(2.001)
            #print payloadList[i]
            #'args are', arg1, arg2
        time.sleep(3)

thread = threading.Thread(target=threadFunc, args=("destination_name", "destination_config"))
thread.daemon = True
thread.start()

sys.stdin.readline()

sys.exit()
