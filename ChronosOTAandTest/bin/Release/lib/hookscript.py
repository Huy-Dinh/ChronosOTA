from testerScriptCommon import *
import Queue, sys, traceback, threading
from math import ceil,log

class HookscriptServer(threading.Thread):
    def __init__(self, tester, attCmds, dataBase = None, logFunc = None, **args):
        self.logoutput = True
        if logFunc != None:
            self.logMethod = tester.LogWrite
            self.guiLogMethod = logFunc
        else:
            self.logMethod = tester.LogWrite
            self.guiLogMethod = tester.LogWrite
            
        try:
            threading.Thread.__init__(self)
            # self.daemon = True
            self.tst = tester
            self.inQueue = Queue.Queue(20)
            self.ePacket = threading.Event()
            self.hookScript = Hookscript(self.LogWrite)
        except Exception,msg:
            self.LogWrite(str(traceback.extract_tb(sys.exc_info()[2])))
            self.LogWrite("Exception: " + str(msg))
    
    def __del__(self):
        self.stop()
    
    def setLogOutput(self, bool):
        self.logoutput = bool

    def LogWrite(self, message):
        self.logMethod("HOOKSCRIPT: " + message)
    
    def ReceivePacket(self, packet):
        try:
            # if (packet.EventCode == SerialCommTypeMapping.ATT_COMMAND_EVENTCODE 
                # or packet.EventCode == SerialCommTypeMapping.SMP_REQUEST_EVENTCODE
                # or packet.EventCode == HciComm.HCI_LL_CONNECTION_TERMINATION_EVENT
                # or packet.EventCode == HciComm.HCI_ENCRYPTION_KEY_REFRESH_COMPLETE_EVENT
                # or packet.EventCode == HciComm.HCI_ENCRYPTION_CHANGE_EVENT):
                self.inQueue.put(packet, True, Common.PACKET_QUEUE_TIMEOUT)
                self.ePacket.set()
        except Exception,msg:
            self.LogWrite("RECEIVE: " + str(traceback.extract_tb(sys.exc_info()[2])))
            self.LogWrite("RECEIVE: Exception: " + str(msg))
            
    def run(self):
        self.tst.AddPacketRecipients(self.ReceivePacket)
        self.running = True
        self.LogWrite("Thread has started")
        while self.running and Dut.doRead:
            try:
                if self.inQueue.empty():
                    self.ePacket.wait(5)
                if not self.ePacket.isSet() and self.inQueue.empty():
                    continue
                packet = self.inQueue.get(True, Common.PACKET_QUEUE_TIMEOUT)
                self.ePacket.clear()
                retval = self.hookScript.processPacket(packet)
                # if self.logoutput:
                    # self.LogWrite("HOOKSCRIPT: " + str(retval))
            except Exception,msg:
                self.LogWrite(str(traceback.extract_tb(sys.exc_info()[2])))
                self.LogWrite("Exception: " + str(msg))
                self.running = False
        self.LogWrite("Thread has stopped")
        
    def stop(self):
        self.LogWrite("Terminating hookscript")
        self.running = False

class Hookscript:
    def __init__(self, logFunc):
        self.LogWrite = logFunc

    def processPacket(self, packet):
        self.LogWrite("Received packet: " + str(packet))