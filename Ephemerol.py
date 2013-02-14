# XML-RPC command dispatch server
# Codename Ephemerol
# Eric Ritezel -- February 2, 2007
#
# v0.0.9 -- (20070208) Frontend polished and ready for testing
# v0.0.95 -- (20070220) Added Zeroconf
# v0.0.97 -- (20070222) Added Pipelines
#

__author__ = "Eric Ritezel"
__date__ = "2007-02-22"
__pname__ = "Ephemerol"
__domain__ = "ritezel.com"
__version__ = "0.0.97"
__description__ = 'A peer-to-peer volume rendering server for legal data.'

import SimpleXMLRPCServer, xmlrpclib, socket
import xml.etree.ElementTree as ET
import os.path, threading
from time import sleep, strftime

# fire up zeroconf binding for announcing myself
from xjob import Zeroconf

# for Ephemerol server frontend
import wax
from aegis.logwindow import AutoWidthListView
from aegis.taskbaricon import TaskBarIcon, MakeIcon as atMakeIcon

# find out if we can OCR
from xjob.ocr import Worker as OCRWorker, test as OCRTest
CanOCR = OCRTest()

# find out if we can embed
from xjob.embed import Worker as EmbedWorker, test as EmbedTest
CanEmbed = EmbedTest()

# find out if we can export
from xjob.export import Worker as ExportWorker, test as ExportTest
CanExport = ExportTest()

# spin a server off into an independent thread
class ThreadedServer(threading.Thread):
	"""
	An XMLRPC server that lives in a thread.
	It does processing of Aegis-style xjob parameters by document.

	Its interface has 5 main calls:
	CanIComeOver(id)
	SendXJOB(id,xjob)
	CanIGetMyResults(id)
	GetResults(id)
	Done(id)

	Usage:
		>>> self.servthread = ThreadedServer(32001, callback)
		>>> self.servthread.start()

		Where callback is a function that throws messages in this format:
			('<category>',<(error|warn|info)>='<message>')
		That gets called like this: self.callback('ServerError',error="Died!")
	"""

	def __init__(self, port, callback=None):
		threading.Thread.__init__(self)
		self.port = port

		# communication with the log window
		self.callback = callback

		# thread / server stuff
		self.timeToQuit = threading.Event()
		self.timeToQuit.clear()

		# set up local ip pulls
		self.hostname = socket.gethostname()
		self.ip = socket.gethostbyname(self.hostname)
		self.ipaton = socket.inet_aton(self.ip)

		# start up server
		self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((self.ip,port))
		self.nameserver = Zeroconf.Zeroconf()

		# define capabilities
		self.capabilities = {'OCR':repr(CanOCR),
		                     'Embed':repr(CanEmbed),
		                     'Export':repr(CanExport),
		                     'Description':" ".join((__pname__,':',__description__))}

		# define service
		self.service = Zeroconf.ServiceInfo('_ephemerol._tcp.local.',
		               socket.gethostname()+'._ephemerol._tcp.local.',
		               address=self.ipaton, port=6669,
		               weight=0, priority=0,
		               properties=self.capabilities)

		# stuff for processing
		self.threads = threading.BoundedSemaphore(value=3)
		self.xjob = None
		self.value = None

	def run(self):
		# register XMLRPC instance
		self.server.register_function(self.CanIComeOver)
		self.server.register_function(self.CanIGetMyResults)
		self.server.register_function(self.SendXJOB)
		self.server.register_function(self.GetResults)
		self.server.register_function(self.Done)

		# announce self via zeroconf
		self.nameserver.registerService(self.service)

		# run server
		while not self.timeToQuit.IsSet(): self.server.handle_request()

	def stop(self):
		# throw unregistration and end to mDNS
		self.nameserver.unregisterService(self.service)
		self.nameserver.close()

		# hack to pump an event into the server
		self.timeToQuit.set()
		xmlrpclib.ServerProxy("http://"+str(self.ip)+":"+str(self.service.getPort())).CanIComeOver()

		return 0

	# important functionality discovery functions
	def CanIComeOver(self):
		self.callback('Ping',info='Somebody wants me!')
		return self.xjob is None

	def CanIGetMyResults(self, clientid):
		self.callback('Poll',zap=str(clientid)+' is asking for its data')
		return self.value is not None and self.xjob.attrib['id'] == clientid and\
		       not self.threads._Semaphore__value == 3

	def SendXJOB(self, xjobid, xjobdata):
		"""
		Remote Public:
			Gets an xjob wrapper of any number of granular objects
			(page, document, file, box, whatever .. it all goes by page)
		Parameters:
			xjobdata -- a string etree produced from an xjob
		"""
		# Q: why do we not have multiple sessions?
		if self.xjob is not None:
			self.callback('Refused', warn="Denied other server")
			return False

		# A: so we can put in performance tuning
		# (wow, look at this!  it doesn't care about speed at all!)
		self.xjob = ET.fromstring(xjobdata.decode('base64').decode('zip'))
		self.xjob.attrib['id'] = xjobid

		# add to server messages
		self.callback('Running', info="Running xjob against %s" % self.xjob.get('id'))

		# throw the bastard back in the ocean
		return runstate

	def GetResults(self, clientid):
		"""
		Public Call:
			A qualified ping that dumps data
		Parameters:
			clientid -- the id to check against
		Returns:
			If the data for <clientid> is done, return it; else return False
		"""
		if self.value is not None: return self.value
		else: return False

	def Done(self, clientid):
		"""
		Public Call:
			A fatal finishing move for the data corresponding to clientid
		Parameters:
			clientid -- the id to check against
		Returns:
			True if the data was removed, false if not
		"""
		if self.xjob.get('id') == clientid:
			self.callback('Complete', info=self.xjob.get('id'))
			self.xjob = None
			self.value = None
			return True
		else:
			return False

	def __doneThread(self, thread):
		"""
		Private:
			A callback point for thread workers.
		"""
		# wait for the thread to die and release a semaphore
		self.callback('Complete', info=thread.getName()+' has finished.')
		thread.join()
		self.threads.release()

		# render data if there are no more active threads
		if self.threads._Semaphore__value == 3:
			self.value = ET.tostring(self.xjob).encode('zip').encode('base64')

