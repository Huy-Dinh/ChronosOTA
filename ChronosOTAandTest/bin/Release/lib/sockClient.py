from socket import *
import time
s = socket(AF_INET, SOCK_STREAM)
s.settimeout(3)

doLoop = True
loopCount = 0

while doLoop == True and loopCount < 3:
    try:
        s.settimeout(3)                        #Don't wait
        s.connect(('127.0.0.1', 8888))
        doLoop = False                              #Connection succeeded
        print "Sync connect succeeded"
        s.settimeout(10)
    except Exception, ex:
        loopCount += 1
        time.sleep(1)
        print "Sync connect failed. Retrying."

print "client connected"
print s.recv(100)
s.send("send this text")
print s.recv(100)
s.send("send this text also")