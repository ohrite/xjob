#-------------------------------------------------------------------
# handlers.py
#   Purpose: Handler classes for WaxRF support
#    Author: Jason Gedge
#
#    TODO:
#       - Provide a facility to use the ArtProvider
#           (put this in WaxRF_LoadImage)
#       - ToolBar support, but Wax needs this first! :)
#       - StatusBar support? (maybe load a panel setup?)
#       - More work for StyledTextBoxHandler (colors, lexer, etc)
#-------------------------------------------------------------------


import wax
import imgcoder
import wax.tools.wizard
import wx
from bitmapcombobox import BitmapComboBox

##################################################################################

def get_and_delete(dict, key, default):
    """ checks for the item in the dictionary, and if it exists it will be
        be returned and deleted. """
    value = dict.get(key, default)
    if key in dict:
        del dict[key]
    return value

def WaxRF_LoadImage(bmpref, waxrf):
    bmp = waxrf.LoadImage(bmpref)
    if bmp: return bmp

    bmp = wax.BitmapFromFile(bmpref)
    if bmp: return bmp

    raise ValueError('could not load bitmap for staticbitmap')

##################################################################################

class BasicHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.__dict__[self.control](parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)
        return object

##################################################################################

class BasicContainerHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.__dict__[self.control](parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        # load all its children, pack it, and return it
        for child in self.children:
            cobject = child.Handle(object)
            border, align, expand = child.addprops
            object.AddComponent(cobject, border=border, expand=expand, align=align)

        object.Pack()
        return object

##################################################################################

class XMLSimpleDialog(wax.CustomDialog):
    def __init__(self, parent, children, *args, **kwargs):
        self.children = children
        wax.CustomDialog.__init__(self, parent, *args, **kwargs)

    def Body(self):
        # load all its children, pack it, and return it
        for child in self.children:
            cobject = child.Handle(self)
            border, align, expand = child.addprops
            self.AddComponent(cobject, border=border, expand=expand, align=align)

class XMLDialog(wax.Dialog):
    def __init__(self, parent, children, *args, **kwargs):
        self.children = children
        wax.Dialog.__init__(self, parent, *args, **kwargs)

    def Body(self):
        # load all its children, pack it, and return it
        for child in self.children:
            cobject = child.Handle(self)
            border, align, expand = child.addprops
            self.AddComponent(cobject, border=border, expand=expand, align=align)

class DialogHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.buttonpanel = bool(get_and_delete(self.attribs, 'buttonpanel', False))

    def Handle(self, parent):
        if self.buttonpanel:
            object = XMLDialog(parent, self.children, **self.attribs)
        else:
            object = XMLSimpleDialog(parent, self.children, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)
        return object

##################################################################################

class GridHandler:
    # note:
    #  --- children, in order, are added left to right, top to bottom

    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.GridPanel(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        rows = self.attribs.get('rows', 1)
        cols = self.attribs.get('cols', 1)
        crow = 0
        ccol = 0

        # load all its children, pack it, and return it
        for child in self.children:
            # make sure crow/ccol is restricted correctly
            if ccol >= cols:
            	ccol = 0
                crow += 1
            if crow >= rows:
				break
            # add the child
            cobject = child.Handle(object)
            border, align, expand = child.addprops
            object.AddComponent(ccol, crow, cobject, border=border, expand=expand, align=align)

            # increment the column
            ccol += 1

        object.Pack()
        return object

##################################################################################

class FlexGridHandler:
    # note:
    #  --- children, in order, are added left to right, top to bottom

    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        gcols = get_and_delete(self.attribs, 'gcols', '').split(',')
        grows = get_and_delete(self.attribs, 'grows', '').split(',')
        self.rows = self.attribs.get('rows', 1)
        self.cols = self.attribs.get('cols', 1)

        # make sure the right amount of children exists
        assert len(self.children) == self.rows * self.cols

        # fetch the growable rows and cols
        if grows:
            self.grows = []
            for x in grows:
                try:
                    self.grows.append(int(x))
                except:
                    pass    # XXX exception / error message?!
        if gcols:
            self.gcols = []
            for x in gcols:
                try:
                    self.gcols.append(int(x))
                except:
                    pass    # XXX exception / error message?!

    def Handle(self, parent):
        object = wax.FlexGridPanel(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        for x in self.grows:
            object.AddGrowableRow(x)
        for x in self.gcols:
            object.AddGrowableCol(x)

        crow = 0
        ccol = 0

        # load all its children, pack it, and return it
        for child in self.children:
            # make sure crow/ccol is restricted correctly
            if ccol >= self.cols:
            	ccol = 0
                crow += 1
            if crow >= self.rows:
				break
            # add the child
            cobject = child.Handle(object)
            border, align, expand = child.addprops
            object.AddComponent(ccol, crow, cobject, border=border, expand=expand, align=align)

            # increment the column
            ccol += 1

        object.Pack()
        return object

##################################################################################

class SplitterHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.direction = get_and_delete(self.attribs, 'direction', 'h')
        self.sashpos = get_and_delete(self.attribs, 'sashposition', 100)
        self.minsize = get_and_delete(self.attribs, 'minsize', 20)

        # make sure the right amount of children exists
        assert len(self.children) == 2

    def Handle(self, parent):
        object = wax.Splitter(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        # load all its children, pack it, and return it
        win1 = self.children[0].Handle(object)
        win2 = self.children[1].Handle(object)

        # split it
        object.Split(win1, win2, self.direction, self.sashpos, self.minsize)

        return object

##################################################################################

class MenuHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.title = get_and_delete(self.attribs, 'text', '')

    def Handle(self, parent):
        object = wax.Menu(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        # load all its children, pack it, and return it
        for x in self.children:
            if x.control == "MenuItem":
                item = object.Append( x.text, **x.attribs )
                if item.IsCheckable(): item.Check(x.checked)
                item.Enable(x.enabled)
            elif x.control == "Separator":
                object.AppendSeparator()
            elif x.control == "Menu":
                object.AppendMenu( x.title, x.Handle(parent) )

        return object

class MenuItemHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.text = get_and_delete(self.attribs, 'text', '')
        self.checked = bool(get_and_delete(self.attribs, 'checked', False))
        self.enabled = bool(get_and_delete(self.attribs, 'enabled', True))

    def Handle(self, parent):
        pass

class MenuBarHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.MenuBar(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        for menu in self.children:
            object.Append(menu.Handle(parent), menu.title)

        return object

##################################################################################

class CheckBoxHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.state = get_and_delete(self.attribs, 'state', 'unchecked')

    def Handle(self, parent):
        object = wax.CheckBox(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)
        object.Set3StateValue(self.state)
        return object

##################################################################################

class CheckListBoxHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.CheckListBox(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        for item in self.children:
            text = item.attribs.get('text', '<no text>')
            checked = bool(item.attribs.get('checked', False))
            index = object.Append(text)
            object.Check(index, checked)

        return object

##################################################################################

class ComboBoxHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.text = get_and_delete(self.attribs, 'text', '')

    def Handle(self, parent):
        object = wax.__dict__[self.control](parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        object.SetValue(self.text)
        for item in self.children:
            text = item.attribs.get('text', '<no text>')
            object.Append(text)

        return object

##################################################################################

class ListBoxHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.__dict__[self.control](parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        selected = -1
        for item in self.children:
            text = item.attribs.get('text', '<no text>')
            index = object.Append(text)
            if item.attribs.get('selected', False):
                object.SetSelection(index)

        return object

##################################################################################

class ListViewHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.columns = get_and_delete(self.attribs, 'columns', '').split(',')
        self.numcols = len(self.columns)
        self.columnwidths = get_and_delete(self.attribs, 'colwidths', ',' * (self.numcols-1)).split(',')

        for x in range(len(self.columnwidths)):
            try:
                self.columnwidths[x] = int(self.columnwidths[x])
            except:
                self.columnwidths[x] = 100

        assert self.numcols > 0

    def Handle(self, parent):
        object = wax.ListView(parent, columns=self.columns, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        selected = -1
        num = 0
        for row in self.children:
            num = self._handlerow(object, row, num)

        return object

    def _handlerow(self, lv, row, num):
        assert len(row.children) <= self.numcols
        new_num = row.attribs.get('num', num)

        for col in range(len(row.children)):
            lv[new_num, col] = row.children[col].textValue

        return new_num + 1

##################################################################################

class ToggleButtonHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.state = bool(get_and_delete(self.attribs, 'pressed', False))

    def Handle(self, parent):
        object = wax.ToggleButton(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)
        object.SetValue(self.state)
        return object

##################################################################################

class TreeViewHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        if len(self.children) != 1:
            raise Exception("error: only one child allowed for treeview")

        object = wax.TreeView(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        # start loading the items
        self._load_node(object, self.children[0])

        return object

    def _load_node(self, object, node, parent=None):
        # load the attributes
        text = str(node.attribs.get('text', '<no text>'))
        value = node.attribs.get('value', None)
        expanded = bool(node.attribs.get('expanded', False))

        # add the item and set its text/data
        item = None
        if parent:
            item = object.AppendItem(parent, text)
        else:
            item = object.AddRoot(text)
        object.SetPyData(item, value)

        # load this nodes children
        for child in node.children:
            self._load_node(object, child, item)

        # expand this node, if necessary
        if expanded:
            object.Expand(item)

        return item

##################################################################################

class TreeListViewHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.columns = get_and_delete(self.attribs, 'columns', '').split(',')
        self.numcols = len(self.columns)
        self.maincolumn = get_and_delete(self.attribs, 'maincol', 0)
        self.columnwidths = get_and_delete(self.attribs, 'colwidths', ',' * (self.numcols-1)).split(',')

        for x in range(len(self.columnwidths)):
            try:
                self.columnwidths[x] = int(self.columnwidths[x])
            except:
                self.columnwidths[x] = 100

        assert self.numcols > 0

    def Handle(self, parent):
        if len(self.children) != 1:
            raise Exception("error: only one child allowed for treelistview")

        object = wax.TreeListView(parent, columns=self.columns, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        # set the initial attributes
        object.SetMainColumn(self.maincolumn)
        for x in range(len(self.columnwidths)):
            object.SetColumnWidth(x, self.columnwidths[x])

        # load the root item and its children
        root = self._load_node(object, self.children[0])

        return object

    def _load_node(self, object, node, parent=None):
        # get the attributes
        expanded = bool(node.attribs.get('expanded', False))

        # get the text values for each column
        texts = []
        for x in range(1, self.numcols+1):
            texts.append(str(node.attribs.get('col%d' % x, '')))

        # now add it to the treelistview object
        item = None
        if parent:
            item = object.AppendItem(parent, '<no text>')
        else:
            item = object.AddRoot('<no text>')

        # load the text values into each column
        for x in range(self.numcols):
            object.SetItemText(item, texts[x], x)

        # load this nodes children
        for child in node.children:
            self._load_node(object, child, item)

        # expand the node, if necessary
        if expanded:
            object.Expand(item)

        return item

##################################################################################

class NoteBookHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.NoteBook(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        for page in self.children:
            assert len(page.children) == 1
            text = page.attribs.get('text', '<no text>')
            win = page.children[0].Handle(object)
            object.AddPage(win, text=text)

        return object

##################################################################################

class BitmapHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.bmpobj = None

    def Handle(self, parent):
        if not self.bmpobj:
            data = imgcoder.DecodeImage(self.textValue)
            self.bmpobj = wax.BitmapFromData(data)
        if self._objname:
            setattr(parent, self._objname, self.bmpobj)

        return self.bmpobj

##################################################################################

class BitmapObjectHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.bmpref = get_and_delete(self.attribs, 'bmp', None)

    def Handle(self, parent):
        bmp = self.waxrf.LoadObject(parent, self.bmpref)
        object = wax.__dict__[self.control](parent, bmp, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)
        return object

##################################################################################

class RadioButtonHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.selected = bool(get_and_delete(self.attribs, 'selected', None))

    def Handle(self, parent):
        object = wax.RadioButton(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)
        if self.selected:
            object.SetValue(self.selected)

        return object

##################################################################################

class ImageListHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.imglist = None

    def Handle(self, parent):
        if self.imglist is None:
            self.imglist = wax.ImageList(**self.attribs)
            for item in self.children:
                bmp = item.attribs.get('bmp', None)
                bmp = self.waxrf.LoadObject(parent, bmp)
                self.imglist.Add(bmp, item._objname)
        if self._objname:
            setattr(parent, self._objname, self.imglist)

        return self.imglist

##################################################################################

class ToolBarHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.ToolBar(**self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        for img in self.children:
           pass

        return object

##################################################################################

class StyledTextBoxHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf

    def Handle(self, parent):
        object = wax.StyledTextBox(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)
        return object

##################################################################################

#		USER ADDITION AREA

##################################################################################

class BitmapComboBoxHandler:
    def __init__(self, control, attribs, addprops, children, waxrf):
        self.control = control
        self.attribs = attribs
        self.addprops = addprops
        self.children = children
        self.waxrf = waxrf
        self.text = get_and_delete(self.attribs, 'text', '')

    def Handle(self, parent):
        object = BitmapComboBox(parent, **self.attribs)
        if self._objname:
            setattr(parent, self._objname, object)

        object.SetValue(self.text)
        for item in self.children:
            bmp = item.attribs.get('bmp',wx.NullBitmap)
            bmp = self.waxrf.LoadObject(parent, bmp)
            text = item.attribs.get('text', '<no text>')
            object.Append(text, bmp)

        return object