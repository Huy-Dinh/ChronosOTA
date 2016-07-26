from socket import *
import time
s = socket(AF_INET, SOCK_STREAM)
s.bind(('',8888))
s.listen(1)
client, addr = s.accept()
print "server connected"
time.sleep(5)
client.send("Send this text")