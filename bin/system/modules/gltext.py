import sys


# TODO: this is not a foolproof way to detect 64-bit python. at least not under windows.
_64bit = sys.maxint == 0x7fffffffffffffff

# python 2.6.x
if 0x2060000 <= sys.hexversion < 0x2070000:
    if   sys.platform == "linux2" and _64bit:
        from linux_py26_64.gltext import *

    elif sys.platform == "linux2":
        from linux_py26_32.gltext import *

    elif sys.platform == "darwin":
        from macosx_py26.gltext import *

    elif sys.platform == "win32" and _64bit:
        from windows_py26_64.gltext import *

    else:
        raise RuntimeError, "unsupported platform '%s'" % sys.platform

# python 2.7.x
elif 0x2070000 <= sys.hexversion < 0x2080000:
    if   sys.platform == "linux2" and _64bit:
        from linux_py27_64.gltext import *

    elif sys.platform == "linux2":
        from linux_py27_32.gltext import *

    elif sys.platform == "darwin":
        from macosx_py27.gltext import *

    elif sys.platform == "win32" and _64bit:
        from windows_py27_64.gltext import *

    else:
        raise RuntimeError, "unsupported platform '%s'" % sys.platform

else:
    print "error importing gltext: python version 2.6.x or 2.7.x required. you have", sys.version
    raise ImportError
