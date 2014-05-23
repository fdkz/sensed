import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

from math import sin, cos, radians
import json
import errno
import math

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

    def __init__(self):
        if not self._filled_circles_xz_vbo:
            self._filled_circles_xz_vbo = self._build_filled_circle_xz_vbo(
                1.5, (0.5, 0.5, 0.9, 0.3), (0.5, 0.5, 0.9, 0.))
        self.age = 0.
        self.max_age = 2.
        self.dead = False

    def tick(self, dt):
        if not self.dead:
            self.age += dt
            if self.age > self.max_age:
                self.dead = True

    def render(self):
        glColor4f(.5, .5, .9, 1. - self.age / self.max_age * 0.6)
        self._filled_circles_xz_vbo.draw(GL_TRIANGLE_FAN)

    def _build_filled_circle_xz_vbo(self, radius, centercolor, edgecolor):
        """Build a vbo of a filled circle. meant to be rendered with GL_TRIANGLE_FAN."""
        v = [0., 0., 0.]
        for angle in range(0, 361, 5):
            v.extend([radius * sin(radians(angle)), 0., radius * cos(radians(angle))])
        return vbo.VBO(v)


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

    def poke(self, src_node=None):
        """ tell the link that a packet just went through. used to calc the rendered link line usage/width """
        self._usage += 1
        self._usage = min(10., self._usage)
        self._just_poked = True

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


