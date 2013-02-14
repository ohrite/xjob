@echo off

del *.pyc
del tp*.BAT

set distdir=Ephemerol

"C:\Python25\python.exe" build_Ephemerol.py py2exe -O2 --dist-dir=%distdir%

attrib +R +H %distdir%\*.dll
attrib +R +H %distdir%\w9xpopen.exe
attrib +R +H /S /D %distdir%\icons
attrib +R +H /S /D %distdir%\support