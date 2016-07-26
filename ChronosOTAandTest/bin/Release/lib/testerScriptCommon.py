#
# Python module for use with debug panel scripts.
# The moule is a collection of code for tasks needed for supporting the scripts.
# Author: Bjorn Inge Hanssen et al.
# Copyright Nordic Semiconductor 2009
#
import sys
#sys.path.append("C:\Python26\Lib") #Required to access the threading module located in the python std lib
import time
try:
    import pickle
    import modules.ublue_setup as ublue_setup_wrapper
except:
    pass
import traceback
import exceptions
import thread
import copy
import Queue
import random
import socket
import threading
import select
import datetime

import clr
import System               #.NET standard libraries
import System.IO.Ports      #.NET serial port libraries
import System.Diagnostics   #.NET lib for interacting with system processes
clr.AddReferenceByName(r'Ulpbt')
import Ulpbt                #Ulpbt is a Debug Panel library (.NET dll). It includes implementations of hci commands and events, hci packet definitions, hci drivers etc.
clr.AddReferenceByName(r'hci_coder_net')
import hci_coder            #hci_coder contains all hci types.
clr.AddReferenceByName(r'UlpbtUtils')
import UlpbtUtils
import math
import os
import modules.packetqueue
from modules.common import Utilities
import protocol
import protocol.L2Cap
import string

## @class Common
# @brief Class for functionality shared between tester and dut.
class Common:
    Queue_Print = True

    #Define variables
    cont = True
    scriptFilePath  = ""
    outputFilePath  = ""
    outputString    = ""
    numberOfErrors  = 0
    errorLogs = {}
    currentTest = ""
    logOutput = ""
    TestStartTime = None
    runLog = {}
    Role = None
    QuietLog = False
    WriteLogToFileAlways = False
    ClearLogFileAtInit = True
    caller = None

    ANY_PACKET = "Any packet"   #Constant to be used as input to WaitFor function

    EVENT_QUEUE_LENGTH = 200     #Length of queue for incoming packets
    WAITFOR_RETRY_LIMIT = 10    #How many incoming packets to search before exiting waitfor loop
    DEFAULT_WAIT = 0.7             #Seconds of delay in passive wait loop
    PACKET_QUEUE_TIMEOUT = 0.2 #How many seconds to block the queue before timing out when fetching packet at top of queue
    DEFAULT_TIMEOUT = 1        #Default timeout for WaitFor function

    COMMAND_PACKET_ID = int(Ulpbt.HciSpiProtocolType.CommandPacket)
    DATA_PACKET_ID    = int(Ulpbt.HciSpiProtocolType.DataPacket)
    EVENT_PACKET_ID   = int(Ulpbt.HciSpiProtocolType.EventPacket)
    VENDOR_PACKET_ID  = int(Ulpbt.HciSpiProtocolType.VendorPacket)

    ## Constructor
    # @param _caller Instance of calling class in Debug Panel. It is passed to the script as a global at the start of the IronPython scripting engine. The caller object gives access to some parameters set by the debug panel.
    def __init__(self, _caller):
        self.caller = _caller
        # self.packetQueue = Queue.Queue(self.EVENT_QUEUE_LENGTH)         #Queue for incoming packets.
        self.pktQueue = modules.packetqueue.PacketQueue(QUEUE_LENGTH=self.EVENT_QUEUE_LENGTH, LOG_FUNCTION=Common.LogWrite)
        self.ePacket = threading.Event()                                #Event for signaling reception of incoming packets
        Common.scriptFilePath = self.caller.scriptParams.scriptPath     #Extract scriptPath from caller object
        Common.outputFilePath = self.caller.scriptParams.outputFilePath #Extract outputFilePath from caller object
        self.StartScript()                                              #Write debug info to logfile

    ## Prints output to standard out. By giving second argument WRITE_TO_LOGFILE the accumulated string is written to file by the method FileWrite.
    # @param message Text string to write to log
    # @param arg Dictionary for additional params. Currently supporting WRITE_TO_LOG_FILE=(0/1) which will write entire log to output file.
    @staticmethod
    def LogWrite(message, **arg):
        messageString = unicode(message, errors="ignore")
        UlpbtUtils.Debugging.Entry(messageString)

    ## Erase log file by creating a new file that overwrites the existing file. If no file exists a new file will still be created.
    @staticmethod
    def FileClear():
        if (Common.outputFilePath != "" and Common.ClearLogFileAtInit):
            file = open(Common.outputFilePath, 'w')
            file.close()

    # Translates bytes in an array to corresponding ASCII characters
    # @param Array of numeric values.
    # @return Returns the translated array as a string.
    @staticmethod
    def GetTextString(array):
        if array != None:
            retval = ''.join([chr(x) for x in array])
        else:
            retval = ''
        return retval

    ## Represents an array of numbers as a text string
    # @param array Input array
    # @return Returns the string representation of the array
    @staticmethod
    def GetHexString(array):
        if array != None:
            retval = ' '.join(hex(int(x)) for x in array)
        else:
            retval = ''
        return retval

    ## Add debug info to the log file
    @staticmethod
    def StartScript():
        Common.FileClear()
        timenow = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        Common.LogWrite(" - - Start of script: (%s) - - " % timenow)
        info = ""
        if Common.scriptFilePath != "":
            info =  "<scriptfile:\"%s\"/>" % Common.scriptFilePath
        if Common.outputFilePath != "":
            info += "\n<reportfile:\"%s\"/>" % (Common.outputFilePath)
        if FtdiComm.deviceId != None and FtdiComm.deviceId != "":
            info += "\n<ftdi_id:%s/>" % (FtdiComm.deviceId)
        if HciDriver.deviceId != None and HciDriver.deviceId != "":
            info += "\n<device:%s/>" % (HciDriver.deviceId)
        if info == "":
            return
        Common.LogWrite(info)

    ## Add debug info at the end of a test
    @staticmethod
    def EndScript():
        # Common.LogWrite("<b><end of script></b>")
        Common.LogWrite(" - - - - - - - - - - - -  - - - - - - - - - - - -")
        Common.LogWrite(" - - - - - - - End of script - - - - - - - ")
        msg = "<b><number of errors: %d></b>" % Common.numberOfErrors
        if Common.numberOfErrors > 0:
            msg = "<c1>" + msg + "</c1>"
        Common.LogWrite("%s" % msg)
        Common.LogWrite(" - - - - - - - - - - - -  - - - - - - - - - - - -")
        Common.LogWrite("",WRITE_LOG_TO_FILE = True)


    ## Put the thread into sleep for a given number of seconds
    # @param seconds Number of seconds to block the thread. Takes type float, e.g. seconds = 0.345
    @staticmethod
    def Sleep(seconds):
        time.sleep(seconds)

    ## Method to set the name of the test case, used for the NUnit XML file
    # @param name The name of the current test
    @staticmethod
    def SetCurrentTest(name):
        Common.currentTest = name
        Common.TestStartTime = datetime.datetime.now()
        if Common.currentTest not in Common.runLog:
            Common.runLog[Common.currentTest] = {'errors':[],'datetime':Common.TestStartTime.strftime("%Y-%m-%d %H:%M:%S"),'failed':0,'passed':0}

    # This function will loop until the cont variable is changed to false (by the debug panel)
    @staticmethod
    def WaitEnd():
        while (Common.cont == True):
            time.sleep(Common.DEFAULT_WAIT)

    ## Wait for user input.
    # Blocks until receiving a user input (click of "continue"-button in GUI).
    # @todo Implement timeout in addition.
    @staticmethod
    def WaitForInput():
        Common.LogWrite("Waiting for user input")
        Common.cont = True
        while (Common.cont == True and Dut.doRead == True):
            time.sleep(Common.DEFAULT_WAIT)
        if Dut.doRead == False:
            raise Exception("Script Stop Requested in WaitForInput!!!")
        else:
            Common.LogWrite("Got user input")

    ## Receives exception messages from debug panel and writes them to log
    @staticmethod
    def ExceptionCallback(source, message):
        msg =  "Exception in %s: %s" % (source, message)
        Common.LogWrite(msg)

    ## Search the packet queue for specific packets.
    # @param args Arbitrary number of byte codes to specify which packets to search for
    def PacketQueueSearch(self, *args):
        return pktQueue.PacketQueueSearch(*args)

    ## Search the queue for specified packets and return with found packets. If wanted packets are not found in queue, the function waits for a specified timeout before returning.
    # @param packets Arbitrary number of packet ids to specify which packets to search for
    # @param timeout Key-Value pair for setting of timeout value.
    def WaitFor(self, *packets, **timeout):                 #Take arbitrary number of search arguments and keys
        return self.pktQueue.WaitFor(*packets, **timeout)

    #This function is deprecated. It is kept for backwards compatibility
    def WaitForEvent(self, event1, secondsTimeout):
        retval = self.WaitForEvents(event1, None, None, secondsTimeout)
        return retval

    #This function is deprecated. It is kept for backwards compatibility
    def WaitForEvents(self, event1, event2, event3, secondstimeout):
        retval = self.WaitFor(event1, event2, event3, TIMEOUT = secondstimeout)
        return retval

    ## Adds a random part of the input strin
    # @param input Text string to add random chars to
    # @param count The number of random chars to add
    @staticmethod
    def AddRandomString(input, count):
        alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        output = input
        for x in random.sample(alphabet,random.randint(count,count)):
            output += x
        return output

