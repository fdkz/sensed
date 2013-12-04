# update: 2012.07.10

import axial_frame
import vector


class CoordinateSystem:
    """
    orthogonal coordinate system
    """
    def __init__(self):
        self.a_frame = axial_frame.AxialFrame()
        self.pos     = vector.Vector()

    def new(self):
        ocs = CoordinateSystem()
        ocs.set(self)
        return ocs

    def set(self, ocs):
        self.a_frame.set(ocs.a_frame)
        self.pos.set(ocs.pos)

    def reset(self):
        self.a_frame.reset()
        self.pos.reset()

    def proj_in(self, ocs):
        cs = CoordinateSystem()
        cs.a_frame = self.a_frame.proj_in(ocs.a_frame)
        cs.pos     = self.a_frame.projv_in(ocs.pos - self.pos)
        return cs

    def proj_out(self, ocs):
        cs = CoordinateSystem()
        cs.a_frame = self.a_frame.proj_out(ocs.a_frame)
        cs.pos     = self.a_frame.projv_out(ocs.pos) + self.pos
        return cs

    def projv_in(self, vect):
        return self.a_frame.projv_in(vect - self.pos)

    def projv_out(self, vect):
        return self.pos + self.a_frame.projv_out(vect)

    def rotate(self, point, axis, angle):
        self.a_frame.rotate(axis, angle)
        newpos = self.pos - point
        newpos.rotate(axis, angle)
        self.pos.set(newpos + point)

    def get_opengl_matrix(self):
        """
        multiplication projects things INTO this coordinate system.
        """
        m = self.a_frame.get_opengl_matrix()
        v = self.pos
        # this method first rotates, then translates..

        #
        # this:
        #    glMultMatrixf((GLfloat*16)(*self.a_frame.get_opengl_matrix()))
        #    glTranslatef(-v[0], -v[1], -v[2])
        # is equivalent to this:
        #    glMultMatrixf((GLfloat*16)(*self.get_opengl_matrix()))
        #

        # https://cvs.khronos.org/svn/repos/registry/trunk/public/webgl/sdk/demos/google/resources/moz/matrix4x4.js
        # multiply the a_frame orientation matrix by translation matrix
        tx, ty, tz = -v[0], -v[1], -v[2]
        m[3*4+0] += m[0*4+0] * tx + m[1*4+0] * ty + m[2*4+0] * tz
        m[3*4+1] += m[0*4+1] * tx + m[1*4+1] * ty + m[2*4+1] * tz
        m[3*4+2] += m[0*4+2] * tx + m[1*4+2] * ty + m[2*4+2] * tz
        m[3*4+3] += m[0*4+3] * tx + m[1*4+3] * ty + m[2*4+3] * tz

        return m

    def get_opengl_matrix2(self):
        """
        multiplication projects things OUT OF this coordinate system. (TODO: position)
        """
        m = self.a_frame.get_opengl_matrix2()
        v = self.pos
        # TODO: this is so very wrong
        #m[0+4+4+4] = v[0]
        #m[1+4+4+4] = v[1]
        #m[2+4+4+4] = v[2]

        return m

