import logging
log = logging.getLogger(__name__)

import sys

# install a logging filter that removes some of these messages when using logging and "from OpenGL import GL":
#     OpenGL.acceleratesupport No OpenGL_accelerate module loaded: No module named OpenGL_accelerate
#     OpenGL.formathandler Unable to load registered array format handler numeric:
#         ImportError: No Numeric module present: No module named Numeric

class PyOpenGLLogNoiseFilter(logging.Filter):
    def filter(self, record):
        try:
            if sys.platform == "win32":
                if record.msg == "Unable to load registered array format handler %s:\n%s" and record.args[0] == "numeric" or \
                        record.msg == "Unable to load registered array format handler %s:\n%s" and record.args[0] == "vbo" or \
                        record.msg == "Unable to load registered array format handler %s:\n%s" and record.args[0] == "vbooffset" or \
                        record.msg == "Unable to load registered array format handler %s:\n%s" and record.args[0] == "numpy":
                    #record.msg = record.msg[:-4]
                    #record.args = record.args[:-1]
                    return 0 # log the message. 0 for no, nonzero for yes.
            else:
                if record.msg == "Unable to load registered array format handler %s:\n%s" and record.args[0] == "numeric":
                    return 0
            return 1
        except:
            log.exception("")
            return 1

#logging.getLogger('OpenGL.formathandler').addFilter(PyOpenGLLogNoiseFilter())

# ---------------------------------------------------------------------------

import os
import time
import random

import conf_reader


def main(py_path, log_path):
    """
    py_path : full absolute path of the main py file. or of the exe.
    """

    conf = conf_reader.read_conf(os.path.join(py_path, "conf/conf_base.py"))
    conf.py_path = py_path

    # convert paths to absolute paths. no harm done if they already were absolute.
    conf.path_log = os.path.join(py_path, log_path)
    conf.path_data = os.path.join(py_path, conf.path_data)
    conf.path_database = os.path.join(py_path, conf.path_database)

    proc = None
    random.seed()

    try:
        import sub_main
        proc = sub_main.SubMain(conf)

        proc.run()

    except KeyboardInterrupt:
        # sleep a bit to let other threads/processes finish logging.
        # don't know if it's necessary in case of multithreading.
        time.sleep(0.2)
        # do not log detailed info about ctrl-c if not debugging
        log.info("")
        log.info("*" * 17)
        log.info("KeyboardInterrupt")
        log.info("*" * 17)
        #if conf.debug:
        #    logging.exception("")

    finally:
        if proc:
            proc.close()
