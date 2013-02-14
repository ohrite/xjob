# Some simple utility Plugins
# Eric Ritezel -- February 27, 2007

import xml.etree.ElementTree as ET, uuid, time
from threading import local as threading_local

# this mess finds the Plugin module
try:
	import sys
	plugin = sys.modules['plugin']
except KeyError:
	import imp, os
	plugin = imp.load_source('plugin', os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'plugin.py')))

class TimerPlugin(plugin.Plugin, threading_local):
	""" Calculates the time from instantiation and since last run. """
	def __init__(self, level, itemq, outq, event, *args, **kwargs):
		plugin.Plugin.__init__(self, level, itemq, outq, event)
		self.__dict__.update({'oldtime':time.clock()})
		self.label = kwargs.get('label', 'elapsed')

	def handle(self, level, arg):
		print self.label,":",(time.clock() - self.oldtime),'sec'
		self.oldtime = time.clock()
		yield arg

class XJOBWriterPlugin(plugin.Plugin):
	""" Dumps to the given file """
	def __init__(self, level, itemq, outq, event, filename=None, **kwargs):
		plugin.Plugin.__init__(self, level, itemq, outq, event)
		if filename is not None: self.filename = filename
		else: self.filename = str(uuid.uuid1())+".xml"

	def canhandle(self, arg): return ET.iselement(arg)
	def handle(self, level, arg):
		ET.ElementTree(arg).write(str(level)+'-'+arg.get('id')+'-'+self.filename)
		yield arg