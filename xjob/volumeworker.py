# VolumeWorker builds
# XMLRPC client for distributed processing architecture
# Eric Ritezel -- February 1, 2007
#

import xml.etree.ElementTree as ET
import os, xmlrpclib, uuid, time, base64, cStringIO
import copy, Queue, heapq
import threading

import Zeroconf

class ZConfAggregator:
	"""A collection client for the Zeroconf service."""
	def __init__(self):
		self.r = Zeroconf.Zeroconf()
		self.serverlist = {}

	# free all memory
	def __del__(self):
		self.r.close()
		del(self.serverlist)

	# get a given service by name (uh)
	def __getitem__(self, index): return self.serverlist[index]
	def __len__(self): return len(self.serverlist)
	def iteritems(self):
		for k, v in self.serverlist.items(): yield (k, v)

	# remove the given service from the list
	def removeService(self, zeroconf, type, name): del(self.serverlist[name])

	# add service to the list
	def addService(self, zeroconf, type, name):
		info = self.r.getServiceInfo(type, name)
		self.serverlist[name] = 'http://'+str(socket.inet_ntoa(info.getAddress()))+':'+str(info.getPort())

class VolumeWorker:
	def __init__(self, volume, callback=None, done=None):
		self.volume = volume
		self.callback = callback
		self.done = done

		# define a queue for threaded document input
		self.docpile = Queue.Queue()

		# define a queue for threaded document output
		self.reassemble = Queue.Queue()

		# define thread pool for document processor clients
		self.workers = []

		# attempt to pull server information from mDNS
		self.zconf = Zeroconf.Zeroconf()
		self.aggregator = ServiceBrowser(self.zconf,'_ephemerol._tcp.local.',
		                                 ZConfAggregator())

	def run(self):
		# spin a reassembly thread to repack volume
		# reassembly thread also writes volumes to new temp directory
		# which means it contains a great deal of logic
		reassembly = ReassemblyWorker(self.volume, self.reassemble, self.callback)

		if len(self.aggregator):
			# spin enough batch clients to work with each server
			for servername, server in self.aggregator.iteritems():
				self.callback(info="Connecting to "+servername)
				self.workers.append(BatchClient(
						self.volume.find('.//settings'),
						self.docpile, self.reassemble, server,
						callback=self.callback, done=self.RenderDone))
				self.workers[-1].start()

			# push all documents from volume onto docpile
			for box in self.volume.findall('.//box'):
				basepath = box.get('path')
				for doc in self.volume.findall('.//document'):
					self.docpile.put((basepath, doc))

		# okay... can't see anything, so let's just run locally.
		else: self.DoRender()

		# while reassembly is still ongoing, wait
		while reassemble.isAlive() and not self.reassemble.empty():
			time.sleep(5)

		# make sure the reassembly thread finished cleanly
		if not self.reassemble.empty():self.callback(error="Reassembly failed")

		# shut down zeroconf aggregator, free the listener and close zeroconf
		self.aggregator.cancel()
		self.aggregator.join()
		del(self.aggregator.listener)
		self.zconf.close()

		return (self.reassemble.empty() and (self.volume,) or (None,))[0]

	def RenderDone(self, thread, dislike=None):
		# issue complaint to local server
		if dislike is not None:
			self.callback(warn="Could not process on " + dislike)

		# remove thread
		self.workers.remove(thread)

		# if external renderers are done and there is still work to be done
		if not len(self.workers) and not self.docpile.empty(): self.DoRender()

	def DoRender(self):
		""" This function creates a local factory for rendering documents. """
		import ocr, embed, export
		self.callback(info="Processing remaining documents locally.")

		# if needed by processing, create an OCR object
		if self.volume.find('.//settings//OCR'):
			if not ocr.test():
				self.callback(error="Project needs OCR, but cannot start OCR.")
				return None
			else: ocr_obj = ocr.OCR()
		else: ocr_obj = None

		# if needed by processing, create an Embed object
		if self.volume.find('.//settings//Embed'):
			if not embed.test():
				self.callback(error="Project needs Embed, but cannot Embed.")
				return None
			else: embed_obj = embed.Embed()
		else: embed_obj = None

		# if needed by processing, create an Embed object
		if self.volume.find('.//settings//Export'):
			if not export.test():
				self.callback(error="Project needs Export, but cannot Export.")
				return None
			else: export_obj = embed.Export()
		else: export_obj = None

		# run processing loop
		while True:
			# get a document with a basepath from the queue
			try: basepath, doc = self.docpile.get(block=True, timeout=5)
			except: break

			# see if we have to export to pump the pipeline
			# FIXME: add export object to pipeline
			if export_obj is not None: pass

			# process each page
			for page in doc.findall('.//page'):
				pass

