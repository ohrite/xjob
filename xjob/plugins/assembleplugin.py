# Assemble Plugins for the Pipeline
# Eric Ritezel -- March 1, 2007

import uuid, xml.etree.ElementTree as ET

# this mess finds the Plugin module
try:
	import sys
	plugin = sys.modules['plugin']
except KeyError:
	import imp, os
	plugin = imp.load_source('plugin', os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'plugin.py')))

class AssembleSourcePlugin(plugin.Plugin):
	""" Reconstuct a source from its documents """
	def Init(self, *args, **kwargs):
		""" set up a tracking dict for master sources and member docs """
		self.registry = {}
		self.masters = {}

	def canhandle(self, xjob):
		""" if we can't reconstruct, push it along
		first case:  master source
		             has reconstruction flag set
		second case: member document
		             document is without reconstruction flag set,
		             one document at source/document level
		"""
		return (xjob.find('source') is not None and \
		        xjob.find('source').get('reconstruct','False') == 'True') or \
		       (xjob.find('source/document') is not None and \
		        xjob.find('source/document').get('reconstruct','False') == 'False' and \
		        len(xjob.findall('source/document')) == 1)

	def handle(self, level, xjob):
		""" Generate source """
		# get the source and document node/ids
		srcnode = xjob.find('source')
		docnode = srcnode.find('document')
		srcid = srcnode.get('id')
		docid = docnode.get('id')

		# set up a convenience variable
		master = None

		# add a master to the pile
		if srcnode.get('reconstruct', False):
			self.masters[srcid] = xjob

		# there's a registry entry, so append to that
		elif self.registry.has_key(srcid):
			self.registry[srcid].append(docnode)

		# create a new entry for this page
		else: self.registry[srcid] = [docnode]


		# yield if all page nodes are filled out in the master
		if self.masters.has_key(srcid) and self.registry.has_key(srcid):
			# set the convenience function
			master = self.masters[srcid].find('source')

			# loop through the registry entries
			for o in xrange(len(self.registry[srcid])):

				# loop through the master entries (baseline documents)
				for i in xrange(len(master)):

					# this will die with an exception if no id exists
					if master[i].get('id') == self.registry[srcid][o].get('id'):
						master.remove(master[i])
						master.insert(i, self.registry[srcid][o])
						break


		# try to yield the source
		if master is not None and len(master) == len(self.registry[srcid]):
			del(master.attrib['reconstruct'])
			self.registry.pop(srcid)
			yield self.masters.pop(srcid)

		# reconstruction is not finished, so destroy this node
		else: yield None

class AssembleDocumentPlugin(plugin.Plugin):
	"""
	Reconstitutes a document from (near) scratch by keying on its document id
	and the reconstruct flag.
	"""
	def Init(self, *args, **kwargs):
		# set up a tracking dict
		self.registry = {}
		self.masters = {}

	def canhandle(self, xjob):
		""" if we can't reconstruct, push it along """
		return xjob.find('source/document') is not None and \
		       (xjob.find('source/document').get('reconstruct','False') == 'True' or \
		       (len(xjob.findall('source/document')) == 1 and \
		        xjob.find('source/document//page') is not None and \
		        len(xjob.findall('source/document//page')) == 1))

	def handle(self, level, xjob):
		""" Reconstructs from source-level document """
		docnode = xjob.find('source/document')
		pgnode = xjob.find('.//page')
		pgid = pgnode.get('id')
		docid = docnode.get('id')

		# set up a convenience variable
		master = None

		# add a master to the pile
		if docnode.get('reconstruct', False): self.masters[docid] = xjob

		# there's a registry entry, so append to that
		elif self.registry.has_key(docid): self.registry[docid].append(pgnode)

		# create a new entry for this page
		else: self.registry[docid] = [pgnode]

		# yield if all page nodes are filled out in the master
		if self.masters.has_key(docid) and self.registry.has_key(docid):
			# set the convenience function
			master = self.masters[docid].find('source/document')

			# loop through the registry entries
			for reg in self.registry[docid]:

				# loop through the master entries (baseline documents)
				for page in master.getiterator('page'):

					# this will die with an exception if no id exists
					if page.get('id') == reg.get('id') and len(page) == 0:
						page.attrib = reg.attrib
						for c in [a for a in list(reg) if a.tag != 'page']: page.append(c)
						break

		# try to yield the source
		if master is not None and \
		    len(master.findall('.//page')) == len(self.registry[docid]):
			del(master.attrib['reconstruct'])
			self.registry.pop(docid)
			yield self.masters.pop(docid)

		# reconstruction is not finished, so destroy this node
		else: yield None