class Node:

    def __init__(self, pos, node_id, gltext):
        """pos is a vector.Vector()"""
        self.pos = pos.new()
        self.gltext = gltext
        # screen_pos is set from outside, usually before calling render_overlay. It's a book-keeping value for
        # the Node owner/renderer/editor.
        self.screen_pos = vector.Vector()
        self.mouse_hover = False
        self.selected = False
        self.inner_color = self._get_node_color(awake=False)
        #self.radioactive_color = ()
        self.radioactive_anim = None

        self.node_id = node_id # "FACE"
        self.node_name = str(node_id)

        self.attrs = {}

        self.radius_pixels = 17.

        self._signal_strength_circles_vbo = self._build_signal_strength_circles_vbo()
        self._signal_strength_filled_circles_xz_vbo = self._build_filled_circle_xz_vbo(
            4., (0.5, 0.5, 0.9, 0.8), (0.5, 0.5, 0.9, 0.))

        self._icon_circle_outer_xy_vbo = self._build_filled_circle_xy_vbo(self.radius_pixels)
        self._icon_circle_inner_xy_vbo = self._build_filled_circle_xy_vbo(self.radius_pixels - 2.)

        self._animations = []

    def poke_radio(self):
        self.radioactive_anim = ColorAnimation(max_age=0.2, start_color=(0.529, 0.808, 0.980, 1.0), end_color=(0.529, 0.808, 0.980, 0.))
        self.append_animation( self.radioactive_anim )

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
        glDisable(GL_TEXTURE_2D)

        glPushMatrix()
        glTranslatef(*s)

        if "radiopowerstate" in self.attrs:
            self.inner_color = self._get_node_color(awake=self.attrs["radiopowerstate"])
        lighter = (0.1, 0.1, 0.1, 1.0)

        if self.selected:
            outer_color = (1., .4, .4, 1.)
            self.inner_color = (sum(x) for x in zip(self.inner_color, lighter))
        elif self.mouse_hover:
            outer_color = (1., 1., 1., 1.)
            self.inner_color = (sum(x) for x in zip(self.inner_color, lighter))
        else:
            outer_color = (1., 1., 1., 1.)

        glColor4f(*outer_color)
        self._icon_circle_outer_xy_vbo.draw(GL_TRIANGLE_FAN)
        glColor4f(*self.inner_color)
        self._icon_circle_inner_xy_vbo.draw(GL_TRIANGLE_FAN)

        if self.radioactive_anim and not self.radioactive_anim.dead:
            glColor4f(*self.radioactive_anim.cur_color)
            self._icon_circle_inner_xy_vbo.draw(GL_TRIANGLE_FAN)

        glPopMatrix()

        glEnable(GL_TEXTURE_2D)
        self.gltext.drawmm(self.node_name, s[0], s[1], bgcolor=(1.0,1.0,1.0,0.), fgcolor=(0.,0.,0.,1.), z=s[2])

        h = self.gltext.height * 2 + 2

        for key, val in self.attrs.items():
            if key.startswith("etx_data"):
                self.gltext.drawmm("%s %s" % (key[9:], val), s[0], s[1] + h, bgcolor=(0,0,0,.3), fgcolor=(1.3,1.3,1.3,1.), z=s[2])
                h += self.gltext.height

        if "ctpf_buf_used" in self.attrs and "ctpf_buf_capacity" in self.attrs:
            self._render_progress_bar_mm(s[0], s[1] - self.radius_pixels - 3., s[2], 24, "testpro", self.attrs["ctpf_buf_capacity"], self.attrs["ctpf_buf_used"])

    def _get_node_color(self, awake):
        if awake:
            return 0.529, 0.808, 0.980, 1.0
        else:
            return 0.8, 0.8, 0.8, 1.0

    def _render_progress_bar_mm(self, x, y, z, w, name, capacity, used):
        """ w - width of the progress bar without the frame """
        glDisable(GL_TEXTURE_2D)
        # background

        xx = round(x - w/2. - 1.)
        yy = round(y - 1.)
        w2 = float(w) * used / capacity

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

        h = 0.  # 10 cm from the ground. nnope. for now, h has to be 0.
        # make a spiral of nodes
        r = 1.
        for i in range(10):
            a = float(i) / (r + 10) * 15.
            x, y = r * math.sin(a), r * math.cos(a)
            r += 0.5
            n = Node( vector.Vector((x, h, y)), i + 1, gltext )
            self.append_node(n)

        # n = Node( vector.Vector((0., h, 0.)), 1, gltext ); self.append_node(n)
        # n = Node( vector.Vector((1., h, 0.)), 2, gltext ); self.append_node(n)

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

    def append_node(self, node):
        assert node.node_id not in self.nodes_dict
        self.nodes.append(node)
        self.nodes_dict[node.node_id] = node

    def tick(self, dt, keys):
        for link in self.links:
            link.tick(dt)
        for node in self.nodes:
            node.tick(dt)

        try:
            while 1:
                d = self.s1.recv(flags=DONTWAIT)
                if d:
                    if d.startswith("data etx"):
                        # ['data', 'etx', '0001000000000200', 'node', '0A', 'parent', '8', 'etx', '10', 'retx', '74']
                        d = d.split()
                        llog.info(d)
                        node_id = int(d[4], 16)

                        # filter out empty rows
                        if int(d[6]) != 0xFFFF:
                            if d[8].startswith("NO_ROUTE"):
                                d[8] = "NO"
                                d[10] = "NO"
                            etx_attr = "etx_data %d" % int(d[6])
                            self.nodes_dict[node_id].attrs[etx_attr] = "e%s r%s" % (d[8], d[10])

                    elif d.startswith("event radiopowerstate"):
                        # ['event', 'radiopowerstate', '0052451410156550', 'node', '04', 'state', '1']
                        d = d.split()
                        llog.info(d)
                        node_id = int(d[4], 16)
                        radiopowerstate = int(d[6], 16)
                        self.nodes_dict[node_id].attrs["radiopowerstate"] = radiopowerstate
                        if radiopowerstate:
                            self.nodes_dict[node_id].poke_radio()
                    elif d.startswith("event beacon"):
                        # ['event', 'beacon', '0052451410156550', 'node', '04', 'options', '0x00', 'parent', '0x0003', 'etx', '30']
                        d = d.split()
                        llog.info(d)
                        node_id = int(d[4], 16)
                        parent = int(d[8], 16)
                        self.nodes_dict[node_id].append_animation(BeaconAnimation())
                        self.nodes_dict[node_id].attrs["parent"] = parent
                    elif d.startswith("event packet_to_activemessage"):
                        # ['event', 'packet', '0000372279297175', 'node', '04', 'dest', '0x1234', 'amid', '0x71']
                        d = d.split()
                        llog.info(d)
                        src_node_id = int(d[4], 16)
                        dst_node_id = int(d[6], 16)
                        amid = int(d[8], 16)
                        if dst_node_id != 0xFFFF: # filter out broadcasts
                            src_node = self.nodes_dict[src_node_id]
                            dst_node = self.nodes_dict[dst_node_id]
                            link = self._get_link(src_node, dst_node)
                            link.poke(src_node)
                    elif d.startswith("event packet_to_model_busy"):
                        d = d.split()
                        llog.info(d)
                        src_node_id = int(d[4], 16)
                        dst_node_id = int(d[6], 16)
                        if dst_node_id != 0xFFFF: # filter out broadcasts
                            src_node = self.nodes_dict[src_node_id]
                            dst_node = self.nodes_dict[dst_node_id]
                            link = self._get_link(src_node, dst_node)
                            link.poke_busy(src_node)
                    elif d.startswith("data ctpf_buf_size"):
                        d = d.split()
                        llog.info(d)
                        node_id = int(d[4], 16)
                        used = int(d[6])
                        capacity = int(d[8])
                        self.nodes_dict[node_id].attrs["ctpf_buf_used"] = used
                        self.nodes_dict[node_id].attrs["ctpf_buf_capacity"] = capacity
                    else:
                        llog.info(d)
                else:
                    break
        except NanoMsgAPIError as e:
            if e.errno != errno.EAGAIN:
                raise

    def _render_links_to_parents(self):
        glLineWidth(1.)
        glColor4f(0.4, 0.4, 0.4, 1.)
        # make this pattern: "1111_11_1______"
        glLineStipple(2, 1+2+4+8+32+64+256)
        glEnable(GL_LINE_STIPPLE)
        glLineWidth(2.)
        for node in self.nodes:
            parent_id = node.attrs.get("parent")
            if parent_id and parent_id != 0xFFFF:
                parent_node = self.nodes_dict[parent_id]

                glBegin(GL_LINES)
                glVertex3f(*parent_node.pos)
                glVertex3f(*node.pos)
                glEnd()

        glDisable(GL_LINE_STIPPLE)

    def render(self):
        self._render_links_to_parents()
        for link in self.links:
            link.render()
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
