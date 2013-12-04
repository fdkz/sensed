import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

#import math
#import random
import time
import ctypes
#import traceback
#import sys

#from OpenGL.GL import *
#from OpenGL.GLU import *

from sdl2 import *

import editor_main


class SubMain:
    def __init__(self, conf):
        self.conf = conf
        self.screen = None
        self.context = None
        self.keys = None
        self.editor_main = None

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
            SDL_GL_SwapWindow(self.screen)

            prev_frame_time = t

        SDL_GL_DeleteContext(self.context)
        SDL_DestroyWindow(self.screen)
        SDL_Quit()

    def _init(self):
        if SDL_Init(SDL_INIT_VIDEO) != 0:
            print SDL_GetError()
            raise RuntimeError

        #SDL_GL_SetAttribute(SDL_GL_MULTISAMPLEBUFFERS, 1);
        #SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES, 4);
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

        if SDL_GL_SetSwapInterval(-1):
            print SDL_GetError()
            if SDL_GL_SetSwapInterval(1):
                llog.info("SDL_GL_SetSwapInterval: %s", SDL_GetError())
                llog.info("vsync failed completely. will munch cpu for lunch.")

        self.keys = SDL_GetKeyboardState(None)

        #FULLSCREEN, HWSURFACE
        #g_screen = pygame.display.set_mode((640, 480), DOUBLEBUF | OPENGL)
        #pygame.display.set_caption('crawlys')
        #pygame.mouse.set_visible(1)

        #random.seed(1)

        self.editor_main = editor_main.EditorMain(w, h, self.conf)