## @class Tester
# Class for tester functionality. The Tester class is currently implemented for spi communication over the ftdi signalyzer.
class Tester(Common):
    ## Constructor for class Tester
    # @param caller Instance of the class in Debug Panel calling this script.
    def __init__(self, caller):
        Common.__init__(self, caller)
        Common.Role = "TST"
        FtdiComm.deviceId = self.caller.scriptParams.ftdiDeviceId
        HciDriver.deviceId = self.caller.scriptParams.ftdiDeviceId
        self.packetRecipients = []
        self.AddPacketRecipients(self.AddToQueue)
        self.isDriverH4 = False

    def AddPacketRecipients(self, recipient):
        if recipient not in self.packetRecipients:
            self.packetRecipients.append(recipient)

    def RemovePacketRecipient(self, recipient):
        if recipient in self.packetRecipients:
            self.packetRecipients.remove(recipient)

    def NotifyPacketRecipients(self, packet):
        for recipient in self.packetRecipients:
            try:
                recipient(packet)
            except:
                pass

    def ExceptionHandler(self, exception):
        Common.ExceptionCallback(exception.Source, exception.Message)

    def PacketEventHandler(self, *args):
        packet = args[2]
        isEventPacket = (args[3] != None)
        isDataPacket = (args[4] != None)

        if isDataPacket:
            #Don't parse data packets, they will be handled in the data event handler
            return

        #Workaround, datapackets from h4 driver have 1 byte less than spi driver
        if self.isDriverH4:
            packet  = System.Array[System.Byte]([Common.EVENT_PACKET_ID,]) + packet

        parsedPacket = self.ParsePacket(packet)
        if parsedPacket != None:
            self.NotifyPacketRecipients(parsedPacket)

    def PacketDataHandler(self, *args):
        packet = args[0]
        if self.isDriverH4:
            packet  = System.Array[System.Byte]([Common.DATA_PACKET_ID,]) + packet
        parsedPacket = self.ParsePacket(packet)
        if parsedPacket != None:
            self.NotifyPacketRecipients(parsedPacket)

    def ParsePacket(self, packet):
        obj = None
        if (packet != None):
            obj = None
            if packet[0] == Common.DATA_PACKET_ID:
                pkt = packet[1:]                            #Copy everything but the first byte
                obj = DataPkt.GenerateDataPacketObject(pkt)
            elif packet[0] == Common.EVENT_PACKET_ID:
                pkt = packet[1:]                            #Strip the first byte of the packet (proprietary id byte)
                obj = HciEvent.GenerateHciEventObject(pkt)    #Convert the data array to an event object
            elif packet[0] in [Common.VENDOR_PACKET_ID, Common.COMMAND_PACKET_ID]:
                #These packet types does not need to be placed in the queue
                pass
            else:
                Common.LogWrite("Packet category was not recognized: 0x%02X" % packet[0])

        return obj # Return the parsed object, or None if not recognized

    def AddToQueue(self, obj):
        #self.LogWrite("ADD TO QUEUE: %r" % obj)
        self.pktQueue.AddToQueue(obj)

## @class FtdiComm
# Class for the ftdi/signalyzer driver for spi communication.
class FtdiComm:
    deviceId = ""

    ## Constructor for class FtdiComm
    # @param driver Instance of debug panel ftdi class. Normally the instance made globally available from the debug panel application.
    def __init__(self, driver):
        if FtdiComm.deviceId == None or FtdiComm.deviceId == "":
            Common.LogWrite("No ftdi device specified")
        self.driver = driver

    ## Connects to the signalyzer with given id.
    def Connect(self):
        device = FtdiComm.deviceId + "A"                #Make the deviceId complete by padding an A to it
        Common.LogWrite("Device nr: %s" % device)
        self.driver.Open(device);                       #Open the FTDI device

    ## Toggles the signalyzer pin connected to the reset pin on the FPGA connector.
    def Reset(self):
        self.driver.Reset()                             #Issue reset func which will toggle the reset pin on the hardware
        time.sleep(Common.DEFAULT_WAIT)

    ## Closes the connection to the signalyzer.
    def Disconnect(self):
        self.driver.Close()                             #Close the FTDI device
        time.sleep(Common.DEFAULT_WAIT);

    #Writes a command packet
    def WriteCmd(self, cmd):
        try:
            self.driver.WriteCmd(cmd)                       #Calling the .NET implemented WriteCmd()
        except Exception, ex:
            Common.LogWrite("WriteCmd failed: %s" % str(ex))

## @class HciDriver
# Generic class for HciDriver for establishing communication from software to device
class HciDriver:
    deviceId = ""

    ## Constructor for class FtdiComm
    # @param driver Instance of ftdi driver class.
    def __init__(self, driver):
        if HciDriver.deviceId == None or HciDriver.deviceId == "":
            Common.LogWrite("No device specified")
        self.driver = driver

    ## Connects to the signalyzer with given id.
    def Connect(self, deviceInfo = "FTDI"):
        if deviceInfo == "FTDI":
            HciDriver.deviceId += "A"
        Common.LogWrite("Device: %s" % HciDriver.deviceId)
        self.driver.Open(HciDriver.deviceId);                       #Open the device

    ## Reset the hardware device
    def Reset(self):
        self.driver.Reset()                             #Issue reset func for resetting hardware
        time.sleep(Common.DEFAULT_WAIT)

    ## Closes the connection to the device
    def Disconnect(self):
        self.driver.Close()                             #Close the connection to the device
        time.sleep(Common.DEFAULT_WAIT);

    #Writes a commdan packet
    def WriteCmd(self, cmd):
        self.driver.WriteCmd(cmd)                       #Calling the .NET implemented WriteCmd()

## @class SerialComm
# Class for communication over serial port. Follows the protocol for host test commands as
# specified in http://svn.nordicsemi.no/repos/wibree_host/trunk/doc/formal/Host Test-Log interface.doc
class SerialComm:
    #Define protocol types for uart packets
    HCI_COMMAND         = 0x01
    HCI_DATA            = 0x03
    L2CAP_COMMAND       = 0x05
    L2CAP_DATA          = 0x07
    ATT_COMMAND         = 0x09
    ATT_NOTIFY          = 0x0A
    IHM_IN_COMMAND      = 0x0B
    SMP_REQUEST         = 0x0D
    NRF8200_IN_COMMAND  = 0x0F

    LOG_DATA            = 0x02
    HCI_EVENT           = 0x04
    L2CAP_RESPONSE      = 0x06
    ATT_RESPONSE        = 0x08
    IHM_OUT_RESPONSE    = 0x0C
    SMP_RESPONSE        = 0x0E
    NRF8200_OUT_RESPONSE= 0x10
    TEST_COMMAND        = 0x11
    TEST_RESPONSE       = 0x12
    ASSERT_MESSAGE      = 0x13
    CUNIT_DATA          = 0x14

class SerialCommTypeMapping:
    #Mapping is needed for Data from TestIF to Script
    HCI_DATA_EVENTCODE   = 0x99
    IHM_OUT_EVENTCODE    = 0x98
    L2CAP_DATA_EVENTCODE = 0x97
    ATT_RESPONSE_EVENTCODE = 0x96
    ATT_COMMAND_EVENTCODE = 0x95
    ATT_NOTIFY_EVENTCODE = 0x94
    SMP_RESPONSE_EVENTCODE = 0x93
    NRF8200_OUT_EVENTCODE = 0x92
    ASSERT_MESSAGE_EVENTCODE = 0x91
    SMP_REQUEST_EVENTCODE = 0x90
    L2CAP_COMMAND_EVENTCODE = 0x8F

    TypeToEventCode = {SerialComm.HCI_DATA: HCI_DATA_EVENTCODE,
                           SerialComm.IHM_OUT_RESPONSE: IHM_OUT_EVENTCODE,
                           SerialComm.NRF8200_OUT_RESPONSE: NRF8200_OUT_EVENTCODE,
                           SerialComm.ASSERT_MESSAGE: ASSERT_MESSAGE_EVENTCODE,
                           SerialComm.L2CAP_DATA: L2CAP_DATA_EVENTCODE,
                           SerialComm.ATT_RESPONSE: ATT_RESPONSE_EVENTCODE,
                           SerialComm.ATT_COMMAND: ATT_COMMAND_EVENTCODE,
                           SerialComm.ATT_NOTIFY: ATT_NOTIFY_EVENTCODE,
                           SerialComm.SMP_RESPONSE: SMP_RESPONSE_EVENTCODE,
                           SerialComm.SMP_REQUEST: SMP_REQUEST_EVENTCODE,
                           SerialComm.L2CAP_COMMAND: L2CAP_COMMAND_EVENTCODE}

