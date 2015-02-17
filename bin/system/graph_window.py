import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

import datetime
import time
import math

import draw
import OpenGL.GL as gl
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *


def timestamp_to_timestr(t):
    """ '2010-01-18 18:40:42.23Z' utc time
    OR '01 12:30:22s"""
    try:
        # this method does not support fractional seconds
        #return time.strftime("%Y-%m-%dT%H:%M:%SZ", d.timetuple())
        # this method does not work with times after 2038
        #return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
        # this method doesn't work in .. some .. cases. don't remember which.
        #return datetime.datetime.utcfromtimestamp(t).strftime("%H:%M:%S.%f")[:11] + "Z"
        # this method does not work with times < 1900
        return (datetime.datetime.utcfromtimestamp(0) + datetime.timedelta(seconds=t)).strftime("%Y-%m-%d %H:%M:%S.%f")[:22] + "Z"
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


class GraphWindow:
    MIN_VISIBLE_SAMPLESPACE_WIDTH = 0.5
    VISIBLE_SAMPLESPACE_BOUND_X1 = -1.
    VISIBLE_SAMPLESPACE_BOUND_X2 = 1.e10
    """
    handles keyboard/mouse navigation (zoom/drag), border drawing. delegates graph rendering to self.graph_renderer
    """
    def __init__(self, font, x=0, y=0, w=100, h=50):
        """ TODO: w, h is with scrollbars and borders?
        :type graph_renderer: GraphRenderer
        """
        self.font = font

        # positions on screen
        self.x, self.y = x, y
        self.w, self.h = w, h

        # graph is moving from right to left? newest sample is anchored to the right window edge.
        self.anchored = True

        # world data
        self.totalsample_x1 = -1.00001
        self.totalsample_x2 = 0.

        # TODO: make these private
        # also, create set_visible_samplespace() method

        # visible sample-space rectangle. x1, y1 is top-left on screen
        # so the top-left screen-pixel of the graph window should have the sample at coordinates (sx1, sy2)
        self.visiblesample_x1 = -self.totalsample_x1
        self.visiblesample_x2 = 0.
        # wanted visible sample-space rectangle. the visible sample-space rectangle is animated towards this rect.
        self.wanted_visiblesample_x1 = self.visiblesample_x1
        self.wanted_visiblesample_x2 = self.visiblesample_x2

        self.ax = 0.

        self._time = time.time
        self._smooth_movement = True

        self.mouse_x = 0.
        self.mouse_y = 0.
        self.mouse_dragging = False

        self.is_active = False
        self.wanted_x2_was_moved = False

        self._t = time.time()

    def place_on_screen(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def get_right_edge_sample(self):
        return self.wanted_visiblesample_x2

    def move_sample_right_edge(self, d):
        dx = self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1
        self.wanted_visiblesample_x2 = self.visiblesample_x2 = d
        self.wanted_visiblesample_x1 = self.visiblesample_x1 = d - dx

    def set_totalsample_start(self, d):
        self.totalsample_x1 = d
        self.VISIBLE_SAMPLESPACE_BOUND_X1 = d - 10.
    def set_totalsample_end(self, d):
        self.totalsample_x2 = d
        self.VISIBLE_SAMPLESPACE_BOUND_X2 = d + 10.

    def set_sample_visibility(self, visiblesample_x1, visiblesample_x2):
        self.wanted_visiblesample_x1 = self.visiblesample_x1 = visiblesample_x1
        self.wanted_visiblesample_x2 = self.visiblesample_x2 = visiblesample_x2

    def tick(self, dt=1./60):
        # smoothly move the visible sample-space towards the wanted values
        # NOTE: only tuned for 60fps. could be TERRIBLE on lower fps
        if abs(self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1) > 0.0001:
            self.ax += (abs(self.wanted_visiblesample_x1 - self.visiblesample_x1) + abs(self.wanted_visiblesample_x2 - self.visiblesample_x2)) / abs(self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1) * .02
        self.ax *= 0.99
        ax = min(self.ax, 1.) if self._smooth_movement else 1

        d = 0.4
        self.visiblesample_x1 += (self.wanted_visiblesample_x1 - self.visiblesample_x1) * d * ax
        self.visiblesample_x2 += (self.wanted_visiblesample_x2 - self.visiblesample_x2) * d * ax

        self._hold_bounds()

    def render(self):
        """ render everything. window edge, scrollbar, legend, and the graph itself. the graph object
         renders the grid, background, grid text and the graph line """
        draw.filled_rect(self.x, self.y, self.w, self.h, (0.0,0.0,0.0,1.))
        self._render_scrollbar(self.x, self.y+1., self.w, 8)

        # render oscilloscope window edge
        gl.glPushMatrix()
        gl.glTranslatef(self.x, self.y, 100.)
#        draw.rect(0.5, 0.5, self.w, self.h, (0.6,0.6,0.6,1.))
        x2 = self.visiblesample_x1
        w2 = self.visiblesample_x2 - self.visiblesample_x1
        # 1. find time values of left/right pixel coordinate
        # 2. calc time values that need a line and draw them using pixel-coordinates
        gl.glColor4f(0.25, 0.25, 0.25, 1.)
        self._render_grid_verlines(0., 10., self.w, self.h-11., x2, w2)

        gl.glEnable(GL_TEXTURE_2D)
        #gl.glScissor(int(self.x), int(self.y), int(self.w), int(self.h))
        #gl.glEnable(gl.GL_SCISSOR_TEST)
        self._render_grid_vertext(0., 10., self.w, self.h-11., x2, w2)
        #gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glDisable(GL_TEXTURE_2D)

        gl.glPopMatrix()

    def set_smooth_movement(self, smooth):
        self._smooth_movement = smooth
        #if not smooth:
        #    self.wanted_visiblesample_x1 = self.visiblesample_x1
        #    self.wanted_visiblesample_x2 = self.visiblesample_x2

    def zoom_in(self, x_ratio, y_ratio):
        """ zoom in. exactly 'percent' fewer samples are visible. """
        n = (self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1) * x_ratio
        self.wanted_visiblesample_x1 += n / 2.
        self.wanted_visiblesample_x2 -= n / 2.
        self._hold_bounds()

    def zoom_out(self, x_ratio, y_ratio):
        n = (self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1) * (1. / (1. - x_ratio) - 1.)
        self.wanted_visiblesample_x1 -= n / 2.
        self.wanted_visiblesample_x2 += n / 2.
        self._hold_bounds()

    def move_by_pixels(self, dx, dy):
        """ move graph by pixels """
        wx, wy, w, h = self._raw_graph_window_dim()
        dwx = dx / w * (self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1)
        self.wanted_visiblesample_x1 -= dwx
        self.wanted_visiblesample_x2 -= dwx
        # moving the graph left releases anchoring
        if dx > 0:
            self.anchored = False
        self._hold_bounds()

    def move_by_ratio(self, dx, dy):
        d = (self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1) * dx
        self.wanted_visiblesample_x1 += d
        self.wanted_visiblesample_x2 += d
        if d < 0.:
            self.anchored = False
        self._hold_bounds()

    def _inside(self, x, y):
        """ return True if coordinate x, y is inside the graph window (excludes window border) """
        wx, wy, w, h = self._raw_graph_window_dim()
        if wx <= x < wx + w and wy <= y < wy + h:
            return True
        return False

    def is_coordinate_inside_window(self, x, y):
        if self.x <= x < self.x + self.w and self.y <= y < self.y + self.h:
            return True
        return False

    def _raw_graph_window_dim(self):
        """ return graph window pos/size in parent window coordinate system, compensating for window border """
        # self.y + 10: 1 for border, 9 for scrollbar
        return self.x+1., self.y+1.+9., self.w-2., self.h-2.-9.

    def _zoom_graph(self, x, y, dx, dy):
        assert self._inside(x, y)
        wx, wy, w, h = self._raw_graph_window_dim()

        # zoom horizontally
        d = (x - wx) / w
        coef = 0.001
        num_samples = (self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1) * dx * coef
        self.wanted_visiblesample_x1 -= d * num_samples
        self.wanted_visiblesample_x2 += (1. - d) * num_samples

        self._hold_bounds()

    def _hold_bounds(self):
        """ anchores and releases right window edge to last sample. movements. """
        if self.wanted_visiblesample_x2 > self.totalsample_x2:
            self.anchored = True

        if self.anchored:
            # anchor right side of the window to the last graph sample. so the graph always animates, grows out from
            # the right side of the window. (anchor sx2 to self.totalsample_x2)
            dx = self.visiblesample_x2 - self.totalsample_x2
            dxw = self.wanted_visiblesample_x2 - self.totalsample_x2
            self.visiblesample_x1 -= dx
            self.visiblesample_x2 -= dx
            self.wanted_visiblesample_x1 -= dxw
            self.wanted_visiblesample_x2 -= dxw

        # limit horizontal zoom
        if self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1 < self.MIN_VISIBLE_SAMPLESPACE_WIDTH:
            d = self.MIN_VISIBLE_SAMPLESPACE_WIDTH - (self.wanted_visiblesample_x2 - self.wanted_visiblesample_x1)
            self.wanted_visiblesample_x1 -= d/2.
            self.wanted_visiblesample_x2 += d/2.
        if self.visiblesample_x2 - self.visiblesample_x1 < self.MIN_VISIBLE_SAMPLESPACE_WIDTH:
            d = self.MIN_VISIBLE_SAMPLESPACE_WIDTH - (self.visiblesample_x2 - self.visiblesample_x1)
            self.visiblesample_x1 -= d/2.
            self.visiblesample_x2 += d/2.

        # enforce bounds
        # enforce left bound. slide whole thing to right if necessary
        if self.wanted_visiblesample_x1 < self.VISIBLE_SAMPLESPACE_BOUND_X1:
            d = self.VISIBLE_SAMPLESPACE_BOUND_X1 - self.wanted_visiblesample_x1
            self.wanted_visiblesample_x1 += d
            self.wanted_visiblesample_x2 += d
        if self.visiblesample_x1 < self.VISIBLE_SAMPLESPACE_BOUND_X1:
            d = self.VISIBLE_SAMPLESPACE_BOUND_X1 - self.visiblesample_x1
            self.visiblesample_x1 += d
            self.visiblesample_x2 += d

        # enforce right bound. slide whole thing to left if necessary
        if self.wanted_visiblesample_x2 > self.VISIBLE_SAMPLESPACE_BOUND_X2:
            d = self.VISIBLE_SAMPLESPACE_BOUND_X2 - self.wanted_visiblesample_x2
            self.wanted_visiblesample_x1 += d
            self.wanted_visiblesample_x2 += d
        if self.visiblesample_x2 > self.VISIBLE_SAMPLESPACE_BOUND_X2:
            d = self.VISIBLE_SAMPLESPACE_BOUND_X2 - self.visiblesample_x2
            self.visiblesample_x1 += d
            self.visiblesample_x2 += d

        # enforce both bounds. this condition is only true if both edges are outside bounds (or exactly on bounds)
        if self.wanted_visiblesample_x2 > self.VISIBLE_SAMPLESPACE_BOUND_X2 or self.wanted_visiblesample_x1 < self.VISIBLE_SAMPLESPACE_BOUND_X1:
            self.wanted_visiblesample_x1 = self.VISIBLE_SAMPLESPACE_BOUND_X1
            self.wanted_visiblesample_x2 = self.VISIBLE_SAMPLESPACE_BOUND_X2
        if self.visiblesample_x2 > self.VISIBLE_SAMPLESPACE_BOUND_X2 or self.visiblesample_x1 < self.VISIBLE_SAMPLESPACE_BOUND_X1:
            self.visiblesample_x1 = self.VISIBLE_SAMPLESPACE_BOUND_X1
            self.visiblesample_x2 = self.VISIBLE_SAMPLESPACE_BOUND_X2

    def _render_scrollbar(self, x, y, w, h):
        v = .6
        draw.line(x+0.5, y+h+0.5, x+w+0.5, y+h+0.5, (v,v,v,1.))

        if self.totalsample_x2 == self.totalsample_x1:
            return

        x1 = (self.visiblesample_x1 - self.totalsample_x1) / (self.totalsample_x2 - self.totalsample_x1) * w
        x2 = (self.visiblesample_x2 - self.totalsample_x1) / (self.totalsample_x2 - self.totalsample_x1) * w

        if x2 - x1 < 1.:
            x2 = x1 + 1.
        x1 = max(x1, 0.)
        x2 = max(x2, 0.)
        x1 = min(x1, w)
        x2 = min(x2, w)
        v = .8
        #draw.filled_rect(x1+x, y+1., x2-x1, h-2., (v,v,v,1.))
        draw.filled_rect(x1+x, y, x2-x1, h-1., (v,v,v,1.))
        v = .7

        #draw.rect(x1, y, x2-x1, h, (v,v,v,1.))

    def _pixel_to_sample(self, y_pixel, h_pixels, y2, h2):
        """ return sample val of a pixel at height y_pixel (0 is top). pixel center coordinates.
        y_pixel : 0..h_pixels
        """
        return y2 + h2 / (h_pixels - 1) * y_pixel

    def _sample_to_pixel(self, y_sample, y2, h2, h_pixels):
        """ return pixel coord of sample at val y_sample """
        return (h_pixels - 1.) / h2 * (y_sample - y2)

    def _samplenum_to_pixel(self, samplenum, x2, w2, w_pixels):
        return (samplenum - x2) / w2 * w_pixels


    def _grid_timestr(self, seconds, step):
        return timestamp_to_timestr_short(seconds)

    def _render_grid_verlines(self, x, y, w, h, x2, w2, min_div_hpix=100.):
        """
        min_div_hpix : minimum division height (grid line distance) in pixels
        """
        assert w > 0.
        if abs(w2) < 0.000001:
            return

        sn1 = x2 # sample num
        sn2 = x2 + w2
        st1 = sn1
        st2 = sn2
        # st1 = ch.sample_to_time(sn1) # sv - sample time
        # st2 = ch.sample_to_time(sn2)
        # swap begin/end if necessary to make following calculations much more convenient
        if st2 < st1:
            st1, st2 = st2, st1
            sn1, sn2 = sn2, sn1

        #volts_per_min_div = (v2 - v1) / (h - 1.) * min_div_hpix
        seconds_per_min_div = (st2 - st1) / w * min_div_hpix
        #pixels_per_volt = (h - 1.) / (v2 - v1)
        # pixels_per_second = float(w) / w2 * ch.freq
        pixels_per_second = float(w) / w2
        st_step  = math.pow(2, math.ceil(math.log(seconds_per_min_div, 2)))
        st_begin = math.floor(st1 / st_step) * st_step + st_step

        px_begin = self._samplenum_to_pixel(st_begin, x2, w2, w)
        px_end   = self._samplenum_to_pixel(sn2, x2, w2, w) # overshooting is intentional
        sign = 1 if px_end > px_begin else -1
        px_step  = pixels_per_second * st_step * sign

        gl.glBegin(gl.GL_LINES)

        px = px_begin + 0.5
        while px * sign < px_end:
            gl.glVertex3f( x+px, y, 0. )
            gl.glVertex3f( x+px, y+h, 0. )
            px += px_step

        gl.glEnd()

    def _render_grid_vertext(self, x, y, w, h, x2, w2, min_div_hpix=100.):

        assert w > 0.
        #ch = self.channels[0]
        if abs(w2) < 0.000001:
            return

        sn1 = x2 # sample num
        sn2 = x2 + w2
        #st1 = ch.sample_to_time(sn1) # sv - sample time
        #st2 = ch.sample_to_time(sn2)
        st1 = sn1
        st2 = sn2
        # swap begin/end if necessary to make following calculations much more convenient
        if st2 < st1:
            st1, st2 = st2, st1
            sn1, sn2 = sn2, sn1

        #volts_per_min_div = (v2 - v1) / (h - 1.) * min_div_hpix
        seconds_per_min_div = (st2 - st1) / w * min_div_hpix
        #pixels_per_volt = (h - 1.) / (v2 - v1)
        # pixels_per_second = float(w) / w2 * ch.freq
        pixels_per_second = float(w) / w2
        st_text_maxwidth = 1. / pixels_per_second * self.font.height * 15 / 2. # assume our text is max 15 characters wide and font width is the same as font height
        st_step  = math.pow(2, math.ceil(math.log(seconds_per_min_div, 2)))
        st_begin = math.floor((st1 - st_text_maxwidth) / st_step) * st_step + st_step
        st_end   = st2 + st_text_maxwidth / 2.

        c = 0.2
        st = st_begin
        while st < st_end:
            # px = self._samplenum_to_pixel(st * ch.freq, x2, w2, w)
            px = self._samplenum_to_pixel(st, x2, w2, w)
            txt = self._grid_timestr(st, st_step)
            self.font.drawtl(txt, x+px - self.font.width(txt)/2. - 0.5, y+1, bgcolor = (c, c, c, .8), fgcolor = (.9, .9, .9, .8))
            st += st_step

    def event(self, event):
        if event.type == SDL_MOUSEMOTION:
            self.mouse_x = float(event.motion.x)
            self.mouse_y = float(event.motion.y)

        x2 = self.wanted_visiblesample_x2

        if self.mouse_dragging or self.is_coordinate_inside_window(self.mouse_x, self.mouse_y):

            if event.type == SDL_MOUSEBUTTONDOWN:
                if event.button.button == SDL_BUTTON_LEFT:
                    self.mouse_dragging = True
                    self.set_smooth_movement(False)
                    self.mouse_last_x = self.mouse_x
                    self.mouse_last_y = self.mouse_y
                    return True

            elif event.type == SDL_MOUSEBUTTONUP:
                if event.button.button == SDL_BUTTON_LEFT:
                    self.mouse_dragging = False
                    self.set_smooth_movement(True)
                    return True

            elif event.type == SDL_MOUSEMOTION:
                if self.mouse_dragging:
                    self.move_by_pixels(event.motion.xrel, event.motion.yrel)
                    if self.wanted_visiblesample_x2 != x2:
                        self.wanted_x2_was_moved = True
                    return True

            elif event.type == SDL_MOUSEWHEEL:
                    return True
    #         elif event.type == SDL_MOUSEWHEEL:
    #             if event.wheel.y:

    # # THIS WILL BE REMOVED

    # def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
    #     k = self.keys
    #     if self._inside(x, y):
    #         if 1: # self.use_trackpad
    #             if not (k[key.LCTRL] or k[key.RCTRL] or k[key.LSHIFT] or k[key.RSHIFT]):
    #                 self.move_by_pixels(scroll_x*4., scroll_y*4.)
    #             # hmm. if shift is down, scroll_x and scroll_y are swapped for mouse wheel.
    #             # but not for apple trackpad.
    #             if not (k[key.LCTRL] or k[key.RCTRL]) and (k[key.LSHIFT] or k[key.RSHIFT]):
    #                 self._zoom_graph(x, y, scroll_x*4., scroll_y*4.)
    #         else: # use mouse wheel
    #             if not (k[key.LCTRL] or k[key.RCTRL] or k[key.LSHIFT] or k[key.RSHIFT]):
    #                 self._zoom_graph(x, y, -scroll_y*16., scroll_x*4.)
    #             if not (k[key.LCTRL] or k[key.RCTRL]) and (k[key.LSHIFT] or k[key.RSHIFT]):
    #                 self._zoom_graph(x, y, -scroll_x*16., scroll_y*4.)

    #             # a hybrid solution. hold down t to use the apple trackpad for navigation
    #             #if not (k[key.LCTRL] or k[key.RCTRL]) and (k[key.LSHIFT] or k[key.RSHIFT]):
    #             if not (k[key.LCTRL] or k[key.RCTRL]) and k[key.T]:
    #                 self.move_by_pixels(scroll_x*4., scroll_y*4.)


            # http://wiki.libsdl.org/SDL_Scancode
            elif event.type == SDL_KEYDOWN:
                key = event.key.keysym.scancode
#                llog.info("keycode %s SDL_SCANCODE_LEFT %s", key, SDL_SCANCODE_LEFT)

                # if shift is not pressed, move the graph.
                if not (event.key.keysym.mod & KMOD_LSHIFT) and not (event.key.keysym.mod & KMOD_RSHIFT):
                    d = 1. / 3
                    if key == SDL_SCANCODE_LEFT:
                        self.move_by_ratio(-d, 0.)
                        if self.wanted_visiblesample_x2 != x2:
                            self.wanted_x2_was_moved = True
#                        llog.info("1111 keycode %s SDL_SCANCODE_LEFT %s", key, SDL_SCANCODE_LEFT)
                        return True
                    if key == SDL_SCANCODE_RIGHT:
                        self.move_by_ratio(d, 0.)
                        if self.wanted_visiblesample_x2 != x2:
                                self.wanted_x2_was_moved = True
                        return True
                # shift was pressed. zoom the graph.
                else:
                    d = 1. / 3
                    if key == SDL_SCANCODE_LEFT:
                        self.zoom_out(d, 0.)
                        if self.wanted_visiblesample_x2 != x2:
                                self.wanted_x2_was_moved = True
#                        llog.info("2222 keycode %s SDL_SCANCODE_LEFT %s", key, SDL_SCANCODE_LEFT)
                        return True
                    if key == SDL_SCANCODE_RIGHT:
                        self.zoom_in(d, 0.)
                        if self.wanted_visiblesample_x2 != x2:
                                self.wanted_x2_was_moved = True
                        return True
