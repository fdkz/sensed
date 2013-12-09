from OpenGL.GL import *
from copenglconstants import * # import to silence opengl enum errors for pycharm. pycharm can't see pyopengl enums.
from ctypes import c_float

from ctypes import c_float, c_void_p


class VBO:
    """
    draw a translucent red line from (0,0,0) to (1,0,0):
        vbo = VBO([0.,0.,0., 1.,0.,0.])
        glColor4f(1., 0., 0., 0.5)
        vbo.draw(GL_LINES)
    """
    def __init__(self, vertices):
        #pyglet.graphics.vertex_list((ntiles+1) * 4, ('v3f/static', v))

        self.num_vertices = len(vertices) / 3
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, len(vertices)*4, (c_float*len(vertices))(*vertices), GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def draw(self, elemtype):
        """ elemtype: GL_LINES, GL_TRIANGLES, .. """
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glDrawArrays(elemtype, 0, self.num_vertices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)



class VBOColor:
    """
    draw a translucent triangle with red, green and blue tips:
        vbo = VBOColor([0.,0.,0.,   1.,0.,0.])
        glColor4f(1., 0., 0., 0.5)
        vbo.draw(GL_LINES)
    """
    def __init__(self, vertices_colors):
        """vertices_color: [x,y,z,r,g,b,a,  x,y,z,r,g,b,a, ... ]. All floats."""
        self.num_vertices = len(vertices_colors) / 7
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, len(vertices_colors)*4, (c_float*len(vertices_colors))(*vertices_colors), GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)


    def draw(self, elemtype):
#        if not self._vbo_initialized:
            # upload vbo contents to the graphics card
#            self._vbo_initialized = True
#            glBufferData(GL_ARRAY_BUFFER, sizeof(self._vbo_vertices), self._vbo_vertices, GL_STATIC_DRAW)
            #glBufferData(GL_ARRAY_BUFFER, sizeof(self._vbo_vertices), pointer(self._vbo_vertices), GL_STATIC_DRAW)
            #glBufferData(GL_ARRAY_BUFFER, sizeof(data), 0, GL_DYNAMIC_DRAW)
            #glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(data), data)

        vertex_offset = c_void_p(0)
        color_offset = c_void_p(12)
        vertex_size = 4*3+4*4 # 3 floats for coordinate, 4 floats for color

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glVertexPointer(3, GL_FLOAT, vertex_size, vertex_offset)
        glColorPointer(4, GL_FLOAT, vertex_size, color_offset)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        glDrawArrays(elemtype, 0, self.num_vertices)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # v_offset = c_void_p(0)
        # c_offset = c_void_p(12)
        # n_offset = c_void_p(16)

        # glVertexPointer(3, GL_FLOAT, sizeof(CubeVertex), v_offset);
        # glColorPointer(4, GL_UNSIGNED_BYTE, sizeof(CubeVertex), c_offset);
        # glNormalPointer(GL_FLOAT, sizeof(CubeVertex), n_offset);
        # glEnableClientState(GL_VERTEX_ARRAY);
        # glEnableClientState(GL_COLOR_ARRAY);
        # glEnableClientState(GL_NORMAL_ARRAY);
        # glDrawArrays(GL_TRIANGLES, 0, self._vbo_vertices_num);
        # glDisableClientState(GL_NORMAL_ARRAY);
        # glDisableClientState(GL_COLOR_ARRAY);
        # glDisableClientState(GL_VERTEX_ARRAY);
        # glBindBuffer(GL_ARRAY_BUFFER, 0)


# class VBOIndexed:
#     def __init__(self, indices, vertices_with_normals):
#         """ vertices_with_normals : interlaced """
#         self.num_vertices = len(vertices) / 3
#         GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
#         self.vbo = GL.glGenBuffers(1)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
#         GL.glBufferData(GL.GL_ARRAY_BUFFER, len(vertices)*4, (c_float*len(vertices))(*vertices), GL.GL_STATIC_DRAW)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

#     def draw(self, elemtype):
#         """ elemtype: GL_LINES, GL_TRIANGLES, .. """
#         stride = 3*4
#         n_offset = c_void_p(stride)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
#         GL.glVertexPointer(3, GL.GL_FLOAT, stride, None)
#         GL.glNormalPointer(GL.GL_FLOAT, stride, n_offset)
#         GL.glDrawArrays(elemtype, 0, self.num_vertices)
#         GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

#         #glDrawElements( GL_TRIANGLES, len( self.indices ), GL_UNSIGNED_SHORT, self.indices )
