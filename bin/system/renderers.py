"""
world_objects renderers
"""

import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

from math import sin, cos, radians, atan2
import random

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

import vbo
import vector
import animations
import draw


class LinkRenderer:
    def __init__(self):
        pass

    def render(self, link):
        if link._usage:
            glLineWidth(link._usage)
            r, g, b = 0.4, 0.4, 0.4
            if link._link_busy:
                r += r * (link._busy_age / link._busy_max_age)
                g += g * (link._busy_age / link._busy_max_age)
            if link._just_poked:
                r, g, b = 0., 0., 0.
            glColor4f(r, g, b, 1.)

            glBegin(GL_LINES)
            glVertex3f(*link.node1.pos)
            glVertex3f(*link.node2.pos)
            glEnd()

        for anim in link._animations:
            anim.render()

    def render_overlay(self, node):
        pass


class NodeRenderer:
    def __init__(self, gltext):
        self.gltext = gltext

        # remember to change this also in node object
        self.radius_pixels = 17.

        #self._signal_strength_circles_vbo = self._build_signal_strength_circles_vbo()
        #self._signal_strength_filled_circles_xz_vbo = self._build_filled_circle_xz_vbo(4., (0.5, 0.5, 0.9, 0.8), (0.5, 0.5, 0.9, 0.))

        self._icon_circle_outer_xy_vbo = self._build_filled_circle_xy_vbo(self.radius_pixels)
        self._icon_circle_inner_xy_vbo = self._build_filled_circle_xy_vbo(self.radius_pixels - 2.)
        self._icon_circle_node_colortag_xy_vbo = self._build_filled_half_circle_xy_vbo(self.radius_pixels - 2., -40., 40., 20)

    def render(self, node):
        glLineWidth(1.)
        glPushMatrix()
        glTranslatef(*node.pos)
        for anim in node._animations:
            anim.render()
        #self._signal_strength_filled_circles_xz_vbo.draw(GL_TRIANGLE_FAN)
        #self._signal_strength_circles_vbo.draw(GL_LINES)
        glPopMatrix()

    def render_overlay(self, node):
        """Render the iconified representation at self.screen_pos screen-coordinates."""
        s = node.screen_pos

        # postprocess some animations
        for anim in node._animations:
            # use restless beacon animation
            if isinstance(anim, animations.BeaconAnimation):
                s = s.new()
                d = 3.
                s.add(vector.Vector((random.random() * d - d*0.5, random.random() * d - d*0.5, 0.)))
            # keep the retry-animation connected to the node
            if isinstance(anim, animations.SendRetryAnimation):
                anim.set_pos(s[0]-node.radius_pixels-3., s[1]+node.radius_pixels-3., s[2])

        glDisable(GL_TEXTURE_2D)

        glPushMatrix()
        glTranslatef(*s)

        lighter = (0.1, 0.1, 0.1, 1.0)
        inner_color = (0.8, 0.8, 0.8, 1.0)

        if node.attrs.get("radiopowerstate"):
            inner_color = node.radio_active_color

        #inner_color = node.node_color

        if node.selected:
            outer_color = (1., .4, .4, 1.)
        #    inner_color = tuple(sum(x) for x in zip(node.node_color, lighter))
        elif node.mouse_hover:
            outer_color = (1., 1., 1., 1.)
        #    inner_color = tuple(sum(x) for x in zip(node.node_color, lighter))
        else:
            outer_color = (1., 1., 1., 1.)

        glColor4f(*outer_color)
        self._icon_circle_outer_xy_vbo.draw(GL_TRIANGLE_FAN)
        glColor4f(*inner_color)
        self._icon_circle_inner_xy_vbo.draw(GL_TRIANGLE_FAN)

        if node.radio_active_anim and not node.radio_active_anim.dead:
            glColor4f(*node.radio_active_anim.cur_color)
            self._icon_circle_inner_xy_vbo.draw(GL_TRIANGLE_FAN)

        glColor4f(*node.node_color)
        self._icon_circle_node_colortag_xy_vbo.draw(GL_TRIANGLE_FAN)

        glPopMatrix()

        glEnable(GL_TEXTURE_2D)
        self.gltext.drawmm(node.node_idstr, s[0], s[1], bgcolor=(1.0,1.0,1.0,0.), fgcolor=(0.,0.,0.,1.), z=s[2])
        self.gltext.drawmm(node.node_name, s[0], s[1] + self.gltext.height, bgcolor=(1.0,1.0,1.0,0.), fgcolor=(0.,0.,0.,1.), z=s[2])

        h = self.gltext.height * 2 + 2

        glDisable(GL_TEXTURE_2D)

        for anim in node._animations:
            anim.render_ortho()

        #for key, val in node.attrs.items():
            #if key.startswith("etx_data"):
        if "etx_table" in node.attrs:
            for etx in node.attrs["etx_table"]:
                self.gltext.drawmm(etx, s[0], s[1] + h, bgcolor=(0,0,0,.3), fgcolor=(1.3,1.3,1.3,1.), z=s[2])
                h += self.gltext.height

        if "ctpf_buf_used" in node.attrs and "ctpf_buf_capacity" in node.attrs:
            self._render_progress_bar_mm(s[0], s[1] - node.radius_pixels - 3., s[2], 24, "testpro", node.attrs["ctpf_buf_capacity"], node.attrs["ctpf_buf_used"])

    def _get_node_color(self, awake):
        if awake:
            return 0.529, 0.808, 0.980, 1.0
        else:
            return node.node_color

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

    # def _build_signal_strength_circles_vbo(self):
    #     """Build a vbo of some concnentric circles. meant to be rendered with GL_LINES."""
    #     v = []
    #     for i in range(4):  # 4 circles
    #         radius = i + 1
    #         prevpoint = []
    #         for a in range(0, 361, 5):
    #             point = [radius * sin(radians(a)), 0., radius * cos(radians(a)), 0.5, 0.5, 0.5, 0.9*(0.6**i)]
    #             if prevpoint:
    #                 v.extend(prevpoint)
    #                 v.extend(point)
    #             prevpoint = point
    #     return vbo.VBOColor(v)

    # def _build_filled_circle_xz_vbo(self, radius, centercolor, edgecolor):
    #     """Build a vbo of a filled circle. meant to be rendered with GL_TRIANGLE_FAN."""
    #     r, g, b, a = edgecolor
    #     v = [0., 0., 0.] + list(centercolor)
    #     for angle in range(0, 361, 5):
    #         v.extend([radius * sin(radians(angle)), 0., radius * cos(radians(angle)), r, g, b, a])
    #     return vbo.VBOColor(v)

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
