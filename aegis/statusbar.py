# statusbar.py

import zlib, time
import wx
from wax import waxobject, styles, bitmap, containers, panel, label
from wax.tools.gauge import Gauge

from logwindow import LogWindow
from images import AegisImages

class StatusBar(wx.StatusBar, waxobject.WaxObject):
	__events__ = {
		"Size" : wx.EVT_SIZE,
		"Idle" : wx.EVT_IDLE
	}

	def __init__(self, parent, **kwargs):
		# note: does not support the 'size' parameter
		style = 0
		style |= self._params(kwargs)
		style |= styles.window(kwargs)

		wx.StatusBar.__init__(self, parent, wx.NewId(), style=style)

		self.BindEvents()
		styles.properties(self, kwargs)
		self.SetDefaultFont()

		# set up fields and status widths
		# left= informational messages
		# center= master volume render control and gauge
		# right= a 100px placeholder for status messages
		self.SetFieldsCount(3)
		self.SetStatusWidths([-1, 100, 100])
		parent.SetStatusBar(self)

		# work around positioning error
		self.sizeChanged = False

		# This status bar has three fields
		self.SetFieldsCount(3)

		# Informational message
		self.SetStatusText('', 0)

		# set progress mode
		self.progress = False

		# set up the volume render / gauge widget
		self.renderer = VolumeState(self)
		self.renderer.SetSize((100, 12))

		# set up the iconlabel
		self.logger = ErrorState(self)
		self.logger.SetSize((100, 12))

		# reposition all elements
		self.Reposition()

	def OnSize(self, evt):
		self.Reposition()  # for normal size events

		# Set a flag so the idle time handler will also do the repositioning.
		# It is done this way to get around a buglet where GetFieldRect is not
		# accurate during the EVT_SIZE resulting from a frame maximize.
		self.sizeChanged = True

	def OnIdle(self, evt):
		if self.renderer.gauge.IsShown() and self.renderer._starttime != 0:
			taken = int(time.time() - self.renderer._starttime)
			estimate = self.renderer.gauge.GetValue() / self.renderer.gauge.GetRange()
			estimate = (taken * estimate) - taken
			self.renderer.SetToolTip(wx.ToolTip(
				"Time remaining: %d:%02d:%02d" %\
				(estimate/3600, (estimate%3600)/60, estimate%60)
			))

		if self.sizeChanged:
			self.Reposition()

	# reposition the widgets
	def Reposition(self):
		for (pos, widget) in [(1, self.renderer), (2, self.logger)]:
			rect = self.GetFieldRect(pos)
			widget.SetPosition((rect.x+2, rect.y+2))
			widget.SetSize((rect.width-4, rect.height-2))
		self.sizeChanged = False

	# gets status update event and applies it
	def __setitem__(self, index, data):
		index = index.lower()

		# set the informational field
		if index == 'info':
			self.SetStatusText(str(data), 0)

		# set the range for the progress bar
		elif index == 'range':
			self.renderer.gauge.SetRange(int(data))

		# set the completion for the progress bar
		elif index == 'progress':
			self.renderer.gauge.SetValue(int(data))

	def AddError(self, text): self.logger.AddError(text)
	def AddWarning(self, text): self.logger.AddWarning(text)
	def AddInfo(self, text): self.logger.AddInfo(text)

	def VolumeReady(self): self.renderer.VolumeReady()
	def NoVolume(self): self.renderer.NoVolume()
	def VolumesDone(self): self.renderer.VolumesDone()
	def InProgress(self): self.renderer.InProgress()


	#
	# style parameters
	def _params(self, kwargs):
		flags = 0
		flags |= styles.stylebool('sizegrip', wx.ST_SIZEGRIP, kwargs)
		return flags

