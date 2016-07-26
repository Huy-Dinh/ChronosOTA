from socket import *
import time
s = socket(AF_INET, SOCK_STREAM)
s.settimeout(30)
s.connect(('localhost', 6001))

s.send("Start FTS;C:\Program Files\Frontline Test System II\Frontline FTS4BT 8.7.13.0\Executables\Core")
print(s.recv(1024))

print("Config Settings")
s.send("Config Settings;IOParameters;Master=0x0012ee92259d;Slave=0x001d98646178;PinCode=1234;EncryptionSelection=1")
print(s.recv(1024))

print "Start Sniffing"
s.send("Start Sniffing")
print(s.recv(1024))

print "sleep"
time.sleep(30)

print "Stop Sniffing"
s.send("Stop Sniffing")
print(s.recv(1024))

print "HTML Export"
s.send("HTML Export;Summary=1;Data Bytes=1;Decode=1;Frame Range Upper=30000;Frame Range Lower=1;File=htmlexport_3.htm")
print(s.recv(1024))

print "sleep"
time.sleep(10)

print "Stop Capture"
s.send("Stop Capture")
print(s.recv(1024))

print "Stop FTS"
s.send("Stop FTS")
print(s.recv(1024))

s.close()
