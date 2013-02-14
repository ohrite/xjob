# comprehend jobprofi.ini, load doculex tables
# Eric Ritezel -- December 15, 2006
# v0.5.0 -- Initial completion 20061219
# v0.7.0 -- Switched to internal XML structure 20070105
# v0.9.0 -- Incorporated more pre/num/suffix heuristics 20070108
# v0.9.5 -- Switched to dbfload to escape odbc dependence
# v0.9.9 -- Making changes to work with Pipeline expected output 20070225
#

import os, uuid, ConfigParser, xml.etree.ElementTree as ET
import glob
from dbfload import *

class Doculex:
	"""
	Class for loading DocuLex files.
	"""
	# map for doculex5.dbf standard column values
	# <xml element name>, <xml element attribute name>, <doculex5.dbf column name>
	valueMap = (("page","name","page_name"),
	            ("data","path","path"),
	            ("data","filename","filename"),
	            ("source","name","volume"))

	# search terms for JobProfi.ini
	# in form {"element name":{"<meta> name attribute":{'match':[<column>]}}}
	#
	# NOTES FOR MAINTAINERS
	# If you need to add a field name to look for, add it to the "match" field
	# You can see this below: under each <document> element,
	# a <meta> element will be created with name of "container" and a value of
	# whatever is in the "FILE TITLE" or "FILETITLE" columns
	# Obviously, namespace collisions default to the first row;
	# if there existed both "FILE TITLE" and "FILETITLE" columns, only the
	# "FILE TITLE" data would go to the value of <meta name="container" />
	searchTerms = {"document":{
                   "container":{"match":["FILE TITLE","FILETITLE"]},
                   "custodian":{"match":["CUSTODIAN"]},
                   "boxsource":{"match":["BOX SOURCE"]},
                   "source":{"match":["SOURCE"]}
                  },"page":{
                   "oversize":{"match":["DRAWINGS"]},
                   "color":{"match":["COLOR"]},
                   "bates_prefix":{"match":["Prefix", "PGPREFIX"]},
                   "bates_number":{"match":["Number", "BATESNUM"]},
                   "bates_suffix":{"match":["SUFFIX"]},
                   "file_prefix":{"match":["File Prfx"]},
                   "file_number":{"match":["File Num"]}
				  }}

	# document, attachment and folder-level status indicators
	reservedTerms = {"is_document": {"match":["DOC LVL"]},
					 "is_file": {"match":["FILE LVL"]},
					 "is_attachment": {"match":["ATTACH LVL"]}}

	def __init__(self):
		"""
		Creates a DocuLex producer based on path parameter.
		(Looks for JobProfi.ini, doculex5.dbf, indices5.dbf in path.)

		Parameters:
			path -- a directory containing the files we need
		"""
		# build an ini file parser for myself
		self.cp = ConfigParser.ConfigParser()

	def getvalidname(self, filename):
		""" See if we can load a given path. """
		if not os.path.exists(filename): return None

		temp = None

		# pack filenames with possible test files
		if os.path.isdir(filename):
			filenames = glob.iglob(os.path.join(filename, '*.[di][bn][fi]'))
		elif os.path.split(filename).split('.')[1] in ('dbf','ini'):
			filenames = (filename,)

		# test out each dbf file until we find one that contains PAGE_NAME
		# for example, both doculex5.dbf and indices5.dbf have it.  GEE!
		for fname in [f for f in filenames if f.split('.')[1] == 'dbf']:
			try:
				temp = DbfLoader() ; temp.open(fname)
				if "PAGE_NAME" not in temp.fieldNames(): raise Exception()
			except: continue
			finally:
				temp.close()
			return fname

		# try to pull out a standard term from the ini file (PAGE_NAME)
		for fname in [f for f in filenames if f.split('.')[1] == 'ini']:
			try:
				# build config parser
				inifile = open(fname, 'r')
				self.cp.readfp(inifile)

				# get mapping terms and try one out
				terms = self._LoadINI(self.cp)
				if terms['PAGE_NAME'] is None: raise Exception()
			except: continue
			finally: inifile.close()

			return fname

		return None

	def Read(self, path):
		"""
		Interface to both parsers -- doesn't bother validating because of above
		"""
		if not os.path.isdir(path): path = os.path.dirname(path)

		# set up file locations
		dlexIndex = os.path.join(path, "indices5.dbf")
		dlexMain = os.path.join(path, "doculex5.dbf")
		dlexJobProfi = os.path.join(path, "JobProfi.ini")

		# build config parser
		inifile = open(dlexJobProfi)
		self.cp.readfp(inifile)
		inifile.close()

		# get mapping terms and open data files with them
		terms = self._LoadINI(self.cp)
		dclx = DbfLoader(terms)
		dclx.open(dlexMain)

		indx = DbfLoader(terms)
		indx.open(dlexIndex)

		# load data from structure and close up
		self._LoadData(iter(dclx), iter(indx), path)
		dclx.close()
		indx.close()

		return self

	def _LoadINI(self, config):
		"""
		Process the JobProfi.ini file contents being passed in.
		Non-validating, but happily operating under the assumption that JobProfi was well-formed

		Parameters:
			config -- a ConfigParser object containing JobProfi.ini

		Returns:
			list[] - a list of terms to query for in the database
		"""
		# return a dict of terms to translate
		terms = {'PATH':'path','PAGE_NAME':'page_name','FILENAME':'filename','VOLUME':'volume','PAGE_NUM':'pagenum'}

		for sec in config.sections():
			for opt in config.options(sec):
				# get value from path
				value = config.get(sec, opt).strip()

				# see if we can add to the reservedTerms lookup table
				for tag in [v for v in self.reservedTerms if value in self.reservedTerms[v]["match"]]:
					self.reservedTerms[tag]["field"] = sec.upper()
					terms[sec.upper()] = tag.lower()

				# see if we can add to the searchTerms lookup table
				for tag in self.searchTerms:
					for attr in self.searchTerms[tag]:
						if value and value in self.searchTerms[tag][attr]["match"]:
							self.searchTerms[tag][attr]["field"] = sec.upper()
							terms[sec.upper()] = attr.lower()

		return terms

	def _LoadData(self, dclx, indx, path):
		"""
		pull the doculex data

		Parameters:
			dclx -- a dictionary-like element populated by doculex5.dbf
			indx -- a dictionary-like element populated by indices5.dbf
			path -- a relative path to the dbfs (usually the image root too)
		"""

		# row checking stuff "Is (row) A (...) In (...)?"
		check = (lambda row,field,state: row.get(field,"void") == state)

		# check for singleton (document starting/ending row | child of document)
		isSingleton = (lambda row,tree: not (check(row,"is_document","SD") or check(row,"is_document","ED") or (tree[-1].tag == "document")))

		# set generic warning message
		warn ="Expected to end %s, but %s still open."
		error="Critical failure: %s"

		# track the presence of a folder (drives folder vs. container)
		is_attach = False
		in_folder = False
		last_doc = None

		# kick off tree-depth tracking stack (we need this for back-references)
		self.XML = ET.Element("xjob")
		tree = [self.XML]

		# run the main doculex data pull
		row = dclx.next()
		row.update(indx.next())

		# map strip to all fields
		row.update(zip(row.keys(), map(lambda x: x.strip(), row.itervalues())))

		# set the document counter up
		doc_count = 1

		# set backtrace row counter to zero
		rowcount = 1

		while row is not None:
			# preload next row for document-ending lookahead
			try:
				nextrow = dclx.next()
				nextrow.update(indx.next())

				# map strip to all fields
				nextrow.update(zip(nextrow.keys(), map(lambda x: x.strip(), nextrow.itervalues())))
			except:
				nextrow = None

			# reset singleton flag
			singleton = False

			# if box has changed in the file (and pop until we hit the box
			if len(tree) > 1 and tree[0].attrib.has_key("name") and tree[0].attrib["name"] != row['volume']:
				while len(tree) > 2: build.end(tree.pop().tag)

			# if box is not set, get metadata from callback and set
			if tree[-1].tag == "xjob":
				tree.append(self.metadata(row, ET.SubElement(tree[-1],
				                          'source', id=str(uuid.uuid4()),
				                          type='doculex', href=path)))

			# check our folder state
			in_folder = (in_folder or check(row, "is_file", "SF")) and not check(row, "is_file", "EF")

			# check our attachment state
			is_attach = (is_attach or check(row, "is_attachment", "SA")) and not check(row, "is_attachment", "EA")

			# if a page has no parent element, set singleton flag
			singleton = isSingleton(row, tree)

			# if row starts a document or is a singleton
			if check(row, "is_document", "SD") or singleton:
				newid = str(uuid.uuid4())

				# build a document ; assign id and name
				tree.append(ET.SubElement(tree[-1], "document", id=newid))

				# bind last document tracker
				if is_attach and lastdoc is not None:
					tree[-1].attrib['parent'] = lastdoc
				else: lastdoc = newid

				# assign ordering information
				ET.SubElement(tree[-1], 'order', value=str(doc_count))

				# attach folder / container metadata
				if row.has_key('container'):
					meta = ET.SubElement(tree[-1], 'meta', value=row['container'])
					meta.attrib['type'] = (in_folder and ('folder',) or ('container',))[0]

				# assign searchable metadata to the document
				self.metadata(row, tree[-1])

			# assign searchable attributes to a new page element with preset id
			pgnode = ET.SubElement(tree[-1], 'page', name=row['page_name'], id=str(uuid.uuid4()))
			ET.SubElement(pgnode, 'order', value=str(rowcount))
			self.metadata(row, pgnode)
			self.metadata(row, ET.SubElement(pgnode, 'data'))

			# see if we have reason to end the document
			if nextrow is None or check(row, "is_document", "ED") or singleton:
				# ignore spurious end of document
				if tree[-1].tag == "document":
					# see if we can move the node to a parent now
					if tree[-1].attrib.has_key('parent'):

						# find parent for attachment vector
						mommy = [x for x in tree[-2].getchildren() \
						         if x.get('id') == tree[-1].get('parent')][0]

						# find/make attachment node
						attachnode = mommy.find('attachment')
						if attachnode is None:
							attachnode = ET.SubElement(mommy, 'attachment')

						# move node
						attachnode.append(tree[-1])
						tree[-2].remove(tree[-1])

					# yield document back to watcher
					#http://online.effbot.org/2004_12_01_archive.htm#element-generator
					#FIXME: not ready for this yet
					#else: yield tree[-1]

					# pop and increase the document counter
					tree.pop()
					doc_count += 1

			# advance loop
			row = nextrow
			rowcount += 1

	# --------------------------------------------------------------------
	# All the ugly work goes here

	def metadata(self, row, element):
		""" Build a list of child metadata nodes under the given element. """
		# extract valuemap mapping data to given node
		for att, col in [s[1:] for s in self.valueMap if (s[0] == element.tag)]:
			strips = ' '
			if att == "path": strips += os.path.sep
			element.attrib[att] = row[col].strip(strips)

		# check and see if the given element exists in the search terms
		if not element.tag in self.searchTerms.keys(): return element

		# see if we should special case on the bates number
		if element.tag == 'page' and row.get('bates_number', False):
			bates = [row.get('bates_number')]
			if row.get('bates_prefix'):bates.insert(0, row.get('bates_prefix'))
			if row.get('bates_suffix'):bates.append(row.get('bates_suffix'))
			ET.SubElement(element, 'number', type='bates', value=''.join(bates),
			              fields='|'.join(bates), lengths="|".join([str(len(x)) for x in bates]))

		# append metadata
		for term, value in [(a, row[a]) for a in self.searchTerms[element.tag]\
		     if "field" in self.searchTerms[element.tag][a] and row.get(a, 0)]:
		    # special case on container and bates
			if term in ('container','bates_number','bates_prefix','bates_suffix'): continue

			# create a metadata tag and pack the value mapping to it
			ET.SubElement(element, 'meta', {'type':term, 'value': value})

		return element

if __name__ == "__main__":
	datapath = r"C:\Users\remove\Desktop\test"
	data = Doculex()
	accesspath = data.getvalidname(datapath)
	if accesspath is not None:
		data.Read(accesspath)
		ET.ElementTree(data.XML).write(str(uuid.uuid1())+".xml")
