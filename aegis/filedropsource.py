# drop source wrapper class
# Eric Ritezel -- January 24, 2007

# wx drag/drop stuff
from wx import DropSource as wxDropSource
from wx import FileDataObject as wxFileDataObject

class FileDropSource:
	def __init__(self, parent, filenames):
		# skip out on anything major if there's no files to pack
		if not len(filenames): return

		# create and add files to fdo
		data = wxFileDataObject()
		for filename in filenames: data.AddFile(filename)

		# create dropsource and run
		dropSource = wxDropSource(parent)
		dropSource.SetData(data)
		dropSource.DoDragDrop(1)

