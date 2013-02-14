# Conversion of BoxWorker's hashing/sizing function to the Pipeline system
# Eric Ritezel -- February 25, 2007
#

import os, zlib

# this mess finds the Plugin module
try:
	import sys
	plugin = sys.modules['plugin']
except KeyError:
	import imp
	plugin = imp.load_source('plugin', os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'plugin.py')))

class HashNSizerPlugin(plugin.Plugin):
	"""
	A Pipeline plugin to run an Adler32 fasthash transform by chunk
	on page data (and document data if it exists)
	Size is calculated during this process.
	"""
	def canhandle(self, xjob):
		""" See if we can actually run the hasher. """
		firstpagedata = xjob.find('.//page/data')
		sourcenode = xjob.find('source')
		if firstpagedata is None or sourcenode is None: return False

		basepath = sourcenode.attrib['href']
		if not os.path.isdir(basepath): basepath = os.path.dirname(basepath)

		return os.path.isfile(os.path.join(basepath,
		                                   firstpagedata.attrib['path'],
		                                   firstpagedata.attrib['filename']))

	def handle(self, level, xjob):
		""" Hash and get the size of the pages in the XJOB. """
		# get the root path of the box
		sourcenode = xjob.find('source')
		basepath = sourcenode.attrib['href']
		if not os.path.isdir(basepath): basepath = os.path.dirname(basepath)

		# get file sizing information for box
		boxsize = 0

		for page in xjob.getiterator("page"):
			# get the data node
			datanode = page.find('data')
			filename = os.path.join(basepath, datanode.attrib['path'],
									datanode.attrib['filename'])

			try:
				# compute adler32 checksum of file (chunked read)
				filehash = 0
				try:
					# attach size info to file and add to box counter
					size = os.stat(filename).st_size
					datanode.attrib['size'] = "%d" % size
					boxsize += size

					fp = open(filename, "rb")
					while True:
						data = fp.read(65534)
						if not data: break
						filehash = zlib.adler32(data, filehash)

				# attach a missing flag and move on
				except: datanode.attrib['missing'] = 'True'

				# close the file pointer
				finally:fp.close()

			# throw checksum onto file
			finally: datanode.attrib['checksum'] = hex(filehash)

		# set box size and checksum
		sourcenode.attrib['size'] = "%d" % boxsize

		yield xjob