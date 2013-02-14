import pagefilemask
import re


class VolumeMask(pagefilemask.PageFileMask):
	"""
	A masking class for user-input volume names.
	Typical input: SFJ001 ([A-z])([0-9])
	"""
	expression = r"^(\D+)(\d+)()$"

	def __init__(self, mask):
		# compile regular expression
		regex = re.compile(self.expression, re.VERBOSE)

		# match against mask
		self.result = regex.search(mask)

		self.num = int(self.result.groups()[1])