## @class HciComm
# This class contains functions which will build and send HCI commands.
if 'System' in locals():
    class HciComm:
        DEPRECATED = 0xEE;

        FALSE = System.Boolean.Parse("False")
        TRUE = System.Boolean.Parse("True")

        EVENT_CODE = 0xFD   #According to spec, all BTLE events shall have this event code.

        #Hci event codes
        HCI_ADVERTISING_PACKET_REPORT_EVENT                 = int(hci_coder.btle_event_code_t.BTLE_EVENT_LE_ADVERTISING_REPORT)
        HCI_LL_CONNECTION_CREATED_EVENT                     = int(hci_coder.btle_event_code_t.BTLE_EVENT_LE_CONNECTION_COMPLETE)
        HCI_LL_CONNECTION_TERMINATION_EVENT                 = int(hci_coder.btle_event_code_t.BTLE_EVENT_DISCONNECTION_COMPLETE)
        HCI_LL_CONNECTION_PAR_UPDATE_COMPLETE_EVENT         = int(hci_coder.btle_event_code_t.BTLE_EVENT_LE_CONNECTION_UPDATE_COMPLETE)
        HCI_NUM_COMPLETED_PACKETS_EVENT                     = int(hci_coder.btle_event_code_t.BTLE_EVENT_NUMBER_OF_COMPLETED_PACKETS)
        HCI_COMMAND_COMPLETE_EVENT                          = int(hci_coder.btle_event_code_t.BTLE_EVENT_COMMAND_COMPLETE)
        HCI_COMMAND_STATUS_EVENT                            = int(hci_coder.btle_event_code_t.BTLE_EVENT_COMMAND_STATUS)
        HCI_ERROR_EVENT                                     = int(hci_coder.btle_event_code_t.BTLE_EVENT_HARDWARE_ERROR)

        HCI_DATA_BUFFER_OVERFLOW_EVENT                      = int(hci_coder.btle_event_code_t.BTLE_EVENT_DATA_BUFFER_OVERFLOW)
        HCI_ENCRYPTION_CHANGE_EVENT                         = int(hci_coder.btle_event_code_t.BTLE_EVENT_ENCRYPTION_CHANGE)
        HCI_ENCRYPTION_KEY_REFRESH_COMPLETE_EVENT           = int(hci_coder.btle_event_code_t.BTLE_EVENT_ENCRYPTION_KEY_REFRESH_COMPLETE)
        HCI_FLUSH_OCCURRED_EVENT                            = int(hci_coder.btle_event_code_t.BTLE_EVENT_FLUSH_OCCURRED)
        HCI_LONG_TERM_KEY_REQUESTED_EVENT                   = int(hci_coder.btle_event_code_t.BTLE_EVENT_LE_LONG_TERM_KEY_REQUESTED)
        HCI_READ_REMOTE_USED_FEATURES_COMPLETE_EVENT        = int(hci_coder.btle_event_code_t.BTLE_EVENT_LE_READ_REMOTE_USED_FEATURES_COMPLETE)
        HCI_READ_REMOTE_VERSION_INFORMATION_COMPLETE_EVENT  = int(hci_coder.btle_event_code_t.BTLE_EVENT_READ_REMOTE_VERSION_INFORMATION_COMPLETE)

        HCI_NONE_EVENT                                      = int(hci_coder.btle_event_code_t.BTLE_EVENT_NONE)

        #Hci Command Codes
        BTLE_CMD_LE_READ_BUFFER_SIZE                = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_LE_READ_BUFFER_SIZE)
        BTLE_CMD_LE_HCI_RAND                        = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_LE_RAND)
        BTLE_CMD_LE_HCI_ENCRYPT                     = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_LE_ENCRYPT)
        BTLE_CMD_LE_READ_BD_ADDR                    = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_READ_BD_ADDR)
        BTLE_CMD_LE_SET_SCAN_PARAMETERS             = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_LE_SET_SCAN_PARAMETERS)
        BTLE_CMD_LE_WRITE_SCAN_PARAMETERS           = BTLE_CMD_LE_SET_SCAN_PARAMETERS
        BTLE_CMD_LE_SET_SCAN_ENNABLE                = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_LE_SET_SCAN_ENABLE)
        BTLE_CMD_LE_WRITE_SCAN_ENNABLE              = BTLE_CMD_LE_SET_SCAN_ENNABLE
        BTLE_CMD_READ_LOCAL_VERSION_INFORMATION     = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_READ_LOCAL_VERSION_INFORMATION)
        BTLE_CMD_LE_CONNECTION_UPDATE               = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_LE_CONNECTION_UPDATE)
        BTLE_CMD_LE_SET_HOST_CHANNEL_CLASSIFICATION = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_LE_SET_HOST_CHANNEL_CLASSIFICATION)
        BTLE_CMD_READ_RSSI                          = int(hci_coder.btle_cmd_opcode_t.BTLE_CMD_READ_RSSI)
        NRF_CMD_GET_VERSION_INFO                    = int(hci_coder.btle_cmd_opcode_t.NRF_CMD_GET_VERSION_INFO)
        NRF_CMD_SET_BD_ADDR                         = int(hci_coder.btle_cmd_opcode_t.NRF_CMD_SET_BD_ADDR)

        #Default filter policies
        HCI_FILTER_POLICY_ALL_UNKNOWN_BLACKLISTED   = int(hci_coder.btle_adv_filter_policy_t.BTLE_ADV_FILTER_ALLOW_WHITELISTED)
        HCI_FILTER_POLICY_ALLOW_SCANNING            = int(hci_coder.btle_adv_filter_policy_t.BTLE_ADV_FILTER_ALLOW_LEVEL1)
        HCI_FILTER_POLICY_ALLOW_CONNECTIONS         = int(hci_coder.btle_adv_filter_policy_t.BTLE_ADV_FILTER_ALLOW_LEVEL2)
        HCI_FILTER_POLICY_ALL_WHITELISTED           = int(hci_coder.btle_adv_filter_policy_t.BTLE_ADV_FILTER_ALLOW_ANY)

        HCI_LE_REMOTE_CLOSED_CONNECTION             = 0x13
        HCI_LE_LOCAL_CLOSED_CONNECTION              = 0x16
        HCI_LE_REMOTE_CLSED_CONNECTION_BAD_TIMING   = 0x3B

        #Address types
        BTLE_ADDR_TYPE_PUBLIC                       = int(hci_coder.btle_address_type_t.BTLE_ADDR_TYPE_PUBLIC)
        BTLE_ADDR_TYPE_RANDOM                       = int(hci_coder.btle_address_type_t.BTLE_ADDR_TYPE_RANDOM)

        INITIAL_NUM_COMPLETE = 0
        AVAILABLE_NUM_COMPLETE = 0
        numCompleteLock = threading.Lock()

        ConnInterval = 0x0050 #Note: The connection interval is NOT scaled for a connect, but is scaled by 1.25 for the params update
        ConnLatency  = 0x0000
        ConnTimeout  = 300    #Note: The latency is NOT scaled for a connect, but is scaled by 10 for the params update

        def __init__(self, hci, driver):
            self.hci = hci
            self.driver = driver

        def ReadBufferSize(self):
            cmd = self.hci.HciBuildHciReadBufferSize()
            self.driver.WriteCmd(cmd.GetPacket())                       #GetPacket() returns a byte array of the packet contents. The method is accessible through the Ulpbt library since the cmd packet is of type HciCmdPacket
            return ("read_buffer_size complete")

        @staticmethod
        def InitNumComplete(ammount):
            HciComm.numCompleteLock.acquire()
            HciComm.INITIAL_NUM_COMPLETE = ammount
            HciComm.AVAILABLE_NUM_COMPLETE = HciComm.INITIAL_NUM_COMPLETE
            HciComm.numCompleteLock.release()

        @staticmethod
        def UpdateNumComplete(ammount):
            HciComm.numCompleteLock.acquire()
            HciComm.AVAILABLE_NUM_COMPLETE += ammount
            HciComm.numCompleteLock.release()

        @staticmethod
        def GetInitialNumComplete():
            return HciComm.INITIAL_NUM_COMPLETE

        @staticmethod
        def GetAvailableNumComplete():
            return HciComm.AVAILABLE_NUM_COMPLETE

        def Reset(self):
            cmd = self.hci.HciBuildHciReset()
            self.driver.WriteCmd(cmd.GetPacket())
            return ("reset complete")

        def SetEventMask(self, eventMask):
            eMask = System.UInt64.Parse(str(eventMask))
            cmd = self.hci.HciBuildHciSetEventMask(eMask)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("set_event_mask complete")

        def SetAdvertiseParameters(self, interval, eventType, addressTypeOwn, directedAddress, addressTypeDirectedAddress, channelMap, filterPolicy):
            interv = System.UInt32.Parse(str(interval))
            evType = System.Byte.Parse(str(eventType))
            adTypeOwn = System.Byte.Parse(str(addressTypeOwn))
            dirAddress = Ulpbt.WbDeviceAddress.CreateAddress(str(directedAddress))
            adTypeDirAddress = System.Byte.Parse(str(addressTypeDirectedAddress))
            chMap = System.Byte.Parse(str(channelMap))
            fltrPlcy = System.Byte.Parse(str(filterPolicy))

            cmd = self.hci.HciBuildHciSetAdvertiseParameters(interv, evType, adTypeOwn, dirAddress, adTypeDirAddress, chMap, fltrPlcy)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("set_adv_params complete")

        def SetPrivateDeviceAddress(self, privateAddress):
            wbDeviceAddress = Ulpbt.WbDeviceAddress.CreateAddress(str(privateAddress))
            self.PrivateAddress = wbDeviceAddress
            cmd = self.hci.HciBuildHciSetPrivateDeviceAddress(wbDeviceAddress)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("set_private_device_address complete")

        def ReadPrivateDeviceAddress(self):
            if 'PrivateAddress' in self.__dict__:
                return self.PrivateAddress

        def ReadPublicDeviceAddress(self):
            cmd = self.hci.HciBuildHciReadPublicDeviceAddress()
            self.driver.WriteCmd(cmd.GetPacket())
            return ("read_public_device_address complete")

        def ClearDeviceWhiteList(self):
            cmd = self.hci.HciBuildHciClearDeviceWhiteList()
            self.driver.WriteCmd(cmd.GetPacket())
            return ("clear_device_white_list complete")

        def AddDeviceWhiteList(self, address, addressType):
            address = Ulpbt.WbDeviceAddress.CreateAddress(address)
            addressType = System.Byte.Parse(str(addressType))
            cmd = self.hci.HciBuildHciAddDeviceWhiteList(address, addressType)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("add_device_to_white_list complete")

        def WriteAdvData(self, advPacketData):
            cmd = self.hci.HciBuildHciWriteAdvData(advPacketData)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("write_adv_data complete")

        def WriteScanResponseData(self, scanResponseData):
            cmd = self.hci.HciBuildHciWriteScanResponseData(scanResponseData)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("write_scan_response_data complete")

        def WriteAdvertiseMode(self, advMode):
            if (advMode == 1):
                aMode = HciComm.TRUE
            elif (advMode == 0):
                aMode = HciComm.FALSE

            cmd = self.hci.HciBuildHciWriteAdvertiseMode(aMode)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("write_adv_mode complete")

        def SetScanParameters(self, active, addressType, scanInterval, scanWindow, filterPolicy):
            if (active == 0):
                isActive = HciComm.FALSE
            elif (active == 1):
                isActive = HciComm.TRUE

            addrType = System.Byte(addressType)
            scanInterv = System.Double(scanInterval)
            scanWin = System.Double(scanWindow)
            filterPlcy = System.Byte(filterPolicy)
            cmd = self.hci.HciBuildHciSetScanParameters(isActive, addrType, scanInterv, scanWin, filterPlcy)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("set_scan_parameters complete")

        def WriteScanMode(self, scanMode):
            if (scanMode == 1):
                scanM = HciComm.TRUE
            elif (scanMode == 0):
                scanM = HciComm.FALSE

            cmd = self.hci.HciBuildHciWriteScanMode(scanM)
            self.driver.WriteCmd(cmd.GetPacket())
            msg = "write_scan_mode (%d) complete" %scanMode
            return (msg)

        def CreateLLConnection(self, scanInterval, scanWindow, whiteList, addressTypePeer,
        peerAddress, addressTypeOwn, connIntervalMin, connIntervalMax, connLatency, connTimeout,
        encrypted, minLength, maxLength):
            scanInterval = System.UInt16.Parse(str(scanInterval))
            scanWindow = System.UInt16.Parse(str(scanWindow))
            whiteList = System.Byte.Parse(str(whiteList))
            addressTypePeer = System.Byte.Parse(str(addressTypePeer))
            peerAddress = Ulpbt.WbDeviceAddress.CreateAddress(str(peerAddress))
            addressTypeOwn = System.Byte.Parse(str(addressTypeOwn))
            connIntervalMin = System.UInt16.Parse(str(connIntervalMin))
            connIntervalMax = System.UInt16.Parse(str(connIntervalMax))
            connLatency = System.UInt16.Parse(str(connLatency))
            connTimeout = System.UInt16.Parse(str(connTimeout))
            encrypted = System.Byte.Parse(str(encrypted))
            minLength = System.UInt16.Parse(str(minLength))
            maxLength = System.UInt16.Parse(str(maxLength))

            cmd = self.hci.HciBuildHciCreateLLConnection(scanInterval, scanWindow, whiteList, addressTypePeer, peerAddress,
            addressTypeOwn, connIntervalMin, connIntervalMax, connLatency, connTimeout, encrypted, minLength, maxLength)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("create_ll_connection complete")

        def StopLLConnectionCreation(self):
            cmd = self.hci.HciBuildHciStopLLConnectionCreation()
            self.driver.WriteCmd(cmd.GetPacket())
            return ("stop_ll_connection_creation complete")

        def TerminateLLConnection(self, connectionId):
            connId = System.UInt16.Parse(str(connectionId))
            cmd = self.hci.HciBuildHciTerminateLLConnection(connId)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("terminate_ll_connection complete")

        def UpdateLLConnectionParameters(self, connectionId, connInterval, connLatency, connTimeout, minLength = 0x0001, maxLength = 0x0001):
            connectionId = System.UInt16.Parse(str(connectionId))

            cmd = self.hci.HciBuildHciUpdateLLConnectionParameters(connectionId, connInterval, connLatency, connTimeout, minLength, maxLength)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("update_ll_connection_parameters complete")

        def SetHostChannelClassification(self, channelMap):
            tmp_chm = channelMap
            channelMapLength = 5
            channelMap = [None]*channelMapLength
            for i in range(channelMapLength):               #Loop over all 5 bytes
                temp = tmp_chm >> (8 * (4 - i)) & 0xFF      #Shift down and extract least significant byte
                channelMap[i] = int(temp)                   #Insert byte into channelMap array
            channelMap = System.Array[System.Byte](channelMap)

            cmd = self.hci.HciBuildSetHostChannelClassification(channelMap)
            self.driver.WriteCmd(cmd.GetPacket())
            return ("update_channel_map is complete")

        def Rand(self):
            cmd = self.hci.HciBuildRand()
            self.driver.WriteCmd(cmd.GetPacket())
            return "rand is complete"

        def Encrypt(self, key, data):
            key = System.Array[System.Byte](key)
            data = System.Array[System.Byte](data)

            cmd = self.hci.HciBuildEncrypt(key,data)
            self.driver.WriteCmd(cmd.GetPacket())
            return "encrypt is complete"

        def Flush(self, connectionId):
            connectionId = System.UInt16.Parse(str(connectionId))
            cmd = self.hci.HciBuildFlush(connectionId)
            self.driver.WriteCmd(cmd.GetPacket())
            return "flush is complete"

        def ReadRemoteVersionInformation(self, connectionId):
            connectionId = System.UInt16.Parse(str(connectionId))
            cmd = self.hci.HciBuildReadRemoteVersionInformation(connectionId)
            self.driver.WriteCmd(cmd.GetPacket())
            return "read_remote_version_info is complete"

        def HciReadLocalVersionInformation(self):
            cmd = self.hci.HciBuildReadLocalVersionInformation()
            self.driver.WriteCmd(cmd.GetPacket())
            return "read_local_version_information is complete"

        def StartEncryption(self, connHandle, rand, eDiv, longTermKey):
            connHandle = System.UInt16.Parse(str(connHandle))
            rand = System.Array[System.Byte](rand)
            eDiv = System.UInt16.Parse(str(eDiv))
            longTermKey = System.Array[System.Byte](longTermKey)

            cmd = self.hci.HciBuildStartEncryption(connHandle, rand, eDiv, longTermKey)
            self.driver.WriteCmd(cmd.GetPacket())
            return "start_encryption is complete"

        def LongTermKeyRequestedReply(self, connHandle, longTermKey):
            connHandle = System.UInt16.Parse(str(connHandle))
            longTermKey = System.Array[System.Byte](longTermKey)

            cmd = self.hci.HciBuildLongTermKeyRequestedReply(connHandle, longTermKey)
            self.driver.WriteCmd(cmd.GetPacket())
            return "LongTermKeyRequestedReply is complete"

        def LongTermKeyRequestedNegativeReply(self, connHandle):
            connHandle = System.UInt16.Parse(str(connHandle))

            cmd = self.hci.HciBuildLongTermKeyRequestedNegativeReply(connHandle)
            self.driver.WriteCmd(cmd.GetPacket())
            return "LongTermKeyRequestedNegativeReply is complete"

        def ReadRssi(self, connHandle):
            connHandle = System.UInt16.Parse(str(connHandle))
            cmd = self.hci.HciBuildReadRssi(connHandle)
            self.driver.WriteCmd(cmd.GetPacket())
            return "ReadRssi is complete"

        #################
        # Vendor specific commands
        #################

        def NrfSetTransmitPowerLevel(self, powerLevel):
            powerLevel = System.Byte.Parse(powerLevel & 0xFF)
            cmd = self.hci.NrfBuildSetTransmitPowerLevel(powerLevel)
            self.driver.WriteCmd(cmd.GetPacket())
            return "set_transmit_power_level is complete"

        def NrfSetClockParameters(self, sleepClockAccuracy):
            sleepClockAccuracyByte = System.Byte.Parse(str(sleepClockAccuracy))
            cmd = self.hci.NrfBuildNrfSetClockParameters(sleepClockAccuracyByte)
            self.driver.WriteCmd(cmd.GetPacket())
            return "nrf_set_clock_parameters is complete"

        def NrfSetBDAddr(self, deviceAddress):
            self.deviceAddress = int(deviceAddress,16)
            deviceAddressByteArray = Ulpbt.WbDeviceAddress.CreateAddressBigEnd(str(deviceAddress))
            cmd = self.hci.NrfBuildSetBDAddr(deviceAddressByteArray)
            self.driver.WriteCmd(cmd.GetPacket())
            return "nrf_set_bd_addr is complete"

        def NrfGetVersionInfo(self):
            cmd = self.hci.NrfBuildGetVersionInfo()
            seld.driver.WriteCmd(cmd.GetPacket())
            return cmd

