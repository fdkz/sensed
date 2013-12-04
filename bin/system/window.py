
from OpenGL.GL import *
from OpenGL.GLU import *



class Window:

    def __init__(self, pos=(0., 0.), size=(100., 100.), frame = True):
        """
        wx, wy, ww, wh - window coordinates and width/height
        """

        # frame width, frame top height
        self.fw, self.fth = 1., 15.

        self.frame = frame
        self.wx, self.wy = pos
        self.ww, self.wh = size
        self.cx, self.cy = 0., 0.
        self.cw, self.ch = 100., 100.

        self.pos(self.wx, self.wy)
        self.size(self.ww, self.wh)

        self.draw_function = None
        
        # bottom-left point is (0., 0.)

        #self.xtl, self.ytl = 0., h
        #self.xbr, self.ybr = w, 0.

        self.pixel_aspect_w_h = 1.

        #self.opengl_tl_x, self.opengl_tl_y = 0., 0.
        #self.children_anchored = self.TOPLEFT
        # this is windowmanager


    def pos(self, wx, wy):

        self.wx, self.wy = wx, wy
        self._recalc_content_sizepos()


    def pos_content(self, cx, cy):

        self.wx, self.wy = cx - self.fw, cy - self.fth
        self._recalc_content_sizepos()


    def size(self, ww, wh):

        self.ww, self.wh = ww, wh
        self._recalc_content_sizepos()


    def size_content(self, cw, ch):

        self.ww, self.wh = cw + 2 * self.fw, ch + self.wh + self.fth
        self._recalc_content_sizepos()


    def draw(self, root_w, root_h, bgcolor = None):
        
        glViewport(int(self.wx), int(root_h - self.wy - self.wh), int(self.ww), int(self.wh))

        if self.frame:

            # set pixelprojection and draw the frame
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            z_near, z_far = -10000, +10000.
            glOrtho(0., self.ww, self.wh, 0., z_near, z_far)

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            self.draw_background(bgcolor)
            self.draw_frame()

            glViewport(int(self.cx), int(root_h - self.cy - self.ch), int(self.cw), int(self.ch))
            glOrtho(0., self.cw, self.ch, 0., z_near, z_far)

        if self.draw_function: self.draw_function()


    def draw_background(self, bgcolor):

        if not bgcolor: return

        # TODO: too sleepy to know if i need a 0.5 pixel offset or something different altogether.
        glColor(bgcolor[0], bgcolor[1], bgcolor[2], bgcolor[3])

        glBegin(GL_QUADS)
        glVertex(0.,           0., 0.)
        glVertex(self.ww,      0., 0.)
        glVertex(self.ww, self.wh, 0.)
        glVertex(0.,      self.wh, 0.)
        glEnd()


    def draw_frame(self, color = (0.3, 0.3, 0.3, 1.)):
        """
        draw line-frame. around the window-area.
        ASSUMES pixel-projection
        """
        
        glLineWidth(1.)
        glColor(color[0], color[1], color[2], color[3])
        self._draw_rect(0., 0., self.ww, self.wh)
        self._draw_rect(self.cx - self.wx - 1., self.cy - self.wy - 1., \
                        self.cw + 2., self.ch + 2.)


    def _draw_rect(self, x, y, w, h):

        xl = .5 + x
        xr = w - 0.5 + x
        yb = h - 0.5 + y
        yt = .5 + y

        glBegin(GL_LINE_LOOP)

        glVertex(xl, yt)
        glVertex(xr, yt)
        glVertex(xr, yb)
        glVertex(xl, yb)

        glEnd()


    def _recalc_content_sizepos(self):

        if self.frame:
            self.cx = self.wx + self.fw
            self.cy = self.wy + self.fth
            self.cw = self.ww - 2 * self.fw
            self.ch = self.wh - self.fw - self.fth
        else:
            self.cx, self.cy = self.wx, self.wy
            self.cw, self.ch = self.ww, self.wh
