# worker system for caching database values to disk
# Eric Ritezel -- February 19, 2007
#

import cdb
import threading
import cPickle

# define a small iterator for fetchmany
def ResultIter(cursor, query, arraysize=1000):
	cursor.execute(query)
	while True:
		results = cursor.fetchmany(arraysize)
		if not results: break
		for result in results: yield result

class DBWorker(threading.Thread):
	"""
	This worker system connects to the specified database using the given
	module,	runs the given query, dumps the result into a CDB.
	When it finishes, it pegs the callback with a filename.

	>>> from dbworker import DBWorker
	>>> from pymssql import pymssql
	>>> from cdb import reader
	>>> def done(filename):
	>>>     a = reader(filename)
	>>>     for k,v in a.iteritems(): print k,'=',v
	>>>
	>>> db = {'db':'v','uname':'x','pwd':'y','server':'z'}
	>>> wkr = DBWorker(dbinfo=db, query=dbquery, module=pymssql, callback=done)
	>>> wkr.start()
	"""
	def __init__(self, dbinfo, query, module, semaphore, prefix=''):
		# assign all data
		self.prefix = prefix
		self.query = query
		self.semaphore = semaphore
		self.connection = module.connect(
			host=dbinfo['host'], user=dbinfo['user'],
			password=dbinfo['password'], database=dbinfo['database'])
		self.cursor = self.connection.cursor()

	def run(self):
		# acquire semaphore lock
		self.semaphore.acquire()

		# set up temporary database
		tfile = tempfile.mkstmp(prefix=self.prefix+'_')
		build = cdb.builder(tfile)

		# yank data from remote connection and throw it into cdb
		for row in ResultIter(self.cursor, self.query):
			if len(row) > 2:
				build[row[0]]=cPickle.dumps(tuple(row[1:]))
			else:
				build[row[0]]=row[1]

		# close and finish connections
		for obj in (self.cursor, self.connection, build): obj.close()

		# peg callback with filename
		self.callback(self, tfile)

		# destroy memory soaks
		del(self.cursor)
		del(self.connection)

		# release semaphore lock
		self.semaphore.release()