## Class DataComm
# This class is for sending of data packets over hci
# @param bc Object normally made globally available for the script from the Debug Panel application. BC gives access to sending of connection oriented data packets.
if 'System' in locals():
    class DataComm:

        accessLock = threading.Lock()

        def __init__(self, bc):
            self.bc = bc

        def SendDataPacket(self, connId, data, pbFlag=0, bcFlag=0):
            cId = System.UInt16.Parse(str(connId))
            pbFlag = System.Byte.Parse(str(pbFlag))
            bcFlag = System.Byte.Parse(str(bcFlag))
            if (data is None):
                return

            length = len(data)
            dataPacket = System.Array[System.Byte](data)

            with DataComm.accessLock:
                dataPkt = Ulpbt.HciDataPacket.InstantiateWithData(cId, pbFlag, bcFlag, dataPacket)
                self.bc.SendDataPacket(dataPkt)
                HciComm.UpdateNumComplete(-1)

class Uuid:
    assignedNumbers = {
          'GAP'                     :0x1800
        , 'DEVICE_NAME'             :0x2A00
        , 'APPEARANCE'              :0x2A01
        , 'PRIVACY_FLAG'            :0x2A02
        , 'RECONN_ADDR'             :0x2A03
        , 'CONNECTION_PARAMETERS'   :0x2A04
        , 'GATT'                    :0x1801
        , 'SERVICE_CHANGED'         :0x2A05
        , 'PRIMARY_SERVICE'         :0x2800
        , 'SECONDARY_SERVICE'       :0x2801
        , 'INCLUDE'                 :0x2802
        , 'CHARACTERISTIC'          :0x2803
        , 'CHARACTERISTIC_EXT_PROP' :0x2900
        , 'CHARACTERISTIC_USER_DESC':0x2901
        , 'CHARACTERISTIC_CLT_CFG'  :0x2902
        , 'CHARACTERISTIC_SVR_CFG'  :0x2903
        , 'CHARACTERISTIC_FORMAT'   :0x2904
        , 'CHARACTERISTIC_AGG_FMT'  :0x2905
        , 'TX_POWER'                :0x1804
        , 'IMMEDIATE_ALERT'         :0x1802
        , 'ALERT_LEVEL'             :0x2A06
    }

    groupingUuids = [
        assignedNumbers['PRIMARY_SERVICE'],
        assignedNumbers['SECONDARY_SERVICE'],
    ]