class ReassemblyWorker(threading.Thread):
	def __init__(self, volume, queue, callback=None):
		threading.Thread.__init__(self)
		self.queue = queue
		self.callback = callback
		self.volume = volume

	def run(self):
		# create new heap to push items to
		heeep = []

		# sleep for 10 seconds while the queue fills up
		sleep(10)

		while True:
			# grab a new item from the qweueue
			try: doc = self.queue.get(block=True, timeout=5)
			except: break

			# write payload (rendered pages / exported stuff) to disk and free


			# push document to queue
			heapq.heappush(heeep, (doc.get('id'), doc))

		# create new XJOB tree


		# write heap, do transforms and clean up
		while True:
			try:
				# get a document
				doc = heapq.heappop(heep)[1]

				# append document node to new XJOB tree


			# end the loop if we've hit the end
			except IndexError: break

	def IsDone(self): return True

class BatchClient(threading.Thread):
	def __init__(self, settings, documentpile, reassemble, server, callback=None, done=None):
		threading.Thread.__init__(self)

		# define settings
		self.settings = settings

		# set up callback functions
		self.callback = callback
		self.done = done

		# define queues for pushing/pulling data
		self.docpile = documentpile
		self.reassemble = reassemble

		# set up server parameters and connect
		self.servername = server
		self.server = xmlrpclib.ServerProxy(self.servername)

	def run(self):
		# probe server or die and inform
		try:self.server.CanIComeOver()
		except: return self.done(self, dislike=self.servername)

		# run processing loop
		while True:
			try: basepath, doc = self.docpile.get(block=True, timeout=5)
			except: break

			# create universal data container parameters (uuid and a stream)
			docid = str(uuid.uuid1())
			data = cStringIO.StringIO()

			# build a new xjob
			for page in doc.findall('.//page'):
				datanode = ET.SubElement(page, "data")

				# this mess basically checks for the oldfilename key's validity
				# if it's in place at the old location (for resumed jobs, etc.)
				# it pulls it, otherwise it goes with the existing filename
				# this is done so that if new data is deleted and the job is
				# restarted, the old data will still be perfectly valid and happy
				pagepath = page.attrib.get('oldpath',page.attrib['path'])
				pagepath = os.path.join(basepath, pagepath)
				oldfile = page.attrib.get('oldfilename', False)
				if oldfile: oldfile = os.path.join(pagepath, oldfile)
				pagepath = os.path.join(pagepath, page.attrib['filename'])

				base64.encode(open(\
					(oldfile and (oldfile,) or (pagepath,))[0],'rb'), data)

				datanode.text = data.getvalue()

			# build an xjob wrapper with a new uuid to identify the batch
			xjobdata = ET.Element("xjob")
			xjobdata.insert(0, self.settings)
			xjobdata.append(doc)
			xjobdata = ET.tostring(xjobdata).encode('zip').encode('base64')

			# set a giveup counter
			errorcount = 0

			while True:
				try:
					if self.server.CanIComeOver():
						if not self.server.sendXJOB(docid, xjobdata):
							self.callback(warn="Server refused my data")
							self.docpile.put(doc)
							self.done(self, dislike=self.servername)
							return

					# standby while server is processing
					while not self.server.CanIGetMyResults(docid):time.sleep(5)

					# get and decode the results
					result = self.server.GetResults(docid)
					result = result.decode('base64').decode('zip')

					# fire done event back to server
					self.server.Done(docid)
					break
				except Exception, inst:
					errorcount += 1
					print inst, "hello? hello?  is anyone there?"

					# if we should give up (after ~15 seconds)
					# tell the user about it and inform the server of our dislike
					if errorcount > 3:
						self.callback(warn="Giving up on " + self.servername)
						self.docpile.put(doc)
						self.done(self, dislike=self.servername)
						return

				# nail sleep
				time.sleep(10)

			# bump callback progress
			self.callback('add', donepages=len(doc.findall('.//page')))

			# add page to reconstruction queue
			self.reassemble.put(doc)

		# end of the loop
		self.done(self)

