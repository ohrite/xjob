# Basic postscript printing idea (switch to tray 2, print something, back to 4)
# Eric Ritezel -- December 15, 2006

import win32print
import PSDraw
import StringIO

# set dpi reference
inch = 72

# setup buffer
psbuf = StringIO.StringIO()
psctl = PSDraw.PSDraw(psbuf)

# draw postscript with drawer change
psctl.begin_document()
psctl.set_mediatype("")

# get number of chunks


# get printer name and open
printer = win32print.GetDefaultPrinter()
hPrinter = win32print.OpenPrinter (printer)

# from Golden
try:
  hJob = win32print.StartDocPrinter (hPrinter, 1, ("test of raw data", None, "RAW"))
  try:
    win32print.WritePrinter (hPrinter, raw_data)
  finally:
    win32print.EndDocPrinter (hPrinter)
finally:
  win32print.ClosePrinter (hPrinter)
