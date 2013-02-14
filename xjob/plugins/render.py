#""" Plugins derived from VolumeRender """
# Eric Ritezel -- February 25, 2007
#

import os, xml.etree.ElementTree as ET
from deps.pagefilemask import PageFileMask

# load the Plugin module
try:
	import sys
	plugin = sys.modules['plugin']
except KeyError:
	import imp
	plugin = imp.load_source('plugin', os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'plugin.py')))

class RenderPlugin(plugin.Plugin):
	""" A base class for the Render* family of Pipeline Plugins """
	def __init__(self, level, itemq, outq, event, *args, **kwargs):
		plugin.Plugin.__init__(self, level, itemq, outq, event, args, kwargs)

		# test settings
		if len(kwargs) == 0 or kwargs.get('settings') is None:
			raise ValueError("Render Plugins need a settings argument")

		# set our settings reference
		else: self.settings = kwargs.get('settings')

		# set up the revision (force the first instance to pull)
		self.revision = -1

class RenderDirectory(RenderPlugin):
	"""
	If the xjob does not have a complete flag set on it, run.
	The complete flag means that the xjob is coming through and all
	the finalization stages have been completed before.
	"""
	def Init(self, *args, **kwargs):
		""" Set up some state variables. """
		self.diridx = 1
		self.userdir = False
		self.usejfs = False
		self.boxdir = False
		self.summation = False

	def canhandle(self, xjob):
		""" See if we can handle the job (we need a number node """
		return xjob.get('complete', None) is None and \
		       xjob.find('.//number') is not None

	def handle(self, level, xjob):
		""" The greatest plugin ever. """
		# see if our settings revision checks out, fetch settings otherwise
		rev = int(self.settings.getrevision())
		if self.revision != rev:
			self.revision = rev

			# chain through directorty settings by popularity
			if self.settings['directory/Custom'] is not None:
				self.userdir = int(self.settings['directory/User'])
			else:
				self.userdir = None
				if self.settings['directory/JFS'] is not None:
					self.usejfs = True
				elif self.settings['directory/Box'] is not None:
					self.boxdir = True

			# handle summation limit (don't split documents across directories)
			self.summation = self.settings['loadfiles/Summation'] is not None

		# if "directory by box" is set, pull from the source's name
		# FIXME: can be extended to any element, I believe
		if self.boxdir: newpath = xjob.find('source').get('name')

		# standin for JFS renamingness
		newfile = None

		# directory breaking tracker
		dbreak = False

		newpath = "%04d" % self.diridx

		# process only top-level documents (attachments fall underneath)
		for node in xjob.find('source').getiterator():
			if node.tag not in ('page', 'document'): continue

			# determine directory break
			dbreak = dbreak or self.userdir and not self.boxdir and \
			         not (int(node.find('.//order').get('value')) % self.userdir)

			# if user-defined page limits are used, test for the limit
			# NOTE: Summation does not like a document's pages to be split
			if dbreak and ((node.tag == 'page' and not self.summation) or \
				           (node.tag == 'document' and self.summation and\
				            not node.attrib.has_key('parent'))):
				self.diridx += 1
				dbreak = False

				# if we're going to name the directory after the first page,
				# make new directory at pathroot / "%0"+pidlen+"{firstpage}"
				# or make new directory for jfs
				newpath = "%04d" % self.diridx

			# reave out documents; only pages from here on
			if node.tag == 'document': continue

			# build a jfs path from the first number node
			if self.usejfs:
				# the number we're getting has hopefully been sorted
				# otherwise, it is the first number assigned to the node
				tempmask = PageFileMask(node.find('number').get('value'))
				path = tempmask.getNumber()

				# set path equal to stages of zeroes: 00/00/00
				newpath = (len(path)%2 and ('0'+path,) or (path,))[0][:-2]
				for x in xrange(len(path), 2):
					newpath.insert(x, os.path.sep)

				# prepend bates prefix
				newpath = tempmask.getPrefix() + os.path.sep + newpath

				# set filename equal to last stage of zeroes: 01.tif
				newfile = newpath[-2:]
				newfile += node.find('data').attrib['filename'].split('.')[-1]

			# get the datanode
			datanode = node.find('.//data')

			# set the oldpath and the current path
			if not datanode.get('oldpath', False):
				datanode.attrib['oldpath'] = datanode.attrib['path']
			datanode.attrib['path'] = newpath

			# see if we're resetting the filename for JFS
			if newfile is not None:
				if not datanode.get('oldfilename', False):
					datanode.attrib['oldfilename'] = datanode.attrib['filename']
				datanode.attrib['filename'] = newfile

		print "AFTER PROCESSING"
		#ET.dump(xjob)
		print "-"*80

		yield xjob

