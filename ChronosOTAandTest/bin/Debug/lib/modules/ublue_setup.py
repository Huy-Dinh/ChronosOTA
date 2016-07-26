#! /usr/bin/python

# Copyright (c) 2010 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is confidential property of 
# Nordic Semiconductor. The use, copying, transfer or disclosure 
# of such information is prohibited except by express written
# agreement with Nordic Semiconductor.

from ctypes import *

class uuid_t(Structure):
    _pack_ = 1
    _fields_ = [ ('type',c_uint16),
                ('value',c_uint16)
    ]

class uint128_t(Structure):
    _pack_ = 1
    _fields_ = [ ('value', c_uint8 * 16),
    ]

class ppcp_t(Structure):
    _pack_ = 1
    _fields_ = [ ('min_conn_interval',c_uint16),
                ('max_conn_interval',c_uint16),
                ('slave_latency',c_uint16),
                ('timeout_multi',c_uint16)
    ]

class clk_sett_t(Structure):
    _pack_ = 1
    _fields_ = [ ('clock_source_32ki',c_uint32),
                ('sleep_clock_accuracy',c_uint32),
                ('bypass_xosc',c_uint32)
    ]

class dcdc_sett_t(Structure):
    _pack_ = 1
    _fields_ = [ ('enable',c_uint32)
    ]

class hw_sett_t(Structure):
    _pack_ = 1
    _fields_ = [ ('clock_settings', clk_sett_t),
                ('dcdc_conv_settings', dcdc_sett_t)
    ]

class ReturnValues(object):
    status_success = 0
    status_failure = 1
    status_invalid_params = 2
    status_too_big = 3
    status_invalid_state = 4
    status_not_supported = 5

class DataStorage(object):
    DATA_STORAGE_INVALID = 0
    DATA_STORAGE_RAM = 1
    DATA_STORAGE_OTP = 2

class UUIDTypes(object):
    UUID_TYPE_INVALID = 0x0
    UUID_TYPE_BLUETOOTH = 0x1
    UUID_TYPE_VS_BASE = 0x2

class ServiceTypes(object):
    SERVICE_TYPE_INVALID = 0x0
    SERVICE_TYPE_PRIMARY = 0x1
    SERVICE_TYPE_SECONDARY = 0x2

class AttrLenType(object):
    ATTRIBUTE_LEN_FIXED = 0x1
    ATTRIBUTE_LEN_VARIABLE = 0x2

class ActiveSignalMode(object):
    ACTIVE_SIGNAL_DISABLE = 0
    ACTIVE_SIGNAL_ENABLE_ACTIVE_HIGH = 1
    ACTIVE_SIGNAL_ENABLE_ACTIVE_LOW = 2

class ADFields(object):
    SERVICES_16_COMPLETE = 0
    SERVICES_16_PARTIAL = 1
    SERVICES_128_COMPLETE = 2
    SERVICES_128_PARTIAL = 3
    LOCAL_NAME_COMPLETE = 4
    LOCAL_NAME_SHORTENED = 5
    TX_POWER_LEVEL = 6
    SM_TK = 7
    SCIR = 8
    SIGNED_DATA = 9
    SERVICE_SOL_16 = 10
    SERVICE_SOL_128 = 11
    SERVICE_DATA = 12
    MANU_SPECIFIC_DATA = 13

class AuthReq(object):
    AUTH_REQ_NONE = 0
    AUTH_REQ_PASSKEY = 1
    AUTH_REQ_OOB = 2

class IOCaps(object):
    IO_CAPS_NONE = 0
    IO_CAPS_DISPLAY_ONLY = 1
    IO_CAPS_KEYBOARD_ONLY = 2
    IO_CAPS_DISPLAY_YESNO = 3
    IO_CAPS_KEYBOARD_DISPLAY = 4

class OOBSetttings(object):
    OOB_DISABLED = 0
    OOB_ENABLED = 1

class Uuid:
    def __init__(self, uuid_type = UUIDTypes.UUID_TYPE_BLUETOOTH, uuid_value = 0x0000):
        self.uuidType = uuid_type
        self.uuidValue = uuid_value

