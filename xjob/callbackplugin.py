# A plugin to dispatch OmniHandler calls
# Eric Ritezel -- March 04, 2007
#

import xml.etree.ElementTree as ET

import plugin

class CallbackOrDie(plugin.Plugin):
	"""
	A Pipeline plugin to dispatch calls using the OmniHandler protocol.
	Initialized using the following protocol
		CallbackOrDie(<commands for OmniHandler>,
		               validate=<true/false fcn>,
		               value=<scalar value>,
		               callback=<OmniHandler instance>)
	
	The default validator passes True on everything,
	and the default value is None.
	If the command is none, the initialization fails.
	"""
	
	def Init(self, *args, **kwargs):
		# set the OmniHandler instance
		self.callback = kwargs.get('callback', False)
		if not self.callback:
			raise ValueError('No callback instance supplied')

		# set up the validator and the value
		self.validator = kwargs.get('validate', lambda x: True)
		self.value = kwargs.get('value', lambda x: None)

		# set up the command
		self.command = kwargs.get('command', False)
		if self.command is False:
			if len(args) > 1:
				self.comamnd = args[-1]
			else:
				raise ValueError("Command for OmniHandler not set")
			
	def handle(self, level, xjob):
		"""
		Split out the arguments, pack with information and throw to OmniHandler
		"""
		
		target = xjob.find('source').get('id')
		
		# if we fail validation, we're fucked, so tell Omni
		if not self.validator(xjob):
			self.callback.dispatch(target, 'warn', 'Validation failed against ' + \
			              str(target) + ' at "' + self.command + '" stage.')
		
		# extract the value and throw command against callback
		# if there's an error in the callback (ie, removal, validation problem)
		# then the xjob passing through is destroyed and the legacy stops
		if self.callback.dispatch(target, self.command, self.value(xjob)) is False:
			self.callback.dispatch(target, 'warn', 'Callback failed against ' + \
			              str(target) + ' at "' + self.command + '" stage.')
			yield None
		
		# otherwise, the full value passes through
		yield xjob
