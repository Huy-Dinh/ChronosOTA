handleDict = {
    0x0001:{'UUID':SERVICE_GROUP_UUID,'DATA':"%02X%02X" % (ATTRIBUTE_PROFILE & 0xFF,(ATTRIBUTE_PROFILE >> 8) & 0xFF),'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0002:{'UUID':ATTRIBUTE_VERSION_INFORMATION,'DATA':"01015672",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0003:{'UUID':ATTRIBUTE_HANDLES_CHANGED,'DATA':"",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0004:{'UUID':ATTRIBUTE_VALUE_CHANGED,'DATA':"",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0005:{'UUID':ATTRIBUTE_OPCODE_SUPPORTED,'DATA':"6F000000",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0006:{'UUID':NUM_PREPARE_WRITE_COMMANDS,'DATA':"0000",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0007:{'UUID':SERVICE_GROUP_UUID,'DATA':"%02X%02X" % (GENERIC_ACCESS_PROFILE & 0xFF,(GENERIC_ACCESS_PROFILE >> 8) & 0xFF),'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0008:{'UUID':DEVICE_NAME,'DATA':"IOP Server Nordic",'DATATYPE':"text",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x0009:{'UUID':VERSION_INFORMATION,'DATA':"3412007856",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x000A:{'UUID':ICON,'DATA':"8623",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x000B:{'UUID':VENDOR_AND_PRODUCT_INFORMATION,'DATA':"0100341230570100",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x000C:{'UUID':DEVICE_LANGUAGE_SUPPORTED,'DATA':"ENDEFRITJAKOMYKGESUK",'DATATYPE':"text",'R_PERM':"yes",'W_PERM':"no",'NOTIFY':"no",'FLIGHTY':"no"},
    0x000D:{'UUID':CURRENT_LANGUAGE,'DATA':"EN",'DATATYPE':"text",'R_PERM':"yes",'W_PERM':"yes",'NOTIFY':"no",'FLIGHTY':"no"},
    0x000E:{'UUID':SLAVE_PREFFERED_CONN_PARAM,'DATA':"060014000200",'DATATYPE':"hex",'R_PERM':"yes",'W_PERM':"yes",'NOTIFY':"no",'FLIGHTY':"no"}
}
