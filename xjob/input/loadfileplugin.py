# Rewrite of BoxWorker to fit within the Pipeline system
# Eric Ritezel -- February 25, 2007
#

import os, xml.etree.ElementTree as ET

# loadfile support libs
from doculex import Doculex
from ipro import IPRO
from opticon import Opticon

# load the Plugin module
try:
	import sys
	plugin = sys.modules['plugin']
except KeyError:
	import imp
	plugin = imp.load_source('plugin', os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'plugin.py')))

class LoadfilePlugin(plugin.Plugin):
	def Init(self, *args, **kwargs):
		# initialize all of our loadfile members
		# okay, so doculex isn't a load "file" ... it HAS files, though
		self.doculex = Doculex()
		self.ipro = IPRO()
		self.opticon = Opticon()

		# filename validity cache (with some sys.stat output)
		self.invalid = {}
		
		# universal page ordering counter
		self.pagecounter = 0

	def canhandle(self, xjob):
		""" Determine if the incoming data is readable by any structure. """
		# is this properly formatted as <xjob><source href='...' /></xjob>
		srcnode = xjob.find('source')
		if srcnode is None or not srcnode.get('href', False): return False

		# see if the work's already done
		if srcnode.get('id'): return False

		# grab some stats
		fname = srcnode.get('href')
		modtime = 0
		if os.path.exists(fname): modtime = os.stat(fname).st_mtime

		# save ourselves a bad trip
		if self.invalid.has_key(fname) and self.invalid[fname] == modtime:
			return False

		# walk the handlers in order of metadata potential
		for ftype in ('doculex', 'ipro', 'opticon'):
			# try to get a valid path for the given handler
			newsrc = getattr(self, ftype).getvalidname(fname)
			if newsrc is None: continue

			# update the source node and delete the key
			srcnode.attrib.update({'href':newsrc, 'type':ftype})
			if self.invalid.has_key(fname): del(self.invalid[fname])

			return True

		# cache our response to this silly question
		self.invalid[srcnode] = modtime

	def handle(self, level, xjob):
		""" Run a Loadfile import against a parameter. """
		srcnode = xjob.find('source')
		fname = srcnode.attrib['href']
		type = srcnode.attrib['type']

		# get data
		loader = getattr(self, type).Read(fname)

		# remove the source node from the xjob
		xjob.remove(srcnode)

		# pack box data into xjob structure
		for source in loader.XML.getiterator('source'):
			xjob.append(source)

		# return a null pointer if there were no boxes
		if not len(xjob): yield None

		yield xjob