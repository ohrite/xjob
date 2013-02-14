#---------------------------------------------------------------------
# waxrf2.py
#	Purpose: Handle Wax Resource Files (that resemble wxWidgets XRC files)
#	 Author: Eric Ritezel (originally by GSOC student Jason Gedge)
#
#	TODO:
#	   - (also see handlers.py)
#---------------------------------------------------------------------


from handlers import *
import xml.etree.cElementTree as ET

class XMLResource:
	""" Class to handle the loading of WaxRFs. """

	def __init__(self, *args, **kwargs):
		self._top = None
		self._names = {}

	def Load(self, *args, **kwargs):
		""" Load WaxRF data from a string or filename. """
		self._names = {}

		# set the object to load from
		if len(args) > 0: _object = args[0]
		else: _object = kwargs.get('filename', kwargs.get('string', None))

		if _object is None:
			raise KeyError("Load needs a filename or string argument")

		# change from the first version: feeds into cElementTree
		self._top = __LoadHandlers(ET.iterparse(_object))

		# complain about a bad root tag
		if self._top.tag != u'resource':
			raise KeyError("Document element should be '<resource>'")

		return self._top

	#
	#---LOADING ROUTINES------------------------------------------------
	#
	#  LoadObject by itself is sufficient to load anything.  A number
	#  of aliases is provided to make it clearer what exactly is being
	#  loaded: LoadImage, LoadPanel, etc.
	#

	def LoadObject(self, parent, name):
		""" At the moment, just an alias for Load*** until I can
			decide what the behaviour of each function will be. """
		if name in self._names:
			obj = self._names[name].Handle(parent)
			if parent:
				setattr(parent, name, obj)
			return obj
		else:
			return None  # should we raise an exception?

	def LoadImage(self, name):
		img = self.LoadObject(None, name)
		return img

	def LoadPanel(self, parent, name):
		p = self.LoadObject(parent, name)
		return p

	def LoadMenu(self, name):
		menu = self.LoadObject(None, name)
		return menu

	def LoadMenuBar(self, parent, name):
		mb = self.LoadObject(parent, name)
		return mb

	def LoadToolBar(self, parent, name):
		tb = self.LoadObject(parent, name)
		return tb

	def LoadIcon(self, name):
		icon = self.LoadObject(None, name)
		return icon

	def LoadDialog(self, parent, name):
		return self.LoadObject(parent, name)

	#------------------------------------------------------------------
	def __LoadHandlers(self, parser):
		""" From an iterparse interface, load an entire WaxRF layout. """
		# set a reservoir for text values
		nodeList = []
		textValue = ''

		# set reserved terms
		reserved = ('_border', '_align', '_expand')

		# run through the iterparse object
		for event, node in parser:
			# append text to main reservoir
			if len(node.text) > 0: textValue += node.text

			# fetch attributes for this node
			attribs = {}
			for k, v in [a for a in node.attrib if a[0] not in reserved]:
				try: attribs[k] = int(v)
				except: attribs[k] = v

			# fetch a name for this node
			name = node.get(u'name', None)

			# fetch AddComponent properties or default values
			properties = []
			properties.append(int(node.get(u'_border', 0)))
			properties.append(node.get(u'_align', ''))
			properties.append(node.get(u'_expand', ''))


	def _load_from_dom(self, dom):
		""" Given a DOM node object, recursively generates the internal
			data model that represents the WaxRF layout. """
		mylist = []
		textValue = ''
		for node in dom.childNodes:
			# Skip text nodes
			if node.nodeType == node.TEXT_NODE:
				textValue = textValue + node.nodeValue
				continue

			# skip comments
			if node.attributes is None: continue

			# First get the name of this object
			objname = str(node.nodeName)

			# Now get the associated attributes
			attributes = {}
			addprops = [0, '', 0]  # AddComponent - border, align, expand
			name = None
			for k, v in node.attributes.items():
				if k == u'name':
					name = str(v)
				elif k == u'_border':
					try:
						addprops[0] = int(str(v))
					except:
						pass
				elif k == u'_align':
					addprops[1] = str(v)
				elif k == u'_expand':
					addprops[2] = str(v)
				else:
					try:
						attributes[str(k)] = int(str(v))
					except:
						attributes[str(k)] = str(v)

			# Add it to the main list
			children, textValue = self._load_from_dom(node)
			h = self.__handlers__.get(objname, BasicHandler)(objname, attributes, addprops, children, self)
			h.textValue = textValue
			h._objname = name
			mylist.append(h)
			# If it had a name attribute, add it to the dictionary
			#   (cache) of name references to speed up loading
			if name:
				self._names[name] = mylist[-1]

		return mylist, textValue

	# Control->Function mappings to handle adding children to panels
	__handlers__ = {
		'Panel': BasicContainerHandler,
		'OverlayPanel': BasicContainerHandler,
		'HorizontalPanel': BasicContainerHandler,
		'VerticalPanel': BasicContainerHandler,
		'PlainPanel': BasicContainerHandler,
		'FlexGridPanel': FlexGridHandler,
		'GridPanel': GridHandler,
		'Splitter': SplitterHandler,
		'Menu': MenuHandler,
		'MenuBar': MenuBarHandler,
		'MenuItem': MenuItemHandler,
		'Dialog': DialogHandler,
		'GroupBox': BasicContainerHandler,
		'CheckBox': CheckBoxHandler,
		'CheckListBox': CheckListBoxHandler,
		'ComboBox': ComboBoxHandler,
		'DropDownBox': ListBoxHandler,
		'ListBox': ListBoxHandler,
		'ListView': ListViewHandler,
		'ToggleButton': ToggleButtonHandler,
		'TreeListView': TreeListViewHandler,
		'TreeView': TreeViewHandler,
		'NoteBook': NoteBookHandler,
		'Image': BitmapHandler,
		'Bitmap': BitmapObjectHandler,
		'BitmapButton': BitmapObjectHandler,
		'RadioButton': RadioButtonHandler,
		'ImageList': ImageListHandler,
		'ToolBarHandler': ToolBarHandler,
		'StyledTextBox': StyledTextBoxHandler,
		'BitmapComboBox': BitmapComboBoxHandler,
		#'': Handler,
		#'': Handler,
	}
