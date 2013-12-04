# this file is in public domain

import os
import sys
import logging
log = logging.getLogger(__name__)


def read_conf(conf_base_filename="conf_base.py"):
    """
    Recursively read configuration files, return the object c from the conf file.

    conf_base_filename HAS to end with ".py"

    example conf files:

      program/conf/conf_base.py (imported with "import" (TODO: with __import__). file is not user-changeable)

        class Conf: pass
        c = Conf()
        c.language = "en"
        c.ui_color = (255, 255, 255, 128)

        # Relative to current conf file. No error if file not found.
        # Each next file is used only if the previous was not found.
        conf_overrides = ["conf.py", "../../conf/conf.py"]

      program/conf/conf.py (imported with "execfile")

        c.language = "en"
        c.ui_color = (0, 0, 0, 128)

    TODO: update the doc. don't know if the new solution with __import__ works with py2exe.

    uses import instead of execfile for conf_base.py because if not:
      * py2exe does not find conf_base.py
      * conf_base.py is user-changeable under py2exe (bad for conf_base. conf overrides are for that)
      TODO: conf_base.py remains unaccessible under py2exe even if __init__.py is in the same dir?

    usage:

      import conf_reader
      g_conf = conf_reader.read_conf("/home/user/program/conf_base.py")
      print g_conf.language, g_conf.ui_color
      >> en (0, 0, 0, 128)
    """
    assert conf_base_filename.endswith(".py")
    exe_path = "."

    def read_conf_override(conf, filename):
        """
        save to/update the given conf object, read from file. return namespace of the given file.
        """
        log.info("loading additional conf:  '%s'" % filename)
        d = {"c": conf}
        try:
            execfile(os.path.join(exe_path, filename), d)
        except IOError:
            log.info("(conf file not found)")
            d = {}
        return d

    log.info("importing root conf file: '%s'", conf_base_filename)
    # TODO: does this method of importing work with app2exe and similar systems?
    sys.path.append(os.path.dirname(conf_base_filename))
    conf_importname = os.path.basename(conf_base_filename)[:-3]
    conf_base = __import__(conf_importname)
    sys.modules[conf_importname] = conf_base
    del sys.path[-1]
    confobj = conf_base.c

    #import conf.conf_base
    #confobj = conf.conf_base.c

    # replace __setattr__ of the conf value holder with a method that warns if an
    # item that is not in conf_base.py is initialized after loading conf_base.py.
    def _setattr(self, item, value):
        if item not in self.__dict__:
            log.warning("unknown configuration setting that is not in root conf %s: '%s'", conf_base_filename, item)
        else:
            self.__dict__[item] = value
    confobj.__class__.__setattr__ = _setattr

    current_conf_dirname = os.path.dirname(conf_base_filename)
    confdict = conf_base.__dict__
    prev_conf_file = ""

    while "conf_overrides" in confdict:
        for conf_file in confdict["conf_overrides"]:
            conf_file = os.path.normpath(os.path.join(current_conf_dirname, conf_file))
            # sanity check for depth-1 infinite loop
            if prev_conf_file:
                assert prev_conf_file != conf_file, \
                       "conf file points to itself as its override. infinite loop: '%s'" % \
                       prev_conf_file
            prev_conf_file = conf_file
            confdict = read_conf_override(confobj, conf_file)
            # conf file reading succeeded. now skip the rest of the list and
            # get ready to dive into next level of conf-files.
            if confdict:
                break
        current_conf_dirname = os.path.dirname(conf_file)

    return confobj


def test():
    print "conf_reader: starting tests"
    logging.basicConfig(level=logging.NOTSET)
    import sys
    g_conf = read_conf(sys.path[0]+"/conf_base.py")
    print g_conf.language, g_conf.ui_color

if __name__ == "__main__":
    test()
