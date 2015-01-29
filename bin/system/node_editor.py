import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

#from math import sin, cos, radians, atan2
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

import world
import renderers
import animations

from nanomsg import Socket, SUB, SUB_SUBSCRIBE, DONTWAIT, NanoMsgAPIError


class NodeEditor:
    def __init__(self, mouse, gltext, conf):
        self.conf = conf
        self.mouse = mouse  # TODO: use a special mouse object instead of the editor_main object directly.
        self.gltext = gltext
        self.world = world.World(self.conf)

        self.mouse_hover = False
        self.mouse_dragging = False
        self.selected = None
        self.selected_pos_ofs = vector.Vector()

        self.node_renderer = renderers.NodeRenderer(self.gltext)
        self.link_renderer = renderers.LinkRenderer()

        # saved when closing the windows. loaded at startup.
        self.session_filename = os.path.normpath(os.path.join(self.conf.path_database, "session_conf.txt"))
        self.load_session()

        # h = 0.  # 10 cm from the ground. nnope. for now, h has to be 0.
        # r = 1.
        # for i in range(10):
        #     a = float(i) / (r + 10) * 15.
        #     x, y = r * math.sin(a), r * math.cos(a)
        #     r += 0.5
        #     n = Node( vector.Vector((x, h, y)), i + 1, self._get_node_color(i+1), gltext )
        #     self.world.append_node(n)

        self.s1 = Socket(SUB)
        self.s1.connect('tcp://127.0.0.1:55555')
        self.s1.set_string_option(SUB, SUB_SUBSCRIBE, '')

    def tick(self, dt, keys):
        self.world.tick(dt)

        try:
            # handle all incoming packets
            # TODO: sync packets by timestamp. sync time configurable. 5 seconds default?
            # print error if a packet arrives out of sync? how to denote this info?
            while 1:
                msg = self.s1.recv(flags=DONTWAIT)
                msg = msg.strip()
                if msg:
                    d = msg.split()
                    if d[0] == "data" or d[0] == "event":

                        # ['data', 'etx', '0001000000000200', 'node', '0A', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']
                        # ['data', 'etx', '0001000000000200', 'node', '0A_sniffy', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']
                        node_id_name = d[4]
                        node = self.world.get_create_named_node(node_id_name)

                        if d[0] == "data":

                            if d[1] == "etx":
                                # ['data', 'etx', '0001000000000200', 'node', '0A', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']

                                # filter out empty rows
                                if int(d[8]) != 0xFFFF:
                                    if d[10].startswith("NO_ROUTE"):
                                        d[10] = "NO"
                                        d[12] = "NO"

                                    # when receiving entry with index 0, then clear out the whole table.
                                    if int(d[6]) == 0:
                                        node.attrs["etx_table"] = []

                                    node.attrs["etx_table"].append("%04X e%s r%s" % (int(d[8]), d[10], "00" if d[12] == "0" else d[12]))
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

                            elif d[1] == "beacon":
                                # ['event', 'beacon', '0052451410156550', 'node', '04', 'options', '0x00', 'parent', '0x0003', 'etx', '30']
                                options = int(d[6], 16)
                                parent = int(d[8], 16)
                                node.append_animation(animations.BeaconAnimation(options))
                                node.attrs["parent"] = parent

                            elif d[1] == "packet_to_activemessage" and 0:
                                # ['event', 'packet', '0000372279297175', 'node', '04', 'dest', '0x1234', 'amid', '0x71']
                                src_node_id = node.node_id
                                dst_node_id = int(d[6], 16)
                                amid = int(d[8], 16)
                                if dst_node_id != 0xFFFF: # filter out broadcasts
                                    src_node = node
                                    dst_node = self.world.get_create_node(dst_node_id)
                                    link = self.world.get_link(src_node, dst_node)
                                    link.poke(src_node)

                            elif d[1] == "send_ctp_packet":
                                # event send_ctp_packet 0:0:38.100017602 node 03 dest 0x0004 origin 0x0009 sequence 21 type 0x71 thl 5
                                # event send_ctp_packet 0:0:10.574584572 node 04 dest 0x0003 origin 0x0005 sequence 4 amid 0x98 thl 1
                                src_node_id = node.node_id
                                dst_node_id = int(d[6], 16)
                                origin_node_id = int(d[8], 16)
                                sequence_num = int(d[10])
                                amid = int(d[12], 16)
                                thl = int(d[14])

                                src_node = node
                                dst_node = self.world.get_create_node(dst_node_id)
                                link = self.world.get_link(src_node, dst_node)
                                # TODO: refactor node color
                                link.poke(src_node, packet_color=self.world.get_node_color(origin_node_id))

                            elif d[1] == "packet_to_model_busy":
                                src_node_id = node.node_id
                                dst_node_id = int(d[6], 16)
                                if dst_node_id != 0xFFFF: # filter out broadcasts
                                    src_node = node
                                    dst_node = self.world.get_create_node(dst_node_id)
                                    link = self.world.get_link(src_node, dst_node)
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
        for node in self.world.nodes:
            parent_id = node.attrs.get("parent")
            if parent_id and parent_id != 0xFFFF:
                parent_node = self.world.get_create_node(parent_id)

                glBegin(GL_LINES)
                glVertex3f(*parent_node.pos)
                glVertex3f(*node.pos)
                glEnd()

        glDisable(GL_LINE_STIPPLE)

    def render(self):
        for link in self.world.links:
            self.link_renderer.render(link)
        self._render_links_to_parents()
        for node in self.world.nodes:
            self.node_renderer.render(node)

    def render_overlay(self, camera, camera_ocs, projection_mode, w_pixels, h_pixels):
        # calculate node screen positions
        for node in self.world.nodes:
            # 1. proj obj to camera_ocs
            # 2. proj coord to screenspace
            v = camera_ocs.projv_in(node.pos)
            node.screen_pos.set(camera.screenspace(projection_mode, v, w_pixels, h_pixels))

        # draw lines from the selected node to every other node
        if 0 and self.selected:
            glLineWidth(1.)
            for node in self.world.nodes:
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
        for node in self.world.nodes:
            self.node_renderer.render_overlay(node)

    def intersects_node(self, sx, sy):
        for node in self.world.nodes:
            if node.intersects(float(sx), float(sy)):
                return node
        return None

    def save_graph_file(self, filename="sensormap.txt"):
        d = {"format": "sensed node graph", "format_version": "2013-12-19", "nodes": [], "edges": []}

        for node in self.world.nodes:
            p = node.pos
            n = {"id": node.node_id, "pos": [p[0], p[1], p[2]]}
            d["nodes"].append(n)

        edge_count = 0
        for node1 in self.world.nodes:
            for node2 in self.world.nodes:
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
            self.world.session_node_positions = {int(k, 16): v for k, v in c.items()}

    def save_session(self):
        """ save node positions. mix together prev session positions and new positions. """
        # convert entries {20907: (1,2,3), ..} to format {"0x51AB", (1,2,3)}
        node_positions_session = {"0x%04X" % k: v for k, v in self.world.session_node_positions.items()}
        node_positions_used = {"0x%04X" % n.node_id: (n.pos[0], n.pos[1], n.pos[2]) for n in self.world.nodes}
        node_positions_session.update(node_positions_used)

        session_conf = {"node_positions": node_positions_session}
        txt = json.dumps(session_conf, indent=4, sort_keys=True)

        with open(self.session_filename, "wb") as f:
            f.write(txt)

    def close(self):
        self.save_session()

    def event(self, event):
        if event.type == SDL_MOUSEMOTION:
            for node in self.world.nodes:
                node.mouse_hover = False
            node = self.intersects_node(event.motion.x, event.motion.y)
            if node:
                self.mouse_hover = True
                node.mouse_hover = True
            else:
                self.mouse_hover = False

            if self.selected and self.mouse_dragging and self.mouse.mouse_lbdown_floor_coord:
                self.selected.pos.set(self.mouse.mouse_floor_coord + self.selected_pos_ofs)

        elif event.type == SDL_MOUSEBUTTONDOWN:
            if event.button.button == SDL_BUTTON_LEFT:
                node = self.intersects_node(event.button.x, event.button.y)
                if node:
                    for n in self.world.nodes:
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
                    node = self.intersects_node(event.button.x, event.button.y)
                    if not node:
                        self.selected = None
                        for n in self.world.nodes:
                            n.selected = False
                self.mouse_dragging = False
