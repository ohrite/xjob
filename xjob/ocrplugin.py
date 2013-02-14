# Conversion of OCRWorker to the Pipeline system
# Eric Ritezel -- February 22, 2007
#

# test for pythoncom/win32com (needed to fire up OCR via MODI)
_HaveCOM = True
try: import pythoncom, win32com.client
except: _HaveCOM = False

import threading
import os, xml.etree.ElementTree as ET

import plugin

class OCRPlugin(plugin.Plugin):
	"""
	A Pipeline plugin to run OCR on an XJOB's pages.
	OCR is often performed on page elements.

	If the data is coming over the wire, the following steps are needed:
	>>> pl.AddTask(xjob.tasks.ProcessByPage)
	>>> pl.AddTask(xjob.tasks.WritePageData)
	>>> pl.AddTask(xjob.tasks.RunOCR)
	>>> pl.AddTask(xjob.tasks.<whatever else>)
	>>> pl.AddTask(xjob.tasks.ReadPageData)
	>>> pl.AddTask(xjob.tasks.ReassemblePages)
	"""
	def Init(self, *args, **kwargs):
		# test settings
		if len(kwargs) == 0 or kwargs.get('settings') is None:
			raise ValueError("Render Plugins need a settings argument")

		# set our settings reference
		else: self.settings = kwargs.get('settings')

		# set up the revision (force the first instance to pull)
		self.revision = -1

		# see if we can run the ocr (set canhandle flag)
		if _HaveCOM:
			self.canOCR = True
			try: self._ocr = OCR()
			except: self.canOCR = False

	def canhandle(self, xjob):
		""" See if a) we can actually run OCR and b) if it needs it. """
		print "hit ocr handler with havecom:", _HaveCOM, " canOCR:", self.canOCR, " ops/OCR", self.settings['operations/OCR']
		return _HaveCOM and self.canOCR and self.settings['operations/OCR'] is not None

	def handle(self, level, xjob):
		""" Run OCR against an xjob. """
		# see if our settings revision checks out, fetch settings otherwise
		rev = int(self.settings.getrevision())
		if self.revision != rev:
			self.revision = rev

			# grab Rotation preference
			if self.settings['operations/ProcessOCR'] is not None:
				self.rotate = True
				self.deskew = True
			else:
				self.rotate = False
				self.deskew = False

		# get the basepath for file-level interaction
		basepath = xjob.find('source').get('temphref', xjob.find('source').get('href'))

		#FIXME: page-level for now
		for page in xjob.itertag('page'):
			self._ocr.Run(basepath, page, autoorient=rotate, deskew=deskew)

		yield xjob

class OCR:
	"""
	Wrapper for the Microsoft Office Document Imaging COM object,
	which itself wraps OmniPage's Scanbridge OCR (d'oh!)
	Plus you can reuse it!  (yay!)

	Usage:
	>>> from modiocr import OCR
	>>> modi_ify = OCR()
	>>> modi_ify = Run('/usr/bin/somepath','<page id="foobar" path="0914/" filename="foo124.tif">')
	Working .. .. .. .. done!


	>>> print modi_ify.text
	The butler did ^t!

	>>> print modi_ify.xml
	<ElementTree:Element>
	"""

	# http://msdn.microsoft.com/library/default.asp?url=/library/en-us/intl/nls_61df.asp
	OCRLanguages = {
		"chinese":				0x0804,	# chinese longform alias
		"c":					2048,	# system schema alias
		"chinese simplified":	2052,
		"chinese traditional":	1028,
		"czech":				0x0005,
		"danish":				0x0006,
		"dutch":				19,
		"english":				0x0009,
		"finnish":				11,
		"french":				12,
		"german":				0x0007,
		"greek":				0x0008,
		"hungarian":			14,
		"italian":				0x0010,
		"japanese":				0x0011,
		"korean":				0x0012,
		"norwegian":			20,
		"polish":				21,
		"portuguese":			22,
		"russian":				25,
		"spanish":				10,
		"swedish":				29,
		"default":				2048,
		"turkish":				31
		}

	def __init__(self):
		# run coinitialize for current thread
		if threading.currentThread ().getName () <> 'MainThread':
			pythoncom.CoInitialize ()

		# create new COM connection to MODI
		self.modi = win32com.client.Dispatch("MODI.Document")

	def __del__(self):
		self.modi = None

	def Run(self, basepath, pagenode, autoorient=True, deskew=True):
		"""
		Run OCR against a new xml parameter.

		FIXME: Page-level for now (yikes)

		Parameters:
			basepath -- the location the file is living in
			xmlparam -- an xjob definition coming over the wire
			            it can be any number of things, but should be an image
		"""
		# define a path to the image
		path = os.path.join(basepath, pagenode.find('data').get("path"),
		                    pagenode.find('data').get("filename"))

		# create document
		self.modi.Create(path)

		# pull first image and OCR with (Default Language(C), Auto-orientation=True, Deskew=True)
		img = self.modi.Images[0]
		try: img.OCR(OCR.OCRLanguages[language.lower()], autoorient, deskew)
		except: img.OCR(OCR.OCRLanguages['c'], autoorient, deskew)

		# close up document (do not save changes)
		self.modi.close(False)

		# assign characteristics
		self.language = img.layout.Language
		self.chars = img.layout.NumChars
		self.words = img.layout.NumWords
		self.fonts = img.layout.NumFonts

		# define a text node to build under
		buildroot = ET.SubElement(pagenode, 'text')

		# build the base region for dumping words into
		parent = ET.SubElement(buildroot, "region", id='0')

		# loop through words in layout collection
		for word in img.layout.Words:
			# see if we should build a new region
			if word.RegionId != int(parent.get("id")):
				parent = ET.SubElement(buildroot, "region", id=str(word.RegionId))

			# get primary bounding box for word
			rect = word.Rects[0]

			# add to style from bounding box
			elem = ET.SubElement(parent, "word")
			elem.text = word.Text.encode('utf8')

			# pull font information
			font = word.Font

			# lesson learned from Chinese: don't assume there's a font
			if font is not None:
				elem.attrib = {"font-size": "%d" % font.FontSize}

				# see if the family is significant
				if font.Family < 6:
					elem.attrib["font-family"] = \
						("Helvetica","Times","Century","TimesCentury","HelveticaCentury")[font.Family-1]

				# see if the font face is significant
				if font.FaceStyle > 1:
					elem.attrib["font-style"] = \
						("italic","bold","bold italic")[font.FaceStyle-2]

				# see if the serif is significant
				if font.SerifStyle < 5:
					elem.attrib["font-serif"] = \
						("sans","thin","square","round")[font.SerifStyle-1]

			# append element and add UTF-8 encoded text
			elem.attrib.update({"left":"%d" % rect.Left, "top":"%d" % rect.Top,
			                    "width":"%d" % (rect.Right - rect.Left),
			                    "height":"%d" % (rect.Bottom - rect.Top)})
