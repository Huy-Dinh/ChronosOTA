from testerScriptCommon import *
from datetime import datetime, timedelta
import protocol.Smp 
import modules.packetqueue

def createMSB(data,size):
    return [int("%02X" % (0xFF & (data >> i)),16) for i in range((size-1)*8,-1,-8)]

def createLSB(data,size):
    return [int("%02X" % (0xFF & (data >> i)),16) for i in range(0,size*8,8)]

## @class testerScriptClient
# Class for maintaining a connection between TST and DUT
class testerScriptEngineClient:
    defaultConnSettings = {
        'scanInterval'      :0x0190,    # 250ms = 400 * 0.625
        'scanWindow'        :0x00A0,    # 100ms = 160 * 0.625
        'whiteList'         :0,         #
        'addressTypePeer'   :1,
        'peerAddress'       :None,
        'addressTypeOwn'    :0,
        'connIntervalMin'   :0x0050,
        'connIntervalMax'   :0x0050,
        'connLatency'       :0x0000,
        'connTimeout'       :300,
        'encrypted'         :0,
        'minLength'         :0x00A0,
        'maxLength'         :0x00A0
    }
    defaultScanSettings = {
        'active':0,
        'addressType':0,
        'scanInterval':0x0190,
        'scanWindow':0x00A0,
        'filterPolicy':0,
        'numScanPackets':30
    }
    defaultEncSettings = {
        'IO':0x03,
        'OOB':0x00,
        'BondingFlags':0x01,
        'MITM':0x00,
        'encKeySize':0x10,
        'minEncKeySize':0x07,
        'maxEncKeySize':0x10,
        'SKeyDistr':['EncKey'],
        'MKeyDistr':[],
        'SendFailed':{'afterPacket':None,'error':None},
        'ReceiveFailed':{'afterPacket':None,'error':None},
    }
    
    DEFAULT_TIMEOUT = 10
    def __init__(self, ftdiComm, hciComm, driver, smpCmds, debug = False):
        self.ftdiComm = ftdiComm
        self.hciComm = hciComm
        self.tester = driver
        self.driver = modules.packetqueue.PacketQueue(QUEUE_LENGTH=200, LOG_FUNCTION = Common.LogWrite)
        self.driver.print_log = False

        self.debug = debug
        self.smpCmds = smpCmds
        self.ConnId = None
        self.connInfo = None
        self.tester.AddPacketRecipients(self.addToQueue)
        
    def addToQueue(self, packet):
        self.driver.AddToQueue(packet)      
        self.PacketLogger(packet)
        
    def PacketLogger(self, packet):
        if isinstance(packet, HciLLConnectionTerminationEvent):
            self.connInfo = None
        elif isinstance(packet, HciLLConnectionCreatedEvent):
            self.connInfo = packet
            
    def ConnectTo(self, address = None, connSettings = defaultConnSettings):
        for key,value in self.defaultConnSettings.iteritems():
            if key not in connSettings:
                connSettings[key] = value
        if address != None:
            connSettings['peerAddress'] = address
        elif connSettings['peerAddress'] == None:
            return None
        timeoutSetting = 10 #(connSettings['scanInterval']*0.625+connSettings['scanWindow']*0.625)/100
        counter = 1
        self.driver.LogWrite("Enter Connect")
        
        while counter > 0:
            #self.driver.LogWrite("Connection attempts left %d" % counter)
            if self.debug:
                self.driver.LogWrite("TST-Client: Sending Create LL connection to %s" % self.ReverseByteString(connSettings['peerAddress']))
            counter =  counter - 1
            self.hciComm.CreateLLConnection(
                  connSettings['scanInterval']
                , connSettings['scanWindow']
                , connSettings['whiteList']
                , connSettings['addressTypePeer']
                , connSettings['peerAddress']
                , connSettings['addressTypeOwn']
                , connSettings['connIntervalMin']
                , connSettings['connIntervalMax']
                , connSettings['connLatency']
                , connSettings['connTimeout']
                , connSettings['encrypted']
                , connSettings['minLength']
                , connSettings['maxLength']
            )
            retval = self.driver.WaitFor(self.hciComm.HCI_COMMAND_STATUS_EVENT, T=self.DEFAULT_TIMEOUT, NO_PRINT = 1)
            if retval != None:
                if retval.Status != 0x00:
                    if self.debug:
                        self.driver.LogWrite("TST-Client: Received error %02X on CreateLLConnection" % retval.Status)
                    return None
            else:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Did not receive any status packet")
                return None
            
            self.driver.LogWrite("TST-Client: Waiting for LL Connection Created Event")
            retval = self.driver.WaitFor(self.hciComm.HCI_LL_CONNECTION_CREATED_EVENT, T=timeoutSetting, NO_PRINT = 1)
            if retval != None:
                if retval.EventCode == self.hciComm.HCI_LL_CONNECTION_CREATED_EVENT:
                    if retval.Status == 0x00:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Connection created successful. ConnectionId: %d" % retval.ConnectionId)
                        self.ConnId = retval.ConnectionId
                        self.hciComm.ConnInterval = retval.ConnectionInterval
                        self.hciComm.ConnLatency  = retval.ConnectionLatency
                        self.hciComm.ConnTimeout  = retval.SupervisionTimeout
                        return retval
                    else:
                        self.driver.LogWrite("TST-Client: Connection created received with status: %d" % retval.Status)
                        continue
            else:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Wait for HCI_LL_CONNECTION_CREATED_EVENT Failed.")
                #self.driver.AssertTrue(False)
                self.driver.LogWrite("TST-Client: Cancelling Connection Creation")                    
                self.hciComm.StopLLConnectionCreation()
                retval = self.driver.WaitFor(Common.ANY_PACKET, T=timeoutSetting, NO_PRINT = 1)
                if retval != None:
                    if retval.EventCode == self.hciComm.HCI_LL_CONNECTION_CREATED_EVENT:
                        if retval.Status == 0x00:
                            if self.debug:
                                self.driver.LogWrite("TST-Client: Connection created successful. ConnectionId: %d" % retval.ConnectionId)
                            self.ConnId = retval.ConnectionId
                            self.hciComm.ConnInterval = retval.ConnectionInterval
                            self.hciComm.ConnLatency  = retval.ConnectionLatency
                            self.hciComm.ConnTimeout  = retval.SupervisionTimeout
                            return retval
                        else:
                            self.driver.LogWrite("TST-Client: Connection created received with status: %d" % retval.Status)
                            continue
                    elif retval.EventCode == self.hciComm.HCI_COMMAND_COMPLETE_EVENT:
                        if retval.Status != 0x00:
                            if self.debug:
                                self.driver.LogWrite("TST-Client: Received error %02X on Command Complete" % retval.Status)                    
                                self.driver.LogWrite("TST-Client: Command Complete For Opcode %x" % retval.CommandOpcode)
                                retval = self.driver.WaitFor(self.hciComm.HCI_LL_CONNECTION_CREATED_EVENT, T=timeoutSetting, NO_PRINT = 1)
                                if retval != None:
                                    if retval.EventCode == self.hciComm.HCI_LL_CONNECTION_CREATED_EVENT:
                                        if retval.Status == 0x00:
                                            if self.debug:
                                                self.driver.LogWrite("TST-Client: Connection created successfully after Command Complete. ConnectionId: %d" % retval.ConnectionId)
                                            self.ConnId = retval.ConnectionId
                                            self.hciComm.ConnInterval = retval.ConnectionInterval
                                            self.hciComm.ConnLatency  = retval.ConnectionLatency
                                            self.hciComm.ConnTimeout  = retval.SupervisionTimeout
                                            return retval
                                        else:
                                            self.driver.LogWrite("TST-Client: Connection creation failed after Command Complete (%02X) " % retval.Status)
                                else:
                                   #self.driver.LogWrite("TST-Client: Received error %02X on Connection Complete after Command Complete" % retval.Status)                    
                                   self.driver.LogWrite("TST-Client: Did not receive any packet after Command Complete")                    
                                   self.ftdiComm.Reset()
                                   time.sleep(1)
                        else:
                            self.driver.LogWrite("TST-Client: Received error %02X on Command Complete" % retval.Status)                    
                            # self.driver.LogWrite("TST-Client: Did not receive Connection Created nor Command COmplete but %d" % retval.EventCode)                    
                            continue
                else:
                    self.driver.LogWrite("TST-Client: Did NOT Receive Connection Complete Event")
                    self.driver.LogWrite("TST-Client: Did not recive a Connection Complete Event for LL Creation Cancellation")
                    self.ftdiComm.Reset()
                    time.sleep(1)
                    continue
        return None

    def NrfSetBDAddr(self,address):
        self.driver.LogWrite("Tester Script Enginer Clinet NrfBD address")
        self.hciComm.NrfSetBDAddr(address)
        retval = None
        while True:
            retval = self.driver.WaitFor(Common.ANY_PACKET, T=self.DEFAULT_TIMEOUT, NO_PRINT = 1)
            # self.driver.LogWrite(retval)
            if isinstance(retval, HciCommandCompleteEvent) and retval.CommandOpcode == self.hciComm.BTLE_CMD_LE_READ_BD_ADDR:
                if retval.Status != 0x00:
                    if self.debug:
                        self.driver.LogWrite("TST-Client: Received failure %02X on Set Device Address" % retval.Status)
                    return None
                break
                     
            elif retval == None:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Did not receive BTLE_CMD_LE_READ_BD_ADDR Command Complete event within timeout")
                return None
            else:
                if self.debug:
                    self.driver.LogWrite(retval)
                    
            return retval
                
    def WaitForScanEvent(self, name, scanSettings = defaultScanSettings):
        device = None
        for key,value in self.defaultScanSettings.iteritems():
            if key not in scanSettings:
                scanSettings[key] = value
        timeoutSetting = (scanSettings['scanInterval']*0.625+scanSettings['scanWindow']*0.625)/100
        self.hciComm.SetScanParameters(
            scanSettings['active'],
            scanSettings['addressType'],
            scanSettings['scanInterval'],
            scanSettings['scanWindow'],
            scanSettings['filterPolicy']
        )
        while True:
            retval = self.driver.WaitFor(Common.ANY_PACKET, T=self.DEFAULT_TIMEOUT, NO_PRINT = 1)
            if isinstance(retval, HciCommandCompleteEvent) and retval.CommandOpcode == self.hciComm.BTLE_CMD_LE_SET_SCAN_PARAMETERS:
                if retval.Status != 0x00:
                    if self.debug:
                        self.driver.LogWrite("TST-Client: Received failure %02X on SetScanParameters" % retval.Status)
                    return None
                break
            elif retval == None:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Did not receive BTLE_CMD_LE_SET_SCAN_PARAMETERS Command Complete event within timeout")
                return None
        
        if self.debug:
            self.driver.LogWrite("TST-Client: Switch scan on")
        self.hciComm.WriteScanMode(1)
        retval = self.driver.WaitFor(self.hciComm.HCI_COMMAND_COMPLETE_EVENT, T=timeoutSetting, NO_PRINT = 1)
        if retval != None:
            if retval.Status != 0x00:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Received failure %02X on WriteScanMode(1)" % retval.Status)
                    self.driver.LogWrite("TST-Client: Sending write scan mode OFF")
                self.hciComm.WriteScanMode(0)
                retval = self.driver.WaitFor(self.hciComm.HCI_COMMAND_COMPLETE_EVENT, T=timeoutSetting, NO_PRINT = 1)
                if retval != None:
                    if retval.Status != 0x00:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Scan mode OFF returned status %02X" % retval.Status)
                        return None
                
                return None
        else:
            self.driver.LogWrite("TST-Client: Did not receive WriteScanMode(1) Command Complete event within timeout")
            self.hciComm.WriteScanMode(0)
            retval = self.driver.WaitFor(self.hciComm.HCI_COMMAND_COMPLETE_EVENT, T=self.DEFAULT_TIMEOUT, NO_PRINT = 1)
            if retval != None:
                if retval.Status != 0x00:
                    if self.debug:
                        self.driver.LogWrite("TST-Client: Scan mode OFF returned status %02X" % retval.Status)
                    return None
            else:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Did not receive WriteScanMode(0) Command Complete event within timeout")
                return None
        
        startTime = datetime.now()
        while datetime.now() - startTime <= timedelta(0,scanSettings['numScanPackets'],0):
            if self.debug:
                self.driver.LogWrite("TST-Client: Waiting for event ADVERTISING_PACKET_REPORT")
            retval = self.driver.WaitFor(self.hciComm.HCI_ADVERTISING_PACKET_REPORT_EVENT, T=5, NO_PRINT = 1)
            if retval != None:
                adv_bdaddr_str = "".join("%02X" % el for el in retval.DeviceAddress)
                pos = 0
                adv_name_str = ""
                while pos < len(retval.Data):
                    length = retval.Data[pos]
                    if retval.Data[pos+1] == ADPacket.types['ShortenedDeviceName'] or retval.Data[pos+1] == ADPacket.types['CompleteDeviceName']:
                        adv_name_str = Common.GetTextString(retval.Data[pos+2:pos+length+1]).decode("UTF-8")
                    pos += length +1
                
                if self.debug:
                    self.driver.LogWrite("TST-Client: Advertiser Address: %s" % (adv_bdaddr_str))
                    if adv_name_str != "":
                        self.driver.LogWrite("TST-Client: Advertiser Name: %s" % (adv_name_str))
                if name != None and name in adv_name_str:
                    if self.debug:
                        self.driver.LogWrite("TST-Client: DUT discovered")
                    device = retval
                    break
                elif 'address' in scanSettings and scanSettings['address'] == adv_bdaddr_str:
                    device = retval
                    break
                elif name == None:
                    device = retval
                    break
            else:
                if self.debug:
                    self.driver.LogWrite("TST-Client: No Advertising packet within 5 seconds, waiting another 5")
        if self.debug:
            self.driver.LogWrite("TST-Client: Setting scan mode OFF")
        self.hciComm.WriteScanMode(0)
        retval = self.driver.WaitFor(self.hciComm.HCI_COMMAND_COMPLETE_EVENT, T=timeoutSetting, NO_PRINT = 1)
        if retval != None:
            if retval.Status != 0x00:
                self.driver.LogWrite("TST-Client: Scan mode OFF returned status %02X" % retval.Status)
                return None
        else:
            if self.debug:
                self.driver.LogWrite("TST-Client: Did not receive WriteScanMode Command Complete event within timeout")
            return None
        
        return device

    def ScanAndConnect(self, name, connSettings = defaultConnSettings, scanSettings = defaultScanSettings):
        retval = self.WaitForScanEvent(name, scanSettings = scanSettings)
        if retval != None:
            connSettings['peerAddress']     = str(retval.DeviceAddressStringLtlEnd)
            connSettings['addressTypePeer'] = retval.AddressType
        else:
            if self.debug:
                self.driver.LogWrite("TST-Client: Could not find advertising packet with given name")
            return None
        
        retval = self.ConnectTo(connSettings = connSettings)
        if retval != None:
            return retval
        else:
            if self.debug:
                self.driver.LogWrite("TST-Client: Could not connect to device")
            return None
            
    
    def ReverseByteString(self,value):
        length = len(value)
        retval = ""
        if length % 2 != 0:
            value = "0" + value
        for i in range(length)[-2::-2]:
            retval = retval + value[i:i+2]
        return retval
    
    def Disconnect(self):
        if self.connInfo != None:
            if self.debug:
                self.driver.LogWrite("TST-Client: Terminating Connection")
            
            self.hciComm.TerminateLLConnection(self.ConnId)
            while True:
                retval = self.driver.WaitFor(Common.ANY_PACKET, T=5, NO_PRINT=True)
                if retval == None:
                    self.driver.LogWrite("TST-CLIENT: Time Out Happened No Command Response Break the loop ")
                    # Reset Chip 
                    self.ftdiComm.Reset()
                    break
                if isinstance(retval, HciCommandStatusEvent):
                    if retval.Status != 0x00:
                        self.driver.LogWrite("TST-CLIENT: Disconnect Command Status Event received  ( Failure ) !!")
                        # Reset Chip 
                        self.ftdiComm.Reset()
                        break
                    else:   
                        self.driver.LogWrite("TST-CLIENT: Disconnect Command Status Event Successfully received  !!")
                        while True:
                            retval = self.driver.WaitFor(Common.ANY_PACKET, T=5, NO_PRINT=True)
                            # retval = self.driver.WaitFor(self.hciComm.HCI_LL_CONNECTION_TERMINATION_EVENT, T=5)
                        
                            if retval != None:
                                if isinstance(retval, HciLLConnectionTerminationEvent):
                                    if retval.Status != 0x00:
                                        self.driver.LogWrite("TST-Client: Failed to terminate connection, Status %02X, Reason %02X" % (retval.Status, retval.Reason))
                                    else:
                                        self.driver.LogWrite("TST-Client: Termination complete, reason %02X" % retval.Reason)
                                        self.ConnID = None
                                    return retval
                                else:
                                    self.driver.LogWrite("TST-Client: Received Strange Packet: <%s> %r %s " % (retval.__class__.__name__,retval,retval))
                
                            else:
                                self.driver.LogWrite("Timeout happened no Terminate EVent Received")
                                break
                            

                else:
                    self.driver.LogWrite("TST-Client: Not Status Event")
                    self.driver.LogWrite("TST-Client: Received Strange Packet: <%s> %r %s " % (retval.__class__.__name__,retval,retval))
                    
        else:
            if self.debug:
                self.driver.LogWrite("TST-Client: Did not have any Connection ID")
        return None
        
    def StartEncryption(self, LTK, EDIV, RAND):
        state = 'Init'
        
        if None in [LTK, EDIV, RAND]:
            return False

        while True:
            if state == 'Init':
                if self.debug:
                    self.driver.LogWrite("TST-Client: Starting Encryption")
                self.hciComm.StartEncryption(self.ConnId,RAND,EDIV,LTK)
                state = 'StartEncryption'
            retval = self.driver.WaitFor(Common.ANY_PACKET, T=30, NO_PRINT=True)
            if isinstance(retval, HciCommandStatusEvent):
                if state == 'StartEncryption':
                    if retval.Status != 0x00:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Failed to start encryption, reason 0x%02X" % retval.Status)
                        return False
                    else:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Start Encryption command returned success")
                        state = 'EncChange'
            elif isinstance(retval, HciEncryptionChangeEvent) or isinstance(retval, HciEncryptionKeyRefreshCompleteEvent):
                if state == 'EncChange':
                    if retval.Status != 0x00:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Encryption event returned with failure, reason 0x%02X" % retval.Status)
                        return False
                    else:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Encryption Event returned success")
                        return True
            elif isinstance(retval, HciLLConnectionTerminationEvent):
                if self.debug:
                    self.driver.LogWrite("TST-Client: Lost connection, reason 0x%02X" % retval.Reason)
                return False
            elif retval == None:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Timed out")
                return False
    
    def CallEncrypt(self, key, plaintextData):
        if self.debug:
            self.driver.LogWrite("TST-Client: calling encrypt function, with key %s and plaintextdata %s" % (Common.GetHexString(key), Common.GetHexString(plaintextData)))
        self.hciComm.Encrypt(key,plaintextData)
        while True:
            packet = self.driver.WaitFor(Common.ANY_PACKET, T=5, NO_PRINT=True)
            if isinstance(packet, HciCommandCompleteEvent):
                if packet.CommandOpcode == self.hciComm.BTLE_CMD_LE_HCI_ENCRYPT and packet.Status == 0x00:
                    if packet.Status == 0x00:
                        retval = int("".join("%02X" % el for el in packet.Content[packet.Content[1]+1:5:-1]),16)
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Received encrypted data: 0x%032X" % retval)
                    else:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Faild with command")
                    break
            elif isinstance(packet, HciLLConnectionTerminationEvent):
                if self.debug:
                    self.driver.LogWrite("TST-Client: Lost connection while waiting for command response event")
                return False
            elif packet == None:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Did not receive a BTLE_CMD_LE_HCI_ENCRYPT command response within 5 seconds")
                retval = None
                break
        return retval
    
    def CallRand(self):
        if self.debug:
            self.driver.LogWrite("TST-Client: calling rand function")
        self.hciComm.Rand()
        while True:
            packet = self.driver.WaitFor(Common.ANY_PACKET, T=5, NO_PRINT=True)
            if isinstance(packet, HciCommandCompleteEvent):
                if packet.CommandOpcode == self.hciComm.BTLE_CMD_LE_HCI_RAND:
                    if packet.Status == 0x00:
                        retval = int("".join("%02X" % el for el in packet.Content[packet.Content[1]+1:5:-1]),16)
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Received random number: 0x%016X" % retval)
                    else:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Faild with command")
                    break
            elif isinstance(packet, HciLLConnectionTerminationEvent):
                if self.debug:
                    self.driver.LogWrite("TST-Client: Lost connection while waiting for command response event")
                return False
            elif packet == None:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Did not receive a BTLE_CMD_LE_HCI_RAND command response within 5 seconds")
                retval = None
                break
        return retval
        
    def CallReadPublicDeviceAddress(self):
        if self.debug:
            self.driver.LogWrite("TST-Client: calling read public device address")
        
        # if 'deviceAddress' in self.hciComm.__dict__:
            # return self.hciComm.deviceAddress
        self.hciComm.ReadPublicDeviceAddress()
        while True:
            packet = self.driver.WaitFor(Common.ANY_PACKET, T=5, NO_PRINT=True)
            if isinstance(packet, HciCommandCompleteEvent):
                if packet.CommandOpcode == self.hciComm.BTLE_CMD_LE_READ_BD_ADDR and packet.Status == 0x00:
                    if packet.Status == 0x00:
                        retval = int("".join("%02X" % el for el in packet.Content[packet.Content[1]+1:5:-1]),16)
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Received device address: 0x%012X" % retval)
                    else:
                        if self.debug:
                            self.driver.LogWrite("TST-Client: Faild with command")
                    break
            elif isinstance(packet, HciLLConnectionTerminationEvent):
                if self.debug:
                    self.driver.LogWrite("TST-Client: Lost connection while waiting for command response event")
                return False
            elif packet == None:
                if self.debug:
                    self.driver.LogWrite("TST-Client: Did not receive a BTLE_CMD_LE_READ_BD_ADDR command response within 5 seconds")
                retval = None
                break
        return retval
        
    def PairingInitial(self, variables):
        self.PairingComplete = False
        self.PairingPaused = False
        
        if self.debug:
            self.driver.LogWrite("TST-Client: Generating MRandom")
        if not self.CreateMRand(variables):
            return False
        if self.debug:
            self.driver.LogWrite("TST-Client: MRandom - {MRandom:#034X}".format(**variables))
        
        if self.debug:
            self.driver.LogWrite("TST-Client: Sending Get Device Address")
        variables['tstAddress'] = self.CallReadPublicDeviceAddress()
        isInteger = isinstance(variables['tstAddress'], (int, long))
        if not isInteger:
            self.driver.LogWrite("TST-Client: Error: Tester address not a number: %s" % variables['tstAddress'])
            return False
        if self.debug:
            self.driver.LogWrite("TST-Client: Tester Address - {tstAddress:#014X}".format(**variables))
        if variables['tstAddress'] == None or variables['tstAddress'] == False:
            return False
        return True
        
    def CreateMRand(self, variables):
        rand1 = self.CallRand()
        if rand1 == None or rand1 == False:
            return False
        rand2 = self.CallRand()
        if rand2 == None or rand2 == False:
            return False
        variables['MRandom'] = (rand1 << 64) | rand2
        return True

    def CreateConfirm(self, variables, master):
        confirm = ['SConfirm','MConfirm'][master]
        random = ['SRandom','MRandom'][master]
        try:
            if self.debug:
                self.driver.LogWrite("TST-Client: Creating {0!s}".format(confirm))
            pairingReq = int("".join("{0:02X}".format(el) for el in variables['pairingReq'][::-1]),16)
            pairingResp = int("".join("{0:02X}".format(el) for el in variables['pairingResp'][::-1]),16)
            dutAddrType = self.connInfo.PeerAddressType # 1 bit
            variables['dutAddr'] = int(str(self.connInfo.PeerAddress),16) # 6 byte, 48 bit
            p1 = int("{0:014X}{1:014X}{2:02X}{3:02X}".format(pairingResp,pairingReq,dutAddrType,0),16)
            if self.debug:
                self.driver.LogWrite('TST-Client: P1 - {0:#034X}'.format(p1))
            p2 = int("{0:08X}{1:012X}{2:012X}".format(0,variables['tstAddress'],variables['dutAddr']),16)
            if self.debug:
                self.driver.LogWrite('TST-Client: P2 - {0:#034X}'.format(p2))
            p1r = variables[random] ^ p1
            if self.debug:
                self.driver.LogWrite('TST-Client: {0!s} XOR p1 - {1:#034X}'.format(random,p1r))
            encp1 = self.CallEncrypt(variables['TK'],createMSB(p1r,16))
            p2r  = encp1 ^ p2
            if self.debug:
                self.driver.LogWrite('TST-Client: Encrypt({0!s} XOR p1) XOR p2 - {1:#034X}'.format(random,p2r))
            variables[confirm] = self.CallEncrypt(variables['TK'],createMSB(p2r,16))
            if self.debug:
                self.driver.LogWrite('TST-Client: {0!s} - {1:#034X}'.format(confirm, variables[confirm]))
        except Exception,msg:
            self.driver.LogWrite(msg)
            return False
        return True
        
        
    def PairingRequest(self, variables, encSettings):
        params = {
            'IoCapability':encSettings['IO'],
            'OobDataFlag':encSettings['OOB'],
            'Bonding':encSettings['BondingFlags'] == 1,
            'Mitm':encSettings['MITM'] == 1,
            'MaxEncKeySize':encSettings['encKeySize'],
            'MKeyDistrBitmap':encSettings['MKeyDistr'],
            'SKeyDistrBitmap':encSettings['SKeyDistr'],
        }
        variables['pairingReq'] = protocol.Smp.SmpPairingRequest(**params)
        if self.debug:
            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(variables['pairingReq']))
        self.smpCmds.driver.Write(variables['pairingReq'])
        return True
    
    ## False means that it does not need more input, True means that it need more input before it can continue
    ## The index corresponds to the IO Capability
    pairingAlgorithms = (
        (False, False,  'RespKey',   False,  'RespKey'),
        (False, False,  'RespKey',   False,  'RespKey'),
        ('InitKey',  'InitKey',   'Both',   False,  'InitKey'),
        (False, False,  False,  False,  False),
        ('InitKey',  'InitKey',   'RespKey',   False,  'InitKey'),
    )
    
    def PairingResponse(self, packet, variables):
        variables['pairingResp'] = packet
        variables['encKeySize'] = min([packet.MaxEncKeySize, variables['encKeySize']])
        
        if variables['pairingResp'].OobDataFlag and variables['pairingReq'].OobDataFlag:
            self.PairingPaused = 'OobKey'
            return True
        
        if variables['pairingResp'].Mitm or variables['pairingReq'].Mitm:
            if (variables['pairingResp'].IoCapability < len(self.pairingAlgorithms) and variables['pairingReq'].IoCapability < len(self.pairingAlgorithms)):
                self.PairingPaused = self.pairingAlgorithms[variables['pairingResp'].IoCapability][variables['pairingReq'].IoCapability]
                if self.PairingPaused:
                    return True
            
        self.CreateConfirm(variables, True)
        packet = protocol.Smp.SmpPairingConfirm(ConfirmValue = variables['MConfirm'])
        if self.debug:
            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
        self.smpCmds.driver.Write(packet)
        return True

    def PairingConfirm(self, packet, variables):
        variables['SConfirmRec'] = packet.ConfirmValue
        packet = protocol.Smp.SmpPairingRandom(RandomValue = variables['MRandom'])
        if self.debug:
            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
        self.smpCmds.driver.Write(packet)
        return True

    def PairingRandom(self, packet, variables):
        variables['SRandom'] = packet.RandomValue
        self.CreateConfirm(variables, False)
        if variables['SConfirm'] != variables['SConfirmRec']:
            packet = protocol.Smp.SmpPairingFailed(protocol.Smp.errorCodes['Confirm Value Failed'])
            if self.debug:
                self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
            self.smpCmds.driver.Write(packet)
            self.PairingComplete = True
            return False
        else:
            rMarked = int("{0:016X}{1:016X}".format(variables['SRandom'] & (2**64-1),variables['MRandom'] & (2**64-1)),16)
            variables['STK'] = self.CallEncrypt(variables['TK'],createMSB(rMarked,16))
            variables['STK'] = createMSB(variables['STK'],16)
            variables['STK'] = [0x00]*(16-variables['encKeySize']) + variables['STK'][16-variables['encKeySize']:]
            if self.debug:
                self.driver.LogWrite('TST-Client: Encrypting the link with STK')
            retval = self.StartEncryption(variables['STK'],0,[0]*8)
            self.CheckPassCriteria(variables)
            return retval
    
    def PairingFailed(self, packet, variables):
        variables['ReceivedPairingFailed'] = packet

    def EncryptionInformation(self, packet, variables):
        variables['LTK'] = packet.LtkLtlEndArray[::-1]

    def MasterIdentification(self, packet, variables):
        variables['keysExchanged'] |= 0b001
        variables['EDIV'] = packet.EdivValue
        variables['RAND'] = packet.RandLtlEndArray[::-1]
        self.CheckPassCriteria(variables)

    def IdentityInformation(self, packet, variables):
        variables['IRK'] = packet.IrkLtlEndArray[::-1]
    
    def IdentityAddressInformation(self, packet, variables):
        variables['keysExchanged'] |= 0b010
        variables['AddrType'] = packet.AddrType
        variables['AddrLtlEndArray'] = packet.AddrLtlEndArray[::-1]
        self.CheckPassCriteria(variables)
    
    def SigningInformation(self, packet, variables):
        variables['keysExchanged'] |= 0b100
        variables['CSRK'] = packet.SrkLtlEndArray[::-1]
        self.CheckPassCriteria(variables)
        
    def EncryptedLink(self, packet, variables):
        self.CheckPassCriteria(variables)
    
    def CheckPassCriteria(self, variables):
        if variables['keysExchanged'] == (variables['pairingReq'].SKeyDistrBitmap & variables['pairingResp'].SKeyDistrBitmap):
            self.PairingComplete = True
        if self.PairingComplete:
            keysToExchange = (variables['pairingReq'].MKeyDistrBitmap & variables['pairingResp'].MKeyDistrBitmap)
            if keysToExchange & 0b001:
                for packet in self.distpackets:
                    if isinstance(packet,protocol.Smp.SmpEncryptionInformation):
                        if self.debug:
                            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
                        self.smpCmds.driver.Write(packet)
                        break
                for packet in self.distpackets:
                    if isinstance(packet,protocol.Smp.SmpMasterIdentification):
                        if self.debug:
                            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
                        self.smpCmds.driver.Write(packet)
                        break
            if keysToExchange & 0b010:
                for packet in self.distpackets:
                    if isinstance(packet,protocol.Smp.SmpIdentityInformation):
                        if self.debug:
                            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
                        self.smpCmds.driver.Write(packet)
                        break
                for packet in self.distpackets:
                    if isinstance(packet,protocol.Smp.SmpIdentityAddressInformation):
                        if self.debug:
                            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
                        self.smpCmds.driver.Write(packet)
                        break
            if keysToExchange & 0b100:
                for packet in self.distpackets:
                    if isinstance(packet,protocol.Smp.SmpSigningInformation):
                        if self.debug:
                            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
                        self.smpCmds.driver.Write(packet)
                        break
    
    def RunPairingSequence(self, *args, **encSettings):
        self.PairingComplete = False
        self.PairingPaused = False
        
        variables = {
            'MRandom':None,
            'MConfirm':None,
            'SConfirm':None,
            'encKeySize':16,
            'keysExchanged':0,
            'STK':None,
            'LTK':None,
            'TK':[0x00]*16,
            'ReceivedPairingFailed':None
        }
        self.distpackets = []
        for key,value in self.defaultEncSettings.iteritems():
            if key not in encSettings:
                encSettings[key] = value
        if 'DistPackets' in encSettings:
            self.distpackets = encSettings['DistPackets']
        if 'TK' in encSettings:
            variables['TK'] = encSettings['TK']

        variables['encKeySize'] = encSettings['encKeySize']

        if isinstance(encSettings['MKeyDistr'],list):
            tmp = 0x00
            if 'EncKey' in encSettings['MKeyDistr']:
                tmp |= 0b001
            if 'IdKey' in encSettings['MKeyDistr']:
                tmp |= 0b010
            if 'Sign' in encSettings['MKeyDistr']:
                tmp |= 0b100
            encSettings['MKeyDistr'] = tmp
        if isinstance(encSettings['SKeyDistr'],list):
            tmp = 0x00
            if 'EncKey' in encSettings['SKeyDistr']:
                tmp |= 0b001
            if 'IdKey' in encSettings['SKeyDistr']:
                tmp |= 0b010
            if 'Sign' in encSettings['SKeyDistr']:
                tmp |= 0b100
            encSettings['SKeyDistr'] = tmp
        
        retval = self.PairingInitial(variables)
        if retval == False:
            return False
        
        retval = self.PairingRequest(variables, encSettings)
        if retval == False:
            return False
        
        return self.PairingStateMachine(variables)
    
    def ContinuePairingSequence(self, variables):
        self.PairingPaused = False
        self.CreateConfirm(variables, True)
        packet = protocol.Smp.SmpPairingConfirm(ConfirmValue = variables['MConfirm'])
        if self.debug:
            self.driver.LogWrite('TST-Client: Sending {0!r} - {0!s}'.format(packet))
        self.smpCmds.driver.Write(packet)
        
        self.PairingStateMachine(variables)
        return variables
    
    def PairingStateMachine(self, variables):
        responses = {
            protocol.Smp.SmpPairingResponse:self.PairingResponse,
            protocol.Smp.SmpPairingConfirm:self.PairingConfirm,
            protocol.Smp.SmpPairingRandom:self.PairingRandom,
            protocol.Smp.SmpPairingFailed:self.PairingFailed,
            protocol.Smp.SmpEncryptionInformation:self.EncryptionInformation,
            protocol.Smp.SmpMasterIdentification:self.MasterIdentification,
            protocol.Smp.SmpIdentityInformation:self.IdentityInformation,
            protocol.Smp.SmpIdentityAddressInformation:self.IdentityAddressInformation,
            protocol.Smp.SmpSigningInformation:self.SigningInformation,
            HciEncryptionChangeEvent:self.EncryptedLink,
            HciEncryptionKeyRefreshCompleteEvent:self.EncryptedLink,
        }
        
        retval = None
        timeout = 30
        startTime = datetime.now()
        while self.connInfo != None and not isinstance(retval, protocol.Smp.SmpPairingFailed) and not self.PairingComplete and not self.PairingPaused:
            timedOut = datetime.now() - startTime > timedelta(0, timeout)
            if timedOut:
                return False
            retval = self.driver.WaitFor(Common.ANY_PACKET, T=30, NO_PRINT = True)
            if retval.__class__ in responses:
                if self.debug:
                    self.driver.LogWrite('TST-Client: Received {0!r} - {0!s}'.format(retval))
                responses[retval.__class__](retval, variables)
            else:
                self.driver.LogWrite('TST-Client: Discarded {0!r} - {0!s}'.format(retval))
        
        return variables
        