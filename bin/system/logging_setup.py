import os
import sys
import time
import math
import logging
import logging.handlers


_console_logger = None


def start_logging_system(log_folder, log_filename="log.txt"):
    """
    """
    # patch Handler.handleError to reraise exceptions. don't know what magic
    # happens in the default handler, but the combination of asyncore and
    # logging module loses my traceback info! a nightmare to debug..
    def logging_handleError(self, record):
        if logging.raiseExceptions: raise
    logging.Handler.handleError = logging_handleError
    logformat = MiscFormatter()

    log_globalfile = logging.handlers.TimedRotatingFileHandler(os.path.join(log_folder, log_filename), "midnight", utc=True) # backupCount=7
    log_globalfile.setFormatter(logformat)

    # conf the root logger to output everything both to console
    rootlogger = logging.getLogger()
    rootlogger.addHandler(log_globalfile)

    global _console_logger
    _console_logger = logging.StreamHandler()
    _console_logger.setFormatter(logformat)
    rootlogger.addHandler(_console_logger)

    rootlogger.setLevel(logging.NOTSET)
    # This line has to exist, because sometimes we could get the following error after redirecting all of stdout
    # to the logging module and the error would never appear:
    #   The process cannot access the file because it is being used by another process
    rootlogger.info("(logger output test)")

    # route all raw print statements through the logging system. add an ERROR prefix
    # to encourage use of the logging module.
    sys.stdout = StdLogger()
    sys.stderr = sys.stdout


def remove_console_logger():
    rootlogger = logging.getLogger()
    # _console_logger.disabled = True also works?
    rootlogger.removeHandler(_console_logger)

#
# ---------------------------------------------------------------------------
#


# create a new Formatter class for the logging module.
class MiscFormatter(logging.Formatter):
    """
    purpose:

      instead of this:

        18-01-2010 18:40:42,235 INFO startup ok
        18-01-2010 18:40:42,235 DEBUG count: 4 init: True
        18-01-2010 18:40:42,235 WARNING object not found!

      we'll get this:

        18-01-2010 16:40:42.235Z startup ok
        18-01-2010 16:40:42.235Z DEBUG count: 4 init: True
        18-01-2010 16:40:42.235Z WARNING object not found!
    """
    def __init__(self):
        logging.Formatter.__init__(self)

    def formatTime(self, record, datefmt=None):
        """ remove the comma and return '18-01-2010 18:40:42.235Z' utc time """
        if datefmt:
            return time.strftime(datefmt)
        else:
            msecs = min(999, record.msecs) # for some reason, record.msecs can be 1000, and that screws with the %03 formatting.
            return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(record.created)) + ".%03.fZ" % msecs

    def format(self, record):
        # skip the INFO text on every line, but show DEBUG and ERROR and others.
        if record.levelno == logging.INFO:
            self._fmt = "%(asctime)s %(name)s %(message)s"
        else:
            self._fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"
        return logging.Formatter.format(self, record)


# last line of unsolicited stdout defence.
# catch stdout and redirect to log.
class StdLogger:
    def __init__(self):
        self.isatty = sys.__stdout__.isatty()
    def write(self, txt):
        logging.info("STDOUT " + txt.rstrip())
    def flush(self):
        pass

