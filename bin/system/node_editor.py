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


class Node:

    def __init__(self, pos, gltext):
        """pos is a vector.Vector()"""
        self.pos = pos.new()
        self.gltext = gltext
        #self.red, self.g, self.b, self.a = red, g, b, a
        self.selected = False

        self.node_id = "FACE"

    def render(self):

        centercolor = (0.5, 0.5, 0.9, 0.6)
        edgecolor   = (0.5, 0.5, 0.9, 0.)
        self._filled_circle_xz(self.pos, 4., centercolor, edgecolor)
        glLineWidth(1.)
        for i in range(4):
            self._circle_xz(self.pos, i+1, (0.5, 0.5, 0.5, 0.9*(0.7**i)))

    def render_overlay(self, screen_pos):
        """Render the iconified representation at these screen-coordinates."""
        glDisable(GL_TEXTURE_2D)
        centercolor = (0.8, 0.8, 0.8, 1.0)
        edgecolor   = (1., 1., 1., 1.)
        radius_pixels = 17.
        self._filled_circle_xy(screen_pos, radius_pixels, centercolor, centercolor)
        glLineWidth(2.)
        self._circle_xy(screen_pos, radius_pixels, edgecolor)
        glEnable(GL_TEXTURE_2D)
        self.gltext.drawmm( self.node_id, screen_pos[0], screen_pos[1], bgcolor=(1.0,1.0,1.0,0.), fgcolor=(0.,0.,0.,1.), z=screen_pos[2])

    def _filled_circle_xz(self, pos, radius, centercolor, edgecolor):
        #glShadeModel(GL_SMOOTH)
        glBegin(GL_TRIANGLE_FAN)
        glColor4d(*centercolor)
        glVertex3f(*pos)
        glColor4d(*edgecolor)
        for a in range(0, 360, 5):
            glVertex3f(pos[0] + radius * sin(radians(a)), pos[1], pos[2] + radius * cos(radians(a)))
        glVertex3f(pos[0], pos[1], pos[2] + radius)
        glEnd()

    def _circle_xz(self, pos, radius, color):
        glColor4d(*color)
        glBegin(GL_LINE_LOOP)
        for a in range(0, 360, 5):
            glVertex3f(pos[0] + radius * sin(radians(a)), pos[1], pos[2] + radius * cos(radians(a)))
        glEnd()

    def _filled_circle_xy(self, pos, radius, centercolor, edgecolor):
        glBegin(GL_TRIANGLE_FAN)
        glColor4d(*centercolor)
        glVertex3f(*pos)
        glColor4d(*edgecolor)
        for a in range(0, 360, 5):
            glVertex3f(pos[0] + radius * sin(radians(a)), pos[1] + radius * cos(radians(a)), pos[2])
        glVertex3f(pos[0], pos[1] + radius, pos[2])
        glEnd()

    def _circle_xy(self, pos, radius, color):
        glColor4d(*color)
        glBegin(GL_LINE_LOOP)
        for a in range(0, 360, 5):
            glVertex3f(pos[0] + radius * sin(radians(a)), pos[1] + radius * cos(radians(a)), pos[2])
        glEnd()


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
        n = Node( vector.Vector((-4., h, 1.)), gltext )
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
