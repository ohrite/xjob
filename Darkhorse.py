# Dark Horse export utility
# Eric Ritezel -- February 14, 2007
# Based on code by Matt Lupfer, Moon Yee, Phil Culliton, Garett , &al.
#

import tempfile
import os, socket
import xml.etree.ElementTree as ET
import Image
import pymssql

from darkhorse import queries as DHQuery, DBWorker
from darkhorse.cdb import reader as DBReader

class DarkHorse:
	"""
	Run an export job with the supplied parameters.
	Gets a settings message and an <xjob><export>...</export></xjob> message.

	Called like this:
	>>> tempdirectory = tempfiles.mkstmp()
	>>> settingsdef = ElementTree.fromstring("<settings><export><GetNatives /></export></settings>")
	>>> xjobdef = ElementTree.fromstring("<xjob><export domain="qa1" firm="1" case="211" view="4" /></xjob>")
	>>> dhexport = DarkHorse(settings=settingsdef, xjob=xjobdef)
	>>> dhexport.write('pre-render.xjob')
	>>> for files in dhexport.iterfiles():
	...     output = open(os.path.join(tempdirectory, os.path.basename(files['native'])), 'wb')
	...     output.write(files['native'].read())
	...     files['native'].close()
	...     output.close()

	It can create a very simple dhexport tool.  But when used in other ways,
	it can cure cancer, deliver babies, make coffee and remove stains.
	"""

	__DarkHorseServers = ET.fromfile('DHServers.xml')

	def __init__(self, settings, xjob):
		# make sure the xjob has an export branch
		exportbase = xjob.find('.//export')
		if exportbase is None: raise ValueError("XJOB has no export branch.")

		# pull in all the basic parameters
		ET.dump(exportbase)
		self.firm = exportbase.attrib.get('firm',None)
		self.case = exportbase.attrib.get('case',None)
		self.view = exportbase.attrib.get('view',None)
		self.domain = exportbase.attrib.get('domain',None)

		# try to pull server
		for server in DarkHorse.__DarkHorseServers.findall('.//domain'):
			if server.get('id','') == self.domain:
				thisserver = server

		# set up database info
		try:
			self.dbinfo = {
				'host':thisserver.find('sql').text,
				'user':thisserver.find('user').text,
				'password':thisserver.find('password').text,
				'database':thisserver.get('prefix')
			}
			if self.dbinfo['password'] is None: self.dbinfo['password'] = ''
		except:
			raise ValueError("Domain %s is not valid." % self.domain)

		# open connection to get root paths
		globalconnection = pymssql.connect(
			host=self.dbinfo['host'],user=self.dbinfo['user'],
			password=self.dbinfo['password'],
			database=self.dbinfo['database']+'GlobalData')

		print 'made connection'

		# get root paths
		cur = globalconnection.cursor()
		cur.execute(DHQuery.GetRoots % {'firm':self.firm,'case':self.case})

		print 'executed cursor'

		# make sure that we have pulled information
		data = cur.fetchone()
		if data is None: raise ValueError("Cannot pull global connection info for FirmID=%05d + CaseID=%05d" % (self.firm, self.case))

		# close the cursor and connection
		cur.close()
		globalconnection.close()

		# set self.ImageFileStore and self.FileStore attributes
		# FIXME: this only works on windows because of UNC
#		for (name, path) in (("ImageFileStore",data[0]), ("FileStore",data[1])):
#			path = r'\\'+socket.gethostbyname(row.split('\\')[2])+'\\'
#			self.setattr(name, path+"%s\\%05d\\%05d" % (name, self.firm, self.case))

		# open connection
