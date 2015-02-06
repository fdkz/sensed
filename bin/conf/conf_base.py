"""
IMPORTANT: CHANGES HERE WILL HAVE NO EFFECT

    this file is here only for reference, to show what can be changed
    in conf.py and what the default values are.


Create conf/conf.py or ../conf/conf.py like this:

c.debug = True
...
#conf_overrides = ["nextconf.py"]
"""

class Conf: pass

# a global object that every class knows about. just a
# configuration-dictionary.
c = Conf()

# how many seconds to wait for data to hold on sync buffer for time-sorting.
c.sync_depth_seconds = 4.

# all paths can be absolute ("/home/user/prog/bin/data"), or relative to the exe dir ("../bin/data")

# data that should be upgraded with the program. voice files, images, fonts..
c.path_data = "../data"
# data that should survive program upgrades.
c.path_database = "../database"

#############################################################################

# an internal conf value. after startup points to the exe or main python
# file absolute directory.
c.py_path = ""

# an internal value and can NOT be changed here. it'll be set to the correct
# (or rather - actual) value after the conf file is loaded.
c.path_log = "../log"

# Relative to current conf file dir. No error if file not found.
# Each next file in the list is used only if the previous was not found.
conf_overrides = ["conf.py", "../../conf/conf.py"]
