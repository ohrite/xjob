# Branch of original OmniHandler function in the Aegis code.
# This version supports thread safety and cooperates with the new Pipeline.
#
# Eric Ritezel -- March 04, 2007
#

import threading

class OmniHandler(object):
	"""
	The OmniHandler class provides a far-reaching, thread-safe hook base
	into the display.  It interprets incoming information from Pipeline
	Plugin objects and also feeds back into them.

	It is mean.  It will take your lunch money.  It doesn't like your sister.
	"""
	def __init__(self, inlist, settings, outlist, statusbar, manager):
		# initialize display widgets
		self.inlist = inlist
		self.settings = settings
		self.outlist = outlist
		self.statusbar = statusbar
		self.manager = manager

		# define error list
		self.__errors = []

		# define RLock for thread-safety
		self.threadlock = threading.RLock()

	def dispatch(self, target, command, value=None):
		"""
		Interpret a <command> string to be run against the given <target>
		with optional <value>.

		Parameters:
			target -- (required) a uuid to be referenced for operations
			command -- (required) an operation string
			value -- (optional) a value for throwing at the target with command

		Returns;
			boolean value making sure that the given parameters were valid.
			False means, in no uncertain terms, that there was an error.
			This error will be displayed later, so it is up to the function
			to kill itself.
			The given UUID will then be blacklisted, and further attempts on it
			will be met with False before any operations happen.
		"""
		# do the threading thing
		self.threadlock.acquire()

		# we know this to be bad, so return False
		if target in self.__errors: return False

		# parse out command string (lower case, space-separated)
		cmd = command.lower().split()

		# handle an error/warning/information command
		if 'error' in cmd:
			self.statusbar.AddError(value)
			self.inlist.FlagError(target)
			self.__errors.append(target)
			return False

		# this is a non-destructive event, but we still can't do much else
		else:
			if 'warning' in cmd:
				self.statusbar.AddWarning(value)
				return True
			elif 'information' in cmd:
				self.statusbar.AddInformation(value)
				return True

		# run a remove command
		if 'remove' in cmd:
			try: del self.inlist[target]
			finally:
				try: del self.outlist[target]
				except:
					self.statusbar.AddError('Cannot remove object with id',target)

			# if the input list is now empty, reset our rendering trigger
			if len(self.inlist) == 0:
				self.statusbar.VolumeWaiting()

			# add the target to the error list
			self.__errors.append(target)

			# return False in case this is a plugin and it needs a hint
			return False

		###################################
		##
		##	INPUT LIST SECTION
		##

		# handle a source-level element push ('add source' or 'add new source')
		elif ('add', 'new', 'source') == tuple(cmd):
			if not self.inlist.has_key(target):
				self.inlist.NewItem(name=value, id=target, image='dir', mode="Building")
			elif self.inlist[target, 'name'] != str(value):
				self.inlist[target, 'name'] = str(value)

		# handle a push of new documents from a source ('add source documents')
		elif ('add', 'source', 'documents') == tuple(cmd):
			if self.inlist.has_key(target):
				self.inlist[target, 'documents'] += int(value)
			else:
				self.inlist.NewItem(name="Unknown", id=target, image='dir', mode="Building")
				self.inlist[target, 'documents'] = int(value)

		# handle a push of size from a source or destination
		elif ('add', 'source', 'size') == tuple(cmd):
			if self.inlist.has_key(target):
				self.inlist[target, 'size'] += int(value)
			else:
				self.statusbar.AddInfo('Debug: Target "'+ target + \
				                          '" referenced before initialization.')

		# finalize source (stop updating and set final display mode)
		elif ('finalize', 'source') == tuple(cmd):
			if self.inlist.has_key(target):
				self.inlist[target, 'mode'] = 'Done'
				self.inlist.SortBy(self.manager.GetSourceOrder())
			else:
				self.statusbar.AddError('Target "'+ target + \
				                        '" tried to close before initialization.')
				self.__errors.append(target)
			self.statusbar.VolumeReady()

		# finalize source (stop updating and set final display mode)
		elif ('add', 'source', 'donedocuments') == tuple(cmd):
			self.inlist[target, 'mode'] = 'Processing'
			self.inlist[target, 'donedocuments'] += int(value)

		###################################
		##
		##	OUTPUT LIST SECTION
		##

		# handle documents from a destination ('add destination documents')
		elif ('add', 'destination', 'documents') == tuple(cmd):
			if not self.outlist.has_key(target):
				self.outlist.NewItem(name="New Volume", id=target, image='cd',
				                     mode="Building")

			# see if we should be thinking about progress
			self.outlist[target, 'documents'] += int(value)
			self.statusbar['range'] = self.outlist[target, 'documents']

		# handle complete docs ('add complete destination documents')
		elif ('add', 'complete', 'destination', 'documents') == tuple(cmd):
			if not self.outlist.has_key(target):
				self.outlist[target, 'complete'] += int(value)
				self.statusbar['progress'] = self.outlist[target, 'complete']

			# tell the status bar that it should start progressing
			self.statusbar.InProgress()

		# set the size and graphical representation of a destination volume
		elif ('add', 'destination', 'size') == tuple(cmd):
			print "added dest size?"
			# pump a size change into the system
			if self.outlist.has_key(target):
				self.outlist[target, 'size'] += int(value)

				# detect change in media size
				if self.outlist[target, 'size'] < (650 << 20):
					self.outlist.SetImage(target, 'cd')
				elif self.outlist[target, 'size'] < (41 << 29):
					self.outlist.SetImage(target, 'dvd')
				else:
					self.outlist.SetImage(target, 'hd')

			# pump a warning into the system
			else:
				self.statusbar.AddWarning('Target "'+ target + \
				                          '" referenced before initialization.')

		# do the threading thing
		self.threadlock.release()
