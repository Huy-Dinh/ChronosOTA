from testerScriptCommon import *
import Queue, sys, traceback, threading
import protocol.Att
import protocol.Smp
from modules.common import Utilities
from math import ceil,log

MaxPacketLength = protocol.Att.ATT_MTU

class testerScriptServer(threading.Thread):
    def __init__(self, tester, attCmds, dataBase = None, logFunc = None, deferWriteRequest = False, **args):
        self.logoutput = True
        self.sendResponse = True
        self.deferWriteRequest = deferWriteRequest
        self.attCmds = attCmds
        if logFunc != None:
            self.LogWrite = logFunc
        else:
            self.LogWrite = tester.LogWrite

        try:
            threading.Thread.__init__(self)
            self.daemon = True
            self.tst = tester
            self.inQueue = Queue.Queue(40)
            self.ePacket = threading.Event()
            self.attDb = AttDb(attCmds = attCmds, dataBase=dataBase, deferWriteRequest = self.deferWriteRequest)
            self.attDb.SetAttributeUpdatedCallback(self.defaultServerAttributeUpdatedHandler)
            self.attDb.SetExecuteWriteCallback(self.defaultServerExecuteWriteHandler)
        except Exception,msg:
            self.LogWrite("SERVER: " + str(traceback.extract_tb(sys.exc_info()[2])))
            self.LogWrite("SERVER: Exception: " + str(msg))

    def __del__(self):
        self.stop()

    def setLogOutput(self, bool):
        self.logoutput = bool

    def setResponseStatus(self, value):
        self.sendResponse = (value == True)

    def resetDatabase(self):
        self.attDb.Database = self.attDb.initDatabase

    def defaultServerAttributeUpdatedHandler(self, handle, value, packetType):
        self.LogWrite("Warning: No ServerUpdatedCallback has been set")

    def defaultServerExecuteWriteHandler(self, handleValueList, numberOfDeferred):
        self.LogWrite("Warning: No ServerExecuteWriteCallback has been set")

    #Callback function must have signature (handle, value) or (self, handle, value)
    def SetServerUpdatedCallback(self, callbackFunction):
        self.attDb.SetAttributeUpdatedCallback(callbackFunction)

    def SetServerExecuteWriteCallback(self, callbackFunction):
        self.attDb.SetExecuteWriteCallback(callbackFunction)

    def UpdateServerDb(self, database):
        self.attDb.Database = database

    def GetServerDb(self):
        return self.attDb.Database

    def ReceivePacket(self, packet):
        try:
            if (packet.EventCode == SerialCommTypeMapping.ATT_COMMAND_EVENTCODE
                or packet.EventCode == SerialCommTypeMapping.SMP_REQUEST_EVENTCODE
                or packet.EventCode == HciComm.HCI_LL_CONNECTION_CREATED_EVENT
                or packet.EventCode == HciComm.HCI_LL_CONNECTION_TERMINATION_EVENT
                or packet.EventCode == HciComm.HCI_ENCRYPTION_KEY_REFRESH_COMPLETE_EVENT
                or packet.EventCode == HciComm.HCI_ENCRYPTION_CHANGE_EVENT):
                self.inQueue.put(packet, True, Common.PACKET_QUEUE_TIMEOUT)
                self.ePacket.set()
        except Exception,msg:
            self.LogWrite("SERVER-RECEIVED: " + str(traceback.extract_tb(sys.exc_info()[2])))
            self.LogWrite("SERVER-RECEIVED: Exception: " + str(msg))

    def run(self):
        self.tst.AddPacketRecipients(self.ReceivePacket)
        self.running = True
        self.LogWrite("SERVER: Server has started")
        while self.running:
            try:
                if self.inQueue.empty():
                    self.ePacket.wait(1)
                if self.inQueue.empty():
                    if self.ePacket.isSet():
                        self.ePacket.clear()
                    continue
                packet = self.inQueue.get(True, Common.PACKET_QUEUE_TIMEOUT)
                self.ePacket.clear()
                if self.logoutput:
                    self.LogWrite("SERVER: Received packet %r - %s" % (packet,packet))
                if self.sendResponse:
                    retval = self.attDb.processPacket(packet)
                    if isinstance(retval,protocol.Att.AttResponse):
                        self.attCmds.driver.Write(retval)
                        if self.logoutput:
                            self.LogWrite("SERVER: Returned packet %r - %s" % (retval,retval))
                    elif self.logoutput and (retval is not None):
                        self.LogWrite("SERVER: %s" % retval)
            except Exception,msg:
                self.LogWrite("SERVER: " + str(traceback.extract_tb(sys.exc_info()[2])))
                self.LogWrite("SERVER: Exception: " + str(msg))
                self.running = False
        self.tst.RemovePacketRecipient(self.ReceivePacket)
        self.LogWrite("SERVER: Server has stopped")

    def stop(self):
        if not self.running:
            return

        self.LogWrite("SERVER: Stopping server")
        self.running = False



