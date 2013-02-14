# XREF frontend code
# uses 3-pane window (top, mid, bottom) to control input and output
# Eric Ritezel -- December 30, 2006
#
# v0.0.1 - December 30, 2006
#          First prototype: accepts files, outputs droppable file objects
#          Has full settings notebook available, except printing
# v0.0.4 - January 3, 2007
#          Main interface work done
# v0.0.9 - January 29, 2007
#          Major work on ProgressCallback communication hook complete.
# v0.0.95- Feburary 5, 2007
#          Incorporation of XMLRPC functionality
# v0.0.96- February 20, 2007
#          Incorporation of Zeroconf functionality
# v0.0.97- February 22, 2007
#          Incorporation Pipeline functionality
# v0.1.0 - March 05, 2007,
#          Initial merge of Pipeline/Omni for testing (remnants remain)
#

__author__ = "Eric Ritezel"
__date__ = "2007-03-05"
__pname__ = "Aegis"
__domain__ = "ritezel.com"
__version__ = "0.1.0"
__description__ = "A rendering frontend for legal data."

# system stuff
import os, warnings
from time import sleep

# wax lib import and forked additions
import wax
import waxrf

# get a wx constant for the delete key
from wx import WXK_DELETE as wxk_del

# type id
from wx._gdi import Bitmap as wxBitmap

# custom event stuff
from wx import Yield as wxYield

# ElementTree XML handling
import xml.etree.ElementTree as ET

import aegis
import xjob

