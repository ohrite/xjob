# Replacement program for boxworker -- an input fed pipeline
# Eric Ritezel -- March 04, 2007
#

import time, uuid, threading

from pipeline import *
from plugins import *
from input import *
from callbackplugin import CallbackOrDie

class InputPipeline(object):
	""" An input handling object using the Pipeline system. """

	def __init__(self, settings, manager, callback):
		# define the Settings and SourceManager objects
		self.sets = settings
		self.manager = manager
		self.callback = callback

		# set a kill event for the listener
		self.killevent = threading.Event()

		# allocate a 30-wide pipeline
		self.pipeline = Pipeline(30)

		# set up a loadfile handler to start
		self.pipeline.AddTask(LoadfilePlugin)

		# attempt to add a named entry to the input list
		self.pipeline.AddTask(CallbackOrDie,
		            command='add new source', callback=self.callback,
					validate=lambda x:x.find('source').get('name') is not None,
				    value=lambda x: x.find('source').get('name'))
	
		# make sure that the result has document nodes or, if it's not a
		# reconstruct system, that it has page nodes
		# then, if it's not a reconstruct, add the number of documents
		# to the list entry
		self.pipeline.AddTask(CallbackOrDie,
		            command='add source documents', callback=self.callback,
		            validate=lambda x:x.find('.//document') is not None and \
		                              (x[0].attrib.has_key('reconstruct') or \
		                              x.find('.//page') is not None),
		            value=lambda x:len(x.findall('.//document')))

		# add a hash and size description to the source/doc/page nodes
		self.pipeline.AddTask(HashNSizerPlugin)

		# make sure that each page node has a data node and that each data node
		# has a size attribute 
		# then add that size to the list entry for the source
		self.pipeline.AddTask(CallbackOrDie,
		    command='add source size', callback=self.callback,
		    validate=lambda x:\
		      0 not in [d.find('data') for d in x.getiterator('page')] and \
		      0 not in [d.get('size',0) for d in x.getiterator('data')],
		    value=lambda x:sum([int(d.get('size')) for d in x.getiterator('data')]))

		# put all the document elements together
		self.pipeline.AddTask(AssembleSourcePlugin)
		
		# load the result into a source manager and destroy it
		self.listener = threading.Thread(target=self.__ManagerListener,
		                                 name="Input-Listener")
		self.listener.setDaemon(True)
		self.listener.start()

	def __ManagerListener(self):
		""" Pulls repeatedly (until kill event is sent) from the pipeline """
		while not self.killevent.isSet():
			data = self.pipeline.get()
			
			# throw out null data
			if data is None: continue
			
			# add the valid data to the manager
			self.manager.AddSource(data)
			
			# set finalize call to callback
			self.callback.dispatch(target=data.find('source').get('id'),
			                       command='finalize source')

	def put(self, newsrc):
		""" Throw a new source into the pipeline """
		xjob = ET.fromstring('<xjob><source href="%s" /></xjob>' % newsrc)
		xjob.set('created', str(time.strftime("%Y%m%d%H%M%S", time.gmtime())))
		xjob.set('id', str(uuid.uuid1()))

		# put the new xjob to the pipeline
		self.pipeline.put(xjob)

	def close(self):
		""" Shut down the pipeline for exit. """
		self.pipeline.close()