class ClockSettings:
    CLK_SRC_32KHZ_XOSC32K = 0
    CLK_SRC_32KHZ_RCOSC32K = 1
    CLK_SRC_32KHZ_IO_LAS = 2
    CLK_SRC_32KHZ_IO_DIGITAL = 3

    CLOCK_ACCURACY_500_PPM = 0x00
    CLOCK_ACCURACY_250_PPM = 0x01
    CLOCK_ACCURACY_150_PPM = 0x02
    CLOCK_ACCURACY_100_PPM = 0x03
    CLOCK_ACCURACY_75_PPM  = 0x04
    CLOCK_ACCURACY_50_PPM  = 0x05
    CLOCK_ACCURACY_30_PPM  = 0x06
    CLOCK_ACCURACY_20_PPM  = 0x07

    CLK_16MHZ_XOSC_RCOSC = 0
    CLK_16MHZ_DIRECT_FROM_PAD = 1

    def __init__(self, clk_src_32k = None, clk_accuracy = None, clk_src_16m = None):
        if clk_src_32k == None:
            self.clkSrc32Ki = ClockSettings.CLK_SRC_32KHZ_XOSC32K
        else:
            self.clkSrc32Ki = clk_src_32k
        if clk_accuracy == None:
            self.clockAccuracy = ClockSettings.CLOCK_ACCURACY_250_PPM
        else:
            self.clockAccuracy = clk_accuracy
        if clk_src_16m == None:
            self.clkBypass16MHzXO = ClockSettings.CLK_16MHZ_XOSC_RCOSC
        else:
            self.clkBypass16MHzXO = clk_src_16m

class DcDcSettings:
    DCDC_DISABLE = 0
    DCDC_ENABLE = 1

    def __init__(self, enable = None):
        if enable == None:
            self.dcdcEnable = DcDcSettings.DCDC_DISABLE
        else:
            self.dcdcEnable = enable

class HwSettings:
    def __init__(self, clk_settings = None, dcdc_settings = None):
        if clk_settings == None:
            self.clkSettings = ClockSettings()
        else:
            self.clkSettings = clk_settings
        if dcdc_settings == None:
            self.dcdcSettings = DcDcSettings()
        else:
            self.dcdcSettings = dcdc_settings

class AssignPipeRetval:
    def __init__(self, retval, pipe):
        self.retval = retval
        self.pipe = pipe

    def __cmp__(self, other):
        if self.retval == other:
            return 0
        else:
            return 1

class UBlueSetupDll(object):
    FILENAME = "ublue_setup.dll"
    VERSION = 13906

    def __init__(self):
        # Check version match if release, ignore on dev versions
        if __name__ == "ublue_setup":
            if self.get_file_version_number() != UBlueSetupDll.VERSION:
                raise Exception("UBlue Setup DLL version mismatch")
        # Load the dll
        self.dll = CDLL(self.FILENAME)


    def get_file_version_number(self):
        from win32api import GetFileVersionInfo
        try:
            info = GetFileVersionInfo(UBlueSetupDll.FILENAME, "\\")
            ls = info['FileVersionLS']
            return ls
        except:
            print "exception here"
            return 0