#		self.connection = pymssql.connect(
#			host=self.dbinfo['host'],user=self.dbinfo['user'],
#			password=self.dbinfo['password'],
#			database=self.dbinfo['database']+'%05d%05d'%(self.firm,self.case))

	def Populate(self, xjob, settings):
		"""
		Public:
			Takes an incoming export structure and fleshes out the following:
			* Node structure (attachments)
			* Metadata for each node (data)
			* Parameters for each node (bates/id/fileid/transfileid)
		Parameters:
			xjob -- a mutable ElementTree to store the pulled data
		"""

		# set the base node for population
		base = xjob.find(".//export")

		# set up tracking semaphores and lock for the first time
		attsem = BoundedSemaphore(2)
		batesem = BoundedSemaphore(2)
		docnumsem = BoundedSemaphore(2)
		fileidsem = BoundedSemaphore(2)
		for s in (attsem, batesem, docnumsem, fileidsem): s.acquire()

		# cache all attachment ids
		atts = DBWorker(self.dbinfo, DHQuery.Attachments, pymssql, attsem)
		docnums = DBWorker(self.dbinfo, DHQuery.DocNumbers, pymssql, docnumsem)
		bates = DBWorker(self.dbinfo, DHQuery.BatesNumbers, pymssql, batesem)
		data = DBWorker(self.dbinfo, DHQuery.DocData, pymssql, datasem)

		# start all jobs in the background
		for obj in (atts, docnums, bates, data): obj.start()

		# set up query and resolve parameters
 		query = DHQuery.GetDocuments % {'view':base.get('view')}

		# build the basic layout of the documents
		for (did, mod, numpages,file,tfile) in ResultIter(self.cursor, query):
			doc = SubElement(base, 'document', id=did)
			if mod: doc.attribs['modified'] = 'modified'
			if file: doc.attribs['file'] = file
			if tfile: doc.attribs['translated'] = tfile
			for i in xrange(numpages): SubElement(doc, 'page')

		# write the element to disk
		xjob.write('pass1.xjob')

		# while the semaphores haven't been released twice
		while (attsem + docnumsem + batesem + datasem) < 8:
			if attsem == 1:
				# loop through disk cache and razor out non-attached nodes
				for document, key in [(x, x.get('id')) for x in base.getiterator('document') if atts.has_key(x.get('id'))]:
					attachnode = SubElement(document,'attachment')

					# reparent nodes from root to newly-created attachment vector
					for child in [y for y in base[:] if x.tag == 'document' and y.get('id') in atts.get(key)]:
						attachnode.append(child)
						base.remove(child)
				attsem.release()

			# add id number nodes to document node
			elif docnumsem == 1:
				for document in [x for x in base.getiterator('document')]:
					for did in [y for y in docnums[document.get('id')]]:
						document.SubElement('did', id=did)
				docnumsem.release()

			# add bates number node to document node
			elif batesem == 1:
				for document in [x for x in base.getiterator('document')]:
					for bnum in [y for y in bates[document.get('id')]]:
						document.SubElement('bates', id=bnum)
				batesem.release()

			# add data
			elif datasem == 1:
				for document in [x for x in base.getiterator('document')]:
					datanode = ET.SubElement(document, 'data')
					for datum in [y for y in data[document.get('id')]]:
						datanode.attribs[datum[0]] = datum[1]
				datasem.release()

			# go to bed for 5 seconds
			time.sleep(5)

		# write the element to disk
		xjob.write('pass2.xjob')
		print "it finally works!"

	def iterfiles(self):
		"""
		Generate a dict of file names / URIs from the database.
		It's up to the user to handle what they are.  We just get them.
		"""
		return
		while 1:
			# fetch the file names into a dict
			fndict['native'] = x
			fndict['translated'] = x
			fndict['fulltext'] = x

			# pull pages
			fndict['pages'] = [page for page in pages]

			# yield the dict
			yield fndict


if __name__ == "__main__":
	# set up test object settings
	__DarkHorseTestSettings = ET.fromstring("""\
		<settings>
			<export>
				<OrderByID />
				<CopyImages />
				<CopyNative />
				<CopyText />
			</export>
			<page>
				<SameAsIDNumber />
			</page>
			<file>
				<DontRenameNatives />
				<SameAsPageName />
			</file>
			<directory>
				<NativesDirectory>NATIVES</NativesDirectory>
				<TextDirectory>TEXT</TextDirectory>
			</directory>
		</settings>""")

	# set up test parameters
	__DarkHorseTestParameters = ET.fromstring("""\
		<xjob>
			<export domain="qa1" firm="1" case="211" view="4" />
		</xjob>""")

	# make temporary directory dictionary
	tempdir = {'native': tempfile.mkdtemp(),
	           'fulltext': tempfile.mkdtemp(),
	           'image': tempfile.mkdtemp()}

	# initialize DarkHorse engine
	dhexport = DarkHorse(settings=__DarkHorseTestSettings, xjob=__DarkHorseTestParameters)

	# grab file batches from DarkHorse
#	for files in dhexport:
		# flip through keys present in files
#		for key in [key for key in tempdir.keys() if files.has_key(key)]:
			# open output file (in temporary directory) against filename
#			output = open(os.path.join(tempdir[key], files[key]['filename']), 'wb')

			# dump data into file
#			output.write(files[key]['data'])

			# close output file
#			output.close()
