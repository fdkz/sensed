"""
In this file are objects that know how to serialise themselves and also represent the full persistent state of the world.
In other worlds - when taking snapshot of the world, only these objects will be saved. No animations (packets, beacons)
will be saved because those are too short-lived.
"""

import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

import vbo
import vector
import animations


class Link:
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2
        self._usage = 0.
        self._just_poked = False

        self._link_busy = False
        self._busy_max_age = 0.2
        self._busy_age = 0.
        #self._reduction_v = 0.1

        self._animations = []

    def poke(self, src_node=None, packet_color=None):
        """ tell the link that a packet just went through. used to calc the rendered link line usage/width """
        self._usage += 1
        self._usage = min(10., self._usage)
        self._just_poked = True
        if not packet_color:
            packet_color = (1.0, 0.3, 0.3, 1.)
        if src_node:
            dst_node = self.node1 if src_node == self.node2 else self.node2
            self._animations.append( animations.PacketAnimation(src_node.pos, dst_node.pos, packet_color) )

    def poke_busy(self, src_node=None):
        self._link_busy = True
        self._busy_age = 0.

    def tick(self, dt):
        self._usage -= 5. * dt
        self._usage = max(0., self._usage)
        if self._link_busy:
            self._busy_age += dt
            if self._busy_age > self._busy_max_age:
                self._link_busy = False
        self._just_poked = False

        for anim in self._animations:
            anim.tick(dt)
        self._animations = [anim for anim in self._animations if not anim.dead]


class Node:
    def __init__(self, pos, node_id, color):
        """pos is a vector.Vector()"""
        self.pos = pos.new()
        # screen_pos is set from outside, usually before calling render_overlay. It's a book-keeping value for
        # the Node owner/renderer/editor.
        self.screen_pos = vector.Vector() # visible screen pos. may be different from wanted_screen_pos
        #self.wanted_screen_pos = vector.Vector() # future.
        self.mouse_hover = False
        self.selected = False

        self.node_color = color # the base color
        #self.inner_color = self._get_node_color(awake=False) # current color

        self.radio_active_color = (0.529, 0.808, 0.980, 1.0)
        self.radio_active_color_end = (0.529, 0.808, 0.980, 0.0)
        self.radio_active_anim = None

        self.node_id = node_id # 0xFACE
        self.node_idstr = "%04X" % node_id
        self.node_name = ""

        self.attrs = {}

        # TODO: remember to change this also in NodeRenderer object
        self.radius_pixels = 17.

        self._animations = []

    def poke_radio(self):
        self.radio_active_anim = animations.ColorAnimation(max_age=0.2, start_color=self.radio_active_color, end_color=self.radio_active_color_end)
        self.append_animation( self.radio_active_anim )

    def append_animation(self, anim_obj):
        self._animations.append(anim_obj)

    def tick(self, dt):
        for anim in self._animations:
            anim.tick(dt)
        self._animations = [anim for anim in self._animations if not anim.dead]

    def intersects(self, sx, sy):
        p = self.screen_pos
        return (sx - p[0])**2 + (sy - p[1])**2 < self.radius_pixels**2
