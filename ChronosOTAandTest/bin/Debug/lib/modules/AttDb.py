#!/usr/bin/python
from modules.common import Utilities

class AssignedNumbers(object):
    Uuid = {
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
    
    GroupingUuids = [
        Uuid['PRIMARY_SERVICE'],
        Uuid['SECONDARY_SERVICE'],
    ]

class Attribute(object):
    def __init__(self, **argv):
        if 'prev' in argv:
            self._prev      = argv['prev']
        else:
            self._prev      = None
        if 'next' in argv:
            self._next      = argv['next']
        else:
            self._next      = None
        
        if 'handle' in argv and argv['handle'] != None:
            self.handle     = argv['handle']
        elif self._prev != None:
            self.handle     = self._prev.handle + 1
        else:
            self.handle     = 1
        
        if 'uuid' in argv and argv['uuid'] != None:
            self.uuid       = argv['uuid']
        elif not self.uuid:
            raise Exception,"Attribute does not have an UUID"
        
        if 'value' in argv and argv['value'] != None:
            self.value      = [int(el) for el in argv['value']]
        else:
            self.value      = []
        self.permissions    = []
    
    def build(self):
        pass
    
    def increaseNextHandle(self):
        if self._next != None:
            if self._next.handle <= self.handle:
                self._next.handle = self.handle + 1
            self._next.increaseNextHandle()
    
    def __getitem__(self,key):
        if isinstance(key,slice) or isinstance(key,list) or isinstance(key,tuple):
            retval = []
            if isinstance(key,slice):
                handles = range(key.start+1,key.stop+1,[1,key.step][key.step != None])
            else:
                handles = key
                
            for attr in self:
                if attr.handle in handles:
                    retval.append(attr)
                if len(handles) > 0 and attr.handle > handles[-1]:
                    break
            return retval
        else:
            for attr in self:
                if attr.handle == key and isinstance(key,int):
                    return attr
    
    def __add__(self, other):
        if isinstance(other,Attribute):
            other._prev = self
            if self._next != None:
                other.last()._next = self._next
            self._next = other
            self.increaseNextHandle()
        else:
            raise Exception,"It's not a member of Attribute Class"
        return self
    
    def __iadd__(self, other):
        if isinstance(other,Attribute):
            other._prev = self
            if self._next != None:
                other.last()._next = self._next
            self._next = other
            self.increaseNextHandle()
        else:
            raise Exception,"It's not a member of Attribute Class"
        return self
    
    def __iter__(self):
        tmp = self.start()
        while tmp != None:
            yield tmp
            tmp = tmp._next
    
    def last(self):
        tmp = self
        while tmp._next != None:
            tmp = tmp._next
        return tmp
    
    def start(self):
        tmp = self
        while tmp._prev != None:
            tmp = self._prev
        return tmp
    
class GattServer(object):
    def __init__(self):
        self.attributes = None
    
    def addService(service):
        if isinstance(service, GattService):
            if self.attributes != None:
                self.attributes += service
            else:
                self.attributes = service
        else:
            raise Exception,"It's not a member of Service Class"
    
            
class GattService(Attribute):
    def __init__(self, uuid,*args,**argv):
        super(GattService,self).__init__(*args,**argv)
        # Attribute.__init__(self)
        self.ServiceUuid        = uuid
        self.Includes           = []
        self.Characteristics    = []
        self.build()
    
    def __getattribute__(self,name):
        if name in ['value']:
            self.build()
        return super(GattService,self).__getattribute__(name)
        
    def build(self):
        self.value = Utilities.littleEndian(self.ServiceUuid)
    
    def addIncludedService(self, include):
        if isinstance(include,GattService):
            include = GattInclude(include)
            if len(self.Includes) > 0:
                self.Includes[-1] += include
            else:
                self += include
            self.Includes.append(include)
        else:
            raise Exception("Not a memer of GattService")
    
    def addCharacteristic(self, characteristic):
        if isinstance(characteristic, GattCharacteristicDefinition):
            if len(self.Characteristics) > 0:
                self.Characteristics[-1] += characteristic
            elif len(self.Includes) > 0:
                self.Includes[-1] += characteristic
            else:
                self += characteristic
            self.Characteristics.append(characteristic)
        else:
            raise Exception("Not a characterisic declaration")
    
    def getCharacteristics(self, uuid):
        return (characteristic for characteristic in self.Characteristics if characteristic.uuid == uuid)

    def getEndGroupHandle(self):
        for attr in self:
            if isinstance(attr,GattService):
                return attr.handle-1
        else:
            return 0xFFFF
    
class GattPrimaryService(GattService):
    uuid = AssignedNumbers.Uuid['PRIMARY_SERVICE']

class GattSecondaryService(GattService):
    uuid = AssignedNumbers.Uuid['SECONDARY_SERVICE']

class GattInclude(Attribute):
    uuid = AssignedNumbers.Uuid['INCLUDE']
    def __init__(self, service,*args,**argv):
        super(GattInclude,self).__init__(*args,**argv)
        self.Service = service
        self.build()
        
    def build(self):
        self.value += Utilities.littleEndian(self.Service.handle,byte=2)
        self.value += Utilities.littleEndian(self.Service.getEndGroupHandle,byte=2)

class GattCharacteristicDefinition(Attribute):
    uuid = AssignedNumbers.Uuid['CHARACTERISTIC']
    
    def __init__(self, properties, uuid, handle = None, value = []):
        super(GattCharacteristicDefinition,self).__init__()
        self.CharProperties     = properties & 0xFF
        self.CharValue          = GattCharacteristicValue(uuid=uuid,value=value,handle=handle)
        self += self.CharValue
        self.CharDescriptors    = []
        self.build()
    
    def __getattribute__(self,name):
        if name in ['value']:
            self.build()
        return super(GattCharacteristicDefinition,self).__getattribute__(name)
        
    def build(self):
        self.value = [self.CharProperties] + Utilities.littleEndian(self.CharValue.handle) + Utilities.littleEndian(self.CharValue.uuid)
    
    def setValue(self, value):
        self.CharValue.value    = value
    
    def addDescriptor(self, descriptor):
        if isinstance(descriptor, GattDescriptor):
            if len(self.CharDescriptors) == 0:
                self.CharValue += descriptor
            else:
                self.CharDescriptors[-1] += descriptor
            self.CharDescriptors.append(descriptor)
        else:
            raise Exception("Not a characteristic descriptor")
    
    def getDescriptor(self, uuid):
        for descriptor in self.descriptors:
            if descriptor.uuid == uuid:
                return descriptor

class GattCharacteristicValue(Attribute):
    pass
                
class GattCaracteristicDescriptor(Attribute):
    pass
        
class GattCharacteristicExtendedProperties(GattCaracteristicDescriptor):
    uuid = AssignedNumbers.Uuid['CHARACTERISTIC_EXT_PROP']
    
class GattCharacteristicUserDescription(GattCaracteristicDescriptor):
    uuid = AssignedNumbers.Uuid['CHARACTERISTIC_USER_DESC']
    
class GattCharacteristicClientConfiguration(GattCaracteristicDescriptor):
    uuid = AssignedNumbers.Uuid['CHARACTERISTIC_CLT_CFG']
    
class GattCharacteristicServerConfiguration(GattCaracteristicDescriptor):
    uuid = AssignedNumbers.Uuid['CHARACTERISTIC_SVR_CFG']
    
class GattCharacteristicPresentationFormat(GattCaracteristicDescriptor):
    uuid = AssignedNumbers.Uuid['CHARACTERISTIC_FORMAT']
    
class GattCharacteristicAggregateFormat(GattCaracteristicDescriptor):
    uuid = AssignedNumbers.Uuid['CHARACTERISTIC_AGG_FMT']
    
if __name__ == "__main__":
    test = GattPrimaryService(0x2A00)
    test2 = GattSecondaryService(0x2A01)
    test3 = test + test2
    test += GattPrimaryService(0x2A03,handle=15)
    # test += GattSecondaryService(0x2A01)
    print ""
    print test3[2:15]
    print ""
    for val in test3:
        print val.__class__,hex(val.handle),hex(val.uuid),val.value
