import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

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

logging.getLogger('OpenGL.formathandler').addFilter(PyOpenGLLogNoiseFilter())

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
        proc = Main(conf)
        proc.run()

    except KeyboardInterrupt:
        # sleep a bit to let other threads/processes finish logging.
        # don't know if it's necessary in case of multithreading.
        time.sleep(0.2)
        # do not log detailed info about ctrl-c if not debugging
        llog.info("")
        llog.info("*" * 17)
        llog.info("KeyboardInterrupt")
        llog.info("*" * 17)
        #if conf.debug:
        #    logging.exception("")

    finally:
        if proc:
            proc.close()


import ctypes
from PIL import Image

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *

import main_window


class Main:
    def __init__(self, conf):
        self.conf = conf
        self.screen = None
        self.context = None
        self.keys = None
        self.main_window = None

        # make so that the first screenshot is saved after 2 minutes, but all later with AUTOSCREENSHOT_PERIOD.
        self.AUTOSCREENSHOT_PERIOD = 5.*60
        self.t_last_autoscreenshot = time.time() - self.AUTOSCREENSHOT_PERIOD + 2.*60

    def close(self):
        if self.main_window:
            self.main_window.close()

    def run(self):
        self._init()

        do_quit = False
        prev_frame_time = time.time()

        event = SDL_Event()
        while not do_quit:

            t = time.time()
            time_elapsed = t - prev_frame_time

            while SDL_PollEvent(ctypes.byref(event)) != 0:

                if event.type == SDL_KEYDOWN:
                    if event.key.keysym.scancode == SDL_SCANCODE_ESCAPE:
                        do_quit = True

                if event.type == SDL_QUIT:
                    do_quit = True

                if self.main_window.event(event):
                    do_quit = True

            self.main_window.tick(time_elapsed, self.keys)


            if t > self.t_last_autoscreenshot + self.AUTOSCREENSHOT_PERIOD:
                self.t_last_autoscreenshot = t
                self.save_screenshot("autoscreenshot_")


            SDL_GL_SwapWindow(self.screen)

            prev_frame_time = t

        SDL_GL_DeleteContext(self.context)
        SDL_DestroyWindow(self.screen)
        SDL_Quit()

    def _init(self):
        if SDL_Init(SDL_INIT_VIDEO) != 0:
            print SDL_GetError()
            raise RuntimeError

        #SDL_GL_SetAttribute(SDL_GL_RED_SIZE, 8);
        #SDL_GL_SetAttribute(SDL_GL_GREEN_SIZE, 8);
        #SDL_GL_SetAttribute(SDL_GL_BLUE_SIZE, 8);
        #SDL_GL_SetAttribute(SDL_GL_ALPHA_SIZE, 8);
        #SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 32);
        #SDL_GL_SetAttribute(SDL_GL_ACCELERATED_VISUAL, 1)
        SDL_GL_SetAttribute(SDL_GL_MULTISAMPLEBUFFERS, 1);
        SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES, 4);

        w, h = 800, 600
        self.screen = SDL_CreateWindow(b"sensed", SDL_WINDOWPOS_UNDEFINED,
                                       SDL_WINDOWPOS_UNDEFINED, w, h,
                                       SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE)

        #print SDL_GetWindowSize(g_screen,1,2)
        #print dir(g_screen)

        if not self.screen:
            llog.error(SDL_GetError())
            raise RuntimeError

        self.context = SDL_GL_CreateContext(self.screen)

        #glEnable(GL_MULTISAMPLE) # hm. multisampling seems to even work without this.

        if SDL_GL_SetSwapInterval(-1):
            print SDL_GetError()
            if SDL_GL_SetSwapInterval(1):
                llog.info("SDL_GL_SetSwapInterval: %s", SDL_GetError())
                llog.info("vsync failed completely. will munch cpu for lunch.")

        self.keys = SDL_GetKeyboardState(None)

        self.main_window = main_window.MainWindow(w, h, self.conf)

    def save_screenshot(self, filename_prefix="screenshot_"):
        """saves screenshots/filename_prefix20090404_120211_utc.png"""
        utc = time.gmtime(time.time())
        filename = filename_prefix + "%04i%02i%02i_%02i%02i%02i_utc.png" % \
                   (utc.tm_year, utc.tm_mon, utc.tm_mday,                  \
                    utc.tm_hour, utc.tm_min, utc.tm_sec)
        llog.info("saving screenshot '%s'", filename)

        w, h = ctypes.c_int(), ctypes.c_int()
        SDL_GetWindowSize(self.screen, ctypes.byref(w), ctypes.byref(h))
        w, h = w.value, h.value
        pixels = (ctypes.c_ubyte * (3 * w * h))()

        glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, pixels);
        i = Image.frombuffer('RGB', (w, h), pixels, 'raw', 'RGB', 0, -1)
        i.save("../screenshots/" + filename)

