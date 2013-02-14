from wax import bitmap
import os.path

class AegisImages:
	def __init__(self):
		self.data = {
			"error": bitmap.BitmapFromFile(os.path.join('icons','exclamation.png')),
			"info": bitmap.BitmapFromFile(os.path.join('icons','information.png')),
			"warn": bitmap.BitmapFromFile(os.path.join('icons','error.png')),
			"disabled": bitmap.BitmapFromFile(os.path.join('icons','accept.png')),
			"go": bitmap.BitmapFromFile(os.path.join('icons','go.png')),
			"go_blue": bitmap.BitmapFromFile(os.path.join('icons','go_blue.png')),
		}

	def __getitem__(self,key):
		if not self.data.has_key(key): return None
		return self.data[key]
