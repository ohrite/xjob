# Custom Listview for Aegis project
# Eric Ritezel -- January 28, 2007
#

import wx
from wax import waxobject, styles, colordb, utils

class ListView(wx.ListCtrl, waxobject.WaxObject):

	__events__ = {
		'BeginDrag': wx.EVT_LIST_BEGIN_DRAG,
		'BeginRightDrag': wx.EVT_LIST_BEGIN_RDRAG,
		'DeleteItem': wx.EVT_LIST_DELETE_ITEM,
		'DeleteAllItems': wx.EVT_LIST_DELETE_ALL_ITEMS,
		'ItemSelected': wx.EVT_LIST_ITEM_SELECTED,
		'ItemDeselected': wx.EVT_LIST_ITEM_DESELECTED,
		'ItemDoubleClick': wx.EVT_LIST_ITEM_ACTIVATED,
		'ItemActivated': wx.EVT_LIST_ITEM_ACTIVATED,	# use one or the other
		'ItemFocused': wx.EVT_LIST_ITEM_FOCUSED,
		'ItemMiddleClick': wx.EVT_LIST_ITEM_MIDDLE_CLICK,
		'ItemRightClick': wx.EVT_LIST_ITEM_RIGHT_CLICK,
		'InsertItem': wx.EVT_LIST_INSERT_ITEM,
		'KeyDown': wx.EVT_LIST_KEY_DOWN,
		'Motion': wx.EVT_MOTION
	}

	__modemessage__ = {
		'Done' : "%(name)s\n%(sizetext)s",
		'Building' : "%(name)s\r\n(%(documents)s Documents)",
		'Scanning' : "%(name)s\r\n(%(documents)s Documents)",
		'Rendering' : "%(name)s\r\n%(percent)s%% Done",
		'Processing' : "%(name)s\r\n%(percent)s%% Done"
	}

	__units__ = ["","Ki","Mi","Gi","Ti"]

	def __init__(self, parent, size=None, **kwargs):
		style = 0
		style |= self._params(kwargs)
		style |= styles.window(kwargs)

		wx.ListCtrl.__init__(self, parent, wx.NewId(), size=size or (-1,-1),
		 style=style)

		# add dictionary for more metadata
		self._dict = {}
		self._ids = []

		# list of items to be redrawn
		self.retexts = []

		self.BindEvents()

		self.SetDefaultFont()
		styles.properties(self, kwargs)

	def NewItem(self, name, id, image, mode):
		# push id to dict and id list
		self._ids.append(id)
		self._dict[id] = {'name':name, 'mode':mode, 'size':0, 'sizetext':'0 B',
		                  'documents':0, 'donedocuments':0, 'percent':0}

		# create a new list item
		item = wx.ListItem()
		item.SetText("%s" % name)
		item.SetImage(self._imagelist[image])
		item.SetData(self._ids.index(id))
		self.InsertItem(item)

	def has_key(self, item):
		return self._dict.has_key(item)

	def __setitem__(self, index, value):
		if not (isinstance(index, tuple) and len(index) == 2):
			raise ValueError("DListView index tuple needs two values")

		(itemid, field) = index
		self._dict[itemid][field] = value

		# set redraw flag
		self.retexts.append(itemid)

	def __getitem__(self, index):
		"""
		Public:
			Get the dictionary of item attributes
		"""
		if not (isinstance(index, tuple) and len(index) == 2):
			raise ValueError("DListView index tuple needs two values")
		print index

		return self._dict[index[0]][index[1]]

	def __len__(self):
		return len(self._dict)

	def __del__(self, itemid):
		# remove index from dictionary and list
		self.DeleteItem(self.FindItemData(-1, self._ids.index(itemid)))
		del list[itemid]

	def Retext(self):
		""" iteratively set text for items """
		for itemid in self.retexts:
			index = self.FindItemData(-1, self._ids.index(itemid))

			# determine magnitude of size
			idx = 1
			while self._dict[itemid]['size']/(2 **(idx*10)) > 1024 and \
			    len(ListView.__units__) > idx:
			        idx += 1

			# set size and magnitude
			if self._dict[itemid]['size'] > 0:
				self._dict[itemid]['sizetext'] = "%4.1f %s" % \
					 (float(self._dict[itemid]['size']) / (2 **(idx*10)),
					  ListView.__units__[idx] + "B")

			# see if we've got a percentage to calculate against
			if self._dict[itemid]['documents'] and self._dict[itemid]['donedocuments']:
				self._dict[itemid]['percentage'] = '%3.0f' % \
				          ((100.0 * self._dict[itemid]['donedocuments']) / \
					                self._dict[itemid]['documents'])

			# render text based on mode
			self.SetItemText(index, ListView.__modemessage__[self._dict[itemid]['mode']] % self._dict[itemid])

			# remove from retexts
			if itemid in self.retexts:
				self.retexts.remove(itemid)

	def SortBy(self, ordering):
		""" Reorder the list items by the <ordering> sequence """
		self.SortItems(lambda x, y:(ordering.find(self._ids[x]) < ordering.find(self._ids[y]) and (-1,) or (1,))[0])

	def GetSelected(self):
		""" Return a list of (indexes of) selected items. """
		items = []
		item = self.GetFirstSelected()
		while item > -1:
			items.append(item)
			item = self.GetNextSelected(item)
		return items

	def FlagError(self, itemid):
		""" Set a visual representation of an error in the list """
		itemindex = self.FindItemData(-1, self._ids.index(itemid))
		self.SetItemTextColor(itemindex, "orange red")

	def SetImage(self, itemid, image):
		self.SetItemImage(self.FindItemData(-1,self._ids.index(itemid)),
		                  self._imagelist[image])

	def SetImageList(self, imagelist, small=1):
		wx.ListCtrl.SetImageList(self, imagelist, [wx.IMAGE_LIST_NORMAL, wx.IMAGE_LIST_SMALL][small])
		self._imagelist = imagelist

	#
	# alternate color methods

	def GetItemBackgroundColor(self, idx):
		return wx.ListCtrl.GetItemBackgroundColour(self, idx)


	def SetItemBackgroundColor(self, idx, color):
		color = colordb.convert_color(color)
		wx.ListCtrl.SetItemBackgroundColour(self, idx, color)

	def GetItemTextColor(self, idx):
		return wx.ListCtrl.GetItemTextColour(self, idx)

	def SetItemTextColor(self, idx, color):
		color = colordb.convert_color(color)
		wx.ListCtrl.SetItemTextColour(self, idx, color)

	#
	# style parameters

	_listview_rules = {
		'horizontal': wx.LC_HRULES,
		'vertical': wx.LC_VRULES,
		'both': wx.LC_HRULES | wx.LC_VRULES,
	}

	_listview_icons = {
		'large': wx.LC_ICON,
		'small': wx.LC_SMALL_ICON,
	}

	_listview_icon_alignment = {
		'top': wx.LC_ALIGN_TOP,
		'left': wx.LC_ALIGN_LEFT,
	}

	def _params(self, kwargs):
		flags = 0
		flags |= styles.styledictstart('icons', self._listview_icons, kwargs)
		flags |= styles.stylebooleither('report', wx.LC_REPORT, wx.LC_LIST, kwargs)
		if not flags: flags |= wx.LC_REPORT
		flags |= styles.stylebool('virtual', wx.LC_VIRTUAL, kwargs)
		flags |= styles.stylebool('single_selection', wx.LC_SINGLE_SEL, kwargs)
		flags |= styles.styledictstart('rules', self._listview_rules, kwargs)
		flags |= styles.styledictstart('icon_alignment', self._listview_icon_alignment, kwargs)
		flags |= styles.stylebool('icon_autoarrange', wx.LC_AUTOARRANGE, kwargs)
		flags |= styles.stylebool('edit_labels', wx.LC_EDIT_LABELS, kwargs)
		flags |= styles.stylebool('noheader', wx.LC_NO_HEADER, kwargs)

		return flags
