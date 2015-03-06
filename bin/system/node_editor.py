import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

#from math import sin, cos, radians, atan2
import os
import json
import errno
import math
import random
import time
import datetime

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *

import coordinate_system
import vector

import world
import renderers
import animations
import world_streamer
import draw
import graph_window

from nanomsg import Socket, SUB, SUB_SUBSCRIBE, DONTWAIT, NanoMsgAPIError


def timestamp_to_timestr(t):
    """ '2010-01-18T18:40:42.23Z' utc time
    OR '01 12:30:22s"""
    try:
        # this method does not support fractional seconds
        #return time.strftime("%Y-%m-%dT%H:%M:%SZ", d.timetuple())
        # this method does not work with times after 2038
        #return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
        # this method doesn't work in .. some .. cases. don't remember which.
        #return datetime.datetime.utcfromtimestamp(t).strftime("%H:%M:%S.%f")[:11] + "Z"
        # this method does not work with times < 1900
        return (datetime.datetime.utcfromtimestamp(0) + datetime.timedelta(seconds=t)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:22] + "Z"
    except:
        # fallback. return time in dhms (days, hours, minutes, seconds) format.
        return "%i %02i:%02i:%02is" % (t // (60*60*24), t // (60*60) % 24, t // 60 % 60, t % 60)

def timestamp_to_timestr_short(t):
    """ '18:40:42.23Z' utc time
    OR '01 12:30:22s"""
    try:
        return (datetime.datetime.utcfromtimestamp(0) + datetime.timedelta(seconds=t)).strftime("%H:%M:%S.%f")[:11] + "Z"
    except:
        return "%i %02i:%02i:%02is" % (t // (60*60*24), t // (60*60) % 24, t // 60 % 60, t % 60)


class NodeEditor:
    #STATE_PLAYBACK_ON_EDGE = 0x01 #
    STATE_PLAYBACK = 0x02 # playback from random place
    STATE_PAUSED = 0x03

    # seek
    # get_delta_packets(dt)
    # get_current_timestamp

    def __init__(self, nugui, mouse, gltext, conf):
        self.conf = conf
        self.mouse = mouse  # TODO: use a special mouse object instead of the editor_main object directly.
        self.gltext = gltext
        self.nugui = nugui

        self.world = world.World("ff", self.conf)
        self.underworld = world.World("", self.conf) # not visible. used serializing keyframes

        self.mouse_x = 0.
        self.mouse_y = 0.
        self.mouse_hover = False
        self.mouse_dragging = False
        self.selected = None
        self.selected_pos_ofs = vector.Vector()

        self.node_renderer = renderers.NodeRenderer(self.gltext)
        self.link_renderer = renderers.LinkRenderer()

        # saved when closing the windows. loaded at startup.
        self.session_filename = os.path.normpath(os.path.join(self.conf.path_database, "session_conf.txt"))
        self.load_session()

        self.recording = True
        self.state = self.STATE_PLAYBACK

        self.worldstreamer = world_streamer.WorldStreamer(sync_window_seconds=self.conf.sync_depth_seconds)

        #self.current_playback_time = 0. # timepoint of the simulation that is currently visible on screen. can be dragged around with a slider.
        self.timeslider_end_time = 0.

        self.graph_window = graph_window.GraphWindow(self.gltext)
        self.graph_window_initialized = False

        self.s1 = Socket(SUB)
        self.s1.connect('tcp://127.0.0.1:55555')
        self.s1.set_string_option(SUB, SUB_SUBSCRIBE, '')

    def tick(self, dt, keys):
        self.world.tick(dt)
        self.underworld.tick(dt)
        self.net_poll_packets()

        fresh_packets = self.worldstreamer.tick()
        for p in fresh_packets:
            self.handle_packet(p[1], self.underworld, barebones=True)

        if self.state == self.STATE_PLAYBACK:
            packets = self.worldstreamer.get_delta_packets(dt)
            for p in packets:
                self.handle_packet(p[1], self.world)

        if self.worldstreamer.need_keyframe():
            llog.info("need keyframe!")
            w = self.underworld.serialize_world()

            #import pprint
            #llog.info("\n\n\nSAVING")
            #llog.info(pprint.pformat(w))

            self.worldstreamer.put_keyframe(w)

        # always set the graph start 10 seconds before the first sample time. user-friendly start condition for the zoom-scroller.
        if self.worldstreamer.start_time != None and not self.graph_window_initialized:
            self.graph_window_initialized = True
            self.graph_window.set_totalsample_start(self.worldstreamer.start_time - 10.)
            self.graph_window.set_totalsample_end(self.worldstreamer.end_time)
            self.graph_window.set_sample_visibility(self.worldstreamer.start_time - 10., self.worldstreamer.end_time)

        if self.graph_window_initialized:
            self.graph_window.set_totalsample_end(self.worldstreamer.end_time)

        self.graph_window.tick()

        if self.graph_window_initialized:
            # if the graph was moved by keyboard/mouse
            if self.graph_window.wanted_x2_was_moved:
                self.graph_window.wanted_x2_was_moved = False
                newtime = self.graph_window.wanted_visiblesample_x2

                if newtime != self.worldstreamer.current_time:
                    llog.info("seeking from %.2f to %.2f between %.2f %.2f", self.worldstreamer.current_time, newtime, self.worldstreamer.start_time, self.worldstreamer.end_time)
                    keyframe, packets = self.worldstreamer.seek(newtime)
                    self.world.deserialize_world(keyframe)
                    llog.info("seeking returned %i packets", len(packets))
                    for p in packets:
                        self.handle_packet(p[1], self.world)

            if self.state == self.STATE_PLAYBACK:
                self.graph_window.move_sample_right_edge(self.worldstreamer.current_time)

    def net_poll_packets(self):
        try:
            # handle all incoming packets
            # TODO: sync packets by timestamp. sync time configurable. 5 seconds default?
            #       print error if a packet arrives out of sync? how to denote this info?
            while 1:
                msg = self.s1.recv(flags=DONTWAIT)
                if not msg:
                    break

                msg = msg.strip()
                if msg:
                    try:
                        # append the packet to timesyncer
                        # get the timestamp.
                        d = msg.split(None, 5)
                        #d = d[1:] # cut off the seqno
                        # ['data', 'etx', '0001000000000200', 'node', '0A', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']
                        if d[0] == "data" or d[0] == "event":
                            # get nodeid from packet
                            node_id_name = d[4]
                            nodeid = int(node_id_name.split("_", 1)[0], 16)
                            self.worldstreamer.put_packet(float(d[2]), msg, nodeid)
                    except:
                        llog.exception("")

        except NanoMsgAPIError as e:
            if e.errno != errno.EAGAIN:
                raise

    def handle_packet(self, msg, world, barebones=False):
        """ barebones : if True, then won't use any animations and non-essential poking of the world.
        Will result in a fast barebones world that is still usable for generating keyframes. """

        #llog.info("handle: %s", msg)
        d = msg.split()
        #d = d[1:] # cut off the seqno
        if d[0] == "data" or d[0] == "event":

            #timestamp = float(d[2])
            #timesyncer.append(timestamp, msg)

            # ['data', 'etx', '0001000000000200', 'node', '0A', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']
            # ['data', 'etx', '0001000000000200', 'node', '0A_sniffy', 'index', '0', 'neighbor', '8', 'etx', '10', 'retx', '74']
            node_id_name = d[4]
            node = world.get_create_named_node(node_id_name)
            src_node = node
            src_node_id = node.node_id

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

                        attrs_etx_table = node.attrs.get("etx_table", [])
                        attrs_etx_table.append("%04X e%s r%s" % (int(d[8]), d[10], "00" if d[12] == "0" else d[12]))
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
                    if not barebones:
                        if radiopowerstate:
                            node.poke_radio()

                elif d[1] == "beacon":
                    # ['event', 'beacon', '0052451410156550', 'node', '04', 'options', '0x00', 'parent', '0x0003', 'etx', '30']
                    options = int(d[6], 16)
                    parent = int(d[8], 16)
                    node.attrs["parent"] = parent
                    if not barebones:
                        node.append_animation(animations.BeaconAnimation(options))

                elif d[1] == "packet_to_activemessage" and 0:
                    # ['event', 'packet', '0000372279297175', 'node', '04', 'dest', '0x1234', 'amid', '0x71']
                    dst_node_id = int(d[6], 16)
                    amid = int(d[8], 16)
                    if dst_node_id != 0xFFFF: # filter out broadcasts
                        dst_node = world.get_create_node(dst_node_id)
                        if not barebones:
                            link = world.get_link(src_node, dst_node)
                            link.poke(src_node)

                elif d[1] == "send_ctp_packet":
                    # event send_ctp_packet 0:0:38.100017602 node 03 dest 0x0004 origin 0x0009 sequence 21 type 0x71 thl 5
                    # event send_ctp_packet 0:0:10.574584572 node 04 dest 0x0003 origin 0x0005 sequence 4 amid 0x98 thl 1
                    dst_node_id = int(d[6], 16)
                    origin_node_id = int(d[8], 16)
                    sequence_num = int(d[10])
                    amid = int(d[12], 16)
                    thl = int(d[14])

                    dst_node = world.get_create_node(dst_node_id)
                    if not barebones:
                        link = world.get_link(src_node, dst_node)
                        # TODO: refactor node color
                        link.poke(src_node, packet_color=world.get_node_color(origin_node_id))

                elif d[1] == "packet_to_model_busy":
                    dst_node_id = int(d[6], 16)
                    if dst_node_id != 0xFFFF: # filter out broadcasts
                        src_node = node
                        dst_node = world.get_create_node(dst_node_id)
                        if not barebones:
                            link = self.world.get_link(src_node, dst_node)
                            link.poke_busy(src_node)

                elif d[1] == "send_done":
                    # 'event send_done 1425601510.21 node 2C13_8 rm 0x02 dest 0x37B6 amid 0x71 error 0x00 retry_count 9 acked 0x01 congested 0x00 dropped 0x00'
                    ramplex_id = int(d[6],16)
                    dst_node_id = int(d[8],16)
                    amid = int(d[10],16)
                    error = int(d[12],16)
                    retry_count = int(d[14],16)
                    acked = int(d[16],16)
                    congested = int(d[18],16)
                    dropped = int(d[20],16)

                    if not barebones and retry_count > 0:
                        node.append_animation(animations.SendRetryAnimation(max_age=1., start_color=(1.,0.,0.,1.), end_color=(0.,0.,0.,0.2), retry_count=retry_count))

            else:
                llog.info("unknown msg %s", repr(msg))

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

        t = self.gltext

        # render some information

        glEnable(GL_TEXTURE_2D)
        y = 5.
        t.drawtl(" sync depth  : %.1f s " % (self.worldstreamer.sync_window_seconds), 5, y, bgcolor=(0.8,0.8,0.8,.9), fgcolor=(0.,0.,0.,1.), z=100.); y += t.height
        t.drawtl(" recording   : yes ", 5, y); y += t.height
        txt = "-" if self.worldstreamer.start_time == None else round(self.worldstreamer.end_time - self.worldstreamer.start_time)
        t.drawtl(" duration    : %s s " % (txt), 5, y); y += t.height
        t.drawtl(" num packets : %i " % self.worldstreamer.num_packets_sorted, 5, y); y += t.height

        # render and handle rewind-slider

        if 1:
            txt = "-" if self.worldstreamer.start_time == None else timestamp_to_timestr(self.worldstreamer.start_time)
            t.drawbl(txt, 5, h_pixels - 53, bgcolor=(0,0,0,.6), fgcolor=(.8,.8,.8,1.), z=100.)
            txt = "-" if self.worldstreamer.end_time == None else timestamp_to_timestr(self.worldstreamer.end_time)
            t.drawbr(txt, w_pixels-5, h_pixels-53)
            txt = "-" if self.worldstreamer.current_time == None else timestamp_to_timestr(self.worldstreamer.current_time)
            t.drawbm(txt, w_pixels/2, h_pixels-53, bgcolor=(0,0,0,.9))

            glLineWidth(1.)
            glDisable(GL_TEXTURE_2D)


    #        self.render_timeslide_scrollbar(h_pixels-80, w_pixels-10, w_pixels-20, 10)

        if 0:
            if self.worldstreamer.start_time == None:
                self.nugui.slider(1001, 10, h_pixels-40, w_pixels-20, 0., 0., 0., True)
            else:
                # don't update slider end time while dragging the slider
                if self.nugui.id_active != 1001:
                    self.timeslider_end_time = self.worldstreamer.end_time
                newtime = self.nugui.slider(1001, 10, h_pixels-40, w_pixels-20, self.worldstreamer.current_time, self.worldstreamer.start_time, self.timeslider_end_time)
                if newtime != self.worldstreamer.current_time:
                    llog.info("seeking from %.2f to %.2f between %.2f %.2f", self.worldstreamer.current_time, newtime, self.worldstreamer.start_time, self.worldstreamer.end_time)
                    keyframe, packets = self.worldstreamer.seek(newtime)
                    self.world.deserialize_world(keyframe)
                    llog.info("seeking returned %i packets", len(packets))
                    for p in packets:
                        self.handle_packet(p[1], self.world)


        self.graph_window.place_on_screen(0, h_pixels-51, w_pixels, 50)
        self.graph_window.render()


        txt = "playing" if self.state == self.STATE_PLAYBACK else "paused"
        if self.nugui.button(1002, 5, h_pixels-90, txt, w=64):
            if self.state == self.STATE_PLAYBACK:
                self.state = self.STATE_PAUSED
            else:
                self.state = self.STATE_PLAYBACK

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

    def is_world_move_allowed(self):
        if self.graph_window.is_coordinate_inside_window(self.mouse_x, self.mouse_y):
            return False
        return True

    def event(self, event):

        if self.graph_window.event(event):
            return True

        if event.type == SDL_MOUSEMOTION:
            self.mouse_x = float(event.motion.x)
            self.mouse_y = float(event.motion.y)

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
                return True

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
