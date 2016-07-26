import sys
sys.path.append("C:\Python26\Lib") #Required to access the threading module located in the python std lib
import threading
import Queue
from datetime import datetime,timedelta
import traceback

class PacketQueue:
    DEFAULT_PACKET_QUEUE_TIMEOUT = 0.2
    DEFAULT_WAIT = 0.7
    DEFAULT_TIMEOUT = 1
    DEFAULT_QUEUE_LENGTH = 20
    ANY_PACKET = "Any packet"   #Constant to be used as input to WaitFor function

    def __init__(self, *args, **argv):
        self.packetQueueTimeout = self.DEFAULT_PACKET_QUEUE_TIMEOUT
        self.wait = self.DEFAULT_WAIT
        self.timeout = self.DEFAULT_TIMEOUT

        self.queueLength = self.DEFAULT_QUEUE_LENGTH
        if "QUEUE_LENGTH" in argv:
            self.queueLength = argv["QUEUE_LENGTH"]

        self.LogWrite = self.defaultLogFunction
        if "LOG_FUNCTION" in argv:
            self.LogWrite = argv["LOG_FUNCTION"]

        self.packetEvent = threading.Event()
        self.packetQueue = Queue.Queue(self.queueLength)
        self.waitLock = threading.Lock()
        self.doRead = True
        self.print_log = False

    def AddToQueue(self, packet):
        if (packet != None):
            try:                                        #Test if the event was generated. If so, inject the event into the event queue
                if self.packetQueue.full():
                    self.packetQueue.get(True, self.packetQueueTimeout)
                    if self.print_log:
                        self.LogWrite("Discarded oldest packet in queue")
                    else:
                        pass
                self.packetQueue.put(packet, True, self.packetQueueTimeout)      #Block for up to 0.2 sec if no slot is available
                self.packetEvent.set()                       #Signal eEvent that a new event is put in the queue
            except Queue.Full, ex:                          #Catch queue full exceptions
                self.LogWrite("Queue Full exception in method AddToQueue().")
            except AttributeError, ex:
                pass
            except Exception, ex:                           #Catch all other exception
                self.LogWrite(traceback.extract_tb(sys.exc_info()[2]))
                self.LogWrite(ex)
        else:
            if self.print_log:
                self.LogWrite("Tried to add empty packet to queue")
            else:
                pass

    ## Search the packet queue for specific packets.
    # @param args Arbitrary number of byte codes to specify which packets to search for
    def PacketQueueSearch(self, *args):

        while (not self.packetQueue.empty()) and self.doRead:              #Loop as long as queue is nonempty, or until we get a match
            try:
                pkt = self.packetQueue.get(True, self.packetQueueTimeout)        #Read (and remove) next event from queue (FIFO) . Blocks for given timeout while trying to get packet from queue
            except Queue.Empty:
                self.LogWrite("Queue Empty exception in method PacketQueueSearch().")
                continue

            if pkt == None:
                return None

            if self.ANY_PACKET in args:
                return pkt

            if pkt.EventCode not in args:
                if self.print_log:
                    self.LogWrite("PacketQueueSearch skipped event code 0x%02X" % (pkt.EventCode))
                continue

            if self.objectType != None:
                if not type(self.objectType) is list:
                    if not isinstance(pkt, self.objectType):
                        continue
                else:
                    if not type(pkt) in self.objectType:
                        continue

            if self.commandCompleteCode != None:
                if not hasattr(pkt, 'CommandOpcode'):
                    continue
                if pkt.CommandOpcode != self.commandCompleteCode:
                    continue

            #All criterias have been fulfilled at this point, so return the packet.
            return pkt

        #Should never get to this point
        return None
    
    ## Search the queue for specified packets and return with found packets. If wanted packets are not found in queue, the function waits for a specified timeout before returning.
    # @param packets Arbitrary number of packet ids to specify which packets to search for
    # @param timeout Key-Value pair for setting of timeout value.
    def WaitFor(self, *packets, **argv):
        with self.waitLock:
            self.commandCompleteCode = None
            self.objectType = None
            self.timeout = self.DEFAULT_TIMEOUT

            self.extractArguments(argv)

            retval = self.PacketQueueSearch(*packets)

            # Return early if we have something
            if retval != None:
                return retval

            startTime = datetime.now()

            while not self.isTimedOut(startTime):
                if self.packetQueue.empty():
                    self.packetEvent.clear()
                    self.packetEvent.wait(self.waitTime)
                else:
                    retval = self.PacketQueueSearch(*packets)

                if retval != None:
                    return retval

                if not self.isPendingWaitValid(*packets):
                    self.LogWrite("Wait canceled: no connection.")
                    return None

            return None
   
    def Cancel(self):
        """Cancel pending wait operations."""
        self.timeout = 0
        self.packetEvent.set()

    def isPendingWaitValid(self, *packets):
        """Returns bool to indicate if the pending wait should proceed or be aborted.
        
        This function is intended to be replaced with a real implementation by the parent object.
        """
        return True

    def isTimedOut(self, startTime):
        timedOut = datetime.now() - startTime > timedelta(0, self.timeout)
        return timedOut

    def extractArguments(self, argv):
        if "CMD_OPCODE" in argv:
            self.commandCompleteCode = argv["CMD_OPCODE"]

        if "TYPE" in argv:
            self.objectType = argv["TYPE"]
            
        if "TIMEOUT" in argv:
            self.timeout = argv["TIMEOUT"]

        elif "T" in argv:
            self.timeout = argv["T"]

        self.waitTime = min(self.timeout, self.wait)

    def emptyQueue(self):
        while not self.packetQueue.empty():
            self.packetQueue.get(True, self.packetQueueTimeout)
        
    def defaultLogFunction(self, *args):
        pass
