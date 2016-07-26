import traceback
import sys
from testerScriptCommon import *
from modules import packetqueue
import protocol.Att

class Attribute(object):
    def __init__(self, handle, value, uuid):
        self.handle = handle & 0xFFFF
        self.value = [int(el) for el in value]
        self.uuid = uuid

class GattService(Attribute):
    def __init__(self, start, end, uuid):
        self.startHandle        = start & 0xFFFF
        self.endHandle          = end & 0xFFFF
        self.uuid               = uuid
        self.includes           = []
        self.characteristics    = []

    def __str__(self):
        return "{0!r} - Serice UUID:{0.uuid:04X} Start Handle:{0.startHandle:04X}".format(self)

    def addIncludedService(self, include):
        if isinstance(include,GattService):
            self.includes.append(include)

    def addCharacteristic(self, characteristic):
        if not isinstance(characteristic, GattCharacteristic):
            raise Exception("Not a characterisic declaration")
        elif self.charExists(characteristic):
            raise Exception("Characteristic allready added")
        else:
            self.characteristics.append(characteristic)

    def charExists(self, characteristic):
        if not isinstance(characteristic, GattCharacteristic):
            raise Exception("Not a characterisic declaration")
        else:
            for charDec in self.characteristics:
                if charDec.startHandle == characteristic.startHandle:
                    return True
        return False

    def getCharacteristics(self, uuid):
        return [characteristic for characteristic in self.characteristics if characteristic.uuid == uuid]

class GattPrimaryService(GattService):
    pass

class GattSecondaryService(GattService):
    pass

class GattInclude(Attribute):
    def __init__(self, start, end, uuid):
        self.startHandle        = start & 0xFFFF
        self.endHandle          = end & 0xFFFF
        self.uuid               = uuid

class GattCharacteristic(Attribute):
    def __init__(self, start, properties, handle, uuid, value = []):
        self.startHandle        = start & 0xFFFF
        self.endHandle          = None
        self.properties         = properties & 0xFF
        self.handle             = handle & 0xFFFF
        self.uuid               = uuid
        self.value              = value
        self.descriptors       = []

    def __str__(self):
        return "{0!r} - UUID:{0.uuid:04X} Start Handle:{0.startHandle:04X}".format(self)

    def setValue(self, value):
        self.value              = value

    def addDescriptor(self, descriptor):
        if isinstance(descriptor, GattDescriptor):
            self.descriptors.append(descriptor)
        else:
            raise Exception("Not a characteristic descriptor")

    def getDescriptor(self, uuid):
        for descriptor in self.descriptors:
            if descriptor.uuid == uuid:
                return descriptor

class GattDescriptor(Attribute):
    def __init__(self, handle, uuid, value = []):
        self.handle             = handle & 0xFFFF
        self.uuid               = uuid
        self.value              = value

