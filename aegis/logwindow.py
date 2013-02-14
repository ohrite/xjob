# Mini-window for showing a list of errors
# Eric Ritezel -- February 4, 2007
#

import wx
from wax import core, styles, containers, panel, listview, button
from wax import SystemSettings

class LogWindow(wx.MiniFrame, containers.Container):
	__events__ = {
		'Close': wx.EVT_CLOSE,
	}

	def __init__(self, parent, title='', errors=[], warnings=[], info=[], **kwargs):
		# note: does not support the 'size' parameter
		style = 0
		style |= self._params(kwargs)
		style |= styles.window(kwargs)

		wx.MiniFrame.__init__(self, parent, wx.NewId(), title,\
		                      wx.DefaultPosition, wx.DefaultSize,\
		                      style)

		self._create_sizer('V')
		self.BindEvents()
		styles.properties(self, kwargs)
		self.SetDefaultFont()

		self.loglist = AutoWidthListView(self, columns=('Type','Message'))
		self.AddComponent(self.loglist, expand='both')

		self.info = []

		# set column widths
		self.loglist.SetColumnWidth(0, 50)
		self.loglist._doResize()

		# set button for close ops
		_button = button.Button(self, "Close")
		self.AddComponent(_button, expand='h')

		# bind the button
		_button.OnClick = self.OnCloseMe

		self.Pack()
		self.Reset()

	def __len__(self):
		return self.loglist.GetItemCount()

	def AddWarning(self,text):
		self.Warnings += 1
		self.loglist.append(('Warning',text))

	def AddError(self,text):
		self.Errors += 1
		self.loglist.append(('Error',text))

	def AddInfo(self,text):
		self.info.append(text)
		self.loglist.append(('Information',text))

	def Reset(self):
		self.Errors = 0
		self.Warnings = 0

		self.loglist.DeleteAllItems()
		for line in self.info:
			self.loglist.append(('Information',text))

	def OnLoseFocus(self, event=None):
		self.SetTransparent(0x80)
		event.Skip()

	def OnGetFocus(self, event=None):
		self.SetTransparent(0xff)
		event.Skip()

	def OnCloseMe(self, event):self.Close(True)
	def OnClose(self, event): self.Hide()

	def _params(self, kwargs):
		flags = wx.DEFAULT_FRAME_STYLE
		flags |= styles.stylebool('v_caption', wx.TINY_CAPTION_VERT, kwargs)
		if flags == wx.DEFAULT_FRAME_STYLE: flags |= wx.TINY_CAPTION_HORIZ
		return flags

class AutoWidthListView(listview.ListView):
	"""inspired by wx.lib.mixins.AutoWidthListCtrlMixin. Automatically resizes
       columns in the ListView to take up all available space. It does not use
       the last column but equally divides it between columns.
	"""

	def append(self, data):
		thisitem = self.GetItemCount()
		self[thisitem,0] = data[0]
		self[thisitem,1] = data[1]

	def OnResize(self, event):
		core.CallAfter(self._doResize)
		event.Skip()

	def OnColumnBeginDrag(self, event):
		if event.GetColumn() == self.ColumnCount - 1:
			event.Veto() # only inner column-separators can be dragged
		else:
			event.Skip()

	def OnColumnEndDrag(self, event):
		core.CallAfter(self._doResize)
		event.Skip()

	def _doResize(self):
		if not self: return # avoid a PyDeadObject error
		if self.ColumnCount <= 0: return # Nothing to resize.

		listWidth = self.GetClientSize().width
		if core.Platform != '__WXMSW__' and self.GetItemCount() > self.GetCountPerPage():
			listWidth = listWidth - wax.SystemSettings.GetMetric('vscroll_x')

		# only resize last column
		newwidths = [self.GetColumnWidth(col) for col in range(self.ColumnCount)]
		totColWidth = sum(newwidths)
		newwidths[-1] += (listWidth - totColWidth - 1)
		if newwidths[-1] > 50: self.SetColumnWidths(newwidths)
