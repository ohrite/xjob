# html generation constants for Aegis
# Eric Ritezel -- February 21, 2007

import re
import os.path

pathto = lambda img: os.path.join(os.path.dirname(__file__), 'images', img)

roundTop = '''
<html>
<body bgcolor="#696969">
<font color="#222222" face="Trebuchet MS, Verdana, Georgia, Times New Roman">
<div align="center">
<table border="0" cellspacing="0" cellpadding="0" bgcolor="white" align="center" width="95%">
<tr valign="top"><td width="20" align="left"><img src="''' + pathto('tl.gif') +'''" /></td><td width="100%">&nbsp;</td><td width="20" align="right"><img src="''' + pathto('tr.gif') +'''" /></td></tr><tr><td></td><td>
'''

roundBottom = '''\
</td><td></td></tr>
<tr valign="bottom"><td width="20" align="left"><img src="''' + pathto('bl.gif') +'''" /></td><td width="100%">&nbsp;</td><td width="20" align="right"><img src="''' + pathto('br.gif') +'''" /></td></tr>
</table>
</div>
</font>
</body>
</html>
'''

roundTopEsc = re.sub(r'%{1}', r'%%', roundTop)

roundBottomEsc = re.sub(r'%{1}', r'%%', roundBottom)

About = """\
<div align="left">
	&nbsp; This program processes files.
	It can then produce ready-to-burn volumes.
</div>"""

TopAbout = roundTop + '''\
<table border="0" cellspacing="0" cellpadding="0" width="200"><tr>
	<td><img src="''' + pathto('id.gif') +'''"></td>
	<td valign="center"><h1><br><b>Aegis</b></h1></td>
</tr></table><div>'''+About+'''</div>
''' + roundBottom


BottomAbout = roundTop + """\
<div align="left">
	Volumes will appear in this output window when they have completed
	rendering.  If you have a copy of the <b><i>Ephemerol</i></b> server,
	please run it now.
</div>
""" + roundBottom

InfoAbout = "<br />" + roundTop + """\
<div align="left">
	<i><b>Aegis</b></i> is copyright &copy; 2006-2007 Eric Ritezel.<br />
	Technologies used include:<br />
	<b>XJOB</b>, <b>Ephemerol</b>, <b>DarkHorse</b> &copy; Inductive Art<br />
	<b>Zeroconf</b> &copy; Apple, Inc., <b>Reverend</b> &copy; DivMod
</div>
""" + roundBottom

BasicHelp = "<br />" + roundTop + """\
<div align="left">
	<h1>Using Aegis</h1>
	<p>
	More here soon
	</p>
</div>
""" + roundBottom