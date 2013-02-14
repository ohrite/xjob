# Zeroconf browser to monitor Ephemerol registration
# Eric Ritezel -- February 20, 2007
#

from xjob.Zeroconf import *
import socket

class MyListener(object):
	def __init__(self):
		self.r = Zeroconf()
		pass

	def removeService(self, zeroconf, type, name):
		print "Service", name, "removed"

	def addService(self, zeroconf, type, name):
		print "Service", name, "added"
		print "Type is", type
		info = self.r.getServiceInfo(type, name)
		if info is not None:
			print "Address is", str(socket.inet_ntoa(info.getAddress()))
			print "Port is", info.getPort()
			print "Weight is", info.getWeight()
			print "Priority is", info.getPriority()
			print "Server is", info.getServer()
			print "Text is", info.getText()
			print "Properties are", info.getProperties()

if __name__ == '__main__':
	print "Multicast DNS Service Discovery for Python Browser test"
	r = Zeroconf()
	print "1. Testing browsing for a service..."
	listener = MyListener()
	browser = ServiceBrowser(r, "_ephemerol._tcp.local.", listener)
