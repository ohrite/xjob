# Process Plugins for the Pipeline
# Eric Ritezel -- February 25, 2007

import uuid, xml.etree.ElementTree as ET

# this mess finds the Plugin module
try:
	import sys
	plugin = sys.modules['plugin']
except KeyError:
	import imp, os
	plugin = imp.load_source('plugin', os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'plugin.py')))

class ProcessByDocumentPlugin(plugin.Plugin):
	"""
	Breaks a source down into its component documents.
	"""
	def canhandle(self, xjob):
		""" See if this XJOB contains the necessary components to decompose """
		return xjob.find('source') is not None and \
		       len(xjob.findall('source')) == 1 and \
		       xjob.find('source').get('reconstruct','False') != 'True'

	def handle(self, level, xjob):
		""" Generate documents """
		# iterate top-level documents
		for document in xjob.findall('source/document'):
			# get a blank xjob node and the current source
			xjobnode = ET.Element('xjob', xjob.attrib)

			# create a blank structure with the source node
			srcnode = ET.SubElement(xjobnode, 'source', xjob.find('source').attrib)

			# duplicate the document element
			docnode = ET.SubElement(srcnode, 'document', document.attrib)

			# append all children, including attachments
			for node in list(document): docnode.append(node)

			# yield back document with structure
			yield xjobnode

		# set reconstruct flag on original xjob
		srcbase = xjob.find('source')
		srcbase.set('reconstruct', 'True')
		for doc in srcbase.findall('document'):
			for node in list(doc): doc.remove(node)

		# yield full XJOB
		yield xjob

class ProcessByPagePlugin(plugin.Plugin):
	"""
	Breaks a document down into its component pages.
	This function includes metadata for its direct parent document and source
	"""
	blocks = ('page', 'document', 'attachment')

	def canhandle(self, xjob):
		""" Assert: (xml document-level) last document is not the original """
		return xjob.find('source') is not None and \
		       xjob.find('source/document') is not None and \
		       len(xjob.findall('source')) == 1 and \
		       xjob.find('source').get('reconstruct','False') != 'True'

	def handle(self, level, xjob):
		""" Generate pages """
		# create a parent map (via effbot, who would know)
		parent_map = dict((c, p) for p in xjob.getiterator() for c in p)

		# create a source node
		srcnode = xjob.find('source')

		# iterate all page nodes for yielding
		for page in xjob.getiterator('page'):
			# create a temporary xjob
			tempxjob = ET.Element('xjob', xjob.attrib)

			# create a temporary source
			tempsrc = ET.SubElement(tempxjob, 'source', srcnode.attrib)

			# create a list of nodes to push crap to
			tempnode = page
			lasttemp = None

			# walk up until we get to the source (so we can push all pages)
			while tempnode is not srcnode:
				# create a new element with the given attributes
				newnode = ET.Element(tempnode.tag, tempnode.attrib)

				# append children (except for extraneous hierarchy)
				for node in [n for n in list(tempnode) if n.tag not in ProcessByPagePlugin.blocks]:
					ET.SubElement(newnode, node.tag, node.attrib)

				# append hierarchy and walk
				if lasttemp is not None:
					newnode.append(lasttemp)
				lasttemp = newnode

				# get the parent of the temporary node
				tempnode = parent_map[tempnode]

			# append to temporary source node
			tempsrc.append(lasttemp)

			# yield back to function
			yield tempxjob

		# set the reconstruction flag (this is a master doc)
		docbase = xjob.find('source/document')
		docbase.set('reconstruct', 'True')
		for page in xjob.getiterator('page'):
			for child in list(page): page.remove(child)

		yield xjob
