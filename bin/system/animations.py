import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

from math import sin, cos, radians, atan2

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

import vbo
import draw


class ColorAnimation:
    """ with every tick interpolates cur_color between start_color and end_color """
    def __init__(self, max_age, start_color=(0.,0.,0.,1.), end_color=(1.,1.,1.,1.)):
        self.start_color = start_color
        self.end_color = end_color
        self.cur_color = start_color
        self.age = 0.
        self.max_age = max_age
        self.dead = False

    def tick(self, dt):
        if not self.dead:
            self.age += dt
            if self.age > self.max_age:
                self.age = self.max_age
                self.dead = True
            c1 = self.start_color
            c2 = self.end_color
            d = self.age / self.max_age
            self.cur_color = (
                c1[0] + d*(c2[0]-c1[0]),
                c1[1] + d*(c2[1]-c1[1]),
                c1[2] + d*(c2[2]-c1[2]),
                c1[3] + d*(c2[3]-c1[3]))

    def render(self):
        pass

    def render_ortho(self):
        pass


class BeaconAnimation:
    """ a blue (push) or red (pull) filled circle around node during beacon send """
    _filled_circles_xz_vbo = None
    _pull_beacon_center_color   = (1.0, 0.271, 0.0, 0.3)
    _pull_beacon_edge_color     = (1.0, 0.271, 1.0, 0.0)
    _normal_beacon_center_color = (0.5, 0.5, 0.9, 0.3)
    _normal_beacon_edge_color   = (0.5, 0.5, 0.9, 0.0)

    CTP_OPT_PULL = 0x80

    def __init__(self, options):
        if options & self.CTP_OPT_PULL:
            self.centercolor = self._pull_beacon_center_color
            self.edgecolor = self._pull_beacon_edge_color
        else:
            self.centercolor = self._normal_beacon_center_color
            self.edgecolor = self._normal_beacon_edge_color

        if not self._filled_circles_xz_vbo:
            self._filled_circles_xz_vbo = self._build_filled_circle_xz_vbo(
                1.5, self.centercolor, self.edgecolor)

        self.age = 0.
        self.max_age = 2.
        self.dead = False

    def tick(self, dt):
        if not self.dead:
            self.age += dt
            if self.age > self.max_age:
                self.dead = True

    def render(self):
        r, g, b, a = self.centercolor
        glColor4f(r, g, b, 1 - self.age / self.max_age * 0.6)
        self._filled_circles_xz_vbo.draw(GL_TRIANGLE_FAN)

    def render_ortho(self):
        pass

    def _build_filled_circle_xz_vbo(self, radius, centercolor, edgecolor):
        """Build a vbo of a filled circle. meant to be rendered with GL_TRIANGLE_FAN."""
        v = [0., 0., 0.]
        for angle in range(0, 361, 5):
            v.extend([radius * sin(radians(angle)), 0., radius * cos(radians(angle))])
        return vbo.VBO(v)


class PacketAnimation:
    """ a little triangle that flows from node to node. one hop. """
    def __init__(self, src_pos, dst_pos, initial_color=(1.0,0.3,0.3,1.)):
        self.src_pos = src_pos
        self.dst_pos = dst_pos

        self.age = 0.
        self.max_age = .5
        self.dead = False
        self.initial_color = initial_color

    def tick(self, dt):
        if not self.dead:
            self.age += dt
            if self.age > self.max_age:
                self.dead = True

    def render(self):
        r, g, b, a = self.initial_color
        d = self.age / self.max_age
        glColor4f(r, g, b, 1 - d * 0.7)
        glLineWidth(2.)

        p1 = self.src_pos
        p2 = self.dst_pos
        a = atan2(p2[0] - p1[0], p2[2] - p1[2])
        r = 0.15
        aa = radians(140.) # angle of attack

        glPushMatrix()
        x, y, z = p1[0] + (p2[0] - p1[0]) * d, p1[1] + (p2[1] - p1[1]) * d, p1[2] + (p2[2] - p1[2]) * d
        glTranslatef(x, y, z)
        glBegin(GL_TRIANGLES)

        x, y, z = sin(a) * r, 0., cos(a) * r
        glVertex3f(x, y, z)
        x, z = sin(a - aa) * r, cos(a - aa) * r
        glVertex3f(x, y, z)
        x, z = sin(a + aa) * r, cos(a + aa) * r
        glVertex3f(x, y, z)

        glEnd()
        glPopMatrix()

    def render_ortho(self):
        pass


class SendRetryAnimation:
    """ a vertical dissolving line besides the node that gets updated with retry count after every sendDone. """
    def __init__(self, max_age, start_color=(0.,0.,0.,1.), end_color=(1.,1.,1.,1.), retry_count=1):
        self.retry_count = retry_count
        self.start_color = start_color
        self.end_color = end_color
        self.cur_color = start_color
        self.age = 0.
        self.max_age = max_age
        self.x = 0.
        self.y = 0.
        self.dead = False

    def set_pos(self, x, y, z):
        self.x = x
        self.y = y

    def tick(self, dt):
        if not self.dead:
            self.age += dt
            if self.age > self.max_age:
                self.age = self.max_age
                self.dead = True
            c1 = self.start_color
            c2 = self.end_color
            d = self.age / self.max_age
            self.cur_color = (
                c1[0] + d*(c2[0]-c1[0]),
                c1[1] + d*(c2[1]-c1[1]),
                c1[2] + d*(c2[2]-c1[2]),
                c1[3] + d*(c2[3]-c1[3]))

    def render(self):
        pass

    def render_ortho(self):
        w = 2.
        h = float(self.retry_count+1.)
        draw.filled_rect(round(self.x-w/2.), round(self.y)-h, w, h, self.cur_color)
