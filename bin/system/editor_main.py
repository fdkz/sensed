import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2
llog.info("make sure numpy is installed, or glGenBuffers will complain and crash"
          "")
import math
import os
import random

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *

import window
import camera
import gltext
import floor
import coordinate_system
import vector
import fps_counter


def g_set_opengl_pixel_projection(w_pixels, h_pixels, z_near=None, z_far=None):
    """
    top-left is (0, 0). (top-left tip of the top-left pixel)
    """

    if z_near is None: z_near = 1.
    if z_far  is None: z_far  = 50. * 1000.

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    glOrtho(0., w_pixels, h_pixels, 0., z_near, z_far)


def g_set_perspective_projection(w, h, fov_x = 90., z_near = 1., z_far = 50 * 1000.):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fov_x * float(h) / w, float(w) / h, z_near, z_far)


class Circle:

    def __init__(self, x, y, r, (red, g, b, a)):
        self.x, self.y, self.r = x, y, r
        self.red, self.g, self.b, self.a = red, g, b, a

    def render(self):

        glColor4d(self.red, self.g, self.b, self.a)

        glBegin(GL_TRIANGLE_FAN)
        for a in range(0, 360, 10):
            x, y = self.x + self.r * math.sin(math.radians(a)), self.y + self.r * math.cos(math.radians(a))
            glVertex3f(x, y, 0.)
        glEnd()

        glBegin(GL_LINE_LOOP)
        for a in range(0, 360, 10):
            x, y = self.x + self.r * math.sin(math.radians(a)), self.y + self.r * math.cos(math.radians(a))
            glVertex3f(x, y, 0.)
        glEnd()


