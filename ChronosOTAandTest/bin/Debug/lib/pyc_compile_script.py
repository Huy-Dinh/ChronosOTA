import pyc

emulatorlibs_args = [
'/out:emulatorlibs',
'/target:dll',
'masteremulator.py',
'masteremulatorprocessor.py',
'testerScriptCommon.py',
'testerScriptEngineClient.py',
'testerScriptServer.py',
'pipesetup.py',
'enum.py',
# modules
r'modules\__init__.py',
r'modules\acim.py',
r'modules\AttDb.py',
r'modules\common.py',
r'modules\ftdiIo.py',
r'modules\packetqueue.py',
r'modules\Smp.py',
r'modules\ublue_setup.py',
# protocol
r'protocol\__init__.py',
r'protocol\Att.py',
r'protocol\Gap.py',
r'protocol\Gatt.py',
r'protocol\L2Cap.py',
r'protocol\L2CapSignPkt.py',
r'protocol\Smp.py',

# python modules (previously pylibs.dll)
'abc.py',
'bisect.py',
'collections.py',
'copy.py',
'dummy_thread.py',
'dummy_threading.py',
'functools.py',
'genericpath.py',
'hashlib.py',
'heapq.py',
'keyword.py',
'linecache.py',
'ntpath.py',
'os.py',
'pickle.py',
'Queue.py',
'random.py',
'sockClient.py',
'sockServer.py',
'sockServer2.py',
'stat.py',
'string.py',
'struct.py',
'temp.py',
'threading.py',
'traceback.py',
'types.py',
'UserDict.py',
'warnings.py',
'weakref.py',
'_abcoll.py',
'_threading_local.py',
'_weakrefset.py',
'__future__.py'
]

pyc.Main(emulatorlibs_args)

#/out:pylibs /target:dll abc.py bisect.py collections.py copy.py functools.py genericpath.py heapq.py hookscript.py keyword.py linecache.py ntpath.py os.py Queue.py random.py sockClient.py sockServer.py sockServer2.py stat.py struct.py temp.py threading.py traceback.py types.py UserDict.py warnings.py _abcoll.py __future__.py
#won't compile with pyc.py: pickle.py

#ipy pyc.py /out:emulatorlibs /target:dll masteremulator.py testerScriptCommon.py testerScriptEngineClient.py testerScriptServer.py
