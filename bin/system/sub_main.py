import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

import time
import ctypes


from PIL import Image

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *

import editor_main


class SubMain:
    def __init__(self, conf):
        self.conf = conf
        self.screen = None
        self.context = None
        self.keys = None
        self.editor_main = None

        # make so that the first screenshot is saved after 2 minutes, but all later with AUTOSCREENSHOT_PERIOD.
        self.AUTOSCREENSHOT_PERIOD = 5.*60
        self.t_last_autoscreenshot = time.time() - self.AUTOSCREENSHOT_PERIOD + 2.*60

    def close(self):
        pass

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

                if self.editor_main.event(event):
                    do_quit = True

            self.editor_main.tick(time_elapsed, self.keys)


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

        self.editor_main = editor_main.EditorMain(w, h, self.conf)

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

