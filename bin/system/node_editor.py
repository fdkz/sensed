import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

import math
from math import sin, cos, radians
import os
import random

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *

import coordinate_system
import vector
import vbo


class Node:

    def __init__(self, pos, gltext):
        """pos is a vector.Vector()"""
        self.pos = pos.new()
        self.gltext = gltext
        self.selected = False

        self.node_id = "FACE"

        self._signal_strength_circles_vbo = self._build_signal_strength_circles_vbo()
        self._signal_strength_filled_circles_xz_vbo = self._build_filled_circle_xz_vbo(4., (0.5, 0.5, 0.9, 0.8), (0.5, 0.5, 0.9, 0.))
        self._icon_circle_outer_xy_vbo = self._build_filled_circle_xy_vbo(17, (1., 1., 1., 1.), (1., 1., 1., 1.))
        self._icon_circle_inner_xy_vbo = self._build_filled_circle_xy_vbo(15, (0.8, 0.8, 0.8, 1.0), (0.8, 0.8, 0.8, 1.0))

    def render(self):
        glLineWidth(1.)
        glPushMatrix()
        glTranslatef(*self.pos)
        self._signal_strength_filled_circles_xz_vbo.draw(GL_TRIANGLE_FAN)
        self._signal_strength_circles_vbo.draw(GL_LINES)
        glPopMatrix()

    def _build_signal_strength_circles_vbo(self):
        """Build a vbo of some concnentric circles. meant to be rendered with GL_LINES."""
        v = []
        for i in range(4): # 4 circles
            radius = i + 1
            prevpoint = []
            for a in range(0, 361, 5):
                point = [radius * sin(radians(a)), 0., radius * cos(radians(a)), 0.5, 0.5, 0.5, 0.9*(0.6**i)]
                if prevpoint:
                    v.extend(prevpoint)
                    v.extend(point)
                prevpoint = point
        return vbo.VBOColor(v)

    def _build_filled_circle_xz_vbo(self, radius, centercolor, edgecolor):
        """Build a vbo of a filled circle. meant to be rendered with GL_TRIANGLE_FAN."""
        r,g,b,a = edgecolor
        v = [0., 0., 0.] + list(centercolor)
        for angle in range(0, 361, 5):
            v.extend([radius * sin(radians(angle)), 0., radius * cos(radians(angle)), r,g,b,a])
        return vbo.VBOColor(v)

    def _build_filled_circle_xy_vbo(self, radius, centercolor, edgecolor):
        """Build a vbo for the text background. Used with pixel projection. Meant to be rendered with GL_TRIANGLE_FAN."""
        r,g,b,a = edgecolor
        v = [0., 0., 0.] + list(centercolor)
        for angle in range(0, 361, 5):
            v.extend([radius * sin(radians(angle)), radius * cos(radians(angle)), 0., r,g,b,a])
        return vbo.VBOColor(v)

    def render_overlay(self, screen_pos):
        """Render the iconified representation at these screen-coordinates."""
        glDisable(GL_TEXTURE_2D)

        glPushMatrix()
        glTranslatef(*screen_pos)
        self._icon_circle_outer_xy_vbo.draw(GL_TRIANGLE_FAN)
        self._icon_circle_inner_xy_vbo.draw(GL_TRIANGLE_FAN)
        glPopMatrix()

        glEnable(GL_TEXTURE_2D)
        self.gltext.drawmm( self.node_id, screen_pos[0], screen_pos[1], bgcolor=(1.0,1.0,1.0,0.), fgcolor=(0.,0.,0.,1.), z=screen_pos[2])


class NodeEditor:
    def __init__(self, gltext, conf):
        self.conf = conf
        self.gltext = gltext
        self.nodes = []

        h = 0.1 # 10 cm from the ground
        n = Node( vector.Vector((0., h, 0.)), gltext )
        self.nodes.append(n)
        n = Node( vector.Vector((4., h, 0.)), gltext )
        self.nodes.append(n)
        n = Node( vector.Vector((6., h, -1.)), gltext )
        self.nodes.append(n)
        n = Node( vector.Vector((-2., h, 2.)), gltext )
        self.nodes.append(n)
        n = Node( vector.Vector((-3., h, -2.)), gltext )
        self.nodes.append(n)
        n = Node( vector.Vector((-11., h, 1.)), gltext )
        self.nodes.append(n)

    def tick(self, dt, keys):
        pass

    def render(self):
        for node in self.nodes:
            node.render()

    def render_overlay(self, camera, camera_ocs, projection_mode, w_pixels, h_pixels):
        for node in self.nodes:
            # 1. proj obj to camera_ocs
            # 2. proj coord to screenspace
            v = camera_ocs.projv_in(node.pos)
            screen_pos = camera.screenspace(projection_mode, v, w_pixels, h_pixels)
            node.render_overlay(screen_pos)
