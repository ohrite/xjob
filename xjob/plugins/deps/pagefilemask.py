# Pagename mask handler class for riven
# Extracted from class file for XJOB handling
# Eric Ritezel - January 4, 2007
#
# class PageFileMask
#	-> __init__(mask)
#	-> __call__(mask)
#	-> getNumber()
#	-> getPrefix()
#	-> getSuffix()
#

import re

class PageFileMask:
	"""
	A masking class for user-input file or page names.
	Typical inputs: SFJ0005011, Wu 234201, Santos-234021-Vega
	Atypical input: V2G0001124
	Unacceptable input: O-eX12312312w2 (because of numerical undifferentiated suffix)
	"""
	expression = r"""^
		((?:[A-z]+?)|(?:[A-z\s\.\-\|\+]+(?:[A-z]|[\s\.\-\|\+])))?	# first group matches AAbco or 124ABC12- or ab2a
		(\d{3,})													# plenty of digits (more than 3)
		((?:[A-z]?[\s\.\-\|\+]\w*?)|(?:[A-z]))?						# last group matches AAbco or -124ABC12
		$"""

	def __init__(self, mask):
		"""
		Define a new mask.

		Parameters:
			mask -- string value of above-mentioned inputs
		"""
		self.value = mask

		# compile regular expression
		regex = re.compile(self.expression, re.VERBOSE)

		# match against mask
		self.result = regex.search(mask)

		self.num = int(self.result.groups()[1])

		self.suffix = False
		if self.result.groups()[2]:
			suffix = self.result.groups()[2].lower().strip('abcdefghijklmnopqrstuvwxyz.- |/\\+')
			if suffix.isdigit(): self.suffix = int(suffix)

	def getNumber(self):
		"""
		Return the whole number portion of the mask, ie SFJ(0000130)

		Returns:
			integer -- integer value of the mask
		"""
		return self.result.groups()[1]

	def getPrefix(self):
		"""
		Returns the prefix of the mask, without a given separator character, ie (Wu) 000012

		Returns:
			string -- the prefix, as stripped of any tokenizing characters
		"""
		return self.result.groups()[0]

	def getSuffix(self):
		"""
		Returns the suffix of the mask, as above, ie Santos-000012-(Vega)

		Returns:
			string -- the suffix, a la mode
		"""
		return self.result.groups()[2]

	def __str__(self):
		return str(self.result.groups())