class XJOBMain(wax.Frame):
	"""
	The absolute controller interface for on-line processing of information
	using the xjob libraries.  There is no command line interface.
	"""
	def Body(self):
		# set up settings, input pipeline, source manager and output pipeline
		self.settings = xjob.Settings()
		self.manager = xjob.SourceManager()

		# load up resource
		res = waxrf.XMLResource()
		res.LoadFromFile(os.path.join(os.path.dirname(__file__),"Aegis.waxrf"))

		# setup image list from waxrf
		self.il = res.LoadObject(self, 'iolist')

		#############
		# TOP SECTION

		# create a new overlay panel for welcome message/inputlist
		self.top_op = wax.OverlayPanel(self)
		self.top_op.SetSize((430, 171))
		self.AddComponent(self.top_op, expand='b')

		# add an html informational display to the top overlay panel
		tophtml = wax.HTMLWindow(self.top_op, fullrepaint=0)

		# set up input listview
		self.inlist = aegis.ListView(self.top_op, icons='large', size=(430, 176))
		self.inlist.SetImageList(self.il, 0)

		# pack everything into the top overlay panel
		self.top_op.AddComponent(tophtml, expand='b')
		self.top_op.AddComponent(self.inlist, expand='b')
		self.top_op.Select(0)
		self.inlist.OnKeyDown = self.InputHitKey
		tophtml.SetPage(aegis.aegishtml.TopAbout)

		################
		# MIDDLE SECTION

		# load volume help dialog
		self.vhelpdialog = res.LoadDialog(self, 'volhelpdlg')
		self.vhelpdialog.SetSize((250, 200))
		self.vhelpdialog.html.SetPage(aegis.aegishtml.BasicHelp)

		# settings notebook definition
		self.nb = res.LoadObject(self, 'nb')
		self.nb.Size = (430, 210)
		self.AddComponent(self.nb, expand='h')
		self.nb.about.html.SetPage(aegis.aegishtml.InfoAbout)
		self.nb.output.container.Media.SetBackgroundColor("white")
		self.nb.output.container.Media.Select(0)
		self.nb.output.header.volhelp.OnClick = xjob.Callback(self.vhelpdialog.ShowModal)

		################
		# BOTTOM SECTION

		# create a new overlay panel for welcome message/inputlist
		self.bot_op = wax.OverlayPanel(self)
		self.bot_op.SetSize((430, 200))
		self.AddComponent(self.bot_op, expand='h')

		# add an html informational display to the top overlay panel
		bothtml = wax.HTMLWindow(self.bot_op, fullrepaint=0)

		# set up input listview
		self.outlist = aegis.ListView(self.bot_op, icons='large', size=(430, 115))
		self.outlist.SetImageList(self.il, 0)

		# pack everything into the top overlay panel
		self.bot_op.AddComponent(bothtml, expand='b')
		self.bot_op.AddComponent(self.outlist, expand='b')
		self.bot_op.Select(0)

		# set up the html display
		bothtml.SetPage(aegis.aegishtml.BottomAbout)

		# build drop target out of first list and set drag event handler for second
		filedrop = wax.FileDropTarget(self.top_op, event=self.InputDropFiles)
		self.outlist.OnBeginDrag = self.OutputDragFiles

		# set the activation functions for OnDrop, OnInsert, etc.
		self.inlist.OnInsertItem = self.TopPanelActivate
		self.outlist.OnInsertItem = self.BottomPanelActivate

		# set deletion functions for the input list
		self.inlist.OnMotion = self.ListMotion

		# setup statusbar
		self.statusbar = aegis.StatusBar(self, sizegrip=1)
		self.statusbar.SetMinHeight(50)

		# attach updateSettings call to each change event
		self.makeUpdateSettingsEvents(self.settings)

		# Set up a timer for updating the lists at 100ms
		timer = wax.Timer(self, event=self.ListUpdate)
		timer.Start(100)

		# build omnihandler, input and output pipelines
		self.callback = aegis.OmniHandler(self.inlist, self.settings,
		                                  self.outlist, self.statusbar,
		                                  self.manager)
		self.inputpipeline = xjob.InputPipeline(self.settings, self.manager,
		                                        self.callback)
		self.outputpipeline = xjob.OutputPipeline(self.settings, self.manager,
		                                          self.callback)

		# connect render "go" button with the output pipeline
		self.statusbar.renderer.CallOnClick = self.outputpipeline.run

		# pack the window for display
		self.top_op.Pack()
		self.bot_op.Pack()
		self.Pack()

	def TopPanelActivate(self, evt=None):
		""" Handler for activation of the top panel's overlay state """
		self.top_op.Select(1)
		evt.Skip()

	def BottomPanelActivate(self, evt=None):
		""" Handler for activation of the bottom panel's overlay state """
		self.bot_op.Select(1)
		evt.Skip()

	def ListMotion(self, evt=None):
		""" Catch movement in the input list and show informational text """
		listindex, _ = self.inlist.HitTest(evt.GetPosition())
		try:
			if listindex > -1:
				# this breaks the 4th wall of abstraction, but it IS a hack
				target = self.inlist._dict[self.inlist._ids[self.inlist.GetItemData(listindex)]]
				self.statusbar['info'] = target['name'] + ': ' +\
										 str(target['documents']) + ' documents, ' +\
										 target['sizetext']
										 #str(target['pages']) + 'pages, ' +\
				wxYield()
			else:
				self.statusbar['info'] = ''
		except Exception, inst:
			self.statusbar['info'] = 'Error in processing'
			self.statusbar.AddWarning(repr(inst))
		finally: evt.Skip()

	def InputHitKey(self, evt=None):
		""" Handler for input's character event (Delete Source) """
		# if this isn't a delete event, we don't care
		if evt.GetKeyCode() != wxk_del:
			evt.Skip()
			return

		# delete all the selected sources
		for selected in self.inlist.GetSelected():
			self.manager.RemoveSource(self.inlist[selected,'id'])
			del self.inlist[selected]

		# clear and reset the top
		if len(self.inlist) == 0:
			self.top_op.Select(0)
			self.inlist.ClearAll()

	def InputDropFiles(self, x, y, filenames):
		"""
		Input handler for drop target.
		"""
		# spin threads to process incoming file names
		for filename in filenames:
			self.statusbar.AddInfo("Opening " + filename)
			self.inputpipeline.put(filename)

	def OutputDragFiles(self, evt=None):
		"""
		Method:
			Runs drag event from output list.
			Operates on completed volumes only.
		"""
		# keep track of files
		files = []

		# get ids for each icon that is being dragged
		for selected in self.outlist.GetSelected():
			# pull accessor data
			volname = self.outlist[selected,'id']

			# is the volumemanager ready to release this volume?
			if self.volmanager.IsRendered(volname):
				# add file data from status to drag list
				files.append(self.manager.GetPath(volname))

		# do drag and drop if there's data
		if len(files): aegis.FileDropSource(files)

		# skip event
		evt.Skip()

	def makeUpdateSettingsEvents(self, settings):
		"""
		Function to rapidly assign updateSettings to the changed event for
		all the controls that updateSettings will touch.

		This is a strange function.  It takes the structure from the waxrf
		layout file and translates it to an actual path structure (with some
		sugar) for XML passing.  It's a lot faster than an LUT, though.
		"""
		# set origtext to false
		self._origtext = None

		reservedtbs = ('this', 'id', 'about')
		reservedsts = ('controls', 'expand', 'proportion', 'align', 'this',
		               'border', '_packed', 'sizer')

		# iterate through notebook's children (except reserved attributes)
		for tab in [tab for tab in self.nb.__dict__ if tab not in reservedtbs]:
			# iterate through widgets via dictionary (except reserved attributes)
			for setting, widget in self.nb.__dict__[tab].container.__dict__.items():
				# skip past unwanted entries
				if isinstance(widget, wxBitmap): continue
				if setting in reservedsts: continue

				# if there's a horizontal panel, get the Text child
				if isinstance(widget, wax.HorizontalPanel):
					widget = widget.__dict__['Text']

				# preset properties based on defaults
				settings[tab,setting] = widget.GetValue()

				# set callback OnSelect for RadioButton and ComboBox widgets
				if isinstance(widget, wax.RadioButton) or \
				   isinstance(widget, waxrf.BitmapComboBox):
					widget.OnSelect = xjob.Callback(self.updateSettings,
					                                settings, (tab,setting),
					                                widget)

				# set callback OnCheck for CheckBox widgets
				elif isinstance(widget, wax.CheckBox):
					widget.OnCheck = xjob.Callback(self.updateSettings,
					                               settings, (tab,setting),
					                               widget)

				# set callback OnText for CheckBox widgets
				elif isinstance(widget, wax.TextBox):
					# store original style for text boxes
					if self._origtext is None:
						self._origtext = widget.GetDefaultStyle()

					widget.OnText = xjob.Callback(self.updateTextBoxSettings,
					                              settings, (tab,setting),
					                              widget)

	def updateSettings(self, settings, key, widget):
		"""
		Handler for updating settings

		Parameters:
			settings -- an XJOBSettings object
			key -- a 2-tuple specifying the branch and the leaf to set
			widget -- a reference to the value-holding widget
		"""
		# call out to settings
		settings[key] =  widget.GetValue()
		if __debug__: print ET.dump(self.settings._settings)

	def updateTextBoxSettings(self, settings, key, widget):
		"""
		Handler for updating the XJOBSettings object

		Parameters:
			settings -- a Settings object
			key -- a 2-tuple specifying the branch and the leaf to set
			widget -- a reference to the value-holding widget
		"""
		value = widget.GetValue()

		# test for mask matching
		try:
			key[1] in ("PageMask", "FileMask") and PageFileMask(value).result is None
			key[1] == "Volume" and VolumeMask(value).result is None
			bad = False
		except: bad = True

		# if the mask isn't worth the screen it was printed on, set colors
		if bad:
			print "BAD:", value
			widget.SetForegroundColor("orange red")

		# else play nice and let settings go through
		else:
			widget.SetForegroundColor("black")

			# call out to settings
			settings[key] = value

			if __debug__: print ET.dump(self.settings._settings)

		# redraw the widget
		widget.Refresh()

	def ListUpdate(self,event=None):
		"""
		Event:
			While the application is idle, redraw box/volume text
		"""
		if len(self.inlist.retexts + self.outlist.retexts) == 0:
			event.Skip()
			return

		# freeze, redraw text, and unfreeze
		for lrt in (self.inlist, self.outlist):
			if len(lrt.retexts) > 0:
				lrt.Freeze() ; lrt.Retext() ; lrt.Thaw()

	def OnClose(self, event):
		self.Hide()
		self.inputpipeline.close()
		self.outputpipeline.close()
		sleep(.5)

		# kill all threads and exit
		exit(1)

# do main loop stuff
app = wax.Application(XJOBMain, title='XJOB Processor', direction='vertical')
app.Run()
