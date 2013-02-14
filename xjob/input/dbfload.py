# Loader class for DBF files (via dbfpy)
# Eric Ritezel -- January 15, 2007
# adds dictionary mapping
# adds iteration
# v0.1.0 -- Major cleanup and switch to struct module (20070227)
#

import struct

class DbfLoader:
	"""
	Loads the contents of a dbf file into memory
	After successful load, the following info is available:
		self.fileName
		self.version
		self.lastUpdate	('mm/dd/yy')
		self.recordCount
		self.headerLength
		self.recordLength
		self.fieldDefs      (list of DbfFieldDef objects)
		self.fieldNames()
		self.fieldInfo()    (list of (name, type, length, decimalCount))
		self.allRecords
		self.allRecordsAsDict
		self.recordStatus
	"""

	def __init__(self, mapterms=None):
		# set storage list for field definitions and copy mapping terms
		self.fieldDefs = []
		self.fieldMap = (mapterms is not None and (mapterms,) or ({},))[0]

		# set file name
		self.dbfs = None

	def open(self, filename):
		"""
		Private:
			Read and decode dbf header data from input stream
		Params:
			dbfs -- a dbf file handle
		"""
		self.index = 0

		# attempt open of file
		try: self.dbfs = open(filename, 'rb')
		except: raise Exception("File not found:", filename)

		# read a version number from the file
		self.version = ord(self.dbfs.read(1))

		# set last updated year, month, day bytes from file
		self.lastUpdate = "%2d/%2d/%2d" % struct.unpack('3B', self.dbfs.read(3))

		# read record count and lengths from file
		self.recordCount, self.headerLength, self.recordLength = \
		struct.unpack('<IHH', self.dbfs.read(8))

		# read junk data into /dev/null
		self.dbfs.read(20)

		# set the start point to jump past the delete flag
		start = 1

		for fn in xrange(33, self.headerLength, 32):
			fd = DbfFieldDef()
			fd.readFieldDef(self.dbfs, start)

			# try to map field name to new name
			fd.name = self.fieldMap.get(fd.name, fd.name)
			self.fieldDefs.append(fd)
			start = fd.end

		# read additional junk data
		self.dbfs.read(1)

		return self

	def close(self):
		"""
		Clean up after dbfs and variables
		"""
		if self.dbfs is not None: self.dbfs.close()
		self.fieldDefs = None
		self.filename = None
		self.fieldMap = None

	def read(self):
		""" Completes the file protocol: just dumps all the records. """
		retval = []

		while len(retval) < self.recordCount:
			# input data
			rawrec = self.dbfs.read(self.recordLength)

			# decode data and append to dictionary
			dictrec = {}
			for fd in self.fieldDefs:
				dictrec.update(fd.decodeValue(rawrec))

			retval.append(dictrec)

		return retval

	def __iter__(self):
		""" Protocol for iteration """
		# make sure we have a file handle and info
		if not getattr(self, "dbfs", False): self.open()
		return self

	def next(self):
		# if iteration is complete, close file and stop iteration
		if self.index == self.recordCount:
			self.close()
			raise StopIteration

		# input data
		rawrec = self.dbfs.read(self.recordLength)

		# decode data and append to dictionary
		dictrec = {}
		for fd in self.fieldDefs:
			dictrec.update(fd.decodeValue(rawrec))

		# return one dictionary row of data
		self.index += 1
		return dictrec

	def fieldNames(self):
		"""
		Public:
			Get a list of the dbf file's member file names
		"""
		return[x.name for x in self.fieldDefs]

	def fieldInfo(self):
		"""
		Public:
			Get a list of the information of the fields in the file
		Returns:
			4-tuple list of field information.
				[(name, type, length, decimalCount),...]
		"""
		return([fd.fieldInfo() for fd in self.fieldDefs])


class DbfFieldDef (object):
	def __init__(self):
		self.length = None
		self.start = None
		self.end = None
		self.decimalCount = None
		self.name = ''

	def readFieldDef(self, dbfs, start):
		"""
		Read and decode dbf field information from file handle.

		Params:
			dbfs -- a file handle
			start -- index to start reading from
		"""
		# read field name
		self.name = dbfs.read(11)

		# trim null bytes off name
		while (self.name[-1:] == '\000'): self.name = self.name[:-1]

		# read type byte (C/D/N/M?)
		self.type = dbfs.read(1)

		dbfs.read(4)
		self.length = ord(dbfs.read(1))
		self.start = start
		self.end = start + self.length
		self.decimalCount = ord(dbfs.read(1))
		dbfs.read(14)

	def fieldInfo(self):
		"""
		Get 4-tuple list of field information
		"""
		return((self.name, self.type, self.length, self.decimalCount))

	def decodeValue(self, rawrec):
		"""
		decode and output a list of field values from rawrec
		"""
		# get raw value from record using markers (then strip)
		rawval = rawrec[self.start:self.end]

		if (self.type == 'C'): 		#string
			pass
		if (self.type == 'D'): 		#date 'yyyymmdd'
			pass
		if (self.type == 'N'): 		#numeric
			if (self.decimalCount == 0):
				# there's no decimal, so process integer
				rawval = rawval.strip()
				if len(rawval):
					try: rawval = int(rawval)
					except ValueError: rawval = long(rawval)
				else: rawval = 0
			else:
				# rv1 = before decimal, rv2 = after
				rv1 = rawval[:-self.decimalCount].strip()
				rv2 = rawval[-self.decimalCount:]
				rawval = rv1+'.'+rv2
				if (rawval=='.'): rawval = 0.0
				else: rawval = float(rawval)
		return {self.name: rawval}
