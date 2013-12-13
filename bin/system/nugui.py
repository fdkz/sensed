import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

import time

from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.

from sdl2 import *


class ListBox: pass

class StateTextEntry:
    def __init__(self, id, clock, initial_text):
        self.cursor_pos = -1
        self.clock = clock
        self.id = id
        self.initial_text = initial_text
        self.text = initial_text


class NuGui:
    def __init__(self, font):
        """
        make sure you call this after calling gltext.init()
        font is a gltext instance
        """
        self.font = font

        self.container_stack = []
        self.z = 100.
        self.listbox_item_height = self.font.height + 1

        # state

        self.mouse_x = 0.
        self.mouse_y = 0.
        self.mousedown = False
        self.mouseclickpos = [0., 0.]

        self.mouseleftclick = False

        self.id_active = 0 # mouse pressed
        self.id_hot = 0 # mouse hover
        self.id_focused = 0

        self.hit_clock = 0
        # increased on every finish_frame() call
        self.current_clock = 0
        self.focuslost_clock = 0

        # widget states. {id: state, ..}
        # temporary local state objects for complex ui elements. textedit for now
        self.states = {}

        # the active element consumes keypresses from this queue.
        self.keyqueue = [] # [(character, scancode), ..]

    def finish_frame(self):
        # clear focus if there was a mouseclick outside of every gui element
        if self.hit_clock < self.current_clock and self.mousedown:
            self.focuslost_clock = self.current_clock
            self.id_focused = None
        self.current_clock += 1

    def begin_listbox(self, id, x, y, w=100.):
        """
        TODO: x, y - pixel-coordinates?
        """
        l = ListBox()
        l.x, l.y = x + 1, y + 1
        l.w = w
        l.hc = 0. # h current
        self.container_stack.append( l )

    def end_listbox(self):
        """
        return True if clicked out of the listbox.
        """
        l = self.container_stack.pop(-1)

        # draw a box..

        glDisable(GL_TEXTURE_2D)
        glLineWidth(1.)
        glColor4f(0., 0., 0., 1.)
        self._draw_rect(l.x - 2, l.y - 2, l.w + 4, l.hc + 3)

        if self.mouseleftclick:
            return not self._mouse_is_inside(l.x - 2, l.y - 2, l.w + 4, l.hc + 3)
        return False

    def listbox_item(self, id, text, disabled=False, selected=False):
        l = self.container_stack[-1]

        x, y, z, w, h = l.x, l.y + l.hc, self.z, l.w, self.font.height

        if self._mouse_is_inside(x, y, w, h):
            self.id_hot = id
            if self.mousedown and not self.id_active:
                self.id_active = id
                self.id_focused = id
            if self.mousedown:
                self.hit_clock = self.current_clock

        fgcolor = (0., 0., 0., 1.)
        if disabled:
            fgcolor = (0.5, 0.5, 0.5, 8.)
            glColor4f(0.8, 0.8, 1.,  0.8)
        elif selected:
            if   self.id_active == id: glColor4f(1.,  0.0, 0.0, 0.95)
            elif self.id_hot    == id: glColor4f(1.,  0.4, 0.4, 0.95)
            else:                      glColor4f(0.8, 0.5, 0.7,  0.9)
        else:
            if   self.id_active == id: glColor4f(1.,  0.3, 0.3, 0.95)
            elif self.id_hot    == id: glColor4f(1.,  0.7, 0.7, 0.95)
            else:                      glColor4f(0.8, 0.8, 1.,  0.9)

        glDisable(GL_TEXTURE_2D)
        self._draw_filled_rect(x, y, w, h)

        glEnable(GL_TEXTURE_2D)
        self.font.drawtl(text, x, y, z = z, fgcolor = fgcolor, bgcolor = (0., 0., 0., 0.))

        l.hc += self.listbox_item_height

        # did the user click the item?

        if not disabled and self.id_hot == id and self.id_active == id and not self.mousedown: return True
        return False

    def listbox_header(self, id, text):
        l = self.container_stack[-1]

        x, y, z, w, h = l.x, l.y + l.hc, self.z, l.w, self.font.height

        glColor4f(0.9, 0.9, 1., 0.93)

        glDisable(GL_TEXTURE_2D)
        self._draw_filled_rect(x, y, w, h)

        glEnable(GL_TEXTURE_2D)
        self.font.drawtl(text, x, y, z = z, fgcolor = (0., 0., 0., 1.), bgcolor = (0., 0., 0., 0.))

        l.hc += self.listbox_item_height

    def button(self, id, x, y, text, w=None, h=None, disabled=False):
        tw, z = self.font.width(text), self.z
        if w is None: w = tw + 10
        if h is None: h = self.font.height + 8

        if self._mouse_is_inside(x, y, w, h):
            self.id_hot = id
            if self.mousedown and not self.id_active:
                self.id_active = id
                self.id_focused = id
            if self.mousedown:
                self.hit_clock = self.current_clock

        # draw the button

        fgcolor = (0., 0., 0., 1.)
        if disabled:
            fgcolor = (0.5, 0.5, 0.5, 8.)
            glColor4f(0.8, 0.8, 1.,  0.8)
        elif self.id_active == id: glColor4f(1.,  0.3, 0.3, 0.95)
        elif self.id_hot    == id: glColor4f(1.,  0.7, 0.7, 0.95)
        else:                      glColor4f(0.8, 0.8, 1.,  0.9)

        glDisable(GL_TEXTURE_2D)
        self._draw_filled_rect(x, y, w, h)

        glColor4f(0., 0., 0., 1.)
        self._draw_rect(x, y, w, h)
        glEnable(GL_TEXTURE_2D)
        self.font.drawmm(text, x + w / 2., y + h / 2., z = z, fgcolor = fgcolor, bgcolor = (0., 0., 0., 0.))

        # did the user click the button?

        if not disabled and self.id_hot == id and self.id_active == id and not self.mousedown:
            return True
        return False

    def listbox_item_menu(self, id, name, x, y, text): pass

    def textentry(self, id, x, y, w, default_text, disabled=False):
        """return (changed, new_text)
        changed is True if enter is pressed or focus is lost and the text is different from the initial default_text.
        disabled: flag not implemented
        """
        h = self.font.height + 8
        if self._mouse_is_inside(x, y, w, h):
            self.id_hot = id
            if self.mousedown and not self.id_active:
                self.id_active = id
                self.id_focused = id
                del self.keyqueue[:]
            if self.mousedown:
                self.hit_clock = self.current_clock

        ret_changed = False
        ret_new_text = default_text

        if self.id_focused == id:
            if id not in self.states:
                self.states[id] = StateTextEntry(id, self.current_clock, default_text)
            id_local = self.states[id]
            id_local.clock = self.current_clock
            assert id_local.id == id

            for character, scancode in self.keyqueue:
                if scancode == SDL_SCANCODE_RETURN:
                    if id_local.text != id_local.initial_text:
                        ret_changed = True
                    self.id_focused = None
                    del self.states[id]
                    break
                elif scancode == SDL_SCANCODE_ESCAPE:
                    id_local.text = id_local.initial_text
                    self.id_focused = None
                    del self.states[id]
                    break
                #elif scancode == SDL_SCANCODE_DELETE:
                elif scancode == SDL_SCANCODE_BACKSPACE:
                    id_local.text = id_local.text[:-1]
                else:
                    if character:
                        id_local.text += character

            ret_new_text = id_local.text
            del self.keyqueue[:]
        else:
            # check if focus was lost just last frame. in that case, generate a "changed" event.
            if id in self.states:
                llog.info("%s focus %s hit %s", self.states[id].clock, self.focuslost_clock, self.hit_clock)
                if self.states[id].clock == self.hit_clock - 1 or self.states[id].clock == self.focuslost_clock:
                    ret_changed = True
                    ret_new_text = self.states[id].text
                    del self.states[id]


        fgcolor = (0., 0., 0., 1.)
        if disabled:
            fgcolor = (0.5, 0.5, 0.5, 8.)
            glColor4f(0.8, 0.8, 1.,  0.8)
        elif self.id_focused == id: glColor4f(1.,  1., 1., 0.95)
        elif self.id_active  == id: glColor4f(1.,  0.3, 0.3, 0.95)
        elif self.id_hot     == id: glColor4f(1.,  0.7, 0.7, 0.95)
        else:                       glColor4f(0.85, 0.85, .85,  0.9)

        glDisable(GL_TEXTURE_2D)
        self._draw_filled_rect(x, y, w, h)

        glColor4f(0.4, 0.4, 0.4, 1.)
        self._draw_rect(x, y, w, h)
        glEnable(GL_TEXTURE_2D)
        self.font.drawml(ret_new_text, x + 5, y + h / 2., z = self.z, fgcolor = fgcolor, bgcolor = (0., 0., 0., 0.))

        # draw the blinking cursor
        if self.id_focused == id and int(time.time() * 4) % 2:
            glColor4f(0.4, 0.4, 0.4, 1.)
            glDisable(GL_TEXTURE_2D)
            self._draw_filled_rect(x + 5 + self.font.width(ret_new_text), y+3, 1, h-6)

        return ret_changed, ret_new_text

    def event(self, event):
        # http://wiki.libsdl.org/SDL_Scancode
        if event.type == SDL_KEYDOWN:
            if self.id_focused:
                #llog.info("keysym %s scancode %s", event.key.keysym.sym, event.key.keysym.scancode)
                sym = event.key.keysym.sym
                # is ascii printable chars?
                # append (character, keycode) if character is ascii-printable. else character is None
                self.keyqueue.append((chr(sym) if 0x20 <= sym <= 0x7e else None, event.key.keysym.scancode))
                #if event.key.keysym.scancode == SDL_SCANCODE_ESCAPE:

    def _mouse_is_inside(self, x, y, w, h):
        if x     <= self.mouse_x and y     <= self.mouse_y and \
           x + w >  self.mouse_x and y + h >  self.mouse_y:
           return True

        return False

    def set_mouse_pos(self, x, y):
        self.mouse_x, self.mouse_y = x, y

    def set_mouse_button(self, leftmousebutton):
        """ boolean """
        if self.mousedown and not leftmousebutton:
            self.mouseleftclick = True
        self.mousedown = leftmousebutton

    def tick(self):
        """
        call this AFTER done using nugui for the frame.
        """
        self.id_hot = 0
        if not self.mousedown: self.id_active = 0
        #else:              self.id_active = 0 # -1
        self.mouseleftclick = False

    def _draw_filled_rect(self, x, y, w, h):
        z = self.z
        glBegin(GL_QUADS)
        glVertex3f(x,     y,     z)
        glVertex3f(x + w, y,     z)
        glVertex3f(x + w, y + h, z)
        glVertex3f(x,     y + h, z)
        glEnd()

    def _draw_rect(self, x, y, w, h):
        xl = .5 + x
        xr = w - 0.5 + x
        yb = h - 0.5 + y
        yt = .5 + y
        z  = self.z

        #xl = x
        #xr = w + x - 1.
        #yb = h + y - 1.
        #yt = y

        glBegin(GL_LINE_LOOP)
        glVertex3f(xl, yt, z)
        glVertex3f(xr, yt, z)
        glVertex3f(xr, yb, z)
        glVertex3f(xl, yb, z)
        glEnd()