class RenderNumbering(RenderPlugin):
	""" A plugin to handle document numbering """
	def canhandle(self, xjob):
		""" See if we can handle the job (we need a number node """
		return xjob.get('complete', None) is None

	def handle(self, level, xjob):
		""" Run!  Run for your life! """
		# see if our settings revision checks out, fetch settings otherwise
		rev = self.settings.getrevision()
		if self.revision != rev:
			self.revision = rev

			# see if we're doing a custom name job
			self.idlogic = self.settings['page/Custom'] is not None

			# get a number (either a number node or the first page name)

			# fetch the mask to be used
			if self.idlogic: mask = PageFileMask(self.settings['page/CustomName'])
			else:# defaults to the first number node, then name
				firstnum = xjob.find('.//number')
				if firstnum is not None: firstnum = firstnum.get('value')
				else: firstnum = xjob.find('.//page').get('name')
				mask = PageFileMask(firstnum)

			# calculate the length of the number of the first id
			self.idlength = str(len(mask.getNumber()))

			# try to extract the bates prefix of the batch
			self.prefix = mask.getPrefix()
			if self.prefix is not None:
				self.prefix = self.prefix.rstrip(r'-. _\/|')

			# see if we're working with an expanded logic set
			if self.idlogic:
				# see if we have a suffix to look after
				suffix = mask.getSuffix()
				if suffix is not None:
					# FIXME: this makes me so sick.
					def with_suffix(page, document):
						""" gets the suffix and document number if needed """
						docorder = int(document.find('order').get('value'))

						result = self.prefix
						result += ('%' + self.idlength + 'd') % (docorder + mask.num)
						if not document.find('page') is page:
							result += ('%' + str(len(suffix)) + 'd') % \
							           (mask.suffix +
									   [x for x in range(len(document)) \
									    if document[x] is page][0])

					self.idlogic = with_suffix
				else:
					self.idlogic = lambda p, d: self.prefix + ('%'+self.idlength+'d') % (int(p.find('order').get('value')) + mask.num)

			# tack on first id number
			elif self.settings['page/SameAsID'] is not None:
				self.idlogic = lambda p, _: [b.get('value') for b in p.findall('number') if b.get('type', 0) == 'did'][0]

			# tack on first Bates number
			elif self.settings['page/SameAsCapturedBates'] is not None:
				self.idlogic = lambda p, _: [b.get('value') for b in p.findall('number') if b.get('type', 0) == 'bates'][0]

			# stick to whatever junk is in the name field
			else:self.idlogic = lambda p, _: p.get('name')

			# FILE NAME SETTINGS SECTION
			# see if we're referring to the page name for this
			if self.settings['file/SameAsPageName']:
				self.filelogic = lambda p, d: self.idlogic(p, d) + \
				                 p.find('data').get('filename').split('.')[-1]

			# see if we've got our own custom mask
			elif self.settings['file/Custom']:
				filemask = PageFileMask(self.settings['file/CustomName'])
				self.filelogic = lambda p, d: self.prefix + \
				                 ('%' + str(len(filemask.getNumber())) + 'd') % \
				                 (int(p.find('order').get('value')) + filemask.num) + \
				                 p.find('data').get('filename').split('.')[-1]

			# stick to whatever junk is in the datanode's filename field
			else: self.filelogic = lambda p, _: p.find('data').get('filename')

		# tracking variable for the document
		thisdoc = None
		firstpage = True

		# run processing on each node
		for node in xjob.find('source').getiterator():
			# catch all non-page, non-document nodes and throw them out
			if node.tag not in ('document', 'page'): continue

			# set a reference to the document node
			if node.tag == 'document':
				thisdoc = node
				firstpage = True

			# start processing page
			if node.tag == 'page':
				print '.',
				# store old and set new page attributes
				if not node.get('oldname', 0):
					node.attrib['oldname'] = node.get('name')

				# we've got a page, so run the id logic on it
				node.attrib['name'] = self.idlogic(node, thisdoc)

			if firstpage and node.tag == 'page':
				# store old and set new page attributes
				if not thisdoc.get('oldname', 0) and thisdoc.get('name', 0):
					thisdoc.attrib['oldname'] = thisdoc.get('name')
					print "thisdoc.get('name')",thisdoc.get('name')
				thisdoc.attrib['name'] = node.get('name')
				print node.get('name')
				firstpage = False


		print "AFTER PROCESSING"
		#ET.dump(xjob)
		print "-"*80

		yield xjob

class RenderVolume(RenderPlugin):
	""" A plugin to handle the output of a volume """
	def handle(self, level, xjob):
		""" Reassemble and write out a new volume """
		# see if our settings revision checks out, fetch settings otherwise
		rev = self.settings.getrevision()
		if self.revision != rev:
			self.revision = rev

			# get the volume name and size
			self.vname = self.settings['output/VolumeMask']
			self.vsize = self.settings['output/Media']

			# get the translated, fulltext and native file storage locations
			self.transfiles = self.settings['export/TranslatedDirectory']
			self.fulltext = self.settings['export/FulltextDirectory']
			self.natives = self.settings['export/NativeDirectory']

			# set the loadfile generation scheme
			self.loadfiles = self.settings.section('loadfiles')

		# make a temporary directory
		renderdir = tempfile.mkstmp(prefix='render-')

		# volume size so far
		thissize = 0

		# for each next source (because we're binding by source)
		for source in xjob.getiterator('source'):
			# for each document
			for doc in source.findall('document'):
				# if document element has a fulltext node
				if doc.find('text'): pass
				if doc.find('data'): pass

				# move through all the pages
				for page in doc.findall('page'):
					# take the text and append it to an existing file
					if page.find('text') is not None:
						pass

					if page.find('data') is not None:
						pass