""" A plugin that pulls data from the filesystem for a document/pages """
# Eric Ritezel -- February 28, 2007
#

import os, xml.etree.ElementTree as ET

try:
	import sys
	plugin = sys.modules['plugin']
except KeyError:
	import imp
	plugin = imp.load_source('plugin', os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'plugin.py')))

class SoakPlugin(plugin.Plugin):
	"""
	A plugin that reads page data from the filesystem
	and appends it using base64 encoding to the data node.
	Useful for over-the-wire transfers.
	Preferably done per-document.
	"""
	def canhandle(self, xjob):
		""" Disallow two soaks on a page. """
		for pagedata in xjob.findall('.//page/data'):
			if pagedata is not None and pagedata.text is not None:
				if __debug__: print "failing?", ET.tostring(pagedata)
				return False

		# test and see if the document data has already been soaked
		docdata = xjob.find('.//document/data')
		return not (docdata is not None and docdata.find('text') is not None)

	def handle(self, level, xjob):
		""" Yank data off the FS for each data node we find. """
		srcnode = xjob.find('source')
		basepath = srcnode.get('temphref', srcnode.get('href'))

		# throw data into each node we find
		for node in xjob.getiterator('data'):
			# get a filepath combo
			filepath = os.path.join(basepath, \
			           node.get('oldpath', node.get('path')),\
			           node.get('oldfilename', node.get('filename')))

			# write and dump to node
			datfile = open(filepath, 'rb')
			node.text = datfile.read()#.encode('zip').encode('base64')
			datfile.close()

		# yield the xjob back
		yield xjob

class FlushPlugin(plugin.Plugin):
	"""
	A plugin that writes the base64-encoded contents of data nodes to
	the filesystem at a specified location
	Useful for over-the-wire transfers.
	Preferably done per-document.
	"""
	def Init(self, *args, **kwargs):
		""" initialize a tracking sequence for documents """
		# below we default to the xjob's uuid
		self.tempdir = (kwargs.has_key('tempdir') and (kwargs['tempdir'],) or (0,))[0]
		self.cleanup = kwargs.has_key('cleanup')

	def canhandle(self, xjob):
		""" Confirm that there's soaked data to be flushed from the nodes. """
		# see if the document data node exists, but is not populated
		docdata = xjob.find('.//document/data')
		if docdata is not None:
			if __debug__: print "failing on doc flush?", len(docdata.text)
			return len(docdata.text) > 0

		# see if all of the pages have data
		for pagedata in xjob.findall('.//page/data'):
			if pagedata.text is None or len(pagedata.text) == 0:
				if __debug__: print "failing on page flush?", len(pagedata.text)
				return False

		return True

	def handle(self, level, xjob):
		""" Dump the contents of each data node we find. """
		srcnode = xjob.find('source')
		if self.tempdir: srcnode.set('temphref', self.tempdir)
		basepath = srcnode.get('temphref', srcnode.get('href'))

		# throw data into each node we find
		for node in xjob.getiterator('data'):
			# get a filepath combo
			filepath = os.path.join(basepath,
			                   node.get('oldpath', node.get('path')),\
			                   node.get('oldfilename', node.get('filename')))

			# create filepath if it doesn't exist
			if not os.path.exists(os.path.dirname(filepath)):
				os.makedirs(os.path.dirname(filepath))

			# write data to it
			datafile = open(filepath, 'wb')
			datafile.write(node.text)#.decode('base64').decode('zip'))
			datafile.close()

			node.text = None

		# yield the xjob back
		yield xjob


