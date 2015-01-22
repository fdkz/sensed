import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

from math import sin, cos, radians, atan2
import os
import json
import errno
import math
import random

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *

import coordinate_system
import vector
import vbo

from nanomsg import Socket, SUB, SUB_SUBSCRIBE, DONTWAIT, NanoMsgAPIError


class ColorAnimation:
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
            self.cur_color = (c1[0] + d * (c2[0] - c1[0]),  c1[1] + d * (c2[1] - c1[1]), c1[2] + d * (c2[2] - c1[2]), c1[3] + d * (c2[3] - c1[3]))

    def render(self):
        pass


class BeaconAnimation:
    _filled_circles_xz_vbo = None
    _pull_beacon_center_color =     (1.0, 0.271, 0.0, 0.3)
    _pull_beacon_edge_color =       (1.0, 0.271, 1.0, 0.0)
    _normal_beacon_center_color =   (0.5, 0.5, 0.9, 0.3)
    _normal_beacon_edge_color =     (0.5, 0.5, 0.9, 0.0)

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

    def _build_filled_circle_xz_vbo(self, radius, centercolor, edgecolor):
        """Build a vbo of a filled circle. meant to be rendered with GL_TRIANGLE_FAN."""
        v = [0., 0., 0.]
        for angle in range(0, 361, 5):
            v.extend([radius * sin(radians(angle)), 0., radius * cos(radians(angle))])
        return vbo.VBO(v)


class PacketAnimation:
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
            self._animations.append( PacketAnimation(src_node.pos, dst_node.pos, packet_color) )

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

    def render(self):
        if self._usage:
            glLineWidth(self._usage)
            r, g, b = 0.4, 0.4, 0.4
            if self._link_busy:
                r += r * (self._busy_age / self._busy_max_age)
                g += g * (self._busy_age / self._busy_max_age)
            if self._just_poked:
                r, g, b = 0., 0., 0.
            glColor4f(r, g, b, 1.)

            glBegin(GL_LINES)
            glVertex3f(*self.node1.pos)
            glVertex3f(*self.node2.pos)
            glEnd()

        for anim in self._animations:
            anim.render()