class DataPkt:
    def __init__(self):
        self.isEvent = False
        self.isDataPacket = True
        self.EventCode = SerialCommTypeMapping.TypeToEventCode[SerialComm.HCI_DATA]

    def __repr__(self):
        return "<DataPacket: id=0x%02X>" % self.EventCode

    @staticmethod
    def GenerateDataPacketObject(packet):
        retval = None
        if packet[0] != None:
            gdp = GeneralDataPacket(packet)
            if gdp.ParsedPacket != None:
                retval = gdp.ParsedPacket
            else:
                retval = gdp
        return retval

class GeneralDataPacket(DataPkt):
    def __init__(self, packet):
        DataPkt.__init__(self)
        self.Content = []
        self.ConnectionId = 0
        self.Len = 0
        self.ParsedPacket = None
        for value in packet:
            self.Content.append(int(value))
        if len(packet) >= 4:
            self.ConnectionId = ((packet[1] << 8) + packet[0]) & 0x0FFF
            self.Len = (packet[3] << 8) + packet[2]
            self.ParsedPacket = protocol.L2Cap.L2CapPkt(packet=packet[4:])
            if self.ParsedPacket != None:
                self.ParsedPacket.HciData = self

class L2CapComm:
    def __init__(self, bc):
        self.driver = DataComm(bc)
        self.connID = 0

    def setConnID(self,connID):
        self.connID = connID

    def Write(self, packet, silent=True):
        packet = L2CapCommands.createL2CapPkt(packet,0x0005)
        self.driver.SendDataPacket(self.connID, packet)

class L2CapCommands:
    Codes = {
        0x01:{'name':'COMMAND_REJECT'},
        0x0A:{'name':'INFORMATION_REQUEST'},
        0x12:{'name':'CONNECTION_PARAM_UPDATE_REQUEST'},
        0x13:{'name':'CONNECTION_PARAM_UPDATE_RESPONSE'}
    }
    Codes_Lookup = dict([value['name'],key] for key,value in Codes.iteritems())

    def __init__(self, driver):
        self.driver = driver

    @staticmethod
    def createL2CapPkt(packet,path):
        size = len(packet)
        return [size & 0xFF, (size >> 8) & 0xFF, path & 0xFF, (path >> 8) & 0xFF] + [int(el) for el in packet]

    def SendInformationRequest(self, identifier, info_type):
        packet = protocol.L2CapSignPkt.L2CapInformationRequest(Identifier = identifier, InfoType = info_type)
        self.driver.Write(packet)
        return packet

    def SendConnectionParameterUpdateRequest(self, identifier, interval_min, interval_max, slave_lat, to_mult):
        packet = protocol.L2CapSignPkt.L2CapConnectionParameterUpdateRequest(Identifier = identifier,
            IntervalMin = interval_min,
            IntervalMax = interval_max,
            SlaveLatency= slave_lat,
            TimeoutMultiplier = to_mult)
        self.driver.Write(packet)
        return packet

    def SendConnectionParameterUpdateResponse(self, identifier, result):
        packet = protocol.L2CapSignPkt.L2CapConnectionParameterUpdateResponse(Identifier = identifier, Result = result)
        self.driver.Write(packet)
        return packet

    def SendCommandReject(self, identifier, result):
        packet = protocol.L2CapSignPkt.L2CapCommandReject(Identifier = identifier, Reason = result)
        self.driver.Write(packet)
        return packet

class AttComm:
    def __init__(self, bc):
        self.driver = DataComm(bc)
        self.connID = 0

    def setConnID(self,connID):
        self.connID = connID

    ## Send ATT Packet
    # @param packet The packet to be sent
    def Write(self, packet, silent=True):
        packet = L2CapCommands.createL2CapPkt(packet,0x0004)
        #if not silent:
        #    Common.LogWrite("Sending packet: %s" % Common.GetHexString(packet))
        packet = [int(el) for el in packet]
        self.driver.SendDataPacket(self.connID, packet)