class Gatt:
    CHARACTERISTICPROPERTIES = {
        'Broadcast':0x01,
        'Read':0x02,
        'Write Without Response':0x04,
        'Write':0x08,
        'Notify':0x10,
        'Indicate':0x20,
        'Authenticated Signed Write':0x40,
        'Extended Properties':0x80,
    }
    CHARACTERISTICPROPERTIES_LOOKUP = dict([value,key] for key,value in CHARACTERISTICPROPERTIES.iteritems())

    def __init__(self, tester, attCmds, *args, **argv):
        self.attCmds = attCmds
        self.tester = tester
        self.tst = packetqueue.PacketQueue(LOG_FUNCTION = self.tester.LogWrite)
        self.tst.LogWrite = self.tester.LogWrite

    def packetQueueHandler(f):
        def f_closure(self, *args, **argv):
            self.tst.emptyQueue()
            removeFromQueue = False
            if not self.tst.AddToQueue in self.tester.packetRecipients:
                self.tester.AddPacketRecipients(self.tst.AddToQueue)
                removeFromQueue = True
            f_pointer = f(self, *args, **argv)
            if removeFromQueue:
                self.tester.RemovePacketRecipient(self.tst.AddToQueue)
            return f_pointer

        return f_closure

    def _defaultLogWrite(self, *args, **argv):
        pass

    @packetQueueHandler
    def DiscoverAllPrimaryServices(self, startHandle = 0x0001, endHandle = 0xFFFF):
        self.tst.LogWrite("GATT: Discovering all Primary Services")
        type = Uuid.assignedNumbers['PRIMARY_SERVICE']
        services = []

        while True and (startHandle & 0xFFFF) != 0x0000:
            self.tst.LogWrite("GATT: Sending Read By Group Type Request, start handle 0x%04X" % startHandle)
            self.attCmds.SendReadByGroupTypeRequest(startHdl = startHandle, endHdl = endHandle, type = type)
            retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
            self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
            if retval != None:
                if isinstance(retval, protocol.Att.AttReadByGroupTypeResponse):
                    self.tst.LogWrite("GATT: Received Read By Group Type Response")
                    for service in retval.Groups:
                        service_uuid = int("".join("%02X" % el for el in service.value[::-1]),16)
                        self.tst.LogWrite("GATT: Found Service 0x%04X" % service_uuid)
                        services.append(GattPrimaryService(service.foundHandle, service.endFoundHandle,service_uuid))
                    startHandle = retval.Groups[-1].endFoundHandle+1
                elif isinstance(retval, protocol.Att.AttErrorResponse):
                    self.tst.LogWrite("GATT: Received Error Response on handle 0x%04X reason 0x%02X" % (retval.Handle, retval.ErrorCode))
                    break
                else:
                    break
            else:
                break

        return services

    @packetQueueHandler
    def DiscoverPrimaryService(self, type, startHandle = 0x0001, endHandle   = 0xFFFF):
        self.tst.LogWrite("GATT: Discovering all Primary Services of type 0x%04X" % (type))
        if isinstance(type, list):
            type_pkt = type
        elif isinstance(type, int) or isinstance(type, long):
            if type > 0xFFFF:
                type_pkt = [int("%02X" % (type >> 8*i & 0xFF),16) for i in range(16)]
            else:
                type_pkt = [type & 0xFF, (type >> 8) & 0xFF]
        uuid = Uuid.assignedNumbers['PRIMARY_SERVICE']
        services = []
        while True and (startHandle & 0xFFFF) != 0x0000:
            self.tst.LogWrite("GATT: Sending Find By Type Value Request, start handle 0x%04X" % startHandle)
            self.attCmds.SendFindByTypeValueRequest(uuid, type_pkt, startHdl = startHandle, endHdl = endHandle)
            retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
            self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
            if retval != None:
                if isinstance(retval, protocol.Att.AttFindByTypeValueResponse):
                    self.tst.LogWrite("GATT: Received Find By Type Value Response")
                    for service in retval.FoundHandles:
                        self.tst.LogWrite("GATT: Found Service handle start 0x%04X and end 0x%04X" % (service.foundHandle,service.endFoundHandle))
                        services.append(GattPrimaryService(service.foundHandle,service.endFoundHandle,type))
                    startHandle = retval.FoundHandles[-1].endFoundHandle+1
                elif isinstance(retval, protocol.Att.AttErrorResponse):
                    self.tst.LogWrite("GATT: Received Error Response on handle 0x%04X reason 0x%02X" % (retval.Handle, retval.ErrorCode))
                    break
                else:
                    break
            else:
                break
        return services


    @packetQueueHandler
    def FindIncludedServices(self, services):
        if isinstance(services, GattService):
            services = [services]
        elif isinstance(services, list):
            pass
        else:
            return False

        for service in services:
            self.tst.LogWrite("GATT: Finding the Included Services of Service 0x%04X" % service.uuid)
            uuid = Uuid.assignedNumbers['INCLUDE']
            startHandle = service.startHandle+1
            endHandle = service.endHandle
            while True and (startHandle & 0xFFFF) != 0x0000:
                self.tst.LogWrite("GATT: Sending Read By Type Request, start handle 0x%04X" % startHandle)
                self.attCmds.SendReadByTypeRequest(uuid, startHdl = startHandle, endHdl = endHandle)
                retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
                self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
                if retval != None:
                    if isinstance(retval, protocol.Att.AttReadByTypeResponse):
                        self.tst.LogWrite("GATT: Received Read By Type Response")
                        for include in retval.Attributes:
                            incStartHandle = include.value[0] | (include.value[1] << 8)
                            incEndHandle = include.value[2] | (include.value[3] << 8)
                            if len(include.value) > 4:
                                serviceUuid = include.value[4] | (include.value[5] << 8)
                            else:
                                serviceUuid = 0x0000
                            service.addIncludedService(GattService(incStartHandle,incEndHandle,serviceUuid))
                        startHandle = retval.Attributes[-1].handle+1
                    elif isinstance(retval, protocol.Att.AttErrorResponse):
                        self.tst.LogWrite("GATT: Received Error Response on handle 0x%04X reason 0x%02X" % (retval.Handle, retval.ErrorCode))
                        break
                    else:
                        break
                else:
                    break
        return services

    @packetQueueHandler
    def DiscoverAllCharacteristics(self, services):
        if isinstance(services, GattService):
            services = [services]
        elif isinstance(services, list):
            pass
        else:
            return False
        for service in services:
            self.tst.LogWrite("GATT: Discovering all Characteristics of service 0x%04X" % service.uuid)
            uuid = Uuid.assignedNumbers['CHARACTERISTIC']
            startHandle = service.startHandle+1
            endHandle = service.endHandle
            while True and (startHandle & 0xFFFF) != 0x0000:
                self.tst.LogWrite("GATT: Sending Read By Type Request, start handle 0x%04X" % startHandle)
                self.attCmds.SendReadByTypeRequest(uuid, startHdl = startHandle, endHdl = endHandle)
                retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
                self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
                if retval != None:
                    if isinstance(retval, protocol.Att.AttReadByTypeResponse):
                        self.tst.LogWrite("GATT: Received Read By Type Response")
                        for characteristic in retval.Attributes:
                            properties = characteristic.value[0]
                            handle = characteristic.value[1] | characteristic.value[2] << 8
                            charUuid = int("".join("%02X" % el for el in characteristic.value[-1:2:-1]),16)
                            service.addCharacteristic(GattCharacteristic(characteristic.handle,properties,handle,charUuid))
                        startHandle = retval.Attributes[-1].handle+1
                    elif isinstance(retval, protocol.Att.AttErrorResponse):
                        self.tst.LogWrite("GATT: Received Error Response on handle 0x%04X reason 0x%02X" % (retval.Handle, retval.ErrorCode))
                        break
                    else:
                        break
                else:
                    break
            nextEnd = endHandle
            for characteristic in service.characteristics[::-1]:
                characteristic.endHandle = nextEnd
                nextEnd = characteristic.startHandle - 1

            self.DiscoverAllCharacteristics(service.includes)
            for include in service.includes:
                for incCharacteristic in include.characteristics:
                    try:
                        service.addCharacteristic(incCharacteristic)
                    except Exception,msg:
                        raise Exception(msg)
        return services

    @packetQueueHandler
    def DiscoverCharacteristic(self, services, type):
        if isinstance(services, GattService):
            services = [services]
        elif isinstance(services, list):
            pass
        else:
            return False
        characteristics = None
        for service in services:
            self.tst.LogWrite("GATT: Discovering all Characteristics of type 0x%04X in service 0x%04X" % (type,service.uuid))
            uuid = Uuid.assignedNumbers['CHARACTERISTIC']
            startHandle = service.startHandle+1
            endHandle = service.endHandle
            while True and (startHandle & 0xFFFF) != 0x0000:
                self.tst.LogWrite("GATT: Sending Read By Type Request, start handle 0x%04X" % startHandle)
                self.attCmds.SendReadByTypeRequest(uuid, startHdl = startHandle, endHdl = endHandle)
                retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
                self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
                if retval != None:
                    if isinstance(retval, protocol.Att.AttReadByTypeResponse):
                        self.tst.LogWrite("GATT: Received Find By Type Value Response")
                        for characteristic in retval.Attributes:
                            properties = characteristic.value[0]
                            handle = characteristic.value[1] | characteristic.value[2] << 8
                            charUuid = int("".join("%02X" % el for el in characteristic.value[-1:2:-1]),16)
                            if characteristics != None:
                                characteristics.endHandle = characteristic.handle-1
                                break
                            if charUuid == type:
                                self.tst.LogWrite("GATT: Found the expected characteristic")
                                characteristics = GattCharacteristic(characteristic.handle,properties,handle,charUuid)
                        startHandle = retval.Attributes[-1].handle+1
                        if characteristics != None and characteristics.endHandle != None:
                            break
                    elif isinstance(retval, protocol.Att.AttErrorResponse):
                        self.tst.LogWrite("GATT: Received Error Response on handle 0x%04X reason 0x%02X" % (retval.Handle, retval.ErrorCode))
                        if characteristics != None:
                            characteristics.endHandle = endHandle
                        break
                    else:
                        break
                else:
                    break
            return characteristics

    @packetQueueHandler
    def DiscoverAllCharacteristicDescriptors(self, characteristic):
        startHandle = characteristic.handle + 1
        endHandle = characteristic.endHandle
        self.tst.LogWrite("GATT: Discovering all the Descriptors of Characteristic 0x%04X, start handle 0x%04X, end handle 0x%04X" % (characteristic.uuid, startHandle, endHandle))
        while True and (startHandle & 0xFFFF) != 0x0000:
            self.tst.LogWrite("GATT: Sending Find Information Request, start handle 0x%04X" % startHandle)
            self.attCmds.SendFindInformationRequest(startHdl = startHandle, endHdl = endHandle)
            retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
            self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
            if retval != None:
                if isinstance(retval, protocol.Att.AttFindInformationResponse):
                    self.tst.LogWrite("GATT: Received Find Information Response")
                    for descriptor in retval.Attributes:
                        handle = descriptor.handle
                        uuid = descriptor.uuid
                        self.tst.LogWrite("GATT: Found Descriptor 0x%04X on handle 0x%04X" % (uuid, handle))
                        characteristic.addDescriptor(GattDescriptor(handle,uuid))
                    startHandle = retval.Attributes[-1].handle+1
                    if startHandle > endHandle:
                        break
                elif isinstance(retval, protocol.Att.AttErrorResponse):
                    self.tst.LogWrite("GATT: Received Error Response on handle 0x%04X reason 0x%02X" % (retval.Handle, retval.ErrorCode))
                    break
                else:
                    break
            else:
                break

        return characteristic

    @packetQueueHandler
    def ReadCharacteristicValue(self, characteristic):
        if not isinstance(characteristic, GattCharacteristic):
            return

        self.tst.LogWrite("GATT: Sending Read Request on Characteristic Value uuid 0x%04X on handle=%04X" % (characteristic.uuid,characteristic.handle))
        if not characteristic.properties & self.CHARACTERISTICPROPERTIES['Read']:
            self.tst.LogWrite("GATT: Expecting a Error Response with Read Not Permitted")

        self.attCmds.SendReadRequest(characteristic.handle)
        retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
        self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
        if retval != None:
            if isinstance(retval, protocol.Att.AttReadResponse):
                self.tst.LogWrite("GATT: Received Read Response")
                characteristic.value = retval.Attributes.value
                return characteristic
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                return retval
            else:
                self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % (retval,retval))
        return False

    @packetQueueHandler
    def ReadLongCharacteristicValue(self, characteristic, offset = 0):
        if not isinstance(characteristic, GattCharacteristic):
            return
        try:
            while True:
                self.tst.LogWrite("GATT: Sending Read Blob Request on Characteristic Value uuid 0x{0.uuid:04X} on handle 0x{0.handle:04X} with offset {1}".format(characteristic,offset))
                if not characteristic.properties & self.CHARACTERISTICPROPERTIES['Read']:
                    self.tst.LogWrite("GATT: Expecting a Error Response with Read Not Permitted")

                self.attCmds.SendReadBlobRequest(characteristic.handle, offset)
                retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT = True)
                self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
                if isinstance(retval, protocol.Att.AttReadBlobResponse):
                    self.tst.LogWrite("GATT: Received Read Blob Response")
                    characteristic.value[offset:] = retval.Attributes.value
                    length = len(retval.Attributes.value)
                    if length == protocol.Att.ATT_MTU-1:
                        offset += length
                    else:
                        return characteristic
                elif isinstance(retval, protocol.Att.AttErrorResponse):
                    self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                    return retval
                elif retval != None:
                    self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % (retval,retval))
                else:
                    return False
        except Exception,msg:
            self.tst.LogWrite(msg)
            self.tst.LogWrite(traceback.extract_tb(sys.exc_info()[2]))

    @packetQueueHandler
    def ReadUsingCharacteristicUuid(self, uuid, startHdl = 0x0001, endHdl = 0xFFFF):
        self.tst.LogWrite("GATT: Sending Read By Type Request on UUID 0x%04X" % uuid)
        attributes = []
        self.attCmds.SendReadByTypeRequest(uuid, startHdl=startHdl, endHdl=endHdl)
        retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
        self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
        if retval != None:
            if isinstance(retval, protocol.Att.AttReadByTypeResponse):
                self.tst.LogWrite("GATT: Received Read By Type Response")
                for characteristic in retval.Attributes:
                    attributes.append(Attribute(characteristic.handle,characteristic.value,uuid))
                startHandle = retval.Attributes[-1].handle+1
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                self.tst.LogWrite("GATT: Received Error Response on handle 0x%04X reason 0x%02X" % (retval.Handle, retval.ErrorCode))
                return retval
        return attributes


    @packetQueueHandler
    def ReadCharacteristicDescriptor(self, descriptor):
        if not isinstance(descriptor,GattDescriptor):
            self.tst.LogWrite("GATT: Not a valid Descriptor")
            return False

        self.tst.LogWrite("GATT: Sending Read Request on Characteristic descriptor 0x%04X on handle=%04X" % (descriptor.uuid,descriptor.handle))
        self.attCmds.SendReadRequest(descriptor.handle)
        retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
        self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
        if retval != None:
            if isinstance (retval, protocol.Att.AttReadResponse):
                self.tst.LogWrite("GATT: Received Read Response")
                descriptor.value = retval.Attributes.value
                return descriptor
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                return retval
            else:
                self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % (retval,retval))
        return False

    @packetQueueHandler
    def ReadLongCharacteristicDescriptor(self, descriptor, offset = 0):
        if not isinstance(descriptor,GattDescriptor):
            self.tst.LogWrite("GATT: Not a valid Descriptor")
            return False

        while True:
            self.tst.LogWrite("GATT: Sending Read Blob Request on Characteristic Descriptor uuid 0x{0.uuid:04X} on handle 0x{0.handle:04X} with offset {1}".format(descriptor,offset))

            self.attCmds.SendReadBlobRequest(descriptor.handle, offset)
            retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT = True)
            self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
            if isinstance(retval, protocol.Att.AttReadBlobResponse):
                self.tst.LogWrite("GATT: Received Read Blob Response")
                descriptor.value[offset:] = retval.Attributes.value
                length = len(retval.Attributes.value)
                if length == protocol.Att.ATT_MTU-1:
                    offset += len(retval.Attributes.value)
                else:
                    return descriptor
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                return retval
            elif retval != None:
                self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % (retval,retval))
            else:
                return False

    @packetQueueHandler
    def WriteCharacteristicValue(self, characteristic, value = []):
        if not isinstance(characteristic, GattCharacteristic):
            return False

        self.tst.LogWrite("GATT: Sending Write Request on Characteristic Value uuid 0x%04X on handle=%04X" % (characteristic.uuid,characteristic.handle))
        if not characteristic.properties & self.CHARACTERISTICPROPERTIES['Write']:
            self.tst.LogWrite("GATT: Expecting a Error Response with Write Not Permitted")

        self.attCmds.SendWriteRequest(characteristic.handle,value)
        retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
        self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
        if retval != None:
            if isinstance (retval, protocol.Att.AttWriteResponse):
                self.tst.LogWrite("GATT: Received Write Response")
                characteristic.value = value
                return characteristic
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                return retval
            else:
                self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % (retval,retval))
        return False

    def WriteWithoutResponse(self, characteristic, value = []):
        if not isinstance(characteristic, GattCharacteristic):
            return False

        self.tst.LogWrite("GATT: Sending Write Command on Characteristic Value uuid 0x%04X on handle=%04X" % (characteristic.uuid,characteristic.handle))
        self.attCmds.SendWriteCommand(characteristic.handle,value)
        return True

    @packetQueueHandler
    def WriteCharacteristicDescriptor(self, descriptor, value = []):
        if not isinstance(descriptor,GattDescriptor):
            return False

        self.tst.LogWrite("GATT: Sending Write Request on Characteristic descriptor 0x%04X on handle=%04X" % (descriptor.uuid,descriptor.handle))
        self.attCmds.SendWriteRequest(descriptor.handle,value)
        retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
        self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))
        if retval != None:
            if isinstance (retval, protocol.Att.AttWriteResponse):
                self.tst.LogWrite("GATT: Att Write Response")
                descriptor.value = value
                return descriptor
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                return retval
            else:
                self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % (retval,retval))
        return False

    @packetQueueHandler
    def WriteLongCharacteristicValues(self, characteristic, value, timeout=30):
        if not isinstance(characteristic, GattCharacteristic):
            return False

        self.tst.LogWrite("GATT: Sending Write Long Request on Characteristic Value uuid 0x%04X on handle=%04X" % (characteristic.uuid,characteristic.handle))
        if not characteristic.properties & self.CHARACTERISTICPROPERTIES['Write']:
            self.tst.LogWrite("GATT: Expecting a Error Response with Write Not Permitted")
            return False

        if not value:
            return False

        offset = 0
        end_index = 0
        header_length = 5
        max_length = protocol.Att.ATT_MTU - header_length
        value_length = len(value)
        retval = 0

        while offset < value_length:
            end_index = offset + max_length
            value_part = value[offset:end_index]

            self.attCmds.SendPrepareWriteRequest(characteristic.handle, value_part, offset)
            retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=timeout, NO_PRINT=True)

            if retval is None:
                self.tst.LogWrite("GATT: Error, no response received for PrepareWriteRequest.")
                return False

            self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))

            if isinstance(retval, protocol.Att.AttPrepareWriteResponse):
                self.tst.LogWrite("GATT: Received Prepare Write Response")
                #TODO: Do response value checking?
                offset = end_index
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                if retval.ErrorCode == self.attCmds.PREPARE_QUEUE_FULL:
                    self.tst.LogWrite("GATT: Received Queue Full response")
                    execute_write_retval = self._ExecuteWriteRequest(True)

                    if isinstance(execute_write_retval, protocol.Att.AttExecuteWriteResponse):
                        continue
                    elif isinstance(execute_write_retval, protocol.Att.AttErrorResponse):
                        return execute_write_retval
                    else:
                        self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % 
                                          (execute_write_retval, execute_write_retval))
                        return False
                else:
                    self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                    return retval
            else:
                self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s" % (retval, retval))

        execute_write_retval = self._ExecuteWriteRequest(True)

        if isinstance(execute_write_retval, protocol.Att.AttExecuteWriteResponse):
            characteristic.value = value
            return characteristic
        elif isinstance(execute_write_retval, protocol.Att.AttErrorResponse):
            return execute_write_retval
        else:
            return False

    def _ExecuteWriteRequest(self, writePending):
        if writePending:
            self.attCmds.SendExecuteWriteRequest(0x01)
        else:
            self.attCmds.SendExecuteWriteRequest(0x00)

        retval = self.tst.WaitFor(SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE, T=30, NO_PRINT=True)
        self.tst.LogWrite("GATT: Received {0!r} - {0!s}".format(retval))

        if retval:
            if isinstance(retval, protocol.Att.AttExecuteWriteResponse):
                self.tst.LogWrite("GATT: Received Execute Write Response")
                return retval
            elif isinstance(retval, protocol.Att.AttErrorResponse):
                self.tst.LogWrite("GATT: Received Error Response, error code 0x%02X" % retval.ErrorCode)
                return retval
            else:
                self.tst.LogWrite("GATT: Received an unexpected ATT packet: %r: %s", retval, retval)
        return False

    def FindDescriptorOfService(self, serUuid, charUuid, descUuid):
        services = self.DiscoverPrimaryService(serUuid)
        self.SpiderIncludes(services)
        services = self.DiscoverAllCharacteristics(services)
        for characteristic in services[-1].characteristics:
            if characteristic.uuid == charUuid:
                characteristic = self.DiscoverAllCharacteristicDescriptors(characteristic)
                return characteristic.getDescriptor(descUuid)

    def SpiderIncludes(self, services, count = 0):
        self.FindIncludedServices(services)
        if count < 5:
            count += 1
            for service in services:
                self.SpiderIncludes(service.includes, count = count)

    def OpenRemotePipe(self, serUuid, charUuid, type, handle = 0x0000):
        # startHandle = 0x0001
        cliConfHandle = 0x0000
        retval = None
        cccdDescriptor = None

        self.tst.LogWrite("OpenRemotePipe()")

        if handle == 0x0000:
            cccdDescriptor = self.FindDescriptorOfService(serUuid,charUuid, Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'])

            if cccdDescriptor == None:
                return False

        else:
            cccdDescriptor = GattDescriptor(handle, Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'])
        if (type == 0):
            data = [0x00, 0x00]
        elif (type == 1):
            data = [0x01, 0x00]
        elif (type == 2):
            data = [0x02, 0x00]
        elif (type == 3):
            data = [0x03, 0x00]

        else:
            self.tst.LogWrite("GATT: Pipe Type Not Valid")
            return False

        retval = self.WriteCharacteristicDescriptor(cccdDescriptor, data)

        return retval != False


    def ReadCCCD(self, serUuid, charUuid, handle = 0x0000):
        startHandle = 0x0001
        cliConfHandle = 0x0000
        retval = None

        self.tst.LogWrite("ReadCCCD()")

        if handle == 0x0000:
            cccdDescriptor = self.FindDescriptorOfService(serUuid,charUuid, Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'])

            if cccdDescriptor == None:
                return False

        else:
            cccdDescriptor = GattDescriptor(handle, Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'])

        cccdDescriptor = self.ReadCharacteristicDescriptor(cccdDescriptor)

        if cccdDescriptor != False:
            return cccdDescriptor.value[0] | (cccdDescriptor.value[1] << 8)
        return False

    def FindCCCDHandle(self, serUuid, charUuid):
        startHandle = 0x0001
        cliConfHandle = 0x0000
        retval = None
        sHdl = None
        eHdl = None

        self.tst.LogWrite("OpenRemotePipe with handle=%04X" % handle)

        cccdDescriptor = self.FindDescriptorOfService(serUuid,charUuid, Uuid.assignedNumbers['CHARACTERISTIC_CLT_CFG'])

        if cccdDescriptor == None:
            return False

        ccHandle = cccdDescriptor.handle

        return ccHandle
