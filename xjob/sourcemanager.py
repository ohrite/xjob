# A management (virtual filesystem) class for xjob
# Eric Ritezel -- January 18, 2007
#
# v0.0.1 -- Basic sketch of structure 20070117
# v0.0.9 -- Fleshed out sketch of structure 20070119
# v0.1.0 -- Overthrew the entire thing for a pipeline-based system 20070304
#
# Provides:
#	SortBy(xpath)
# 	AddSource(XML)
# 	RemoveSource(uuid)
# 	GetOrderedXJOB()
#

import xml.etree.ElementTree as ET

class SourceManager:
	def __init__(self):
		"""
		Public:
			Creates a new SourceManager
		"""
		# a list of Volumes sorted by id
		self.__xjob = None

		# set up the sorting parameter (xpath, attrib)
		self.sortby = ('source', 'name')

	def AddSource(self, xjob, sortby=None):
		"""
		Public:
			Add a source xjob to the volume manager
		Parameters:
			xjob -- the ElementTree representation of the source to add
			sortby -- the xpath/attrib pair to sort the insertion by
		Returns:
			A copy of the xjob
		"""
		# make sure we've got a source
		if xjob.find('source') is None:
			raise ValueError("Got invalid source")

		# make sure our sortby is valid
		if sortby is not None:
			if isinstance(sortby, tuple) and len(sortby)!=2:
				raise ValueError("Got invalid sorting parameter")

			# set our sortby for this
			self.sortby = sortby


		# append incoming xjob
		if self.__xjob is not None:
			self.__xjob.append(xjob.find('source'))
		else: self.__xjob = xjob
	
		# pull data from sortby
		sortpath, sortattrib = self.sortby

		# determine sorting function
		if sortpath.find('/') > -1:
			keyfcn = lambda x:str(x.find('/'.join(sortpath.split('/')[1:])).get(sortattrib))
		else: keyfcn = lambda x:str(x.get(sortattrib))

		# rebuild xjob index
		newxjob = ET.Element('xjob', self.__xjob.attrib)
		for node in sorted(list(self.__xjob), key=keyfcn): newxjob.append(node)
		self.__xjob = newxjob

		return self.__xjob
	
	def RemoveSource(self, sourceid):
		"""
		Public:
			Searches the xjob for the source with the given id=sourceid.
			It then pops it from the tree and returns it.
		Parameters:
			sourceid -- the id of the source to be extracted.
		Returns:
			A copy of the xjob
		"""
		# search for volume
		removeidx = None
		for i in xrange(len(self.__xjob)):
			if self.__xjob[i].get('id') == str(sourceid):
				removeidx = i ; break
				
		# trash out if not found
		if removeidx is None: raise ValueError("Source does not exist")

		# remove source from main list
		self.__xjob.remove(self.__xjob[removeidx])
		
		return self.__xjob

	def GetSourceOrder(self):
		"""
		Public:
			Gets an n-tuple (by id) of the sources as they are ordered
		Returns:
			An n-tuple of strings
		"""
		return tuple([n.get('id') for n in list(self.__xjob)])

	def GetOrderedXJOB(self):
		"""
		Public:
			Generates a monolithic XJOB with <order> nodes on the docs/pages
		Returns:
			One XJOB please
		"""
		page = document = 0
		for node in self.__xjob.getiterator():
			# skip non-page/doc nodes
			if node.tag not in ('page', 'document'): continue

			# remove preexisting order nodes
			while node.find('order') is not None:
				node.remove(node.find('order'))
			
			# add an ordering node
			if node.tag == 'page':
				page += 1
				ET.SubElement(node, 'order', value=str(page))
			else:
				document += 1
				ET.SubElement(node, 'order', value=str(document))

		return self.__xjob