class AttCommands:
    ## Client initiated opcodes
    ERROR_RESPONSE              = 0x01
    EXCHANGE_MTU_REQUEST        = 0x02
    EXCHANGE_MTU_RESPONSE       = 0x03
    FIND_INFORMATION_REQUEST    = 0x04
    FIND_INFORMATION_RESPONSE   = 0x05
    ## New Command Opcodes
    FIND_BY_TYPE_VALUE_REQUEST  = 0x06
    FIND_BY_TYPE_VALUE_RESPONSE = 0x07
    READ_BY_TYPE_REQUEST        = 0x08
    READ_BY_TYPE_RESPONSE       = 0x09
    READ_REQUEST                = 0x0A
    READ_RESPONSE               = 0x0B
    READ_BLOB_REQUEST           = 0x0C
    READ_BLOB_RESPONSE          = 0x0D
    READ_MULTIPLE_REQUEST       = 0x0E
    READ_MULTIPLE_RESPONSE      = 0x0F
    READ_BY_GROUP_TYPE_REQUEST  = 0x10
    READ_BY_GROUP_TYPE_RESPONSE = 0x11
    WRITE_REQUEST               = 0x12
    WRITE_RESPONSE              = 0x13
    WRITE_COMMAND               = 0x52
    PREPARE_WRITE_REQUEST       = 0x16
    PREPARE_WRITE_RESPONSE      = 0x17
    EXECUTE_WRITE_REQUEST       = 0x18
    EXECUTE_WRITE_RESPONSE      = 0x19
    ## Server initiated opcodes
    HANDLE_VALUE_NOTIFICATION   = 0x1B
    HANDLE_VALUE_INDICATION     = 0x1D
    HANDLE_VALUE_CONFIRMATION   = 0x1E
    SIGNED_WRITE_COMMAND        = 0xD2

    ## ERROR_RESPONSE codes
    INVALID_HANDLE              = 0x01
    READ_NOT_PERMITTED          = 0x02
    WRITE_NOT_PERMITTED         = 0x03
    INVALID_PDU                 = 0x04
    INSUFFICIENT_AUTHENTICATION = 0x05
    REQUEST_NOT_SUPPORTED       = 0x06
    INVALID_OFFSET              = 0x07
    INSUFFICIENT_AUTHORIZATION  = 0x08
    PREPARE_QUEUE_FULL          = 0x09
    ATTRIBUTE_NOT_FOUND         = 0x0A
    ATTRIBUTE_NOT_LONG          = 0x0B
    INSUFFICIENT_ENC_KEY_SIZE   = 0x0C
    INVALID_ATTRIBUTE_VALUE_LEN = 0x0D
    UNSUPPORTED_GROUP_TYPE      = 0x10
    APPLICATION_ERROR_STRT      = 0x80
    APPLICATION_ERROR_END       = 0xFF

    TYPE_16     = 0x01
    TYPE_128    = 0x02
    TYPE_HANDLE = 0x03

    BT_BASE_UUID = 0x0000000000001000800000805F9B34FB
    ATT_MTU = 23

    ## Bitmaping of attribute support
    BM_EXCHANGE_MTU_REQUEST         = 0x00000001
    BM_READ_INFORMATION_REQUEST     = 0x00000002
    BM_READ_BY_TYPE_REQUEST         = 0x00000004
    BM_READ_REQUEST                 = 0x00000008
    BM_READ_BLOB_REQUEST            = 0X00000010
    BM_WRITE_COMMAND                = 0x00000020
    BM_WRITE_REQUEST                = 0x00000040
    BM_PREPARE_WRITE_REQUEST        = 0x00000100
    BM_EXECUTE_WRITE_REQUEST        = 0x00000200
    BM_HANDLE_VALUE_CONFIRMATION    = 0x00000400
    BM_SIGNED_WRITE_COMMAND         = 0x00000800
    BM_SIGNED_WRITE_REQUEST         = 0x00001000

    def __init__(self, driver):
        self.driver = driver
        self.connID = 0x0000

    def setConnId(self,id):
        self.connID = id

    def SendAttPacket(self, packet):
        size = len(packet)
        # create packet[size, channel, data]
        # packet = L2CapCommands.createL2CapPkt(packet,0x0004)
        # Common.LogWrite("Sending packet: %s" % Common.GetHexString(packet))
        self.driver.Write(packet)

    ## Wait for ATT Packet
    # @param[in] delay How long to wait for a packet before timing out
    # @param[in] user The user of this function
    # @param[out] retval The received ATT packet
    def WaitForAttPacket(self,user,delay):
        Common.LogWrite("TST: Waiting for ATT Response...")
        retval = user.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=delay, NO_PRINT = 1)
        if retval != None:
            Common.LogWrite("TST: ATT Response received : " + Common.GetHexString(retval.Content))
        else:
            Common.LogWrite("TST: no ATT Response received !!!")
        return retval

    def SendErrorResponse(self,opcode,handle,error):
        packet = protocol.Att.AttErrorResponse(ErrorOpcode = opcode, Handle = handle, ErrorCode = error)
        self.driver.Write(packet)
        return packet

    def SendExchangeMtuRequest(self,MtuSize):
        packet = protocol.Att.AttExchangeMtuRequest(MtuSize)
        self.driver.Write(packet)
        return packet

    def SendExchangeMtuResponse(self,MtuSize):
        packet = protocol.Att.AttExchangeMtuResponse(MtuSize)
        self.driver.Write(packet)
        return packet

    def SendFindInformationRequest(self, startHdl=0x0001,endHdl=0xFFFF):
        packet = protocol.Att.AttFindInformationRequest(StartHdl = startHdl, EndHdl = endHdl)
        self.driver.Write(packet, silent=False)
        return packet

    def SendFindInformationResponse(self, Attributes = [], format = None):
        packet = protocol.Att.AttFindInformationResponse(Attributes = Attributes, Format = format)
        self.driver.Write(packet)
        return packet

    def SendFindByTypeValueRequest(self,UUID,value,startHdl=0x0001,endHdl=0xFFFF):
        packet = protocol.Att.AttFindByTypeValueRequest(StartHdl = startHdl, EndHdl = endHdl, AttributeType = UUID, AttributeValue = value)
        self.driver.Write(packet, silent=False)
        return packet

    def SendFindByTypeValueResponse(self,FoundHandles = []):
        packet = protocol.Att.AttFindByTypeValueRequest(FoundHandles)
        self.driver.Write(packet)
        return packet

    def SendReadByTypeRequest(self,UUID,startHdl=0x0001,endHdl=0xFFFF):
        packet = protocol.Att.AttReadByTypeRequest(StartHdl = startHdl, EndHdl = endHdl, UUID = UUID)
        self.driver.Write(packet, silent=False)
        return packet

    def SendReadByTypeResponse(self,Length,Attributes):
        packet = protocol.Att.AttReadByTypeResponse(Length = Length, Attributes = Attributes)
        self.driver.Write(packet)
        return packet

    def SendReadRequest(self,handle):
        packet = protocol.Att.AttReadRequest(handle)
        self.driver.Write(packet)
        return packet

    def SendReadResponse(self,value):
        packet = protocol.Att.AttReadResponse(protocol.Att.Attribute(None,None,value))
        self.driver.Write(packet)
        return packet

    def SendReadBlobRequest(self,handle,offset):
        packet = protocol.Att.AttReadBlobRequest(Handle = handle, Offset = offset)
        self.driver.Write(packet)
        return packet

    def SendReadByGroupTypeRequest(self, startHdl = 0x0001, endHdl = 0xFFFF, type = Uuid.assignedNumbers['PRIMARY_SERVICE']):
        packet = protocol.Att.AttReadByGroupTypeRequest(StartingHandle = startHdl, EndingHandle = endHdl, Type = type)
        self.driver.Write(packet, silent=False)
        return packet

    def SendWriteCommand(self,handle,value):
        packet = protocol.Att.AttWriteCommand(Attributes = protocol.Att.Attribute(handle,None,value))
        self.driver.Write(packet)
        return packet

    def SendWriteRequest(self,handle,value,signature=None):
        packet = protocol.Att.AttWriteRequest(protocol.Att.Attribute(handle,None,value))
        self.driver.Write(packet)
        return packet

    def SendWriteResponse(self, *args):
        packet = protocol.Att.AttWriteResponse()
        self.driver.Write(packet)
        return packet

    def SendPrepareWriteRequest(self, handle, value, offset):
        packet = protocol.Att.AttPrepareWriteRequest(protocol.Att.Attribute(handle, None, value), offset)
        self.driver.Write(packet)
        return packet

    def SendPrepareWriteResponse(self, handle, value, offset):
        packet = protocol.Att.AttPrepareWriteResponse(protocol.Att.Attribute(handle, None, value), offset)
        self.driver.Write(packet)
        return packet

    def SendExecuteWriteRequest(self, Flags = 0x01):
        packet = protocol.Att.AttExecuteWriteRequest(Flags)
        self.driver.Write(packet)
        return packet

    def SendExecuteWriteResponse(self):
        packet = protocol.Att.AttExecuteWriteResponse()
        self.driver.Write(packet)
        return packet

    def SendHandleValueNotification(self,handle,value):
        packet = protocol.Att.AttHandleValueNotification(protocol.Att.Attribute(handle,None,value))
        self.driver.Write(packet)
        return packet

    def SendHandleValueIndication(self,handle,value):
        packet = protocol.Att.AttHandleValueIndication(protocol.Att.Attribute(handle,None,value))
        self.driver.Write(packet)
        return packet

    def SendHandleValueConfirmation(self):
        packet = protocol.Att.AttHandleValueConfirmation()
        self.driver.Write(packet)
        return packet

