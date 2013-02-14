# Settings XML handler
# Now with pythonic accessors
# Eric Ritezel - January 4, 2007
#
# class Settings
#	-> __init__()
#	-> __getitem__()
#	-> __setitem__()
#	-> findall()

import xml.etree.ElementTree as ET

import uuid, threading

class Settings (object):
	"""
	A handler class for XJOB settings.
	"""
	exclude = { "page":("SameAsCapturedBates","SameAsIDNumber","Custom"),
				"file":("SameAsPageName","SameAsCapturedFilename","Custom"),
				"directory":("JFS","SFCityAttorney","BoxDirectories","UserDefinedNumber")}

	exclusive = lambda _, parent, node: (Settings.exclude.has_key(parent) and node in Settings.exclude[parent])

	def __init__(self):
		"""
		Creates a new settings container (with nearly blank structure)
		"""
		self._settings = ET.Element("settings",id=str(uuid.uuid1()), rev="0")

		# set up a thread lock
		self.session = threading.RLock()

	def __setitem__(self, index, value):
		"""
		A setter method for the settings class (now with pythonic semantics)

		Parameters:
			index -- a string 2-tuple representing the branch in the tree
					 OR! a fake-XPath (ie. 'foo/bar')
			value -- some value
		"""
    	# make sure the access is valid
		if isinstance(index, tuple) and len(index) == 2:
			branch, node = index
		elif isinstance(index, str) and index.find('/') != -1:
			branch, node = index.split('/', 2)
		else: raise ValueError("Incorrect index for settings access.")

		# set our destroy mode
		destroy = (value is False or value == '')

		# get the lock
		self.session.acquire()
		try:
			# update revision
			self._settings.attrib['rev'] = str(int(self._settings.attrib['rev'])+1)

			# search for child named _tab_ in settings, or create it if not found
			try:
				section = self._settings.getiterator(branch)[0]
			except:
				if not destroy: section = ET.SubElement(self._settings, branch)

			# search for child named _setting_ in tree or make a new one
			try:
				child = section.getiterator(node)[0]
				if destroy: section.remove(child)
			except:
				# make sure we've got something to do
				if not destroy:
					# prune exclusive nodes from branch
					map(section.remove,[x for x in section.getchildren() if self.exclusive(section.tag, x.tag)])

					# strip value if names are in play
					if node in ("CustomName","Name") and branch in ("file","page","volume"):
						value = value.strip()

					# add node to section and set value
					child = ET.SubElement(section, node)

			# see if we should set a value
			if not destroy and value != True: child.text = str(value)

			# prune empty section
			if not len(branch): self.settings.remove(section)

		# release the lock
		finally: self.session.release()

	def __getitem__(self, index):
		""" Ignore thread safety and just start grabbing data """
    	# make sure the access is valid
		if isinstance(index, tuple) and len(index) == 2:
			branch, node = index
		elif isinstance(index, str) and index.find('/') != -1:
			branch, node = index.split('/', 2)
		else: raise ValueError("Incorrect index for settings access.")

		# return the first value that occurs (None if there's an error)
		try:
			rv = self._settings.getiterator(branch)[0].getiterator(node)[0]
			if rv.text: result = rv.text
			else: result = True
		except: result = None

		return result

	def section(self, param):
		"""
		Public:
			Proxy for ElementTree XPath access.
		Parameters:
			param -- xpath for ElementTree access
		"""
		# get the lock
		self.session.acquire()

		try: result = self.settings.getiterator(param)[0].tostring()
		except: result = None

		# release the lock
		finally: self.session.release()

		return result

	def getrevision(self):
		""" Revision accessor for version checking """
		self.session.acquire()
		try: result = self._settings.attrib['rev']
		finally: self.session.release()
		return result