class EditorMain:
    def __init__(self, w, h, conf):
        self.conf = conf
        self.w_pixels, self.h_pixels = w, h
        self.window = window.Window((0. ,0.), (w, h))
        self.camera = camera.Camera()
        self.camera_ocs = coordinate_system.CoordinateSystem()
        # look down to the x/z plane from 10 units above.
        self.camera_ocs.pos.set([0, 20., 0])
        self.camera_ocs.a_frame.x_axis.set([ 1.0,  0.0,  0.0])
        self.camera_ocs.a_frame.y_axis.set([ 0.0,  0.0,  1.0])
        self.camera_ocs.a_frame.z_axis.set([ 0.0, -1.0,  0.0])

        # this can also be None, so be sure to check before use
        self.mouse_floor_coord = vector.Vector()

        self.mouse_x = 0
        self.mouse_y = 0

        self.fps_counter = fps_counter.FpsCounter()

        self.circles = []
        self.init_circles()
        self._init_gl()

        glEnableClientState (GL_VERTEX_ARRAY)

        self.floor = floor.Floor()
        #self._set_pixel_projection(w, h)
        self.gltext = gltext.GLText(os.path.join(self.conf.path_data, "font_proggy_opti_small.txt"))
        self.gltext.init()

    @staticmethod
    def _init_gl():
        #print "GL_DEPTH_BITS: ", glGetIntegerv(GL_DEPTH_BITS)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_FOG)
        glDisable(GL_DITHER)
        glDisable(GL_LIGHTING)
        glShadeModel(GL_FLAT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glDisable(GL_LINE_STIPPLE)

    def init_circles(self):
        self.circles.append(Circle(-3, 0, 2, (0.5, 0.5, 0.4, 1.)))
        self.circles.append(Circle(3, 1, 3, (0.5, 0.5, 1., 1.)))

    def tick(self, t, keys):
        """
        @param t: timestamp of the call
        @param keys:
        """
        glViewport(0, 0, self.w_pixels, self.h_pixels)

        glClearColor(0.8,0.8,1.8,1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        #glColor(1,0,0,1)

        self.camera.set_fovx(80.)
        self.camera.update_fovy(float(self.w_pixels) / self.h_pixels)
        self.camera.set_opengl_projection(self.camera.PERSPECTIVE, self.w_pixels, self.h_pixels, .1, 1000.)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glScalef(1.,1.,-1.)

        #camera_ocs = self.camera_ocs.new()
 #       camera_ocs.pos.add( camera_ocs.a_frame.y_axis * 0. )
        #camocs = self.camera.ocs
        ### project the world into camera space
        ##ocs = camera.ocs.proj_in( coordinate_system.CoordinateSystem() )
        ##glMultMatrixf(ocs.get_opengl_matrix2())
        #glMultMatrixf(camocs.a_frame.get_opengl_matrix())
        #glTranslated(-camocs.pos[0], -camocs.pos[1], -camocs.pos[2])
        p = self.camera_ocs.pos
        glMultMatrixf(self.camera_ocs.a_frame.get_opengl_matrix())
        #glMultMatrixf((GLfloat*16)(*camera_ocs.a_frame.get_opengl_matrix()))
        glTranslatef(-p[0], -p[1], -p[2])

        # render world

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)

        self.floor.render()
        for c in self.circles:
            c.render()


        start, direction = self.camera.window_ray(self.camera.PERSPECTIVE, self.w_pixels, self.h_pixels, self.mouse_x, self.mouse_y)
        if start:
            direction = self.camera_ocs.projv_out(direction)
            start += self.camera_ocs.pos
            self.mouse_floor_coord = self.floor.intersection(start, direction)

        # render text and 2D overlay

        self.camera.set_opengl_projection(self.camera.PIXEL, self.w_pixels, self.h_pixels, .1, 1000.)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glScalef(1.,1.,-1.)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)

        #glScale(40., 40., 1.)
        #glTranslate(10., 0., -15.)

        #if keys[SDL_SCANCODE_LEFT]:  p.direction_new -= turn_speed * t
        #if keys[SDL_SCANCODE_RIGHT]: p.direction_new += turn_speed * t
        #if keys[SDL_SCANCODE_UP]:    p.acc = speed * 0.6
        #if keys[SDL_SCANCODE_DOWN]:  p.acc = -speed * 0.6
        #if keys[K_UP]:    p.acc += speed * t
        #if keys[K_DOWN]:  p.acc -= speed * t

        self.fps_counter.tick(t)
        self.render_hud_text()

    def render_hud_text(self):
        y = 5.
        x = self.w_pixels - 6.
        t = self.gltext
        y += t.height
        t.drawtr(" example text 1        ", x, y, bgcolor=(1.0,1.0,1.0,.9), fgcolor=(0.,0.,0.,1.), z=100.); y+=t.height
        t.drawtr(" example text 2: %6.1f " % (55.65), x, y, bgcolor=(.9,.9,.9,.9)); y+=t.height

        if self.mouse_floor_coord:
            mouse_x = self.mouse_floor_coord[0]
            mouse_y = self.mouse_floor_coord[2]
        else:
            mouse_x, mouse_y = 0., 0.
        t.drawtl(" mouse coord: %6.2f %6.2f " % (mouse_x, mouse_y), 5, 5, bgcolor=(1.0,1.0,1.0,.9), fgcolor=(0.,0.,0.,1.), z=100.)

        t.drawbr("fps: %.0f" % (self.fps_counter.fps), self.w_pixels, self.h_pixels,
                 fgcolor = (0., 0., 0., 1.), bgcolor = (0.7, 0.7, 0.7, .9), z = 100.)

    def event(self, event):
        if event.type == SDL_WINDOWEVENT:
            if event.window.event == SDL_WINDOWEVENT_RESIZED:
                llog.info("event window resized to %ix%i", event.window.data1, event.window.data2)
                self.w_pixels = event.window.data1
                self.h_pixels = event.window.data2
        elif event.type == SDL_MOUSEMOTION:
            #llog.info("event mousemotion abs %i %i rel %i %i",
            #           event.motion.x, event.motion.y, event.motion.xrel, event.motion.yrel)
            self.mouse_x = event.motion.x
            self.mouse_y = event.motion.y
        else:
            #llog.info("event! type %s", event.type)
            pass
