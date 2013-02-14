# comprehend Dataflight Opticon loadfiles
# Eric Ritezel -- January 8, 2007
# v0.0.1 -- Initial completion 20070109
# v0.0.9 -- Moved to become part of a plugin system 20070225
#

import re, glob, os, uuid
import xml.etree.ElementTree as ET

class Opticon:
	"""
	Class for loading Opticon files.
	"""

	def __init__(self):
		"""
		Creates an Opticon connector based on filename parameter.

		Parameters:
			-> callback -- hopefully a callback function with Omni syntax
		"""

		# expression for loading image lines
		#AIR 04722,AIRDM06,Q:\AIRDM06\AIR\AIR04722\AIR04722.TIF,Y,,,
		expression = r"""^
			(?P<name>[^,]+),                  # page name
			(?P<volume>[^,]+),                # volume name
			([A-Z]:\\)?(?P<path>([^\\]+\\)*)  # a path
			(?P<file>[^,]+),
			(?P<break>Y?),                    # new document indicator (Y)
			(?:.+)                            # detritus
			$"""

		# compile regular expression
		self.regex = re.compile(expression, re.VERBOSE)

	def getvalidname(self, filename):
		""" See if we can load a given path. """
		if not os.path.exists(filename): return None

		# pack filenames with possible test files
		if os.path.isdir(filename):
			filenames = glob.iglob(os.path.join(filename, '*.[lot][xop][gt]'))
		else: filenames = (filename,)

		# run through file names trying to match lines we know
		for fname in filenames:
			try:
				tfile = open(fname, 'r')
				test = tfile.readline()
			except: continue
			finally: tfile.close()
			if self.regex.match(test): return fname

		return None

	def Read(self, filename):
		# fire up the loadfile in text mode
		self.loadfile = open(filename, 'r')
		basepath = os.path.dirname(filename)

		# build base of tree
		build = ET.TreeBuilder()
		root = build.start("xjob",{})
		volume = build.start("source",{'href':basepath, 'id':str(uuid.uuid4()), 'type':'opticon'})

		# kick off tree-depth tracking stack (we need this for back-references)
		tree = []
		tree.append(root)

		# initialize number of lines and errors
		linenum = 0
		linerrs = []

		# get hint for readlines
		self.loadfile.readlines()
		hint = self.loadfile.tell()
		self.loadfile.seek(0)

		# read lines from Opticon
		for line in self.loadfile.readlines(hint):
			# increment line number
			linenum+= 1

			# parse line
			result = self.regex.search(line)

			# complain about result
			if not result:
				linerrs.append(linenum, line)
				continue

			# try to assign the volume one of our values
			if not volume.attrib.has_key("name"):
				volume.attrib["name"] = result.group("volume")

			# otherwise see if we should start a new volume
			elif volume.attrib["name"] != result.group("volume"):
				build.end("source")
				volume = build.start("source", {'href':basepath,
				                                'id':str(uuid.uuid4()),
				                                'name':result.group('volume'),
				                                'type':'opticon'})

			# if there's a break, create a new document
			if result.group("break").strip() == "Y":
				if tree[-1].tag == "document":
					build.end("document")
					tree.pop()
				tree.append(build.start("document",{'id':str(uuid.uuid4())}))

			# start a new page element
			pgnode = build.start("page",{'id':str(uuid.uuid4()), 'name':result.group("name")})
			ET.SubElement(pgnode, 'number', {'type':'bates', 'value':result.group("name")})
			ET.SubElement(pgnode, 'data', {'path':result.group("path").strip(os.path.sep),
			                               'filename':result.group("file")})
			build.end("page")

		# close up processing
		build.end("document")
		build.end("source")
		build.end("xjob")

		# generate xml output
		self.XML = build.close()
		self.loadfile.close()

		self.lines = linenum

if __name__ == "__main__":
	datapath = r"M:\02_07_FM\CityAttorney\AMEC_SALTER_0214\Scan\SALTER001"
	data = Opticon()
	accesspath = data.getvalidname(datapath)
	if accesspath is not None: data.Read(accesspath)
	else: raise Exception("WHEE!")
	ET.ElementTree(data.XML).write(str(uuid.uuid1())+".xml")