class Ephemerol(wax.Frame):
	def Body(self):
		self.trayicon = ['normal','normal']
		self.servicons = {
			"normal": atMakeIcon(os.path.join('icons','server.png')),
			"warning": atMakeIcon(os.path.join('icons','server_error.png')),
			"error": atMakeIcon(os.path.join('icons','server_delete.png')),
			"info": atMakeIcon(os.path.join('icons','server_add.png')),
			"zap": atMakeIcon(os.path.join('icons','server_zap.png')),
		}

		self.tbicon = TaskBarIcon()
		self.tbicon.SetIcon(self.servicons['normal'], 'Ephemerol Processing Center')

		self.tbicon.OnLeftDoubleClick = self.RestoreWindow
		self.tbicon.OnRightUp = self.ShowTaskBarMenu

		self.loglist = AutoWidthListView(self, columns=('Type','Message'))
		self.AddComponent(self.loglist, expand='both')

		self.Pack()

		self.SetSize((200,300))
		self.SetIcon(self.servicons['normal'])

		# set up blinker
		self.blink_counter = 0
		self.timer = wax.Timer(self, event=self.BlinkIcon)
		self.timer.Start(850)

		# kick off one server thread
		self.servthread = ThreadedServer(32001, self.ServerMessage)
		self.servthread.start()

	def RestartServer(self, event):
		self.servthread.stop()
		sleep(1)
		self.servthread = ThreadedServer(32001, self.ServerMessage)
		self.servthread.start()
		self.trayicon[0] = 'normal'
		self.trayicon[1] = 'zap'
		self.blink_counter = 0
		self.ServerMessage('ServRestart', zap='Restarting server at %s'%strftime("%c"))

	def RestoreWindow(self, event=None):
		""" Show/restore main window. """
		self.Show(1)
		self.Iconize(0)

	def HideWindow(self, event=None):
		self.Iconize(1)

	def ShowTaskBarMenu(self, event=None):
		menu = wax.Menu(self.tbicon)

		# choose Show/Hide based on current window state
		if self.IsIconized():
			menu.Append('&Show window', self.RestoreWindow)
		else:
			menu.Append('&Hide window', self.HideWindow)

		# these entries are always present
		menu.Append('&Restart Server', self.RestartServer)
		menu.Append('E&xit', self.ExitApp)

		self.tbicon.PopupMenu(menu)

	def ExitApp(self, event):
		self.Close(True)
		self.tbicon.Destroy()# without this, icon stays in tray

	def OnIconize(self, event=None):
		self.Iconize(1) # minimize
		self.Show(0)    # hide taskbar button

	def OnClose(self, event):
		self.HideWindow()
		self.servthread.stop()
		self.timer.Stop()
		self.Destroy()

	def ServerMessage(self, level='info', **kwargs):
		if len(kwargs) == 0: self.loglist.append(('Debug', 'ServerMessage needs kwargs'))
		self.loglist.append((level,kwargs.values()[0]))

		# blink the tray icon
		key = kwargs.keys()[0].lower()
		if (self.trayicon[0] == self.trayicon[1] or key == 'error') and\
			key in self.servicons.keys():
			self.trayicon[1] = key

	def BlinkIcon(self, event=None):
		# reset the blink counter
		if self.trayicon[0] == self.trayicon[1]:
			self.blink_counter = 0
			return

		self.tbicon.SetIcon(self.servicons[self.trayicon[self.blink_counter % 2]], 'Ephemerol Processing Center')
		self.blink_counter += 1

		# cannot unset an error without restarting
		if self.blink_counter > 8 and self.trayicon[1] != 'error':
			self.trayicon[1] = self.trayicon[0]

app = wax.Application(Ephemerol, title='Ephemerol Server')
app.Run()
