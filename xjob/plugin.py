# The default plugin class for the rendering pipeline
# Eric Ritezel -- February 22, 2007
#

import threading
import time

class Plugin(threading.Thread):
	""" A template for a pipeline processing stage. """
	def __init__(self, level, itemq, outq, event, *args, **kwargs):
		threading.Thread.__init__(self)
		self.level = level
		self.inputq = itemq
		self.outputq = outq
		self.quitevent = event

		# seems to work pretty well. huh.  maybe it's just this system
		self.sleeplength = 0.0125+(self.level*0.0001)

		# put our own custom init stuff here
		self.Init(*args, **kwargs)

	def run(self):
		# while we're not on the way out (duh)
		while not self.quitevent.isSet():
			time.sleep(self.sleeplength)

			# get an item from the queue and deny everyone else
			incoming = self.inputq.get(block=True)

			# priority mismatch means we need to put this back to input
			if str(self.level) != str(incoming[0]):
				self.inputq.put(incoming, block=True)
				continue

			# see if we just got a dead event (so we can clean up the queue)
			if incoming[1] == None: continue

			# see if we have a priority match and handling capability
			if self.canhandle(incoming[1]):
				for output in self.handle(incoming[0], incoming[1]):
					self.outputq.put((incoming[0], output), block=True)

			# skip this data forward
			else:self.outputq.put(incoming, block=True)

			self.inputq.task_done()

		# run a function on exit
		self.on_end()

	def canhandle(self, arg):
		""" A test to see if this module can handle the data given to it. """
		return True

	def handle(self, level, arg):
		""" A generator that runs a transform on a given data object. """
		yield arg

	def on_end(self): pass
	def Init(self, *args, **kwargs): pass

class PushBackPlugin(Plugin):
	""" Added automatically to the end of the pipeline. """
	def __init__(self, level, itemq, outq, masteroutput, event):
		Plugin.__init__(self, level, itemq, outq, event)
		self.masteroutput = masteroutput

	def run(self):
		""" dummy run """
		while not self.quitevent.isSet():
			time.sleep(0.01)

			# get an item from the queue and deny everyone else
			incoming = self.inputq.get(block=True)

			# see if we have a priority match and handling capability
			if self.level == incoming[0]:
				self.handle(incoming[0], incoming[1])
				self.inputq.task_done()
			else: self.inputq.put(incoming, block=True)

	def handle(self, level, arg):
		""" Push the argument to the master output queue. """
		#print '+',
		self.masteroutput.put(arg, block=True)
		return None

class RecyclerPlugin(threading.Thread):
	""" Runs against the middle and input queues as an elevator. """
	def __init__(self, inputq, middleq, levels, event):
		threading.Thread.__init__(self)
		self.inputq = inputq
		self.middleq = middleq
		self.quitevent = event
		self.levels = levels
		self.level_lock = threading.Lock()

	def setLevels(self, newlevels):
		""" Set the levels for the Recycler to walk by. """
		self.level_lock.acquire(True)
		self.levels = newlevels
		self.level_lock.release()

	def run(self):
		"""
			Keep pulling tuples from the middle queue (until we die).
			Modify the processing level by walking it up the level list.
		"""
		while not self.quitevent.isSet():
			time.sleep(0.01)

			# grab something from the middle queue
			incoming = self.middleq.get(block=True)

			# see if we just got a dead event (so we can clean up the queue)
			if incoming[1] == None: continue

			# lock and look up level in levels
			self.level_lock.acquire(True)

			# sort the levels (don't trust nobody)
			self.levels.sort()

			# look for the priority level of the incoming object
			# default to the end of the list (output)
			newlevel = self.levels[-1]
			for i in xrange(len(self.levels)):
				if self.levels[i] == incoming[0]:
					if i + 1 == len(self.levels):
						newlevel = self.levels[-1]
					else:
						newlevel = self.levels[i+1]
					break

			# release the lock on levels
			self.level_lock.release()

			# put the level onto the input queue
			self.inputq.put((newlevel, incoming[1]), block=True)
