# comprehend IPRO Tech .LFP loadfiles
# Eric Ritezel -- January 8, 2007
# v0.0.1 -- Initial completion 20070109
#

import os, re, glob, uuid
from xml.etree import ElementTree as ET

class IPRO:
	"""
	Class for loading Ipro files.
	"""
	def __init__(self, callback=None):
		"""
		Creates an IPRO connector based on filename parameter.

		Parameters:
			-> filename
		"""

		# set callback
		self.callback = callback

		# expression for loading image lines
		#IM,MAI023932,D,0,@MAI004;0001;MAI023932.tif;2
		expression = r"""^
			(?P<type>.{2}),		# line header IM = image, IO = infomration only, FT = fulltext
			(?P<name>[^,]+),	# page name
			(?P<break>[^,]?),	# maybe a D or C? (doesn't have to be anything)
			(?P<offset>\d+),	# digit for multipage offset
			@(?P<volume>[^;]+);	# volume prefix
			(?P<path>[^;]+);	# a path
			(?P<file>[^;]+);	# a file name
			(?P<mime>\d)		# a file type code
			$"""

		# compile regular expression
		self.regex = re.compile(expression, re.VERBOSE)

	def getvalidname(self, filename):
		""" See if we can load a given path. """
		if not os.path.exists(filename): return None
		
		# pack filenames with possible test files
		if os.path.isdir(filename):
			filenames = glob.iglob(os.path.join(filename, '*.lfp'))
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
		volume = build.start("source",{'href':basepath, 'id':str(uuid.uuid4()), 'type':'ipro'})

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

		# read lines from LFP
		for line in self.loadfile.readlines(hint):
			# increment line number
			linenum+= 1

			# parse line
			result = self.regex.search(line)

			# complain about result
			if not result:
				linerrs.append(linenum, line)
				continue

			# see if we're getting an image key definition line
			# TODO: add Fulltext and Information Only handlers
			if result.group("type") != "IM": continue

			# try to assign the volume one of our values
			if not volume.attrib.has_key("name"):
				volume.attrib["name"] = result.group("volume")

			# otherwise see if we should start a new volume
			elif volume.attrib["name"] != result.group("volume"):
				build.end("source")
				volume = build.start("source", {'href':basepath,
				                                'id':str(uuid.uuid4()),
				                                'name':result.group('volume'),
				                                'type':'ipro'})

			# if there's a break, create a new document and structure
			# FIXME: assumes D/C as the hierarchy
			if result.group("break").strip() != "":
				if tree[-1].tag == "document":
					build.end("document")
					
					# see if we can move the node to a parent now
					if tree[-1].has_key('parent'):
						# find parent for attachment vector
						mommy = [x for x in tree[-2].getchildren().reverse() \
						         if x.get('id') == tree[-1].get('parent')][0]
							
						# find/make attachment node
						attachnode = mommy.find('attachment') 
						if attachnode is None:
							attachnode = ET.SubElement(mommy, 'attachment')
						
						# move node
						attachnode.append(tree[-1])
						mommy.remove(tree[-1])

					tree.pop()
				
				# append document to node and try 
				tree.append(build.start("document",{'id':str(uuid.uuid4())}))

				# set "last true document"
				if result.group("break").strip() == "D":
					lastdoc = tree[-1].get('id')
				elif result.group("break").strip() == "C":
					tree[-1].attrib['parent'] = lastdoc


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
	data = IPRO()
	accesspath = data.getvalidname(datapath)
	if accesspath is not None:
		data.Read(accesspath)
		ET.ElementTree(data.XML).write(str(uuid.uuid1())+".xml")
	else: raise ValueError("Path does not exist or invalid: "+datapath)
	