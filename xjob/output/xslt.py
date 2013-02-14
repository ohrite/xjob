# XSLT puller for transforming tree
# Eric Ritezel -- February 2, 2007
#

import libxml2, libxslt
import xslt

class Transformer:
	styles = {}
	document = None

	def Parse(self, argument):
		try:
			if isinstance(argument, ElementTree):
				self.document = libxml2.parseDoc(argument.tostring())
			else: self.document = libxml2.parseFile(filename)
		except: self.document = libxml2.parseDoc(argument)

	def __getattr__(self, attrib):
		assert hasattr(xslt, attrib)
		assert self.document is not None

		if not self.styles.has_key(attrib):
			stile = libxml2.parseDoc(str(getattr(xslt, attrib)))
			stile = libxslt.parseStylesheetDoc(stile)
			self.styles[attrib] = stile

		return self.styles[attrib].applyStylesheet(self.document, None)

if __name__ == "__main__":
	testdoc = """<job><box id="testingbox" name="testbox">
        <document name="MRVL007670">
            <page bates_number="007670" bates_prefix="MRVL" filename="MRVL007670.tif" id="MRVL007670" path="\AEGIS_001A" />
            <page bates_number="007671" bates_prefix="MRVL" filename="MRVL007671.tif" id="MRVL007671" path="\AEGIS_001A" />
            <page bates_number="007672" bates_prefix="MRVL" filename="MRVL007672.tif" id="MRVL007672" path="\AEGIS_001A" />
            <page bates_number="007673" bates_prefix="MRVL" filename="MRVL007673.tif" id="MRVL007673" path="\AEGIS_001A" />
            <page bates_number="007674" bates_prefix="MRVL" filename="MRVL007674.tif" id="MRVL007674" path="\AEGIS_001A" />
            <page bates_number="007675" bates_prefix="MRVL" filename="MRVL007675.tif" id="MRVL007675" path="\AEGIS_001A" />
        </document></box></job>"""

	xfrmr = Transformer()
	xfrmr.Parse(testdoc)
	print xfrmr.ipro
	print xfrmr.doclvl
