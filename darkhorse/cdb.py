# CDB implemented in python ... with a pythonic interface!
# Starting point provided by Yusuke Shinyama
# Eric Ritezel -- February 17, 2007
#
# 20070218 - longstream optimization started
#            there's something slow about this.  low memory usage, though.
# 20070219 - had dream that led to increased performance.
#

from struct import unpack, pack
import array

# calc hash value with a given key	(6.644s against 50k | 8.679s w/o psyco)
def calc_hash(string):
	h = 5381
	for c in array.array('B', string): h = ((h << 5) + h) ^ c
	return h & 0xffffffffL

# attempt to use psyco for binding calc hash -- not a big deal
try:
	from psyco import bind
	bind(calc_hash)
except:pass

class reader(object):
	"""
	This is a reader for the CDB system from Dave Bernstein.
	It is pythonic, and it doesn't follow his interface, but that's okay.

	THIS IS IN NO WAY THREAD SAFE -- DO NOT DOUBT THE MIGHTY FILESYSTEM

	Here's how it works:
	[header] <- 256 pairs of uint32 structures [absolute offset][length]
	 ...        positioning works like this: header[hash & 0xff]
	[header]
	[data] <- we're jumping over this;
	 ...      each data node consists of [key_length][value_length][key][value]
	[data]
	[hash_lookup_table]	<- there's 256 of these; they're full of babies
	 ...                   each one has [hash][absolute offset]
	 ...                   each is (2*entries) long for hash searches
	[hash_lookup_table]

	Usage:
	>>> (build a cdb)
	>>> read = reader("test.cdb")
	>>> print 'read["a key"] =', read["a key"]
	>>> for (key, value) in read.iteritems():
	...     print key, '= (',
	...     for values in value:
	...         print value + ',',
	...     print ')'
	"""
	def __init__(self, infile):
		"""Open the file connection."""
		if isinstance(infile, str): self.filep = open(infile, "r+b")
		else: self.filep = infile

		# attempt to read file from the start
		self.filep.seek(0)
		self.start = self.filep.tell()

		# get the least pos_bucket position (beginning of subtables)
		self.header = unpack('<512L', self.filep.read(2048))

		# find the end of the data
		self.enddata = min(self.header[0::2])

	def __get(self,index,single=True):
		return_value = []
		hash_prime = calc_hash(index)

		# pull data from the cached header
		headhash = hash_prime % 256
		pos_bucket= self.header[headhash + headhash]
		ncells = self.header[headhash + headhash + 1]

		# since the 256*8 bytes are all zeroed, this means the hash
		# was invalid as we pulled it.
		if ncells == 0: raise KeyError

		# calculate predictive lookup
		offset = (hash_prime >> 8) % ncells

		# set a die badly flag (throw key error)
		found = False

		# loop through the number of cells in the hash range
		for step in range(ncells):
			self.filep.seek(pos_bucket + ((offset + step) % ncells) * 8)

			# grab the hash and position in the data stream
			(hash, pointer) = unpack('<LL', self.filep.read(8))

			# throw an error if the hash just dumped us in the dirt
			if pointer == 0:
				# if there were no keys found, complain (else break)
				if not found: raise KeyError
				break

			# check that the hash values check
			if hash == hash_prime:
				# seek to the location indicated
				self.filep.seek(pointer)

				# fetch the lengths of the key and value
				(klen, vlen) = unpack('<LL', self.filep.read(8))
				key = self.filep.read(klen)
				value = self.filep.read(vlen)

				# make sure that the keys match
				if key == index:
					return_value.append(value)

					# if we're only looking for one item, break out
					if single: break

					# set found flag for multiple value end condition
					found = True

		# if there were no records hit, dump a keyerror
		else: raise KeyError

		# throw back a tuple of the values found for key
		return tuple(return_value)

	def __getitem__(self,index):
		# shortcut to __get
		if not isinstance(index, str): raise TypeError
		self.__get(index)

	def get(self,index,default=None):
		try:
			return self.__get(index,single=False)
		except:
			if default is not None: return default
			raise KeyError

	def has_key(self,index):
		"""A simple analog of the has_key dict function."""
		try:
			self.__get(index)
			return True
		except:
			return False

	def iteritems(self):
		"""A straight pull of the items in the cdb."""
		self.filep.seek(self.start + 2048)

		# iterate until we hit the enddata marker
		while self.filep.tell() < self.enddata - 1:
			# fetch the lengths of the key and value
			(klen, vlen) = unpack('<LL', self.filep.read(8))

			# yield the key and value as a tuple
			yield (self.filep.read(klen), self.filep.read(vlen))

	def close(self):
		"""Close out the file connection."""
		self.filep.close()