class Node:
    def __init__(self, pos, node_id, color, gltext):
        """pos is a vector.Vector()"""
        self.pos = pos.new()
        self.gltext = gltext
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

        self.radius_pixels = 17.

        self._signal_strength_circles_vbo = self._build_signal_strength_circles_vbo()
        self._signal_strength_filled_circles_xz_vbo = self._build_filled_circle_xz_vbo(
            4., (0.5, 0.5, 0.9, 0.8), (0.5, 0.5, 0.9, 0.))

        self._icon_circle_outer_xy_vbo = self._build_filled_circle_xy_vbo(self.radius_pixels)
        self._icon_circle_inner_xy_vbo = self._build_filled_circle_xy_vbo(self.radius_pixels - 2.)
        self._icon_circle_node_colortag_xy_vbo = self._build_filled_half_circle_xy_vbo(self.radius_pixels - 2., -40., 40., 20)

        self._animations = []

    def poke_radio(self):
        self.radio_active_anim = ColorAnimation(max_age=0.2, start_color=self.radio_active_color, end_color=self.radio_active_color_end)
        self.append_animation( self.radio_active_anim )

    def append_animation(self, anim_obj):
        self._animations.append(anim_obj)

    def tick(self, dt):
        for anim in self._animations:
            anim.tick(dt)
        self._animations = [anim for anim in self._animations if not anim.dead]

    def render(self):
        glLineWidth(1.)
        glPushMatrix()
        glTranslatef(*self.pos)
        for anim in self._animations:
            anim.render()
        #self._signal_strength_filled_circles_xz_vbo.draw(GL_TRIANGLE_FAN)
        #self._signal_strength_circles_vbo.draw(GL_LINES)
        glPopMatrix()

    def render_overlay(self):
        """Render the iconified representation at self.screen_pos screen-coordinates."""
        s = self.screen_pos

        if 1: # use restless beacon animation
            for anim in self._animations:
                if isinstance(anim, BeaconAnimation):
                    s = s.new()
                    d = 3.
                    s.add(vector.Vector((random.random() * d - d*0.5, random.random() * d - d*0.5, 0.)))
                    break

        glDisable(GL_TEXTURE_2D)

        glPushMatrix()
        glTranslatef(*s)

        lighter = (0.1, 0.1, 0.1, 1.0)
        inner_color = (0.8, 0.8, 0.8, 1.0)

        if self.attrs.get("radiopowerstate"):
            inner_color = self.radio_active_color

        #inner_color = self.node_color

        if self.selected:
            outer_color = (1., .4, .4, 1.)
        #    inner_color = tuple(sum(x) for x in zip(self.node_color, lighter))
        elif self.mouse_hover:
            outer_color = (1., 1., 1., 1.)
        #    inner_color = tuple(sum(x) for x in zip(self.node_color, lighter))
        else:
            outer_color = (1., 1., 1., 1.)

        glColor4f(*outer_color)
        self._icon_circle_outer_xy_vbo.draw(GL_TRIANGLE_FAN)
        glColor4f(*inner_color)
        self._icon_circle_inner_xy_vbo.draw(GL_TRIANGLE_FAN)

        if self.radio_active_anim and not self.radio_active_anim.dead:
            glColor4f(*self.radio_active_anim.cur_color)
            self._icon_circle_inner_xy_vbo.draw(GL_TRIANGLE_FAN)

        glColor4f(*self.node_color)
        self._icon_circle_node_colortag_xy_vbo.draw(GL_TRIANGLE_FAN)

        glPopMatrix()

        glEnable(GL_TEXTURE_2D)
        self.gltext.drawmm(self.node_idstr, s[0], s[1], bgcolor=(1.0,1.0,1.0,0.), fgcolor=(0.,0.,0.,1.), z=s[2])
        self.gltext.drawmm(self.node_name, s[0], s[1] + self.gltext.height, bgcolor=(1.0,1.0,1.0,0.), fgcolor=(0.,0.,0.,1.), z=s[2])

        h = self.gltext.height * 2 + 2

        #for key, val in self.attrs.items():
            #if key.startswith("etx_data"):
        if "etx_table" in self.attrs:
            for etx in self.attrs["etx_table"]:
                self.gltext.drawmm(etx, s[0], s[1] + h, bgcolor=(0,0,0,.3), fgcolor=(1.3,1.3,1.3,1.), z=s[2])
                h += self.gltext.height

        if "ctpf_buf_used" in self.attrs and "ctpf_buf_capacity" in self.attrs:
            self._render_progress_bar_mm(s[0], s[1] - self.radius_pixels - 3., s[2], 24, "testpro", self.attrs["ctpf_buf_capacity"], self.attrs["ctpf_buf_used"])

    def _get_node_color(self, awake):
        if awake:
            return 0.529, 0.808, 0.980, 1.0
        else:
            return self.node_color

    def _render_progress_bar_mm(self, x, y, z, w, name, capacity, used):
        """ w - width of the progress bar without the frame """
        glDisable(GL_TEXTURE_2D)
        # background

        xx = round(x - w/2. - 1.)
        yy = round(y - 1.)
        w2 = float(w) * used / capacity if capacity else 0

        glColor4f(0.4, 0.4, 0.4, 1.0)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(xx, yy, z)
        glVertex3f(xx + w + 2., yy, z)
        glVertex3f(xx + w + 2., yy + 3., z)
        glVertex3f(xx, yy + 3., z)
        glEnd()

        # the thin progress line
        if used == capacity:
            glColor4f(1., 0.3, 0.3, 1.0)
        else:
            glColor4f(1., 1., 1., 1.0)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(xx + 1., yy + 1., z)
        glVertex3f(xx + 1. + w2, yy + 1., z)
        glVertex3f(xx + 1. + w2, yy + 2., z)
        glVertex3f(xx + 1., yy + 2., z)
        glEnd()

    def intersects(self, sx, sy):
        p = self.screen_pos
        return (sx - p[0])**2 + (sy - p[1])**2 < self.radius_pixels**2

    def _build_signal_strength_circles_vbo(self):
        """Build a vbo of some concnentric circles. meant to be rendered with GL_LINES."""
        v = []
        for i in range(4):  # 4 circles
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
        r, g, b, a = edgecolor
        v = [0., 0., 0.] + list(centercolor)
        for angle in range(0, 361, 5):
            v.extend([radius * sin(radians(angle)), 0., radius * cos(radians(angle)), r, g, b, a])
        return vbo.VBOColor(v)

    def _build_filled_circle_xy_vbo(self, radius):
        """Build a vbo for the text background. Used with pixel projection. Meant to be rendered with GL_TRIANGLE_FAN."""
        v = [0., 0., 0.]
        for angle in range(0, 361, 5):
            v.extend([radius * sin(radians(angle)), radius * cos(radians(angle)), 0.])
        return vbo.VBO(v)

    def _build_filled_half_circle_xy_vbo(self, radius, start_angle, end_angle, num_steps):
        """Build a vbo for the text background. Used with pixel projection. Meant to be rendered with GL_TRIANGLE_FAN."""
        v = [0., 0., 0.]
        angle = start_angle
        start_angle = radians(start_angle)
        end_angle = radians(end_angle)
        for i in range(num_steps):
            angle = start_angle + float(end_angle - start_angle) / (num_steps - 1) * i
            v.extend([radius * sin(angle), -radius * cos(angle), 0.])
        return vbo.VBO(v)


