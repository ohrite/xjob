# combobox.py

import wx.combo
from wax import containers
from wax import styles
from wax import waxobject

class BitmapComboBox(wx.combo.BitmapComboBox, waxobject.WaxObject):

    __events__ = {
        'Select': wx.EVT_COMBOBOX,
        'TextChanged': wx.EVT_TEXT,
    }

    def __init__(self, parent, choices=[], size=None, **kwargs):
        style = 0
        style |= self._params(kwargs)
        style |= styles.window(kwargs)

        wx.combo.BitmapComboBox.__init__(self, parent, wx.NewId(), "",
         size=size or (-1,-1), choices=choices, style=style)
        self.SetDefaultFont()

        self.BindEvents()
        styles.properties(self, kwargs)

    def SetItems(self, items):
        """ Clear the internal list of items, and set new items.  <items> is
            a list of 3-tuples (string, bitmap, data). """
        self.Clear()
        for s, data in items:
            self.Append(s, data)

    def GetItems(self):
        """ Return a list of 3-tuples (string, bitmap, data). """
        items = []
        for i in range(self.GetCount()):
            s = self.GetString(i)
            data = self.GetClientData(i)
            items.append((s, data))
        return items

    #
    # style parameters

    def _params(self, kwargs):
        flags = wx.CB_DROPDOWN # default
        flags |= styles.stylebool('simple', wx.CB_SIMPLE, kwargs)
        flags |= styles.stylebool('readonly', wx.CB_READONLY, kwargs)
        flags |= styles.stylebool('sort', wx.CB_SORT, kwargs)
        return flags