class SmpComm:
    def __init__(self, bc):
        self.driver = DataComm(bc)
        self.connID = 0

    def setConnID(self,connID):
        self.connID = connID

    ## Send SMP Packet
    # @param packet The packet to be sent
    def Write(self, packet, silent=True):
        packet = L2CapCommands.createL2CapPkt(packet,0x0006)
        #if not silent:
        #    Common.LogWrite("Sending packet: %s" % Common.GetHexString(packet))
        self.driver.SendDataPacket(self.connID, packet)

class SmpCommands:
    ## SMP Command Codes Start
    COMMANDS = {
          'PAIRING_REQUEST'       : 0x01
        , 'PAIRING_RESPONSE'      : 0x02
        , 'PAIRING_CONFIRM'       : 0x03
        , 'PAIRING_RANDOM'        : 0x04
        , 'PAIRING_FAILED'        : 0x05
        , 'ENCRYPTION_INFORMATION': 0x06
        , 'MASTER_INFORMATION'    : 0x07
        , 'IDENTITY_INFORMATION'  : 0x08
        , 'IDENTITY_ADDRESS_INFO' : 0x09
        , 'SIGNING_INFORMATION'   : 0x0A
        , 'SECURITY_REQUEST'      : 0x0B
    }
    COMMANDS_LOOKUP = dict([value,key] for key,value in COMMANDS.iteritems())

    PAIRING_REQUEST             = 0x01
    PAIRING_RESPONSE            = 0x02
    PAIRING_CONFIRM             = 0x03
    PAIRING_RANDOM              = 0x04
    PAIRING_FAILED              = 0x05
    ENCRYPTION_INFORMATION      = 0x06
    MASTER_INFORMATION          = 0x07
    IDENTITY_INFORMATION        = 0x08
    SIGNING_INFORMATION         = 0x09
    SECURITY_REQUEST            = 0x0A
    ## SMP Command Codes End

    ## SMP IO Capability Start
    IO_CAPABILITY = {
          0x00:'DISPLAY_ONLY'
        , 0x01:'DISPLAY_YES_NO'
        , 0x02:'KEYBOARD_ONLY'
        , 0x03:'NO_INPUT_NO_OUTPUT'
        , 0x04:'KEYBOARD_DISPLAY'
    }
    IO_CAPABILITY_INV = dict([value,key] for key,value in IO_CAPABILITY.iteritems())
    ## SMP IO Capability End

    ## SMP OOB data flag Start
    OOB_AUTH_DATA = {
          0x00:'NOT_PRESENT'
        , 0x01:'PRESENT_FROM_REMOTE_DEVICE'
    }
    OOB_AUTH_DATA_INV = dict([value,key] for key,value in OOB_AUTH_DATA.iteritems())
    ## SMP OOB data flag End

    ## SMP Reason Pairing Failed Start
    PAIRING_FAILED_REASON = {
          0x01:'PASSKEY_ENTRY_FAILED'
        , 0x02:'OOB_NOT_AVAILABLE'
        , 0x03:'AUTHENTICATION_REQUIREMENTS'
        , 0x04:'CONFIRM_VALUE_FAILED'
        , 0x05:'PAIRING_NOT_SUPPORTED'
        , 0x06:'ENCRYPTION_KEY_SIZE'
        , 0x07:'COMMAND_NOT_SUPPORTED'
        , 0x08:'UNSPECIFIED_RESON'
        , 0x09:'REPEATED_ATTEMPTS'
        , 0x0A:'INVALID_PARAMETERS'
    }
    PAIRING_FAILED_REASON_INV = dict([value,key] for key,value in PAIRING_FAILED_REASON.iteritems())
    ## SMP Reason Pairing Failed End

    ## SMP Key Distribution Start
    KEY_DISTRIBUTION = {
          'EncKey' : 0x01
        , 'IdKey'  : 0x02
        , 'Sign'   : 0x04
    }
    ## SMP Key Distribution End

    def __init__(self, driver):
        self.driver = driver
        self.connID = 0x0000

    def SendPairingRequest(self,IO_Cap,OOB_Data,BondingFlags,MITM,encSize,MKeyDist, SKeyDist):
        if MITM:
            MITM = 4
        else:
            MITM = 0
        SKeyDistribution = self.GetKeyDistrMap(SKeyDist)
        MKeyDistribution = self.GetKeyDistrMap(MKeyDist)

        packet = protocol.Smp.SmpPairingRequest(IoCapability = IO_Cap, OobDataFlag = OOB_Data, Bonding = (BondingFlags != 0), Mitm = (MITM != 0), MaxEncKeySize = encSize, MKeyDistrBitmap = MKeyDistribution, SKeyDistrBitmap = SKeyDistribution)
        Common.LogWrite("COMMON: Sending {0!r} - {0!s}".format(packet) )
        self.driver.Write(packet)
        return packet

    def SendPairingResponse(self,IO_Cap,OOB_Data,BondingFlags,MITM,encSize,MKeyDist,SKeyDist):
        if MITM:
            MITM = 4
        else:
            MITM = 0

        SKeyDistribution = self.GetKeyDistrMap(SKeyDist)
        MKeyDistribution = self.GetKeyDistrMap(MKeyDist)

        packet = protocol.Smp.SmpPairingResponse(IoCapability = IO_Cap, OobDataFlag = OOB_Data, Bonding = (BondingFlags != 0), Mitm = (MITM != 0), MaxEncKeySize = encSize, MKeyDistrBitmap = MKeyDistribution, SKeyDistrBitmap = SKeyDistribution)
        Common.LogWrite("COMMON: Sending {0!r} - {0!s}".format(packet) )
        self.driver.Write(packet)
        return packet

    def SendPairingConfirm(self, confValue):
        if isinstance(confValue,str):
            confValue = [int(confValue[i:i+2],16) for i in range(0,len(confValue),2)]
        else:
            confValue = [int(el) for el in confValue]
        confValue.reverse()
        packet = protocol.Smp.SmpPairingConfirm(ConfirmLtlEndArray = confValue)
        self.driver.Write(packet)
        return packet

    def SendPairingRandom(self, random):
        if isinstance(random,str):
            random = [int(random[i:i+2],16) for i in range(0,len(random)-2,2)]
            random.reverse()
        elif isinstance(random,int) or isinstance(random,long) or isinstance(random,System.Int64):
            tempRand = []
            for i in range(16):
                tempRand.append(int("%02X" % ((random >> 8*i) & 0xFF),16))
            random = tempRand
        else:
            random = [int(el) for el in random]
            random.reverse()
        packet = protocol.Smp.SmpPairingRandom(RandomLtlEndArray = random)
        self.driver.Write(packet)
        return packet

    def PairingFailed(self, reason):
        packet = protocol.Smp.SmpPairingFailed(Reason = reason)
        self.driver.Write(packet)
        return packet

    def PairingReserved0(self):
        packet = protocol.Smp.SmpPairingReserved0()
        self.driver.Write(packet)
        return packet

    def GetKeyDistrMap(self, KeyDist):
        KeyDistribution = 0
        if isinstance(KeyDist, int):
            return KeyDistribution
        for el in KeyDist:
            if el in SmpCommands.KEY_DISTRIBUTION:
                KeyDistribution |= SmpCommands.KEY_DISTRIBUTION[el]
        return KeyDistribution

    @staticmethod
    def ParseKeyDistr(map):
        keyDistr = []
        if int(map) & 0x01:
            keyDistr.append('EncKey')
        if int(map) & 0x02:
            keyDistr.append('IdKey')
        if int(map) & 0x04:
            keyDistr.append('Sign')
        return keyDistr

class HciData:
    def __init__(self, packet):
        DataPkt.__init__(self)
        self.Content = []
        for value in packet:
            self.Content.append(int(value))

