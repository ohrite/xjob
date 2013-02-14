# Conversion of Embed to the Pipeline system
# Eric Ritezel -- February 25, 2007
#

# test for Imaging and ctypes
_HaveImage = True
try: import Image, ImageFont, ImageDraw, ctypes
except: _HaveImage = False

import sys, os, shutil, tempfile, xml.etree.ElementTree as ET

import plugin

class EmbedPlugin(plugin.Plugin, object):
	"""
	A Pipeline plugin to run Embedding on an XJOB's pages.
	This is an inline image operation for now, but depending on where
	it shows up in the pipeline, that may change.

	If the data is coming over the wire, the following steps are needed:
	>>> pl.AddTask(xjob.tasks.ProcessByPage)
	>>> pl.AddTask(xjob.tasks.WritePageData)
	>>> pl.AddTask(xjob.tasks.EmbedPlugin)
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

		# see if we can run embedding
		if _HaveImage and sys.platform == "win32":
			dllroot = os.path.join(os.path.dirname(__file__), "dlls")
			updllroot = os.path.join(dllroot, '..','..','dlls')

			# look in one of our child directories for dlls
			if os.path.isdir(dllroot):
				os.environ["PATH"] = dllroot + os.pathsep + os.environ["PATH"]
				self.canEmbed = True

			# try to look in the grandparent directory
			elif os.path.isdir(updllroot):
				os.environ["PATH"] = updllroot + os.pathsep + os.environ["PATH"]
				self.canEmbed = True

			# fail
			else: self.canEmbed = False

		# set up the font and a new embed object
		if self.canEmbed:
			fontname = "arial.ttf"
			unifont = "msgothic.ttc"

			# ISO 639-1 compatible naming (tee)
			if kwargs.has_key('language'):
				if kwargs['language'] in ('zh', 'ja', 'ko', 'ru', 'gr'):
					unifont = "msgothic.ttc"

			# fire up the embedding engine
			self._embed = Embed(fontname=fontname, unifont=unifont)

			# set default settings
			self.rotatelandscape = True

	def canhandle(self, xjob):
		""" See if a) we can actually run Embedding and b) if it needs it. """
		print "hit embed handler with haveimage:", _HaveImage, " canEmbed:", self.canEmbed, " ops/Embed", self.settings['operations/Embed']
		return _HaveImage and self.canEmbed and self.settings['operations/Embed'] is not None

	def handle(self, level, xjob):
		""" Embed an xjob object. """
		# see if our settings revision checks out, fetch settings otherwise
		rev = int(self.settings.getrevision())
		if self.revision != rev:
			self.revision = rev

			# grab Rotation preference
			if self.settings['operations/RotateLandscape'] is not None:
				self.rotatelandscape = True
			else: self.rotatelandscape = False

			# grab the default embeds
			# FIXME: need good interface for this
			embednames=('level', 'horizontal', 'vertical', 'type', 'attribute', 'value')
			self.masterembeds = [zip(embednames, es.split(',')) for es in \
			                     self.settings['operations/EmbedStrings'].split(';')]

		# get the basepath for file-level interaction
		basepath = xjob.find('source').get('temphref', xjob.find('source').get('href'))

		# define some convenient accessors
		doc = xjob.find('.//document')

		for page in xjob.itertag('page'):
			# blank temporary sequence
			embeds = []

			# get embedding parameters
			for embed in self.masterembeds:
				# page-level text (an attribute of page; that's all it has)
				if embed['level'] == 'page':
					# spurious for-loop to reave meta/number attribute
					for term in [x for x in ('meta', 'number') if embed.has_key(x)]:
						for search in [x for x in page.getchildren() if x.tag == term]:
							if search.get('type') == embed[term]:
								value = search.get(embed.get('attribute','value'))

				# doc-level text (an attribute of document or a node->attrib)
				elif embed['level'] == 'document':
					# spurious for-loop to reave meta/number attribute
					for term in [x for x in ('meta', 'number') if embed.has_key(x)]:
						for search in [x for x in doc.getchildren() if x.tag == term]:
							if search.get('type') == embed[term]:
								value = search.get(embed.get('attribute','value'))

				# static embed (fixed text)
				elif embed['level'] == 'static':
					value = embed['value']

				# attach new embedding value
				embeds.append((value, embed['horizontal'], embed['vertical']))

			# run embedding
			embedder.Run(basepath, page, embeds)

		# pass xjob along
		yield xjob

class Embed:
	"""
	Main workhorse code to hook into libTIFF and the Python Imaging Library.
	This writes some parameters onto the given images.
	It is a permanent modification.
	"""
	ltiffconst = {
		'Compression':259,
		'CCITTFAX4':4,
		'ImageWidth':256,
		'ImageLength':257,
		'BitsPerSample':258,
		'Photometric':262,
		'MinIsWhite':1,
		'SamplesPerPixel':277,
		'RowsPerStrip':278,
		'FillOrder':266,
		'MSB2LSB':1,
		'PlanarConfig':284,
		'Contiguous':1,
		'XResolution':282,
		'YResolution':283,
		'ResolutionUnit':296,
		'Inch':2
	}

	def __init__(self, fontname="arial.ttf", fontsize=55, unifont=None):
		"""
		A new embedding object that defaults to Arial 40pt (for 300dpi images)
		"""
		# create new libtiff3 instance
		if sys.platform == "win32":
			dllroot = os.path.join(os.path.dirname(__file__), "dlls")
			updllroot = os.path.join(dllroot, '..','..','dlls')
			up2dllroot = os.path.join(dllroot,'..','..','..','dlls')
			if os.path.exists(os.path.join(dllroot, 'libtiff3.dll')):
				os.environ["PATH"] = dllroot + os.pathsep + os.environ["PATH"]
			elif os.path.exists(os.path.join(updllroot, 'libtiff3.dll')):
				os.environ["PATH"] = updllroot + os.pathsep + os.environ["PATH"]
			elif os.path.exists(os.path.join(up2dllroot, 'libtiff3.dll')):
				os.environ["PATH"] = up2dllroot + os.pathsep + os.environ["PATH"]
			else: raise Exception("PATH NOT FOUND!")

		self.libtiff = ctypes.cdll.libtiff3

		# set up the font for this session
		self.font = ImageFont.truetype(fontname, fontsize)
		if unifont is not None:
			self.unifont = ImageFont.truetype(unifont, fontsize, encoding="unicode")
		else: self.unifont = self.font

	def __WriteTIFF(self, filename, im):
		# try to open a new temp file for writing with libtiff
		tif = self.libtiff.TIFFOpen(filename, "w")
		if not tif: raise IOError("libtiff failed to open the file")

		# set some basic tags before adding data
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['ImageWidth'], im.size[0])
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['ImageLength'], im.size[1])
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['BitsPerSample'], 1)
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['SamplesPerPixel'], 1)
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['RowsPerStrip'], im.size[1])

		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['Compression'], Embed.ltiffconst['CCITTFAX4'])
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['Photometric'], Embed.ltiffconst['MinIsWhite'])
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['FillOrder'], Embed.ltiffconst['MSB2LSB'])
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['PlanarConfig'], Embed.ltiffconst['Contiguous'])

		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['XResolution'], 300)
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['YResolution'], 300)
		self.libtiff.TIFFSetField(tif, Embed.ltiffconst['ResolutionUnit'], Embed.ltiffconst['Inch'])

		# do some ctype calculations
		mainbuf = ctypes.create_string_buffer(im.tostring())
		imglen = ctypes.sizeof(mainbuf)

		# Write the information to the file
		result = self.libtiff.TIFFWriteEncodedStrip(tif, 0, mainbuf, imglen)
		if result < 0: raise IOError("libtiff failed to write the file back")

		# Close the file
		self.libtiff.TIFFClose(tif)

	def __LoadTIFF(self, data, im):
		"""
		Private:
			Loads a TIFF or JPEG image and returns an instance
		Parameters:
			filename -- An incoming filename
		"""
		# try to open the file again with libtiff
		tif = self.libtiff.TIFFOpen(data, "r")
		if not tif: raise IOError("libtiff failed to open the file")

		# create a new image
		out = Image.new(im.mode, im.size, None)

		# allocate transfer buffer
		bufsize = self.libtiff.TIFFStripSize(tif)
		buf = ctypes.create_string_buffer(bufsize)

		# make sure that PIL and libtiff agrees on the layout
		if self.libtiff.TIFFNumberOfStrips(tif) != len(im.tile):
			raise IOError("wrong number of strips")

		# min is white if getscalar(262, 0) returns a value
		rawmode = (im.tag.getscalar(262, 0) and ('1',) or ('1;I',))[0]

		# copy strips to the PIL image
		for strip, tile in enumerate(im.tile):
			compression, bbox, offset, info = tile
			result = self.libtiff.TIFFReadEncodedStrip(tif, strip, buf, -1)
			if result < 0:
				raise IOError("libtiff failed to read strip")
			size = bbox[2]-bbox[0], bbox[3]-bbox[1]
			tile = Image.frombuffer(im.mode, size, buf, "raw", rawmode)
			out.paste(tile, bbox)

		self.libtiff.TIFFClose(tif)

		# update source image object
		im.tile = []
		im.im = out.im

		return im

	def Run(self, basepath, xjob, embeds, rotate=0):
		"""
		Public:
			Write the given embeds against a page Element's file.
			Optionally, rotate landscape images before writing
		Parameters:
			basepath -- a file descriptor object (ie cStringIO)
			xmlparam -- an ElementTree parameter containing a <page> element
			settings -- an ElementTree parameter containing a <settings> element
		"""
		# define a path to the image
		path = os.path.join(basepath, xjob.find('data').get("path"), xjob.find('data').get("filename"))

		# load image with PIL
		im = Image.open(path)

		# load image with libtiff
		waslibTIFF = False
		if im.format == "TIFF" and im.tile and im.tile[0][0] in ("group3","group4"):
			waslibTIFF = True
			self.__LoadTIFF(path, im)
		else: im.load()

		# we process in portrait mode, so rotate 90 degrees
		if rotate and im.size[0] > im.size[1]:
			im = im.rotate(270)

		# get size
		width, height = im.size

		# get letter mode (coef. 0.772727 ~ 8.5/11)
		# FIXME: don't just throw the correction value away
		correction = float(width / height) - 0.772727

		# FIXME: get DPI by dividing height by 11?  that sucks!
		if im.info.has_key('dpi'): dpi = im.info["dpi"][1]
		elif -0.1 < correction < 0.1: dpi = (im.size[1] / 11.0)
		else: dpi = 300 # ?

		# build parameter stack for each edge
		positions = ([],[],[],[],[],[])

		# instantiate drawing surface
		draw = ImageDraw.Draw(im)

		# shrink picture to not intersect tagging
		copyimg = im.copy()
		im.paste('#fff',(0,0,width,height))

		# create a bounding box for the image to sit inside
		newy = newheight = 0

		# get an approximation of the maximum height of a string
		stringheight = (dpi * 0.075) + self.font.getsize('^EREIAMjhg|')[1]

		# get location for writing strings
		for string, xpos, ypos in embeds:
			# calculate position (starts at upper left)
			idx = 0
			if xpos == 'center': idx = 1
			elif xpos == 'right': idx = 2
			if ypos == 'bottom': idx += 3

			# if the string might not fit, test for overflow
			if len(string) > 40:
				try:
					str(string)
					thisfont = self.font
				except: thisfont = self.unifont

				# if the rendered text is greater than the image width
				strw = thisfont.getsize(string)[0]
				while strw > width:
					dangling = int(len(string) * width/strw)
					for i in xrange(dangling - 10, 0, -1):
						if i <= len(string) - dangling: splt = 0 ; break
						if string[i] in " \\/.:|-": splt = i ; break

					# if we're just spinning our wheels, split clean
					if not splt: splt = dangling - 1

					# split and append
					positions[idx].append(string[0:splt].strip())
					string = string[splt:]
					strw = thisfont.getsize(string)[0]

			# insert into holder list
			positions[idx].append(string)

		# get offsets from top and bottom
		try: yoff = len(max(positions[0:2], key=len))
		except:yoff = 0
		try: hoff = len(max(positions[3: ], key=len))
		except:hoff = 0

		# calculate new bounding box if offset needed (otherwise not)
		newy = int((yoff * stringheight) + (dpi * 0.0001))
		newheight= height - int((hoff * stringheight) - (dpi * 0.0001))

		# resize the copied image and paste it into the original
		copyimg.thumbnail((width, newheight - newy))
		im.paste(copyimg, (int((width - copyimg.size[0]) / 2.0), newy))

		# positioning logic for embedding strings
		positionlogic = (
			lambda x, _, f: dpi*.1,
			lambda x, p, f: (width / 2) - (f.getsize(positions[p][x])[0] / 2),
			lambda x, p, f: width - f.getsize(positions[p][x])[0] - (dpi * .1),
			lambda y, p, f: y * stringheight,
			lambda y, p, f: height - (len(positions[p]) - y) * stringheight
		)

		# embed everything in one go
		for pos in xrange(6):
			for i in xrange(len(positions[pos])):
				# see if we need unicode for this operation
				try:
					str(positions[pos][i])
					thisfont = self.font
				except: thisfont = self.unifont

				# draw the text
				draw.text((positionlogic[pos % 3](i, pos, thisfont),
						   positionlogic[(pos/3) + 3](i, pos, thisfont)),
						   positions[pos][i], fill='#000',
						   font=thisfont)

		# if embed has other parameters, handle those
		if waslibTIFF: self.__WriteTIFF(path, im)
		else: im.save(path, format=im.format)
