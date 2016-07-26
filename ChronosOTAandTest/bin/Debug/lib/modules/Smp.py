
from math import ceil
from modules.common import ByteArray
try:
    import sys
    #sys.path.append("C:\Python26\Lib") #Required to access the threading module located in the python std lib
    from Crypto.Cipher import AES

except Exception,msg:
    print msg
    
const_Zero  = ByteArray('B',(0x00,)*16)
const_Rb    = ByteArray('B',(0x00,)*15+(0x87,))
const_Bsize = 16

class _toolbox(object):
    @staticmethod
    def _aes128(key, message):
        if isinstance(key,list) or isinstance(key,tuple):
            key = ByteArray('B',key)
        engine = AES.new(key.tostring(),AES.MODE_CBC)
        enc = ByteArray('B')
        if isinstance(message,list) or isinstance(message,tuple):
            message = ByteArray('B',message)
        enc.fromstring(engine.encrypt(message.tostring()))
        return enc

class PrivateAddress(object):
    
    def __init__(self, encrypt = None):
        self.encrypt = _toolbox._aes128
        if encrypt != None:
            self.encrypt = encrypt
    
    def callEncrypt(self, irk, message):
        M = self.encrypt(irk, message)
        if isinstance(M,int) or isinstance(M,long):
            M = ByteArray('B',[(M >> ((15-i)*8)) & 0xFF for i in range(16)])
        return M
    
    def encode(self, irk, prand):
        hash = self.callEncrypt(irk,[0x00]*13+prand)
        print [hex(el) for el in hash]
        addr = int("".join("{0:02X}".format(el) for el in prand)+"".join("{0:02X}".format(el) for el in hash[-3::]),16)
        return addr
        
    def match(self, irk, address):
        prand = [(address >> (5-i)*8) & 0xFF for i in range(3)]
        genAddr = self.encode(irk, prand)
        return address == genAddr
        
class Signature(object):
    _counter = 0
    def __init__(self, Cmac, encrypt = None, LogWrite = None):
        self.Cmac = ByteArray('B',Cmac)
        
        self.encrypt = _toolbox._aes128
        if encrypt != None:
            self.encrypt = encrypt
        
        self.log = LogWrite
        
        K1,K2 = self._genSubkey()
        self.K1 = K1
        self.K2 = K2
    
    def LogWrite(self, message):
        if self.log != None:
            self.log(message)
        else:
            print message
    
    def callEncrypt(self, message):
        M = self.encrypt(self.Cmac, message)
        if isinstance(M,int) or isinstance(M,long):
            M = ByteArray('B',[(M >> ((15-i)*8)) & 0xFF for i in range(16)])
        return M
        
    def _genSubkey(self):
        L = self.callEncrypt(const_Zero)
        if not L[0] & 0x80:
            K1 = L << 1
        else:
            K1 = (L << 1) ^ const_Rb
        
        if not K1[0] & 0x80:
            K2 = K1 << 1
        else:
            K2 = (K1 << 1) ^ const_Rb
        
        return (K1,K2)
    
    def _padding(self, key):
        if len(key) < const_Bsize:
            key += [0x80] + [0x00]*(const_Bsize-1-len(key))
            """
            key = [0x00]*(const_Bsize-1-len(key)) + [0x80] + key
            """
            return key
        
    def encode(self, packet, length = None):
        if length == None:
            length = len(packet)
        M = []
        n = int(ceil(length/float(const_Bsize)))
        for i in range(n):
            M.append(packet[(i*16):(i*16)+16])
        if n == 0:
            n = 1
            M.append([])
            flag = False
        else:
            if (length % const_Bsize) == 0:
                flag = True
            else:
                flag = False
        
        if flag:
            M_last = ByteArray('B',M[n-1]) ^ self.K1
        else:
            tmp_2 = self._padding(M[n-1])
            M_last = ByteArray('B', tmp_2) ^ self.K2
        X = const_Zero
        for i in range(0,n-1):
            Y = X ^ M[i]
            X = self.callEncrypt(Y)
        
        Y = M_last ^ X
        T = self.callEncrypt(Y)
        return T
    
    def sign(self, packet, counter):
        packet += [((counter >> (8*i)) & 0xFF) for i in range(4)]
        encoded = self.encode(packet[::-1])
        packet += [int(el) for el in encoded[-1:-9:-1]]
        return packet
    
    def match(self, packet):
        if len(packet) > 13:
            signature = packet[-12::]
            tmpCounter = int("".join("{0:02X}".format(el) for el in packet[3::-1]),16)
            cmac = packet[-8::]
            tmpCmac = self.encode(packet[-9::-1])
            return cmac == [int(el) for el in tmpCmac[:-9:-1]]
        else:
            return False