class HciEvent:
    def __repr__(self):
        return "<HciEvent: eventCode=0x%02X>" % self.EventCode        #Define how to print object info

    def __init__(self):
        self.isEvent = True
        self.isDataPacket = False

    #This function generates event object instances from a raw packet array.
    #If the packet matches any of the predefined classes the return value is the generated object. Otherwise
    #the return value is None.
    @staticmethod
    def GenerateHciEventObject(packet):
        eventIdx = 0
        retval = None
        event = Ulpbt.HciEventFactory.Instantiate(packet)
        eventId = int(event.GetEventId())

        if  (eventId == HciComm.HCI_ADVERTISING_PACKET_REPORT_EVENT):
            retval = HciAdvPacketReportEvent(packet)
        elif (eventId == HciComm.HCI_LL_CONNECTION_CREATED_EVENT):
            retval = HciLLConnectionCreatedEvent(packet)
        elif (eventId == HciComm.HCI_LL_CONNECTION_TERMINATION_EVENT):
            retval = HciLLConnectionTerminationEvent(packet)
        elif (eventId == HciComm.HCI_LL_CONNECTION_PAR_UPDATE_COMPLETE_EVENT):
            retval = HciConnectionParametersUpdateCompleteEvent(packet)
        elif (eventId == HciComm.HCI_NUM_COMPLETED_PACKETS_EVENT):
            retval = HciNumCompletedPacketsEvent(packet)
        elif (eventId == HciComm.HCI_COMMAND_COMPLETE_EVENT):
            retval = HciCommandCompleteEvent(packet)
        elif (eventId == HciComm.HCI_COMMAND_STATUS_EVENT):
            retval = HciCommandStatusEvent(packet)
        elif (eventId == HciComm.HCI_ERROR_EVENT):
            retval = HciErrorEvent(packet)
        elif (eventId == HciComm.HCI_DATA_BUFFER_OVERFLOW_EVENT):
            Common.LogWrite("HCI_DATA_BUFFER_OVERFLOW_EVENT!")
            retval = HciDataBufferOverflowEvent(packet)
        elif (eventId == HciComm.HCI_ENCRYPTION_CHANGE_EVENT):
            retval = HciEncryptionChangeEvent(packet)
        elif (eventId == HciComm.HCI_ENCRYPTION_KEY_REFRESH_COMPLETE_EVENT):
            retval = HciEncryptionKeyRefreshCompleteEvent(packet)
        elif (eventId == HciComm.HCI_LONG_TERM_KEY_REQUESTED_EVENT):
            retval = HciLongTermKeyRequestedEvent(packet)
        elif (eventId == HciComm.HCI_READ_REMOTE_VERSION_INFORMATION_COMPLETE_EVENT):
            Common.LogWrite("HCI_READ_REMOTE_VERSION_INFO")
            retval = HciReadRemoteVersionInfoEvent(packet)
        else:
            Common.LogWrite("No matching HCI event code found in GenerateHciEventObject: %02X" % eventId)
        return retval

class HciAdvPacketReportEvent(HciEvent):
    # Init
    # @param self
    # @param packet
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)     #Use event factory implemented in debug panel lib.
        self.Content            = []
        for cell in packet:                                                     ## List of all packet data. e.g. [60,61,62,63,64,65,66,67,68,69]
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())                       ## EventCode Event code. e.g. 0x3c
        self.NumDevices         = int(event.GetNumberOfDevices())               ## Number of devices. e.g. 0x01
        self.EventType          = int(event.GetEventType(0))                    ## Event type. e.g. 0x00
        self.AddressType        = int(event.GetAddressType(0))                  ## Address type. e.g. 0x00
        tmp                     = event.GetDeviceAddress(0)
        self.DeviceAddress      = tmp.GetAddressBytes()                         ## Device address list. e.g. [1,2,3,4,5,6]
        self.DeviceAddressStringBigEnd = tmp.ToString()
        self.DeviceAddressStringLtlEnd = Ulpbt.WbDeviceAddress.CreateAddressLtlEnd(self.DeviceAddress, 0).ToString()
        self.DataLen            = int(event.GetDataLen(0))                      ## Data length. e.g. 0x09
        self.Data               = event.GetData(0)                              ## Advertising data. e.g. [60,61,62,63,64,65,66,67,68]
        self.AdPacketData       = event.GetAdvPacketData(0)
        self.Rssi               = event.GetRssi(0)

class HciLLConnectionCreatedEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)           #Use event factory implemented in debug panel lib.
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())
        self.Status             = int(event.GetStatus())
        self.ConnectionId       = int(event.GetConnectionID())
        self.Role               = int(event.GetRole())
        self.PeerAddressType    = int(event.GetAddressType())
        self.PeerAddress        = event.GetPeerAddress().ToString()
        self.PeerAddressBigEnd  = self.PeerAddress
        self.PeerAddressLtlEnd  = Ulpbt.WbDeviceAddress.CreateAddressBigEnd(self.PeerAddress).ToString()
        self.ConnectionInterval = int(event.GetConnectionInterval())
        self.ConnectionLatency  = int(event.GetConnectionLatency())
        self.SupervisionTimeout = int(event.GetSupervisionTimeout())
        self.ClockAccuracy      = int(event.GetClockAccuracy())

class HciLLConnectionTerminationEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode      = int(event.GetEventId())
        self.ConnectionId   = int(event.GetConnectionID())
        self.Reason         = int(event.GetReason())
        self.ReasonAsString = event.GetReason().ToString()
        self.Status         = int(event.GetStatus())
        Common.LogWrite("Received LL Connection Termination Event, reason %02X" % self.Reason)

class HciConnectionParametersUpdateCompleteEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())
        self.ConnectionId       = int(event.GetConnectionID())
        self.ConnInterval       = int(event.GetConnInterval())
        self.ConnLatency        = int(event.GetConnLatency())
        self.ConnTimeout        = int(event.GetConnTimeout())
        self.Status             = int(event.GetStatus())

class HciNumCompletedPacketsEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode      = int(event.GetEventId())
        self.ConnectionId   = int(event.GetConnectionID())
        self.NumPackets     = int(event.GetNumPackets())
        HciComm.UpdateNumComplete(self.NumPackets)

class HciCommandCompleteEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        self.event                       = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content                = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode              = int(self.event.GetEventId())
        self.NumHciCommandPackets   = int(self.event.GetCmdBufferDepth())
        self.CommandOpcode          = int(self.event.GetOpCode())
        self.Status                 = int(self.event.GetStatus())
        if self.CommandOpcode == HciComm.BTLE_CMD_LE_READ_BUFFER_SIZE:
            HciComm.InitNumComplete(int(self.Content[8]))
        if self.CommandOpcode == HciComm.BTLE_CMD_READ_LOCAL_VERSION_INFORMATION:
            self.HciVersion             = self.event.GetHciVersion()
            self.HciRevision            = self.event.GetHciRevision()
            self.LmpVersion             = self.event.GetLmpVersion()
            self.ManufacturerName       = self.event.GetManufacturerName()
            self.LmpSubversion          = self.event.GetLmpSubversion()
        if self.CommandOpcode == HciComm.BTLE_CMD_READ_RSSI:
            self.Rssi                   = self.event.Rssi

    def GetPublicDeviceAddress(self):
        address = (self.event.GetPublicDeviceAddress()).ToString()
        return address

    def GetVersionInfo(self):
        versionInfo = self.event.GetVersionInfo()
        return versionInfo

class HciCommandStatusEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode      = int(event.GetEventId())
        self.Status         = int(event.GetStatus())
        self.NumHciCommandPackets   = int(event.GetCmdBufferDepth())
        self.CommandOpcode          = int(event.GetOpCode())

class HciDataBufferOverflowEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())

class HciErrorEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())
        self.ErrorCode          = int(event.GetErrorCode())
        Common.LogWrite("Error event received! Error code %d" % self.ErrorCode)

class HciEncryptionChangeEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())
        self.Status             = int(event.GetStatus())
        self.ConnectionId       = int(event.GetConnectionID())
        self.EncEnabled         = int(event.GetEncryptionEnabled())

class HciEncryptionKeyRefreshCompleteEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        self.event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(self.event.GetEventId())
        self.Status             = int(self.event.GetStatus())
        self.ConnectionId       = int(self.event.GetConnectionID())

class HciLongTermKeyRequestedEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())
        self.ConnectionId       = int(event.GetConnectionID())
        self.RandomNumber       = event.GetRandomNumber()
        self.EncryptedDiversifier = event.GetEncryptedDiversifier()

class HciReadRemoteVersionInfoEvent(HciEvent):
    def __init__(self, packet):
        HciEvent.__init__(self)
        event                   = Ulpbt.HciEventFactory.Instantiate(packet)
        self.Content            = []
        len = packet[1]
        for cell in packet:
            self.Content.append(int(cell))
        self.EventCode          = int(event.GetEventId())
        self.Status             = int(event.GetStatus())
        self.ConnectionId       = int(event.GetConnectionID())
        self.ManufacturerName   = event.GetManufacturerName()
        self.LmpVersion         = event.GetLmpVersion()
        self.LmpSubversion      = event.GetLmpSubversion()
