# taskbaricon.py

from wax import waxobject
import wx

def MakeIcon(path): return wx.Icon(path, wx.BITMAP_TYPE_PNG)

class TaskBarIcon(wx.TaskBarIcon, waxobject.WaxObject):

    __events__ = {
        'LeftDoubleClick': wx.EVT_TASKBAR_LEFT_DCLICK,
        'RightUp': wx.EVT_TASKBAR_RIGHT_UP,
        'LeftDown' : wx.EVT_TASKBAR_LEFT_DOWN,
        'RightDoubleClick' : wx.EVT_TASKBAR_RIGHT_DCLICK,
        'RightUp': wx.EVT_TASKBAR_RIGHT_UP,
        'RightDown': wx.EVT_TASKBAR_RIGHT_DOWN,
    }

    def __init__(self):
        wx.TaskBarIcon.__init__(self)
        self.BindEvents()

    def SetIcon(self, obj, tooltip=""):
        """ Like wx.Frame.SetIcon, but also accepts a path to an icon file. """
        if isinstance(obj, str) or isinstance(obj, unicode):
            obj = wx.Icon(obj, wx.BITMAP_TYPE_PNG)    # FIXME
        wx.TaskBarIcon.SetIcon(self, obj, tooltip)
