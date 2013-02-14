# Replacement program for half of volumeworker -- an input fed pipeline
# Eric Ritezel -- March 05, 2007
#

import xml.etree.ElementTree as ET

import tempfile

from pipeline import *
from plugins import *
from ocrplugin import OCRPlugin
from embedplugin import EmbedPlugin
from callbackplugin import CallbackOrDie

class OutputPipeline(object):
	""" An input handling object using the Pipeline system. """

	def __init__(self, settings, manager, callback):
		# define the Settings object
		self.settings = settings
		self.manager = manager
		self.callback = callback

		# create a local temporary directory for file storage
		self.tempdir = tempfile.mkdtemp(prefix="xjob-local-")

		# allocate a 30-wide pipeline
		self.pipeline = Pipeline(30)

		# process the bulk by document
		self.pipeline.AddTask(ProcessByDocumentPlugin)

		# callback to flag completion of output
		self.pipeline.AddTask(CallbackOrDie,
		            callback=self.callback, command='add destination documents',
		            validate=lambda x:x.find('.//document') is not None and \
		                              (not x[0].attrib.has_key('reconstruct') or \
		                              x.find('.//page') is not None),
		            value=lambda x:len(x.findall('.//document')))

		# write numbering for each document
		self.pipeline.AddTask(RenderNumbering, settings=self.settings)

		# pull the data from its location
		self.pipeline.AddTask(SoakPlugin)

		# write the data to a temporary location
		self.pipeline.AddTask(FlushPlugin, tempdir=self.tempdir)

		# add a hash and size description to the source/doc/page nodes
		self.pipeline.AddTask(OCRPlugin, settings=self.settings)

		# add a hash and size description to the source/doc/page nodes
		self.pipeline.AddTask(EmbedPlugin, settings=self.settings)

		# callback to flag completion of output
		self.pipeline.AddTask(CallbackOrDie, callback=self.callback,
		            command='add complete destination documents',
		            validate=lambda x:x.find('.//document') is not None,
		            value=lambda x:len(x.findall('.//document')))

		# put all the document elements together
		self.pipeline.AddTask(AssembleSourcePlugin)

		# define boundaries for volume rendering
		self.pipeline.AddTask(RenderVolume, settings=self.settings)

		# change the directory structure for each volume
		self.pipeline.AddTask(RenderDirectory, settings=self.settings)

		# write the compatibility layer (loadfiles for each volume)
		#self.pipeline.AddTask(OutputLoadfiles, settings=self.settings)

		# attempt to add a named entry to the input list
		self.pipeline.AddTask(CallbackOrDie,
		    callback=self.callback, command='add new destination',
		    validate=lambda x:x.find('destination').get('name') is not None,
		    value=lambda x: x.find('destination').get('name'))

	def run(self, foo=None):
		""" Run the pipeline on each successive xjob """
		# get the ordered set of xjobs to render
		basexjob = self.manager.GetOrderedXJOB()

		# for each source underneath it
		for source in basexjob:
			# make a facsimile xjob
			xjob = ET.Element('xjob', basexjob.attrib)

			# append the given sort-order source
			xjob.append(source)

			# push the new node
			self.pipeline.put(xjob)

	def close(self):
		""" Shut down the pipeline for exit. """
		self.pipeline.close()
