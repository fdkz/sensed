#import copengl as gl
import OpenGL.GL as gl


def line(x1, y1, x2, y2, color=(1.,0.,0.,1.)):
    if color:
        gl.glColor4f(*color)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex3f( x1, y1, 100. )
    gl.glVertex3f( x2, y2, 100. )
    gl.glEnd()

def rect(x, y, w, h, color=(1.,0.,0.,1.)):
    w -= 1; h -= 1
    if color:
        gl.glColor4f(*color)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex3f( x,   y,   100. )
    gl.glVertex3f( x+w, y,   100. )
    gl.glVertex3f( x+w, y+h, 100. )
    gl.glVertex3f( x,   y+h, 100. )
    gl.glEnd()

def filled_rect(x, y, w, h, color=(1.,0.,0.,1.)):
    #w -= 1; h -= 1
    if color:
        gl.glColor4f(*color)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex3f( x,   y,   100. )
    gl.glVertex3f( x+w, y,   100. )
    gl.glVertex3f( x+w, y+h, 100. )
    gl.glVertex3f( x,   y+h, 100. )
    gl.glEnd()