class builder(object):
	"""
	The Constant Database system is by DJB (the greatest hero on the interwub)
	I just happen to implement it here bceause it's 1.fast, 2.good, 3.fast.
	And I need all three aspects.

	Usage:
	>>> build = builder("test.cdb")
	>>> build['a key'] = 'some value n for stupid'
	>>> build.close()

	The resultant CDB is read by any compatible lib (including reader above)
	Access times are good, but can be made mucho faster with psyco.
	"""
	def __init__(self, infile):
		if isinstance(infile, str):
			self.filep = open(infile, "w+b")
		else: self.filep = infile

		# attempt to read file from the start
		self.filep.seek(0)
		self.start = self.filep.tell()

		# track pointers and hash table data
		self.hashbucket = [ array.array('L') for i in range(256) ]

		# skip past header storage (file header + 2048)
		self.position_hash = self.start + 2048
		self.filep.seek(self.position_hash)

	def __setitem__(self, index, value):
		"""CDB supports multiple values for each key.  Problems?  Too bad."""
		# create value and key storage
		self.filep.write(pack('<LL',len(index), len(value)))
		self.filep.write(index)
		self.filep.write(value)

		# grab a hash for the key
		hash = calc_hash(index)

		# dump a new hash into our bucket
		self.hashbucket[hash % 256].fromlist([hash, self.position_hash])
		self.position_hash += 8 + (len(index) + len(value))

	def close(self):
		from sys import byteorder
		# preinitialize array and find byteorder
		cell = array.array('L')
		shouldswap = (byteorder == 'big')

		# iterate completed values for the hash bucket
		for hpindex in [ i for i in xrange(256) ]:
			ncells = self.hashbucket[hpindex].buffer_info()[1]
			if ncells <= 0:
				self.hashbucket[hpindex].append(0)
				continue

			# create blank cell structure
			cell.fromlist([ 0 for i in xrange(ncells+ncells) ])

			# loop over hash pairs (xrange with parameters = fast)
			for i in xrange(0, ncells, 2):
				# pull hash from the hashbucket
				hash = self.hashbucket[hpindex].pop(0)

				# predictive lookup for jump
				index = (hash >> 8) % ncells

				# skip occupied cells
				while cell[index+index] != 0: index = (index + 1) % ncells

				# pull pointer and assign hash/pointer set to cell
				cell[index+index] = hash
				cell[index+index+1] = self.hashbucket[hpindex].pop(0)

			# push length back onto stack
			self.hashbucket[hpindex].append(ncells)

			# write the hash table (swap bytes if we're bigendian)
			if shouldswap: cell.byteswap()
			cell.tofile(self.filep)
			del cell[:]

		# skip to start of file
		self.filep.seek(self.start)

		# dump some information about the hash pairs into the header
		for i in xrange(256):
			self.filep.write(pack('<LL', self.position_hash, self.hashbucket[i][0]))
			self.position_hash += 8 * self.hashbucket[i].pop()

		# free up the hashbucket and cell
		del(cell)
		del(self.hashbucket)

		self.filep.close()

# a rather complete test suite
if __name__ == "__main__":
	import os,sys,time
	from random import randint, seed
	import hotshot, hotshot.stats

	# make python behave for our massive crunching needs
	sys.setcheckinterval(10000)

	# utility to write data
	def randstr(): return "".join([ chr(randint(65,90)) for i in xrange(randint(1,32)) ])

	def make_data(n):
		print "TEST: Making test data"
		return [ (randstr(),randstr()) for i in xrange(n)]

	def test_write(testlist, fname="test.cdb"):
		starttime = time.time()
		# initialize a builder system for a cdb
		print "TEST: Building CDB"
		a = builder(fname)

		# run the test
		for (item,value) in testlist: a[item] = value

		a['meat'] = "moo"
		a['meat'] = "baa"
		a['meat'] = "bow wow"
		a['meat'] = "mew"
		a['meat'] = "ouch"

		# close the builder
		a.close()

		print "TEST: %fs to run build" % (time.time() - starttime)

	def test_read(fname="test.cdb"):
		print "TEST: Doing read of",fname

		cdb = reader(fname)
		print 'TEST: Should be False: cdb["not a key"] =', cdb.has_key("not a key")
		if cdb.has_key("meat"):
			print 'TEST: Multiple values: cdb["meat"] =', cdb.get("meat")

		starttime = time.time()
		print "TEST: Reconstructing keys from database"
		testlist = {}
		for (key, values) in cdb.iteritems(): testlist[key]=None
		print "TEST: %fs to run fetch" % (time.time() - starttime)

		starttime = time.time()
		print "TEST: Reading",len(testlist),"entries by access key"
		for slug in testlist.keys(): cdb.get(slug)
		print "TEST: %fs to run fetch" % (time.time() - starttime)

		cdb.close()

	def test_massive(testlist, fname="stress.cdb", massive=10**5):
		starttime = time.time()
		print "TEST: Massive stress test for large databases (%d entries)" % massive
		a = builder(fname)
		for i in xrange(massive):
			a[testlist[i%len(testlist)][0]] = testlist[i%len(testlist)][1]
			if not i % (massive / 37): print '.', #print "%3.1f%% complete" % (float(i) / (5*(10**6))*100)
		a.close()
		print 'done'
		print "TEST: %fs to run write" % (time.time() - starttime)

##############################################
###############TESTSUITEBLOCK#################
##############################################

	data = make_data(1000)
	test_massive(data, massive=10000)
	del(data)
	test_read(fname='stress.cdb')
	exit(1)

	# launch profiler test suite
	prof = hotshot.Profile("pycdb.prof")
	data = make_data(500000)
	prof.runcall(test_write, data)
	prof.runcall(test_read)
	prof.runcall(test_massive, data, massive=500000, fname="stress.cdb")
	prof.runcall(test_read, fname="stress.cdb", nomeat=True)
	prof.close()

	print "TEST: Loading hotshot stats"
	stats = hotshot.stats.load("pycdb.prof")
	stats.strip_dirs()
	stats.sort_stats('time', 'calls')
	stats.print_stats(20)