class VolumeState(panel.Panel):
	def __init__(self, parent, **kwargs):
		panel.Panel.__init__(self, parent, size=(100,18), direction='h',**kwargs)

		self.BindEvents()
		styles.properties(self, kwargs)
		self.SetDefaultFont()

		# make an imagelist
		self.imagelist = AegisImages()

		# fire up the bitmap
		bmp = bitmap.Bitmap(self, wx.EmptyBitmap(16,16))
		setattr(self, 'bitmap', bmp)
		self.AddComponent(bmp, align='l', border=0)

		# set the info icon
		self.bitmap.SetBitmap(self.imagelist['go'])
		self.bitmap.Hide()

		# set a click event for the bitmap
		self.CallOnClick = None
		wx.EVT_LEFT_DOWN(self.bitmap, self.OnClick)
		wx.EVT_LEFT_UP(self.bitmap, self.OnClickUp)
		wx.EVT_ENTER_WINDOW(self.bitmap, self.OnMouseOver)
		wx.EVT_LEAVE_WINDOW(self.bitmap, self.OnMouseLeave)

		# set up the label
		self._label = " (Waiting for Input) "
		text = label.Label(self, self._label)
		setattr(self, 'text', text)
		self.AddComponent(text, align='l',border=1)

		self.gauge = Gauge(self, size=(96,16), range=1)
		self.gauge.SetToolTip(wx.ToolTip("No volume rendering in progress."))
		self.AddComponent(self.gauge, align='c',border=1)
		self.gauge.Hide()

		# set time of initial comprehension to none
		self._starttime=0

		self.Pack()

	# placeholder for click
	def OnClick(self, event=None):
		self.bitmap.SetBitmap(self.imagelist['go'])
		if self.CallOnClick is not None: self.CallOnClick(event)
		event.Skip()

	def OnClickUp(self, event=None):
		self.bitmap.SetBitmap(self.imagelist['go_blue'])
		event.Skip()

	def OnMouseOver(self, event=None):
		self.bitmap.SetBitmap(self.imagelist['go_blue'])
		event.Skip()

	def OnMouseLeave(self, event=None):
		self.bitmap.SetBitmap(self.imagelist['go'])
		event.Skip()

	def NoVolume(self):
		if self.gauge.IsShown() or self.bitmap.IsShown():
			self.bitmap.Hide()
			self.gauge.Hide()
			self._label = " (No Volumes)  "
			self.text.SetLabel(self._label)
			self.text.SetPosition((1,1))

	def InProgress(self):
		if not self.gauge.IsShown():
			self.bitmap.Hide()
			self.text.Hide()
			self.gauge.Show()

	def VolumeReady(self):
		if not self.bitmap.IsShown() or self.gauge.IsShown():
			self.bitmap.Show()
			self.gauge.Hide()
			self._label = " Render"
			self.text.SetLabel(self._label)
			self.text.Show()
			self.text.SetPosition((self.bitmap.GetSize()[0],1))

	def VolumesDone(self):
		if self.gauge.IsShown() or self.bitmap.IsShown():
			self.bitmap.Hide()
			self.gauge.Hide()
			self._label = "Render Complete"
			self.text.SetLabel(self._label)
			self.text.Show()
			self.text.SetPosition((1,1))

class ErrorState(panel.Panel):
	__events__ = {
		'DoubleClick': wx.EVT_LEFT_DCLICK
	}

	# set up simple pluralizer
	plural = lambda s,x: (x and ("s",) or ("",))[0]

	def __init__(self, parent, **kwargs):
		panel.Panel.__init__(self, parent, size=(100,18), direction='h',**kwargs)

		self.BindEvents()
		styles.properties(self, kwargs)
		self.SetDefaultFont()

		# tack on an imagelist
		self.imagelist = AegisImages()

		# work around positioning error
		self.sizeChanged = False

		# fire up the bitmap
		bmp = bitmap.Bitmap(self, wx.EmptyBitmap(16,16))
		setattr(self, 'bitmap', bmp)
		self.AddComponent(bmp, align='t', border=0)

		# set up the label
		self._label = " No Errors            "
		self.text = label.Label(self, self._label)
		self.AddComponent(self.text, align='l')

		# add in extra events
		wx.EVT_LEFT_DCLICK(bmp, self.OnDoubleClick)
		wx.EVT_LEFT_DCLICK(self.text, self.OnDoubleClick)

		self.Pack()

		# set the info icon
		self.bitmap.SetBitmap(self.imagelist['disabled'])

		# construct logging window (blah)
		self.logwindow = LogWindow(self, title="Processing Information")
		self.logwindow.SetSize((180,220))
		self.logwindow.Show(False)

	def AddError(self, text):
		# add some error text to the log
		self.logwindow.AddError(text)
		if self.logwindow.Errors == 1:
			self.bitmap.SetBitmap(self.imagelist['error'])

		# set up the label
		self._label = " %d Error%s" % (self.logwindow.Errors,
		                               self.plural(self.logwindow.Errors > 1))
		self.text.SetLabel(self._label)

	def AddWarning(self, text):
		# add some error text to the log
		self.logwindow.AddWarning(text)
		if self.logwindow.Errors == 0:
			if self.logwindow.Warnings == 1:
				self.bitmap.SetBitmap(self.imagelist['warn'])

			# set up the label
			self._label = " %d Warning%s" %\
			              (self.logwindow.Warnings,
			               self.plural(self.logwindow.Warnings > 1))
			self.text.SetLabel(self._label)

	def AddInfo(self, text):
		if len(self.logwindow) == 0:
			self.bitmap.SetBitmap(self.imagelist['info'])
		self.logwindow.AddInfo(text)

	def Reset(self):
		self.logwindow.Reset()
		self.bitmap = self.imagelist['info']
		self._label = ' No Errors'
		self.text.SetLabel(self._label)

	def OnDoubleClick(self, event=None):
		self.logwindow.CenterOnParent(wx.BOTH)
		self.logwindow.Show(True)
