# Class file for beefed-up callbacks
# Eric Ritezel - January 4, 2007
#
# Resurrected for insulating input loaders from gui stuff

class Callback:
	"""
	Generic handler class for passing arguments to callback functions.
	"""
	def __init__(self, func, *args, **kwargs):
		self.func = func
		self.args = args
		self.kwargs = kwargs

	def __call__(self, evt=None):
		self.func(*self.args, **self.kwargs)
		evt.Skip()

class ProgressCallback(Callback):
	"""
	Specific callback for use in the boxworker.
	"""
	def __call__(self, *args, **kwargs):
		newargs = args + self.args
		newkwargs = self.kwargs.copy()
		newkwargs.update(kwargs)
		self.func(*newargs, **newkwargs)
