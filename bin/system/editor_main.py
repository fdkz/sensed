import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2
llog.info("make sure numpy is installed, or glGenBuffers will complain and crash"
          "")
import math
import os
import sys
import random

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *

import window
import camera
from modules import gltext
import floor
import coordinate_system
import vector
import fps_counter
import node_editor
import nugui


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
            x, z = self.x + self.r * math.sin(math.radians(a)), self.y + self.r * math.cos(math.radians(a))
            glVertex3f(x, 0., z)
        glEnd()

        #glBegin(GL_LINE_LOOP)
        #for a in range(0, 360, 10):
        #    x, z = self.x + self.r * math.sin(math.radians(a)), self.y + self.r * math.cos(math.radians(a))
        #    glVertex3f(x, 0., z)
        #glEnd()


class EditorMain:
    def __init__(self, w, h, conf):
        self.conf = conf
        self.w_pixels, self.h_pixels = w, h
        self.window = window.Window((0. ,0.), (w, h))
        self.camera = camera.Camera()
        self.camera_ocs = coordinate_system.CoordinateSystem()
        # look down to the x/z plane from 10 units above.
        self.camera_ocs.pos.set([0, 10., 0])
        self.camera_ocs.a_frame.x_axis.set([ 1.0,  0.0,  0.0])
        self.camera_ocs.a_frame.y_axis.set([ 0.0,  0.0,  1.0])
        self.camera_ocs.a_frame.z_axis.set([ 0.0, -1.0,  0.0])
        # initial size of the viewport in opengl units (let's think we use meters in this case)
        self.camera.set_orthox(10)
        self.camera.update_fovy(float(w) / h)

        self.keyb_zoom_speed = 3.
        if sys.platform == "win32":
            self.mouse_zoom_speed = 0.2
        else:
            # for macosx touchpad, use a much smaller zoom speed than on windows.
            self.mouse_zoom_speed = 0.02

        self.mouse_x = 0
        self.mouse_y = 0
        # these are vectors, but also None if no valid vector could be constructed
        self.mouse_floor_coord = None
        self.mouse_lbdown_floor_coord = None
        self.mouse_lbdown_camera_coord = None
        self.mouse_lbdown_window_coord = None
        self.mouse_window_coord = None
        self.mouse_lbdown = False
        self.mouse_dragging = False

        self.fps_counter = fps_counter.FpsCounter()

        self.circles = []
        self.init_circles()
        self._init_gl()

        self.floor = floor.Floor()
        #self._set_pixel_projection(w, h)
        self.gltext = gltext.GLText(os.path.join(self.conf.path_data, "font_proggy_opti_small.txt"))
        self.gltext.init()

        self.nugui = nugui.NuGui(self.gltext)

        self.node_editor = node_editor.NodeEditor(self, self.gltext, conf)

    #@staticmethod
    def _init_gl(self):
        #print "GL_DEPTH_BITS: ", glGetIntegerv(GL_DEPTH_BITS)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_FOG)
        glDisable(GL_DITHER)
        glDisable(GL_LIGHTING)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # for some reason this doesnt work when using multisampling. have to use 4 samples to get a passable result.
        glEnable(GL_LINE_SMOOTH)
        glDisable(GL_LINE_STIPPLE)

    def init_circles(self):
        #self.circles.append(Circle(-3, 0, 2, (0.5, 0.5, 0.4, 1.)))
        #self.circles.append(Circle(3, 1, 3, (0.5, 0.5, 1., 1.)))
        pass

    def tick(self, dt, keys):
        """
        @param t: timestamp of the call
        @param keys:
        """
        self.handle_controls(dt, keys)
        self.node_editor.tick(dt, keys)
        self.render(dt)
        self.nugui.tick()

    def render(self, dt):
        self.fps_counter.tick(dt)

        glShadeModel(GL_SMOOTH) # go to hell opengl. it's not enough if this line is the _init_gl method. why is it not enough?

        glViewport(0, 0, self.w_pixels, self.h_pixels)

        glClearColor(0.8,0.8,0.8,1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        #glColor(1,0,0,1)

        # if using perspective projection:
        #self.camera.set_fovx(80.)
        #self.camera.update_fovy(float(self.w_pixels) / self.h_pixels)
        #self.camera.set_opengl_projection(self.camera.PERSPECTIVE, self.w_pixels, self.h_pixels, .1, 1000.)
        # else if using orthogonal projection
        self.camera.set_opengl_projection(self.camera.ORTHOGONAL, self.w_pixels, self.h_pixels, .1, 1000.)
        self.camera.update_fovy(float(self.w_pixels) / self.h_pixels)

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

        self.node_editor.render()

        # render text and 2D overlay

        self.camera.set_opengl_projection(self.camera.PIXEL, self.w_pixels, self.h_pixels, .1, 1000.)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        #glTranslatef(0.375, 0.375, 0.0)
        glScalef(1.,1.,-1.)
        glDisable(GL_DEPTH_TEST)

        self.node_editor.render_overlay(self.camera, self.camera_ocs, self.camera.ORTHOGONAL, self.w_pixels, self.h_pixels)

        #glScale(40., 40., 1.)
        #glTranslate(10., 0., -15.)

        #if keys[SDL_SCANCODE_LEFT]:  p.direction_new -= turn_speed * t
        #if keys[SDL_SCANCODE_RIGHT]: p.direction_new += turn_speed * t
        #if keys[SDL_SCANCODE_UP]:    p.acc = speed * 0.6
        #if keys[SDL_SCANCODE_DOWN]:  p.acc = -speed * 0.6
        #if keys[K_UP]:    p.acc += speed * t
        #if keys[K_DOWN]:  p.acc -= speed * t

        self.render_hud_text()
        self.render_handle_gui()
        self.nugui.finish_frame()

    def render_handle_gui(self):
        glEnable(GL_TEXTURE_2D)
        glLineWidth(1.)
        # self.nugui.begin_listbox(1, 100, 100, w = 200.)
        # if self.nugui.listbox_item(2, "itemnum1 here"):     llog.info("item1")
        # if self.nugui.listbox_item(3, "itemnum2 here too"): llog.info("item2")
        # if self.nugui.listbox_item(4, "itemnum3 bla"):      llog.info("item3")
        # if self.nugui.listbox_item(5, "itemnum4 1"):        llog.info("item4")
        # if self.nugui.listbox_item(6, "itemnum5 test"):     llog.info("item5")
        # self.nugui.end_listbox()
        if self.nugui.button(7, 5, 30, "save user/sensormap.txt"):
            llog.info("saving sensormap.txt")
            self.node_editor.save_graph_file(os.path.join(self.conf.py_path, "sensormap.txt"))

        changed, text = self.nugui.textentry(8, 100, 100, 60, "FF33")
        if changed:
            llog.info("text changed to %s", text)
        #if self.nugui.button(8, 210, 250, "hover me too"): llog.info("clicked2")

    def render_hud_text(self):
        glEnable(GL_TEXTURE_2D)
        y = 5.
        x = self.w_pixels - 6.
        t = self.gltext
        y += t.height
        t.drawtr(" example text 1         ", x, y, bgcolor=(1.0,1.0,1.0,.9), fgcolor=(0.,0.,0.,1.), z=100.); y+=t.height
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
            return

        if event.type == SDL_MOUSEMOTION:
            #llog.info("event mousemotion abs %i %i rel %i %i",
            #           event.motion.x, event.motion.y, event.motion.xrel, event.motion.yrel)
            self.mouse_x = float(event.motion.x)
            self.mouse_y = float(event.motion.y)
            self.nugui.set_mouse_pos(self.mouse_x, self.mouse_y)
            self.mouse_window_coord = (float(event.motion.x), float(event.motion.y))
            # works only if orthogonal projection is used
            if self.mouse_lbdown and self.mouse_lbdown_floor_coord and not self.node_editor.mouse_dragging:
                d = vector.Vector((-(self.mouse_x - self.mouse_lbdown_window_coord[0]) / self.w_pixels * self.camera.orthox,
                                   0.,
                                   (self.mouse_y - self.mouse_lbdown_window_coord[1]) / self.h_pixels * self.camera.orthoy))
                self.camera_ocs.pos.set( self.mouse_lbdown_camera_coord + d )
            self.mouse_floor_coord = self.get_pixel_floor_coord(self.mouse_x, self.mouse_y)

        elif event.type == SDL_MOUSEWHEEL:
            if event.wheel.y:
                self._zoom_view(self.mouse_x, self.mouse_y, self.mouse_zoom_speed * event.wheel.y)

        elif event.type == SDL_MOUSEBUTTONDOWN:
            if event.button.button == SDL_BUTTON_LEFT:
                self.nugui.set_mouse_button(True)
                self.mouse_lbdown = True
                # find object under cursor. if no object, drag the world
                self.mouse_dragging = True
                self.object_under_cursor = None
                self.mouse_floor_coord = self.get_pixel_floor_coord(event.button.x, event.button.y)
                if self.mouse_floor_coord:
                    self.mouse_lbdown_floor_coord = self.mouse_floor_coord.new()
                    self.mouse_lbdown_camera_coord = self.camera_ocs.pos.new()
                    self.mouse_lbdown_window_coord = (float(event.button.x), float(event.button.y))

        elif event.type == SDL_MOUSEBUTTONUP:
            if event.button.button == SDL_BUTTON_LEFT:
                self.nugui.set_mouse_button(False)
                self.mouse_lbdown = False
                self.mouse_dragging = False
                #self.mouse_lbdown_floor_coord = None
                #self.mouse_lbdown_camera_coord = None
                #self.mouse_lbdown_window_coord = None

        elif event.type == SDL_KEYDOWN:
            self.nugui.event(event)
        else:
            #llog.info("event! type %s", event.type)
            pass

        self.node_editor.event(event)

    def _zoom_view(self, anchor_pixel_x, anchor_pixel_y, zoom_percent):
        # Zoom the camera view, but hold the point under mouse cursor steady. AND stop all movement when
        # zoom limit is reached. Works only if using orthogonal projection.
        p = self.camera_ocs.pos
        if zoom_percent > 0:
            MIN_FOV = 1.
            orthox = max(self.camera.orthox * (1. / (1. + zoom_percent)), MIN_FOV)
            zoom_amount = self.camera.orthox / orthox - 1
            p[0] += (anchor_pixel_x / self.w_pixels - 0.5) * self.camera.orthox * (1. - 1. / (1. + zoom_amount))
            p[2] -= (anchor_pixel_y / self.h_pixels - 0.5) * self.camera.orthoy * (1. - 1. / (1. + zoom_amount))
            self.camera.set_orthox(orthox)

        else:
            MAX_FOV = 100.
            orthox = min(self.camera.orthox * (1. - zoom_percent), MAX_FOV)
            zoom_amount = (orthox - self.camera.orthox) / self.camera.orthox
            p[0] -= (anchor_pixel_x / self.w_pixels - 0.5) * self.camera.orthox * zoom_amount
            p[2] += (anchor_pixel_y / self.h_pixels - 0.5) * self.camera.orthoy * zoom_amount
            self.camera.set_orthox(orthox)

        self.camera.update_fovy(float(self.w_pixels) / self.h_pixels)

    def handle_controls(self, dt, keys):
        """Continuous (as opposed to event-based) UI control. Move the camera (or other objects?) according to
        what keys are being held down."""

        #speed    = 5.
        #rotspeed = 120.

        #cp = self.selected_obj.ocs.pos
        #ca = self.selected_obj.ocs.a_frame

        # if keys[SDL_SCANCODE_A]: cp.add(-ca.x_axis * speed * dt)
        # if keys[SDL_SCANCODE_D]: cp.add( ca.x_axis * speed * dt)
        # if keys[SDL_SCANCODE_E]: cp[1] += speed * dt
        # if keys[SDL_SCANCODE_Q]: cp[1] -= speed * dt
        # if keys[SDL_SCANCODE_W]: cp.add( ca.z_axis * speed * dt)
        # if keys[SDL_SCANCODE_S]: cp.add(-ca.z_axis * speed * dt)

        # up = vector.Vector((0., 1., 0.))

        # if keys[SDL_SCANCODE_LEFT]:      ca.rotate(up,  rotspeed * dt)
        # if keys[SDL_SCANCODE_RIGHT]:     ca.rotate(up, -rotspeed * dt)
        # if keys[SDL_SCANCODE_UP]:        ca.rotate(ca.x_axis, -rotspeed * dt)
        # if keys[SDL_SCANCODE_DOWN]:      ca.rotate(ca.x_axis,  rotspeed * dt)
        # # if keys[k.MOTION_NEXT_PAGE]: ca.rotate(ca.z_axis,  rotspeed * dt)
        # # if keys[k.MOTION_DELETE]:    ca.rotate(ca.z_axis, -rotspeed * dt)


        # units per second. by using the view-area size, we'll always move by a percentage of the window.
        speed = self.camera.orthox
        p = self.camera_ocs.pos
        c = False

        if keys[SDL_SCANCODE_LEFT]:  p[0] -= speed * dt; c = True
        if keys[SDL_SCANCODE_RIGHT]: p[0] += speed * dt; c = True
        if keys[SDL_SCANCODE_UP]:    p[2] += speed * dt; c = True
        if keys[SDL_SCANCODE_DOWN]:  p[2] -= speed * dt; c = True

        if keys[SDL_SCANCODE_PAGEDOWN]:
            self._zoom_view(self.w_pixels / 2., self.h_pixels / 2., -self.keyb_zoom_speed * dt)
            c = True
        if keys[SDL_SCANCODE_PAGEUP]:
            self._zoom_view(self.w_pixels / 2., self.h_pixels / 2., self.keyb_zoom_speed * dt)
            c = True

        if c:
            self.mouse_floor_coord = self.get_pixel_floor_coord(self.mouse_x, self.mouse_y)

    def get_pixel_floor_coord(self, x, y):
        #start, direction = self.camera.window_ray(self.camera.PERSPECTIVE, self.w_pixels, self.h_pixels, x, y)
        #if start:
        #    direction = self.camera_ocs.projv_out(direction)
        #    start += self.camera_ocs.pos
        #    return self.floor.intersection(start, direction)
        start, direction = self.camera.window_ray(self.camera.ORTHOGONAL, self.w_pixels, self.h_pixels, x, y)
        if start:
#            llog.info("%s %s %s", start, direction, self.camera_ocs.pos)
            start = self.camera_ocs.projv_out(start)
#            llog.info("%s", start)
            direction = self.camera_ocs.a_frame.projv_out(direction)
            return self.floor.intersection(start, direction)
        else:
            return None