class UBlueSetup:
    def __init__(self):
        self.ublue_setup_dll = UBlueSetupDll()
 
    def log_retval(f):
        def f_closure(*args, **argv):
            retv = f(*args, **argv)
            if retv != ReturnValues.status_success:
                print("Call to \"%s\" failed with error \"%d\"" % (f.__name__, retv))
            return retv
        return f_closure

    @log_retval   
    def init(self, format = 0x01, perm=0x00, appearance = 0x1801, hw_settings = None):
        perm = c_uint8(perm)
        appce = c_uint16(appearance)
        if hw_settings == None:
            hw_settings = HwSettings()
        cksett = clk_sett_t(c_uint32(hw_settings.clkSettings.clkSrc32Ki), c_uint32(hw_settings.clkSettings.clockAccuracy), c_uint32(hw_settings.clkSettings.clkBypass16MHzXO))
        dcdcsett = dcdc_sett_t(c_uint32(hw_settings.dcdcSettings.dcdcEnable))
        hwsett = hw_sett_t(cksett, dcdcsett)
        retval = self.ublue_setup_dll.dll.ublue_setup_init(format, perm, appce, byref(hwsett))
        return retval
    
    @log_retval
    def assign_vs_uuids(self, uuids):
        uuids_s = (uint128_t * len(uuids))()
        k = 0
        for i in uuids:
            if len(i) != 16:
                raise Exception("Invalid UUID length")
            data8 = (c_ubyte * 16)()
            for j in range(16):
                data8[j] = i[j]
            uuid_s = uint128_t(data8)
            uuids_s[k] = uuid_s
            k = k + 1
        retval = self.ublue_setup_dll.dll.ublue_setup_assign_vs_uuids(len(uuids), byref(uuids_s))
        return retval

    @log_retval   
    def add_service(self, svc_type, uuid, store):
        if not isinstance(uuid, Uuid):
            raise Exception("Invalid UUID class")
        svc_type = c_uint32(svc_type)
        uuid_s = uuid_t(uuid.uuidType, uuid.uuidValue)
        store8 = c_uint32(store)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_add_service(svc_type, uuid_s, store8))
        return retval
        
    @log_retval   
    def add_included_service(self, uuid):
        if not isinstance(uuid, Uuid):
            raise Exception("Invalid UUID class")
        uuid_s = uuid_t(uuid.uuidType, uuid.uuidValue)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_add_included_service(uuid_s))
        return retval

    @log_retval   
    def add_char_definition(self, uuid, max_data_len, attr_len_type, format, exponent, unit_id, name_space, desc_id, init_data_len, data):
        if not isinstance(uuid, Uuid):
            raise Exception("Invalid UUID class")
        uuid_s = uuid_t(uuid.uuidType, uuid.uuidValue)
        max_data_len = c_uint16(max_data_len)
        attr_len_type = c_uint32(attr_len_type)
        format = c_uint32(format)
        exponent = c_uint8(exponent)
        unit_id = c_uint16(unit_id)
        name_space = c_uint8(name_space)
        desc_id = c_uint16(desc_id)
        init_data_len = c_uint16(init_data_len)
        data8 = (c_ubyte * len(data))()
        for i in range(len(data)):
            data8[i] = data[i]
        retval = int(self.ublue_setup_dll.dll.ublue_setup_add_char_definition(uuid_s, max_data_len, attr_len_type, format, exponent, unit_id, name_space, desc_id, init_data_len, byref(data8)))
        return retval
    
    @log_retval   
    def add_char_descriptor(self, uuid, max_data_len, attr_len_type, init_data_len, data):
        if not isinstance(uuid, Uuid):
            raise Exception("Invalid UUID class")
        uuid_s = uuid_t(uuid.uuidType, uuid.uuidValue)
        max_data_len = c_uint16(max_data_len)
        attr_len_type = c_uint32(attr_len_type)
        init_data_len = c_uint16(init_data_len)
        data8 = (c_ubyte * len(data))()
        for i in range(len(data)):
            data8[i] = data[i]
        retval = int(self.ublue_setup_dll.dll.ublue_setup_add_char_descriptor(uuid_s, max_data_len, attr_len_type, init_data_len, byref(data8)))
        return retval
        
    def assign_pipe(self, type):
        type = c_uint32(type)
        num = c_uint8(0x00)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_assign_pipe(type, byref(num)))
        if retval != ReturnValues.status_success:
            print("Call to \"assign_pipe\" failed with error \"%d\"" % (retval))
        return AssignPipeRetval(retval, num.value)
        
    @log_retval   
    def set_device_name(self, name, name_short_len = None):
        name_len = c_uint8(len(name))
        if name_short_len != None:
            name_short_len = c_uint8(name_short_len)
        else:
            name_short_len = name_len
        name_uint8 = (c_ubyte * len(name))()
        for i in range(len(name)):
            name_uint8[i] = c_ubyte(ord(name[i]))
        retval = int(self.ublue_setup_dll.dll.ublue_setup_gap_set_device_name(name_len, name_short_len, byref(name_uint8)))
        return retval
    
    @log_retval   
    def set_preferred_conn_params(self, min_conn_interval, max_conn_interval, slave_latency, timeout_multi):
        ppcp = ppcp_t(min_conn_interval, max_conn_interval, slave_latency, timeout_multi)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_gap_set_ppcp(byref(ppcp)))
        return retval

    @log_retval
    def set_active_signal(self, mode, distance):
        mode = c_uint32(mode)
        distance = c_uint8(distance)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_hw_set_active_signal(mode, distance))
        return retval

    @log_retval
    def set_window_limit(self, limit, dropped_packet_threshold, auto_off_count):
        limit = c_uint32(limit)
        dropped_packet_threshold = c_uint8(dropped_packet_threshold)
        auto_off_count = c_uint8(auto_off_count)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_hw_set_window_limit(limit, dropped_packet_threshold, auto_off_count))
        return retval

    @log_retval   
    def hw_ad_set_tx_power(self, device_output_power, gain):
        device_output_power = c_uint32(device_output_power)
        gain = c_int8(gain)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_hw_ad_set_tx_power(device_output_power, gain))
        return retval        

    @log_retval   
    def set_ad_data_uuids(self, local = [], remote = []):
        local_len = c_uint8(len(local))
        remote_len = c_uint8(len(remote))
        local_uuid_t = (uuid_t*len(local))()
        remote_uuid_t = (uuid_t*len(remote))()

        for i in range(len(local)):
            if not isinstance(local[i], Uuid):
                raise Exception("Invalid UUID class")
            luuid = uuid_t(local[i].uuidType, local[i].uuidValue)
            local_uuid_t[i] = luuid
        for i in range(len(remote)):
            if not isinstance(remote[i], Uuid):
                raise Exception("Invalid UUID class")
            ruuid = uuid_t(remote[i].uuidType, remote[i].uuidValue)
            remote_uuid_t[i] = ruuid

        retval = int(self.ublue_setup_dll.dll.ublue_setup_ad_set_svcuuids(local_len, byref(local_uuid_t), remote_len, byref(remote_uuid_t)))
        return retval
    
    @log_retval   
    def ad_select_fields_raw(self, ad_bm_bitmap, ad_gm_bitmap):
        ad_bm_bitmap = c_uint32(ad_bm_bitmap)
        ad_gm_bitmap = c_uint32(ad_gm_bitmap)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_ad_select_fields(byref(ad_bm_bitmap), byref(ad_gm_bitmap)))
        return retval

    @log_retval   
    def ad_select_fields(self, ad_bm_list, ad_gm_list):
        ad_bm_bitmap = 0
        ad_gm_bitmap = 0
        for i in ad_bm_list:
            if i < 14:
                ad_bm_bitmap |= (1 << i)
            else:
                return 1
        for i in ad_gm_list:
            if i < 14:
                ad_gm_bitmap |= (1 << i)
            else:
                return 1
        ad_bm_bitmap = c_uint32(ad_bm_bitmap)
        ad_gm_bitmap = c_uint32(ad_gm_bitmap)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_ad_select_fields(byref(ad_bm_bitmap), byref(ad_gm_bitmap)))
        return retval
    
    @log_retval   
    def sec_set_params(self, auth_req, io_caps, oob, min_keysize, max_keysize, bond_timeout):
        auth_req = c_uint32(auth_req)
        io_caps = c_uint32(io_caps)
        oob = c_uint32(oob)
        min_keysize = c_uint8(min_keysize)
        max_keysize = c_uint8(max_keysize)
        retval = int(self.ublue_setup_dll.dll.ublue_setup_sec_set_params(auth_req, io_caps, oob, min_keysize, max_keysize, bond_timeout))
        return retval
    
    def gen_cmds(self, data_storage, setup_id):
        data_storage = c_uint32(data_storage)
        setup_id = c_uint32(setup_id)
        length = c_uint16(8192)
        msg = (c_ubyte * 8192)()
        retval = int(self.ublue_setup_dll.dll.ublue_setup_gen_cmds(data_storage, setup_id, byref(length),byref(msg)))
        if retval != ReturnValues.status_success:
            return []
        length = int(length.value)
        msg = [int(el) for el in msg]
        if length != 0:
            msg = [int(el) for el in msg[:length]]
            tmparray = []
            while len(msg) > 0:
                tmparray.append(msg[1:msg[0]+1])
                del msg[:msg[0]+1]
            return tmparray
        else: 
            return []