class AttDb:
    PERM_AUTHORIZATION      = 0x01
    PERM_AUTHENTICATION     = 0x02
    PERM_READ               = 0x04
    PERM_WRITE              = 0x08

    prepareWriteRequestQueue = {}

    def __init__(self, dataBase = None, attCmds = None, deferWriteRequest = False):
        self.Authenticated = False
        self.deferWriteRequest = deferWriteRequest
        self.attributeUpdatedCallback = None
        self.executeWriteCallback = None
        if dataBase != None:
            self.initDatabase = dataBase
        else:
            self.initDatabase = {
                # Service: GAP
                0x0001:{'UUID':Uuid.assignedNumbers['PRIMARY_SERVICE'],'R_PERM':'yes','W_PERM':'no','DATA':[Uuid.assignedNumbers['GAP'] & 0xFF, (Uuid.assignedNumbers['GAP'] >> 8) & 0xFF]},
                #   Char GAP.1: Device Name
                0x0002:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x02,0x03,0x00,Uuid.assignedNumbers['DEVICE_NAME'] & 0xFF, (Uuid.assignedNumbers['DEVICE_NAME'] >> 8) & 0xFF]},
                0x0003:{'UUID':Uuid.assignedNumbers['DEVICE_NAME'],'R_PERM':'yes','W_PERM':'no','DATA':[ord(el) for el in "testAttrClient"]},
                #   Char GAP.2: Appearance
                0x0004:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x02,0x05,0x00,Uuid.assignedNumbers['APPEARANCE'] & 0xFF, (Uuid.assignedNumbers['APPEARANCE'] >> 8) & 0xFF]},
                0x0005:{'UUID':Uuid.assignedNumbers['APPEARANCE'],'R_PERM':'yes','W_PERM':'no','DATA':[0x86, 0x23]},
                # Service: GATT
                0x0006:{'UUID':Uuid.assignedNumbers['PRIMARY_SERVICE'],'R_PERM':'yes','W_PERM':'no','DATA':[Uuid.assignedNumbers['GATT'] & 0xFF, (Uuid.assignedNumbers['GATT'] >> 8) & 0xFF]},
                # Service: #1, UUID = 0x9000
                0x0010:{'UUID':Uuid.assignedNumbers['PRIMARY_SERVICE'],'R_PERM':'yes','W_PERM':'no','DATA':[0x00, 0x90]},
                #   Char S1.1: UUID = 0x9025
                0x0012:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x06,0x15,0x00,0x25,0x90]},
                0x0015:{'UUID':0x9025,'R_PERM':'yes','W_PERM':'yes','MAX_LEN':2,'DATA':[0x5D,0x69]},
                #   Char S1.2: UUID = 0x9027
                0x0020:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x06,0x31,0x00,0x27,0x90]},
                0x0031:{'UUID':0x9027,'R_PERM':'yes','W_PERM':'aut','MAX_LEN':2,'DATA':[0x11,0xB1]},
                #     Desc S1.2.1: Char Ext Properties
                0x0035:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_EXT_PROP'],'R_PERM':'yes','W_PERM':'yes','DATA':[0x02,0x00]},
                #   Char with 128 bit uuid
                0x004A:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x0A,0x4B,0x00,0x28,0x90,0x01,0x02,0x01,0x02,0xB1,0x0F,0xA1,0x02,0x71,0x02,0x28,0x90,0x01,0x0E]},
                0x004B:{'UUID':0x0E010902827102A10FB1020102019028,'R_PERM':'yes','W_PERM':'yes','MAX_LEN':20,'DATA':[ord(el) for el in "IOP Broadcaster"]},
                #   Char S1.3: UUID = 0x9028
                0x0050:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x1A,0x54,0x00,0x28,0x90]},
                0x0054:{'UUID':0x9028,'R_PERM':'yes','W_PERM':'yes','MAX_LEN':20,'DATA':[ord(el) for el in "IOP Broadcaster"]},
                0x0055:{'UUID':0x0E012902027102A10FB10201020102AC,'R_PERM':'yes','W_PERM':'no','MAX_LEN':20,'DATA':[ord(el) for el in "128Bit UUID"]},
                0x0056:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'],'R_PERM':'yes','W_PERM':'yes','DATA':[0x00, 0x00]},
                0x0057:{'UUID':0x0E012902027102A10FB10201020102AC,'R_PERM':'yes','W_PERM':'no','MAX_LEN':20,'DATA':[ord(el) for el in "128Bit UUID"]},
                #   Char S1.4: UUID = 0x9030
                0x0060:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x04,0x63,0x00,0x30,0x90]},
                0x0063:{'UUID':0x9030,'R_PERM':'no','W_PERM':'yes','MAX_LEN':20,'DATA':[]},
                #   Char S1.5: UUID = 0x9029
                0x0090:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x02,0xA3,0x00,0x29,0x90]},
                0x00A3:{'UUID':0x9029,'R_PERM':'yes','W_PERM':'no','MAX_LEN':20,'DATA':[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]},
                0x00A4:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_EXT_PROP'],'R_PERM':'yes','W_PERM':'no','DATA':[0x02,0x00]},
                #   Char S1.6: UUID = 0xA029
                0x0103:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x20,0x15,0x01,0x29,0xA0]},
                0x0115:{'UUID':0xA029,'R_PERM':'no','W_PERM':'no','MAX_LEN':20,'DATA':[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]},
                #     Desc S1.6.1: Char User Description
                0x0127:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_USER_DESC'],'R_PERM':'yes','W_PERM':'yes','DATA':[ord(el) for el in "I Am a Happy Char"]},
                #     Bunch of descriptors to pad the DB: force client to issue multiple Find Info Req
                0x0128:{'UUID':0xC0C0,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0129:{'UUID':0xC0C1,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x012A:{'UUID':0xC0C2,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x012B:{'UUID':0xC0C3,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x012C:{'UUID':0xC0C4,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x012D:{'UUID':0xC0C5,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x012E:{'UUID':0xC0C6,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x012F:{'UUID':0xC0C7,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0130:{'UUID':0xC0C8,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0131:{'UUID':0xC0C9,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0132:{'UUID':0xC0CA,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0133:{'UUID':0xC0CB,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0144:{'UUID':0xC0CC,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0145:{'UUID':0xC0CD,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0146:{'UUID':0xC0CE,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0147:{'UUID':0xC0CF,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                #     Desc S1.6.x: Client Char Config
                0x0157:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'],'R_PERM':'yes','W_PERM':'yes','DATA':[0x00, 0x00]},
                0x0158:{'UUID':0xC0D0,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x0159:{'UUID':0xC0D1,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x015A:{'UUID':0xC0D2,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x015B:{'UUID':0xC0D3,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                0x015C:{'UUID':0xC0D4,'R_PERM':'yes','W_PERM':'yes','DATA':[0x1, 0x2]},
                # Secondary service 0x1234
                0x0160:{'UUID':Uuid.assignedNumbers['SECONDARY_SERVICE'],'R_PERM':'yes','W_PERM':'no','DATA':[0x34, 0x12]},
                #   Char S2.1: UUID = 0x9026
                0x0162:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x06,0x15,0x02,0x26,0x90]},
                0x0165:{'UUID':0x9026,'R_PERM':'yes','W_PERM':'yes','MAX_LEN':2,'DATA':[0x5D,0x69]},
                0x0169:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'],'R_PERM':'yes','W_PERM':'yes','DATA':[0x00, 0x00]},
                # Service #2, UUID = 0x9001
                0x0210:{'UUID':Uuid.assignedNumbers['PRIMARY_SERVICE'],'R_PERM':'yes','W_PERM':'no','DATA':[0x01, 0x90]},
                #   Char S2.1: UUID = 0x9026
                0x0212:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x06,0x15,0x02,0x26,0x90]},
                0x0215:{'UUID':0x9026,'R_PERM':'yes','W_PERM':'yes','MAX_LEN':2,'DATA':[0x5D,0x69]},
                0x0219:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'],'R_PERM':'yes','W_PERM':'yes','DATA':[0x00, 0x00]},
                # Service #3, UUID = 0xA000
                0x0301:{'UUID':Uuid.assignedNumbers['PRIMARY_SERVICE'],'R_PERM':'yes','W_PERM':'no','DATA':[0x00, 0xA0]},
                #   Char S3.1: UUID = 0xA001
                0x0311:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x56,0x12,0x03,0x01,0xA0]},
                0x0312:{'UUID':0xA001,'R_PERM':'aut','W_PERM':'aut','MAX_LEN':2,'DATA':[0x5D,0x69]},
                #     Desc S3.1.1: UUID = 0xBEEF
                0x0315:{'UUID':0xBEEF,'R_PERM':'yes','W_PERM':'yes','DATA':[0xDE, 0xAD, 0xBE, 0xEF]},
                0x0319:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'],'R_PERM':'yes','W_PERM':'yes','DATA':[0x00, 0x00]},
                #   Char S3.2: UUID = 0xB001
                0x0321:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC'],'R_PERM':'yes','W_PERM':'no','DATA':[0x18,0x22,0x03,0x01,0xB0]},
                0x0322:{'UUID':0xB001,'R_PERM':'no','W_PERM':'yes','MAX_LEN':2,'DATA':[0xAA, 0xBB, 0xCC, 0xDD]},
                0x0325:{'UUID':Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'],'R_PERM':'yes','W_PERM':'yes','DATA':[0x00, 0x00]},
            }
        self.Database = self.initDatabase

    #Callback function must have signature functionname(handle, value) or (self, handle, value)
    def SetAttributeUpdatedCallback(self, callbackFunction):
        self.attributeUpdatedCallback = callbackFunction

    def SetExecuteWriteCallback(self, callbackFunction):
        self.executeWriteCallback = callbackFunction

    def SetAuthenticationLevel(self, authentication):
        self.Authenticated = authentication

    def FindInformation(self, start, end):
        if start > end or start == 0x00 or end == 0x00:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['FIND_INFORMATION_REQUEST']['Opcode'],
                start,
                protocol.Att.errorCode['INVALID_HANDLE'])

        Attributes = []
        packet = []; tmpPacket = []
        handleInRange = list(set(self.Database).intersection(range(start,end+1)))
        handleInRange.sort()
        for handle in handleInRange:
            dbUuid = self.Database[handle]['UUID']
            tmpPacket = packet + Utilities.littleEndian(handle) + Utilities.littleEndian(dbUuid)
            if len(tmpPacket) > protocol.Att.ATT_MTU - 2:
                break
            Attributes.append(protocol.Att.Attribute(handle,self.Database[handle]['UUID']))
            packet = tmpPacket

        if len(packet) == 0:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['FIND_INFORMATION_REQUEST']['Opcode'],
                start,
                protocol.Att.errorCode['ATTRIBUTE_NOT_FOUND'])
        else:
            return protocol.Att.AttFindInformationResponse(
                Attributes,
                [protocol.Att.format['TYPE_16'],protocol.Att.format['TYPE_128']][len(packet) == 18])

    def FindByType(self, start, end, uuid, value):
        if start > end or start == 0x0 or end == 0x00:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['FIND_BY_TYPE_VALUE_REQUEST']['Opcode'],
                start,
                protocol.Att.errorCode['INVALID_HANDLE'])

        uuidFound = False
        groupingType = False
        startHandle = None
        if uuid in Uuid.groupingUuids:
            groupingType = True

        packet = []
        AttributeFound = []
        handleInRange = list(set(self.Database).intersection(range(start,end+1)))
        handleInRange.sort()
        for handle in handleInRange:
            tmpPacket = []
            dbUuid = self.Database[handle]['UUID']
            if (not self.compareUuid(uuid,dbUuid)) and (groupingType and dbUuid not in Uuid.groupingUuids):
                continue
            if self.compareUuid(uuid,dbUuid) and self.compareValues(value,self.Database[handle]['DATA'])[0]:
                if uuidFound:
                    tmpPacket = packet + Utilities.littleEndian(startHandle) + Utilities.littleEndian(handle-1)
                    found = protocol.Att.AttributeFound(startHandle, handle-1)
                uuidFound = True
                startHandle = handle
            elif uuidFound:
                tmpPacket = packet + Utilities.littleEndian(startHandle) + Utilities.littleEndian(handle-1)
                found = protocol.Att.AttributeFound(startHandle, handle-1)

                uuidFound = False
                startHandle = None

            if len(tmpPacket) > protocol.Att.ATT_MTU-1:
                break
            elif tmpPacket != []:
                AttributeFound.append(found)
                packet = tmpPacket

        if uuidFound:
            tmpPacket = packet + Utilities.littleEndian(startHandle) + Utilities.littleEndian(0xFFFF)
            if len(tmpPacket) <= protocol.Att.ATT_MTU-1:
                packet = tmpPacket
                AttributeFound.append(protocol.Att.AttributeFound(startHandle, 0xFFFF))

        if len(packet) == 0:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['FIND_BY_TYPE_VALUE_REQUEST']['Opcode'],
                start,
                protocol.Att.errorCode['ATTRIBUTE_NOT_FOUND'])
        else:
            return protocol.Att.AttFindByTypeValueResponse(AttributeFound)

    def ReadByGroupType(self, startHandle, endHandle, uuid):
        if startHandle > endHandle or startHandle == 0x00 or endHandle == 0x00:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['READ_BY_GROUP_TYPE_REQUEST']['Opcode'],
                startHandle,
                protocol.Att.errorCode['INVALID_HANDLE'])
        elif uuid not in Uuid.groupingUuids:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['READ_BY_GROUP_TYPE_REQUEST']['Opcode'],
                startHandle,
                protocol.Att.errorCode['UNSUPPORTED_GROUP_TYPE'])

        HeaderLength = 4 #Starthandle + endhandle

        totalLength = 0
        handleInRange = list(set(self.Database).intersection(range(startHandle,endHandle+1)))
        handleInRange.sort()
        Attributes = []
        totalLength = 0
        attribute = None

        for dbHandle in handleInRange:
            if self.compareUuid(self.Database[dbHandle]['UUID'],uuid):
                if attribute != None:
                    #We have found end of the group and can add the attribute
                    Attributes.append(attribute)
                    #clear attribute to mark end of group
                    attribute = None

                handle = dbHandle
                entry = self.Database[handle]
                perm = self.checkPermissions(handle,self.PERM_READ)
                if perm != None:
                    if totalLength == 0:
                        return protocol.Att.AttErrorResponse(
                            protocol.Att.packets['READ_BY_GROUP_TYPE_REQUEST']['Opcode'],
                            handle,perm)
                    else:
                        break
                totalLength += (len(entry['DATA'][:MaxPacketLength]) + HeaderLength)

                if totalLength > MaxPacketLength - 1:
                    break

                attribute = protocol.Att.Attribute(
                                handle,
                                None,
                                self.Database[handle]['DATA'][:MaxPacketLength],
                                endHandle = handle #Add end handle here in case it is the last handle
                            )
            else:
                if attribute != None:
                    #Update attribute endhandle,
                    attribute.endHandle = dbHandle

        if attribute != None:
            #special case for end of db, add last attribute
            Attributes.append(attribute)

        if totalLength == 0:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['READ_BY_GROUP_TYPE_REQUEST']['Opcode'],
                startHandle,
                protocol.Att.errorCode['ATTRIBUTE_NOT_FOUND'])
        length = len(Attributes[-1].value) + HeaderLength
        return protocol.Att.AttReadByGroupTypeResponse(Length=length, Attributes=Attributes)

    def ReadByType(self, startHandle, endHandle, uuid):
        if startHandle > endHandle or startHandle == 0x0 or endHandle == 0x00:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['READ_BY_TYPE_REQUEST']['Opcode'],
                startHandle,
                protocol.Att.errorCode['INVALID_HANDLE'])

        packet = []
        tmpPacket = []
        length = 0
        handleInRange = list(set(self.Database).intersection(range(startHandle,endHandle+1)))
        handleInRange.sort()
        serviceFound = False
        Attributes = []
        for dbHandle in handleInRange:
            if self.compareUuid(self.Database[dbHandle]['UUID'],uuid):
                handle = dbHandle
                entry = self.Database[handle]
                perm = self.checkPermissions(handle,self.PERM_READ)
                if perm != None:
                    if length == 0:
                        return protocol.Att.AttErrorResponse(
                            protocol.Att.packets['READ_BY_TYPE_REQUEST']['Opcode'],
                            handle,perm)
                    else:
                        break
                if length == 0:
                    length = len(entry['DATA'][:protocol.Att.ATT_MTU-4])+2
                    packet = [length]
                elif len(entry['DATA']) + 2 != length:
                    break
                tmpPacket = [handle & 0xFF, handle >> 8 & 0xFF] + entry['DATA'][:protocol.Att.ATT_MTU-4]
                if len(packet+tmpPacket) > protocol.Att.ATT_MTU-1:
                    break
                Attributes.append(protocol.Att.Attribute(handle,None,self.Database[handle]['DATA'][:protocol.Att.ATT_MTU-4]))
                packet += tmpPacket
        if len(packet) == 0:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['READ_BY_TYPE_REQUEST']['Opcode'],
                startHandle,
                protocol.Att.errorCode['ATTRIBUTE_NOT_FOUND'])
        return protocol.Att.AttReadByTypeResponse(Length=len(Attributes[-1].value)+2,Attributes=Attributes)

    def ReadBlobRequest(self, handle, offset):
        if handle not in self.Database:
            return protocol.Att.AttErrorResponse(protocol.Att.packets['READ_BLOB_REQUEST']['Opcode'],
                                                 handle, protocol.Att.errorCode['INVALID_HANDLE'])

        entry = self.Database[handle]

        ##ReadBlobRequest deferral is not supported for now, requires a separate event, TODO.
        #if entry.has_key('DEFER'):
        #    return "ReadRequest deferred"

        perm = self.checkPermissions(handle, self.PERM_READ)

        if perm != None:
            return protocol.Att.AttErrorResponse(protocol.Att.packets['READ_BLOB_REQUEST']['Opcode'],
                                                 handle, perm)

        attributeData = self.Database[handle]['DATA']

        if len(attributeData) < offset:
            return protocol.Att.AttErrorResponse(protocol.Att.packets['READ_BLOB_REQUEST']['Opcode'],
                                                 handle, protocol.Att.errorCode['INVALID_OFFSET'])

        offsetMaxIndex = offset + protocol.Att.ATT_MTU-1
        readData = attributeData[offset:offsetMaxIndex]
        return protocol.Att.AttReadBlobResponse(protocol.Att.Attribute(None, None, readData))

    def ReadRequest(self, handle):
        if handle in self.Database:
            entry = self.Database[handle]

            if entry.has_key('DEFER'):
                return "ReadRequest deferred"

            perm = self.checkPermissions(handle,self.PERM_READ)
            if perm != None:
                return protocol.Att.AttErrorResponse(
                    protocol.Att.packets['READ_REQUEST']['Opcode'],
                    handle,perm)
            else:
                return protocol.Att.AttReadResponse(protocol.Att.Attribute(None,None,self.Database[handle]['DATA'][:protocol.Att.ATT_MTU-1]))
        else:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['READ_REQUEST']['Opcode'],
                handle,
                protocol.Att.errorCode['INVALID_HANDLE'])

    def PrepareWriteRequest(self, handle, offset, data):
        if handle not in self.Database:
            return protocol.Att.AttErrorResponse(protocol.Att.packets['PREPARE_WRITE_REQUEST']['Opcode'],
                                                 handle, protocol.Att.errorCode['INVALID_HANDLE'])

        entry = self.Database[handle]

        perm =  self.checkPermissions(handle,self.PERM_WRITE)

        if perm != None:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['PREPARE_WRITE_REQUEST']['Opcode'],
                handle,perm)

        if not self.prepareWriteRequestQueue.has_key(handle):
            self.prepareWriteRequestQueue[handle] = []

        self.prepareWriteRequestQueue[handle].append((offset, data))

        return protocol.Att.AttPrepareWriteResponse(protocol.Att.Attribute(handle,None,data), offset)

    def ExecuteWriteRequest(self, flags):
        writeQueue = self.prepareWriteRequestQueue
        self.prepareWriteRequestQueue = {}
        temporaryValues = {}
        numberOfDeferred = 0

        if flags == 0x00:
            #Canceling all prepared writes is already done
            return protocol.Att.AttExecuteWriteResponse()

        for handle in writeQueue.keys():
            entry = self.Database[handle]

            perm =  self.checkPermissions(handle,self.PERM_WRITE)

            if perm != None:
               return protocol.Att.AttErrorResponse(
                    protocol.Att.packets['EXECUTE_WRITE_REQUEST']['Opcode'],
                    handle,perm)

            if handle not in temporaryValues:
                currentData = []
                if 'DATA' in entry:
                    currentData = entry['DATA']

                temporaryValues[handle] = currentData

            value = temporaryValues[handle]

            for offset, data in writeQueue[handle]:
                # if Variable length of attribute
                if offset > len(value):
                    return protocol.Att.AttErrorResponse(protocol.Att.packets['EXECUTE_WRITE_REQUEST']['Opcode'],
                                                         handle, protocol.Att.errorCode['INVALID_OFFSET'])

                if ('MAX_LEN' in entry and (offset + len(data)) > entry['MAX_LEN']):
                    return protocol.Att.AttErrorResponse(protocol.Att.packets['EXECUTE_WRITE_REQUEST']['Opcode'],
                                                         handle,
                                                         protocol.Att.errorCode['INVALID_ATTRIBUTE_VALUE_LEN'])

                value = value[:offset]
                value.extend(data)

                # elif Fixed length of attribute
                # update data, do not truncate

            temporaryValues[handle] = value

            if entry.has_key('DEFER'):
                numberOfDeferred += 1
        #endforloop

        self.executeWriteCallback(temporaryValues, numberOfDeferred)

        if numberOfDeferred > 0:
            return "WriteRequest deferred"
        else:
            for handle in temporaryValues.keys():
                self.Database[handle]['DATA'] = temporaryValues[handle]
            return protocol.Att.AttExecuteWriteResponse()

    def WriteRequest(self, handle, data, packetType):
        if handle not in self.Database:
            return protocol.Att.AttErrorResponse(
                protocol.Att.packets['WRITE_REQUEST']['Opcode'],
                handle,
                protocol.Att.errorCode['INVALID_HANDLE'])

        entry = self.Database[handle]

        perm =  self.checkPermissions(handle,self.PERM_WRITE)
        if perm != None:
            return protocol.Att.AttErrorResponse(protocol.Att.packets['WRITE_REQUEST']['Opcode'],
                                                 handle,perm)

        if ('MAX_LEN' in entry and len(data) > entry['MAX_LEN']):
            return protocol.Att.AttErrorResponse(protocol.Att.packets['WRITE_REQUEST']['Opcode'],
                                                 handle,
                                                 protocol.Att.errorCode['INVALID_ATTRIBUTE_VALUE_LEN'])

        self.attributeUpdatedCallback(handle, data, packetType)

        if entry.has_key('DEFER'):
            return "WriteRequest deferred"
        else:
            self.Database[handle]['DATA'] = data
            if packetType == protocol.Att.AttWriteRequest:
                return protocol.Att.AttWriteResponse()

    def processPacket(self, packet):
        if isinstance(packet,protocol.Att.AttRequest):
            if packet.Opcode == None:
                return protocol.Att.AttErrorResponse(packet.Content[0],0x0000,protocol.Att.errorCode['REQUEST_NOT_SUPPORTED'])
            elif isinstance(packet,protocol.Att.AttExchangeMtuRequest):
                return protocol.Att.AttExchangeMtuResponse(23)
            elif isinstance(packet,protocol.Att.AttFindInformationRequest):
                response = self.FindInformation(packet.StartHdl,packet.EndHdl)
                return response
            elif isinstance(packet, protocol.Att.AttFindByTypeValueRequest):
                response = self.FindByType(packet.StartHdl,packet.EndHdl,packet.AttributeType,packet.AttributeValue)
                return response
            elif isinstance(packet,protocol.Att.AttReadByTypeRequest):
                response = self.ReadByType(packet.StartHdl,packet.EndHdl,packet.UUID)
                return response
            elif isinstance(packet,protocol.Att.AttReadByGroupTypeRequest):
                response = self.ReadByGroupType(packet.StartingHandle, packet.EndingHandle, packet.Type)
                return response
            elif isinstance(packet,protocol.Att.AttReadBlobRequest):
                response = self.ReadBlobRequest(packet.Handle, packet.Offset)
                return response
            elif isinstance(packet,protocol.Att.AttReadRequest):
                response = self.ReadRequest(packet.Handle)
                return response
            elif isinstance(packet, protocol.Att.AttPrepareWriteRequest):
                response = self.PrepareWriteRequest(packet.Attributes.handle,packet.Offset,packet.Attributes.value)
                return response
            elif isinstance(packet, protocol.Att.AttExecuteWriteRequest):
                response = self.ExecuteWriteRequest(packet.Flags)
                return response
            elif isinstance(packet, protocol.Att.AttWriteRequest):
                packetType = protocol.Att.AttWriteRequest
                response = self.WriteRequest(packet.Attributes.handle,packet.Attributes.value, packetType)
                return response
            elif packet.Opcode in [0x0C,0x0E,0x14,0x16,0x18]:
                return protocol.Att.AttErrorResponse(packet.Opcode,0x0000,protocol.Att.errorCode['REQUEST_NOT_SUPPORTED'])
            else:
                return protocol.Att.AttErrorResponse(packet.Opcode,0x0000,protocol.Att.errorCode['INVALID_PDU'])

        elif isinstance(packet, protocol.Att.AttCommand):
            if isinstance(packet, protocol.Att.AttWriteCommand):
                packetType = protocol.Att.AttWriteCommand
                response = self.WriteRequest(packet.Attributes.handle,packet.Attributes.value, packetType)
                if isinstance(response,protocol.Att.AttErrorResponse):
                    return "Write Command on handle %04X, failed" % packet.Attributes.handle
                else:
                    return "Write Command on handle %04X, succeeded" % packet.Attributes.handle

        elif isinstance(packet,protocol.Smp.SmpPkt):
            return "Received SMP Packet"
        elif isinstance(packet,HciEvent):
            if isinstance(packet,HciLLConnectionCreatedEvent):
                self.prepareWriteRequestQueue = {}
            elif isinstance(packet,HciLLConnectionTerminationEvent):
                self.SetAuthenticationLevel(False)
                return "Received Link Loss"
            elif isinstance(packet,HciEncryptionChangeEvent):
                self.SetAuthenticationLevel(True)
                return "Received Encryption Change Event"
            elif isinstance(packet,HciEncryptionKeyRefreshCompleteEvent):
                self.SetAuthenticationLevel(True)
                return "Received Encryption Key Refresh Event"

    def compareValues(self, newValue, dataValue):
        isEqual = True
        message = ""
        if len(newValue) != len(dataValue):
            return False,"Length does not match"
        for i in range(len(newValue)):
            if newValue[i] != dataValue[i]:
                message = "FAIL - Wrong data"
                isEqual = False
                break
        return isEqual,message

    def compareUuid(self, uuid1, uuid2):
        if uuid1 < 0xFFFF:
            uuid1 = protocol.Att.BT_BASE_UUID | (uuid1 << 96)
        if uuid2 < 0xFFFF:
            uuid2 = protocol.Att.BT_BASE_UUID | (uuid2 << 96)

        return uuid1 == uuid2

    def checkPermissions(self,dbHandle,permissionType):
        if False:
            return protocol.Att.errorCode['INSUFFICIENT_AUTHORIZATION']
        if False:
            return protocol.Att.errorCode['INSUFFICIENT_AUTHENTICATION']

        if permissionType & self.PERM_READ:
            if self.Database[dbHandle]['R_PERM'] == 'aut' and not self.Authenticated:
                return protocol.Att.errorCode['INSUFFICIENT_AUTHENTICATION']
            elif self.Database[dbHandle]['R_PERM'] == 'no':
                return protocol.Att.errorCode['READ_NOT_PERMITTED']
        elif permissionType & self.PERM_WRITE:
            if self.Database[dbHandle]['W_PERM'] == 'aut' and not self.Authenticated:
                return protocol.Att.errorCode['INSUFFICIENT_AUTHENTICATION']
            elif self.Database[dbHandle]['W_PERM'] == 'no':
                return protocol.Att.errorCode['WRITE_NOT_PERMITTED']
        else:
            return None