class NodeEditor:
    def __init__(self, mouse, gltext, conf):
        self.conf = conf
        self.mouse = mouse  # TODO: use a special mouse object instead of the editor_main object directly.
        self.gltext = gltext
        self.nodes = []
        self.links = []
        self.nodes_dict = {} # integers. 16-bit node addresses
        self.links_dict = {} # a pair of node objects. (node1, node2) is equivalent to (node2, node1), but only one pair exists in links_dict

        self.mouse_hover = False
        self.mouse_dragging = False
        self.selected = None
        self.selected_pos_ofs = vector.Vector()

        # saved when closing the windows. loaded at startup.
        self.session_node_positions = {} # {"0x31FE": (x,y), ..}
        self.session_filename = os.path.normpath(os.path.join(self.conf.path_database, "session_conf.txt"))
        self.load_session()

        # h = 0.  # 10 cm from the ground. nnope. for now, h has to be 0.
        # r = 1.
        # for i in range(10):
        #     a = float(i) / (r + 10) * 15.
        #     x, y = r * math.sin(a), r * math.cos(a)
        #     r += 0.5
        #     n = Node( vector.Vector((x, h, y)), i + 1, self._get_node_color(i+1), gltext )
        #     self.append_node(n)

        # n = Node( vector.Vector((0., h, 0.)), 1, gltext ); self.append_node(n)
        # n = Node( vector.Vector((1., h, 0.)), 2, gltext ); self.append_node(n)
        # n = Node( vector.Vector((2., h, -1.)), 3, gltext ); self.append_node(n)
        # n = Node( vector.Vector((-2., h, 2.)), 4, gltext ); self.append_node(n)
        # n = Node( vector.Vector((-1., h, 2.)), 5, gltext ); self.append_node(n)
        # n = Node( vector.Vector((-2., h, 1.)), 6, gltext ); self.append_node(n)
        # n = Node( vector.Vector((-1., h, 0.)), 7, gltext ); self.append_node(n)
        # n = Node( vector.Vector((-1.5, h, -1.)), 8, gltext ); self.append_node(n)
        # n = Node( vector.Vector((0.5, h, 1.)), 9, gltext ); self.append_node(n)
        # n = Node( vector.Vector((-1.4, h, 0.5)), 10, gltext ); self.append_node(n)
        #n.attrs["etx"] = 44

        self.s1 = Socket(SUB)
        self.s1.connect('tcp://127.0.0.1:55555')
        self.s1.set_string_option(SUB, SUB_SUBSCRIBE, '')

    def _get_link(self, src_node, dst_node):
        """ create a new link object if not found from self.links.
        fill self.links and self.links_dict (the dict both with src_node_id and dst_node_id) """
        if (src_node, dst_node) in self.links_dict:
            return self.links_dict[(src_node, dst_node)]
        elif (dst_node, src_node) in self.links_dict:
            return self.links_dict[(dst_node, src_node)]
        else:
            link = Link(src_node, dst_node)
            self.links.append(link)
            self.links_dict[(src_node, dst_node)] = link
            return link

    def _get_node_color(self, origin_node_id):
        origin_node_id %= 11
        if origin_node_id == 9:
            return 0.753, 0.753, 0.753, 1.
        if origin_node_id == 8:
            return 0.824, 0.412, 0.118, 1.
        if origin_node_id == 7:
            return 1.000, 0.000, 1.000, 1.
        if origin_node_id == 6:
            return 1.000, 1.000, 0.000, 1.
        if origin_node_id == 5:
            return 1.000, 0.627, 0.478, 1.
        if origin_node_id == 4:
            return 0.498, 1.000, 0.000, 1.
        if origin_node_id == 3:
            return 0.000, 1.000, 1.000, 1.
        if origin_node_id == 2:
            return 1.000, 0.922, 0.804, 1.
        if origin_node_id == 1:
            return 0.871, 0.722, 0.529, 1.
        if origin_node_id == 0:
            return 0.000, 0.749, 1.000, 1.
        if origin_node_id == 0:
            return 0.500, 0.549, 1.000, 1.

        return 0.8, 0.8, 0.8, 1.0

    def append_node(self, node):
        assert node.node_id not in self.nodes_dict
        self.nodes.append(node)
        self.nodes_dict[node.node_id] = node

    def get_create_node(self, node_id):
        if node_id in self.nodes_dict:
            return self.nodes_dict[node_id]
        else:
            if node_id not in self.session_node_positions:
                h = 0.
                r = 1. + 0.5 * len(self.nodes)
                a = float(len(self.nodes)) / (r + 10) * 15.
                x, y = r * math.sin(a), r * math.cos(a)
                pos = (x, h, y)
            else:
                pos = self.session_node_positions[node_id]

            node = Node( vector.Vector(pos), node_id, self._get_node_color(node_id), self.gltext )
            self.append_node(node)
            return node

    def get_create_named_node(self, node_id_name):
        """ Createa node if it doesn't exist yet. Also set its name if given.
        node_id_name can be "12AB_somename" or "12AB" """
        n = node_id_name.split("_", 1)
        node = self.get_create_node(int(n[0], 16))
        if len(n) == 2:
            node.node_name = n[1]
        return node

    def tick(self, dt, keys):
        for link in self.links:
            link.tick(dt)
        for node in self.nodes:
            node.tick(dt)

        try:
            while 1:
                msg = self.s1.recv(flags=DONTWAIT)
                msg = msg.strip()
                if msg:
                    d = msg.split()
                    if d[0] == "data" or d[0] == "event":

                        # ['data', 'etx', '0001000000000200', 'node', '0A', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']
                        # ['data', 'etx', '0001000000000200', 'node', '0A_sniffy', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']
                        node_id_name = d[4]
                        node = self.get_create_named_node(node_id_name)

                        if d[0] == "data":

                            if d[1] == "etx":
                                # ['data', 'etx', '0001000000000200', 'node', '0A', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']

                                # filter out empty rows
                                if int(d[8]) != 0xFFFF:
                                    if d[10].startswith("NO_ROUTE"):
                                        d[10] = "NO"
                                        d[12] = "NO"

                                    if int(d[6]) == 0:
                                        node.attrs["etx_table"] = []

                                    node.attrs["etx_table"].append("%04X e%s r%s" % (int(d[8]), d[10], d[12]))
                            elif d[1] == "ctpf_buf_size":
                                used = int(d[6])
                                capacity = int(d[8])
                                node.attrs["ctpf_buf_used"] = used
                                node.attrs["ctpf_buf_capacity"] = capacity

                        elif d[0] == "event":

                            if d[1] == "radiopowerstate":
                                # ['event', 'radiopowerstate', '0052451410156550', 'node', '04', 'state', '1']
                                radiopowerstate = int(d[6], 16)
                                node.attrs["radiopowerstate"] = radiopowerstate
                                if radiopowerstate:
                                    node.poke_radio()

                            elif d[1] == "event beacon":
                                # ['event', 'beacon', '0052451410156550', 'node', '04', 'options', '0x00', 'parent', '0x0003', 'etx', '30']
                                options = int(d[6], 16)
                                parent = int(d[8], 16)
                                node.append_animation(BeaconAnimation(options))
                                node.attrs["parent"] = parent

                            elif d[1] == "event packet_to_activemessage" and 0:
                                # ['event', 'packet', '0000372279297175', 'node', '04', 'dest', '0x1234', 'amid', '0x71']
                                src_node_id = node.node_id
                                dst_node_id = int(d[6], 16)
                                amid = int(d[8], 16)
                                if dst_node_id != 0xFFFF: # filter out broadcasts
                                    src_node = node
                                    dst_node = self.get_create_node(dst_node_id)
                                    link = self._get_link(src_node, dst_node)
                                    link.poke(src_node)

                            elif d[1] == "event send_ctp_packet":
                                # event send_ctp_packet 0:0:38.100017602 node 03 dest 0x0004 origin 0x0009 sequence 21 type 0x71 thl 5
                                # event send_ctp_packet 0:0:10.574584572 node 04 dest 0x0003 origin 0x0005 sequence 4 amid 0x98 thl 1
                                src_node_id = node.node_id
                                dst_node_id = int(d[6], 16)
                                origin_node_id = int(d[8], 16)
                                sequence_num = int(d[10])
                                amid = int(d[12], 16)
                                thl = int(d[14])

                                src_node = node
                                dst_node = self.get_create_node(dst_node_id)
                                link = self._get_link(src_node, dst_node)
                                link.poke(src_node, packet_color=self._get_node_color(origin_node_id))

                            elif d[1] == "event packet_to_model_busy":
                                src_node_id = node.node_id
                                dst_node_id = int(d[6], 16)
                                if dst_node_id != 0xFFFF: # filter out broadcasts
                                    src_node = node
                                    dst_node = self.get_create_node(dst_node_id)
                                    link = self._get_link(src_node, dst_node)
                                    link.poke_busy(src_node)
                        else:
                            llog.info("unknown msg %s", repr(msg))
                else:
                    break
        except NanoMsgAPIError as e:
            if e.errno != errno.EAGAIN:
                raise

    def _render_links_to_parents(self):
        glLineWidth(1.)
        glColor4f(0.4, 0.4, 0.4, 1.)

        # 1111_11_1______
        glLineStipple(2, 1+2+4+8+32+64+256)
        glEnable(GL_LINE_STIPPLE)
        glLineWidth(2.)
        for node in self.nodes:
            parent_id = node.attrs.get("parent")
            if parent_id and parent_id != 0xFFFF:
                parent_node = self.get_create_node(parent_id)

                glBegin(GL_LINES)
                glVertex3f(*parent_node.pos)
                glVertex3f(*node.pos)
                glEnd()

        glDisable(GL_LINE_STIPPLE)

    def render(self):
        for link in self.links:
            link.render()
        self._render_links_to_parents()
        for node in self.nodes:
            node.render()

    def render_overlay(self, camera, camera_ocs, projection_mode, w_pixels, h_pixels):
        # calculate node screen positions
        for node in self.nodes:
            # 1. proj obj to camera_ocs
            # 2. proj coord to screenspace
            v = camera_ocs.projv_in(node.pos)
            node.screen_pos.set(camera.screenspace(projection_mode, v, w_pixels, h_pixels))

        # draw lines from the selected node to every other node
        if 0 and self.selected:
            glLineWidth(1.)
            for node in self.nodes:
                if node != self.selected:
                    glColor4f(0.3,0.3,0.3,.9)
                    glBegin(GL_LINES)
                    glVertex3f(*self.selected.screen_pos)
                    glVertex3f(*node.screen_pos)
                    glEnd()

                    glEnable(GL_TEXTURE_2D)
                    s = (self.selected.screen_pos + node.screen_pos) / 2.
                    link_quality = self._calc_link_quality(node, self.selected)
                    self.gltext.drawmm("%.2f" % link_quality, s[0], s[1], bgcolor=(0.2,0.2,0.2,0.7), fgcolor=(1.,1.,1.,1.), z=s[2])
                    glDisable(GL_TEXTURE_2D)

        # draw the nodes themselves
        for node in self.nodes:
            node.render_overlay()

    #def recalculate_screen_pos(self, camera, camera_ocs, projection_mode, w_pixels, h_pixels):
    #    for node in self.nodes:
    #        # 1. proj obj to camera_ocs
    #        # 2. proj coord to screenspace
    #        v = camera_ocs.projv_in(node.pos)
    #        node.screen_pos.set(camera.screenspace(projection_mode, v, w_pixels, h_pixels))

    def intersects(self, sx, sy):
        for node in self.nodes:
            if node.intersects(float(sx), float(sy)):
                return node
        return None

    def save_graph_file(self, filename="sensormap.txt"):
        d = {"format": "sensed node graph", "format_version": "2013-12-19", "nodes": [], "edges": []}

        for node in self.nodes:
            p = node.pos
            n = {"id": node.node_id, "pos": [p[0], p[1], p[2]]}
            d["nodes"].append(n)

        edge_count = 0
        for node1 in self.nodes:
            for node2 in self.nodes:
                if node1 != node2:
                    edge_count += 1
                    e = {"id": edge_count, "source": node1.node_id, "dest": node2.node_id, "link_quality": self._calc_link_quality(node1, node2)}
                    d["edges"].append(e)

        txt = json.dumps(d, indent=4, sort_keys=True)

        with open(filename, "wb") as f:
            f.write(txt)

    def _calc_link_quality(self, node1, node2):
        dist = node1.pos.dist(node2.pos)
        return dist

    def load_session(self):
        """ load node positions. write to self.session_node_positions """
        try:
            with open(self.session_filename, "rb") as f:
                session_conf = json.load(f)
        except IOError:
            #log.warning("'%s' file not found" % path)
            session_conf = None

        # extract node positions from the conf dict
        if session_conf and "node_positions" in session_conf:
            c = session_conf.get("node_positions")
            # convert entries {"0x51AB": (1,2,3), ..} to format {20907, (1,2,3)}
            self.session_node_positions = {int(k, 16): v for k, v in c.items()}

    def save_session(self):
        """ save node positions. mix together prev session positions and new positions. """
        # convert entries {20907: (1,2,3), ..} to format {"0x51AB", (1,2,3)}
        node_positions_session = {"0x%04X" % k: v for k, v in self.session_node_positions.items()}
        node_positions_used = {"0x%04X" % n.node_id: (n.pos[0], n.pos[1], n.pos[2]) for n in self.nodes}
        node_positions_session.update(node_positions_used)

        session_conf = {"node_positions": node_positions_session}
        txt = json.dumps(session_conf, indent=4, sort_keys=True)

        with open(self.session_filename, "wb") as f:
            f.write(txt)

    def close(self):
        self.save_session()

    def event(self, event):
        if event.type == SDL_MOUSEMOTION:
            for node in self.nodes:
                node.mouse_hover = False
            node = self.intersects(event.motion.x, event.motion.y)
            if node:
                self.mouse_hover = True
                node.mouse_hover = True
            else:
                self.mouse_hover = False

            if self.selected and self.mouse_dragging and self.mouse.mouse_lbdown_floor_coord:
                self.selected.pos.set(self.mouse.mouse_floor_coord + self.selected_pos_ofs)

        elif event.type == SDL_MOUSEBUTTONDOWN:
            if event.button.button == SDL_BUTTON_LEFT:
                node = self.intersects(event.button.x, event.button.y)
                if node:
                    for n in self.nodes:
                        n.selected = False
                    self.selected = node
                    node.selected = True
                    self.selected_pos_ofs.set(node.pos - self.mouse.mouse_lbdown_floor_coord)
                    self.mouse_dragging = True
                else:
                    self.mouse_dragging = False

        elif event.type == SDL_MOUSEBUTTONUP:
            if event.button.button == SDL_BUTTON_LEFT:
                #if self.mouse_dragging:
                if self.mouse.mouse_lbdown_window_coord == self.mouse.mouse_window_coord:
                    node = self.intersects(event.button.x, event.button.y)
                    if not node:
                        self.selected = None
                        for n in self.nodes:
                            n.selected = False
                self.mouse_dragging = False
