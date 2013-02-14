# A rendering pipeline class
# Eric Ritezel -- February 22, 2007
#

import sys, time, os
import threading, Queue

from plugin import *

class Pipeline(object):
	"""
	A data rendering pipeline, generalized for modules.
	Register modules with this object.
	Incoming modules must have the following methods:
		__init__(settings, queue, outqueue, quitevent, args, kwargs), run()
	Most modules inherit from Plugin, which has:
		canhandle(self, xjob), handle(self, signature, xjob)

	A simple module will act like this:
		while not self.quitevent.isSet():
			sleep(1) # needs to yield
			(signature, item) = self.queue.get(1)
			if not self.handles(signature):
				self.queue.put((signature, item))
			print signature,':',item
			self.process(item)
			self.outqueue.put((signature+1, item))

	So, signatures are basically an elevator.
		If a signature is not handled at a certain elevator level,
		the signature is incremented until it falls off the edge of the earth.
		(Or, at least, until the signature hits a level that is handled.)

	Registering with the pipeline is as simple as this:
		pipeline.AddItem(module)
	"""
	def __init__(self, length=10):
		self.masterquit = threading.Event()
		self.pipeline = Queue.Queue(length)
		self.middle = Queue.Queue()
		self.output = Queue.Queue()

		# make sure that we don't stop before we start
		self.masterquit.clear()

		# initialize tasks, tack pushback to end
		self.tasklist = [(sys.maxint, PushBackPlugin(sys.maxint, self.pipeline,
		                  self.middle, self.output, self.masterquit))]

		# set up Recycler (elevates based on the task list)
		self.recycler = RecyclerPlugin(self.pipeline, self.middle,
		                               [x[0] for x in self.tasklist],
		                               self.masterquit)

		# boot up the master threads
		self.tasklist[0][1].setDaemon(True)
		self.tasklist[0][1].start()
		self.recycler.setDaemon(True)
		self.recycler.start()

	def AddTask(self, plugin, *args, **kwargs):
		"""
		Append a task to the pipeline task list.
		>>> pl = Pipeline()
		>>> pl.AddTask(xjob.tasks.CopyToTempFiles)
		>>> pl.AddTask(xjob.tasks.Embed)
		>>> pl.AddTask(xjob.tasks.OCR)
		>>> for doc in docs: pl.put(doc)
		>>> while not pl.empty():
		...     out_docs.append(pl.get())
		"""
		# add the plugin and sort the list
		newkey = len(self.tasklist)-1
		self.tasklist.insert(newkey, (newkey, plugin(newkey, self.pipeline, self.middle, self.masterquit, *args, **kwargs)))

		# run the plugin (it will always be at the second-to-last position)
		self.tasklist[-2][1].setDaemon(True)
		try:self.tasklist[-2][1].setName(str(newkey)+'-'+plugin.__name__)
		finally:self.tasklist[-2][1].start()
		self.recycler.setLevels([x[0] for x in self.tasklist])

	def empty(self):
		""" A shortcut to the three-way boolean state of our child queues. """
		return self.pipeline.empty() and self.middle.empty() and self.output.empty()

	def put(self, item):
		""" This method inserts a new value into the pipeline queue. """
		self.pipeline.put((0, item), block=True)

	def get(self, timeout=None):
		""" Blocking get on self.output with a timeout parameter. """
		if timeout is not None: return self.output.get(True, timeout)
		else: return self.output.get(True)

	def close(self):
		""" Destroys all pipeline plugins, aborts processing and returns. """
		self.masterquit.set()

		# wake up the Recycler and all the tasks
		if not self.middle.full(): self.middle.put_nowait((0, None))
		for i in xrange(len(self.tasklist)):
			if not self.pipeline.full():
				self.pipeline.put_nowait((0, None))

		# wait a bit
		time.sleep(0)

		# drain all pipeline and middle tasks
		while not self.middle.empty(): self.middle.get_nowait()
		while not self.pipeline.empty(): self.pipeline.get_nowait()

		# delete all the queues
		del(self.pipeline)
		del(self.middle)
		del(self.output)

		# delete all pipeline tasks
		del(self.tasklist)
