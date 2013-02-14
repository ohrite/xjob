from distutils.core import setup
import py2exe
import os, glob

sep = os.path.sep

# build information
buildVersion = "Ephemerol 0.9.9"

# A nice template to give XP some widget drawing hints
manifest = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="%(prog)s"
    type="win32"
/>
<description>%(desc)s</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''

RT_MANIFEST = 24

# run setup command
setup(
	windows=[
		{'script':'Ephemerol.py',
		 'other_resources': [(u"VERSIONTAG",1,buildVersion), (24,1,manifest % {'prog':'Ephemerol','desc':'Distributed Processing Center'})],
		 'icon_resources': [(1,'icons' + sep + 'ephemerol.ico')]
		}
	],
	zipfile = r"support\Ephemerol.dat",
	name="Ephemerol",
	version="1.0.9.9",
	description="Distributed Processing Center",
	data_files=[
		("icons",
			glob.glob("icons" + sep + "*.png")
		),
		("support",[
			"dlls" + sep + "gdiplus.dll",
			"dlls" + sep + "msvcp71.dll"
		]),
		"doc"+ sep +"About.txt",
		"doc"+ sep +"Install.txt"
	]
)