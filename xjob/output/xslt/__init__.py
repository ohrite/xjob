# precaching for the output xml style sheets

class cached:
	def __init__(self, name):
		self.name = name
		self.content = None

	def __str__(self):
		if self.content is None:
			import os

			infile = open(os.path.join(os.path.dirname(__file__),self.name),'r')
			self.content = infile.read()
			infile.close()
		return self.content

ipro = cached("ipro.xsl")
pgelvl = cached("pgelvl.xsl")
doclvl = cached("doclvl.xsl")
opticon = cached("opticon.xsl")
summation_i = cached("summation-i.xsl")
summation_v = cached("summation-v.xsl")
