# update: 2012.07.10

from vector import *

#
# x - right
# y - up
# z - front
#
# clockwise motion around axis is considered positive.
# rotate():
#
#     turn down  (x-axis) - negative
#     turn right (y-axis) - negative
#     tilt right (z-axis) - positive
#

class AxialFrame:
    def __init__(self):
        self.reset()

    def __str__(self):
        return 'x_axis: %s\ny_axis: %s\nz_axis: %s' % \
               (str(self.x_axis), str(self.y_axis), str(self.z_axis))

    def reset(self):
        self.x_axis = Vector((1., 0., 0.))
        self.y_axis = Vector((0., 1., 0.))
        self.z_axis = Vector((0., 0., 1.))

    def new(self):
        aframe = AxialFrame()
        aframe.set(self)
        return aframe

    def set(self, aframe):
        """ use aframe1.set(aframe2) instead of aframe1 = aframe2. """
        self.x_axis.set(aframe.x_axis)
        self.y_axis.set(aframe.y_axis)
        self.z_axis.set(aframe.z_axis)

    def projv_out(self, vector):
        """
        project the vector out of the axial frame. to world-space.
        """
        return self.x_axis * vector[0] + \
               self.y_axis * vector[1] + \
               self.z_axis * vector[2]

    def projv_in(self, vector):
        """
        project the vector into the axial frame. to object-space.
        """
        x = self.x_axis.dot(vector)
        y = self.y_axis.dot(vector)
        z = self.z_axis.dot(vector)
        return Vector((x, y, z))

    def proj_out(self, a_frame):
        a = AxialFrame()
        a.x_axis = self.projv_out( a_frame.x_axis )
        a.y_axis = self.projv_out( a_frame.y_axis )
        a.z_axis = self.projv_out( a_frame.z_axis )
        return a

    def proj_in(self, a_frame):
        a = AxialFrame()
        a.x_axis = self.projv_in( a_frame.x_axis )
        a.y_axis = self.projv_in( a_frame.y_axis )
        a.z_axis = self.projv_in( a_frame.z_axis )
        return a

    def rotate(self, vector, angle):
        self.x_axis.rotate(vector, angle)
        self.y_axis.rotate(vector, angle)
        self.z_axis.rotate(vector, angle)
        self.orthogonalize_z()

    def look_direction(self, direction_vector):
        """
        turn axial_frame to look in the given direction.
        orientation will be the closest to what already was.

        direction_vector has to be unit-vector.
        """
        self.z_axis.set(direction_vector)

        # y & z axis too parallel?
        if self.z_axis.cross(self.y_axis).len2() < 0.001:
            # can't compute x-axis from z & y. have to compute y-axis first
            self.y_axis = self.x_axis.cross(self.z_axis).normal()
            self.x_axis = self.z_axis.cross(self.y_axis).normal()
        else:
            self.x_axis = self.z_axis.cross(self.y_axis).normal()
            self.y_axis = self.x_axis.cross(self.z_axis).normal()

    def look_direction2(self, direction_vector, up_hint_vector):
        """
        turn axial-frame to look in direction_vector, up tries to point
        in the direction of up_hint_vector.
        """
        self.z_axis.set(direction_vector)
        self.z_axis.normalize()

        if self.z_axis.cross(up_hint_vector).len2() < 0.001:
            # our view-direction (z-axis) is the same as the up_hint_vector.
            # so we have two choices:
            #    1. generate a random down-looking aframe
            #    2. try to preserve orientation from the previous frame
            if self.z_axis.cross(self.y_axis).len2() < 0.001:
                # choice 2 failed. generate a random aframe
                self.look_direction_random(self.z_axis)
                return
        else:
            self.y_axis.set(up_hint_vector)

        self.x_axis = self.z_axis.cross(self.y_axis).normal()
        self.y_axis = self.x_axis.cross(self.z_axis).normal()

    def look_direction_random(self, direction_vector):
        """
        generate an axial frame from the given vector. z-axis points in
        the given direction. x-axis and y-axis are random, but guaranteed
        to be orthonormal to every other axis.
        """
        self.z_axis.set(direction_vector)
        self.z_axis.normalize()
        z = self.z_axis

        # guard for collinearity

        #if x*x + y*y < x*x + z*z: a.x_axis.set((0., 1., 0.))
        if z[1]*z[1] < z[2]*z[2]:
            # near the z-axis. have to use y-axis
            self.x_axis.set((0., 1., 0.))
        else:
            # near the y-axis. have to use z-axis
            self.x_axis.set((0., 0., 1.))

        # make the axial frame orthogonal.
        self.y_axis = self.x_axis.cross(self.z_axis).normal()
        self.x_axis = self.z_axis.cross(self.y_axis).normal()

    def remove_xtilt(self, up_vector):
        if self.z_axis.cross(up_vector).len2() > 0.001:
            new_x_axis = self.z_axis.cross(up_vector).normal()
            if self.x_axis.dot(new_x_axis) < 0.:
                self.x_axis = -new_x_axis
            else:
                self.x_axis = new_x_axis
            self.y_axis = self.x_axis.cross(self.z_axis).normal()
        else:
            # if smaller than 0.001, then we already ARE almost looking down.. but it never
            # hurts to try fix things that are already working.
            new_x_axis = self.y_axis.cross(up_vector).normal()
            if self.x_axis.dist2(new_x_axis) > self.x_axis.len2():
                self.x_axis = -new_x_axis
            else:
                self.x_axis = new_x_axis
            self.z_axis = self.y_axis.cross(self.x_axis).normal()

    def orthogonalize_x(self):
        """
        x-axis will not change

        Sometimes errors accumulate and the axial frame becomes more and more
        unorthogonal. You might want to call one of these after a couple of
        hundred rotations made with axial frame.
        """
        self.x_axis.normalize()
        self.z_axis = self.y_axis.cross(self.x_axis).normal()
        self.y_axis = self.x_axis.cross(self.z_axis).normal()

    def orthogonalize_y(self):
        """ y-axis will not change """
        self.y_axis.normalize()
        self.x_axis = self.z_axis.cross(self.y_axis).normal()
        self.z_axis = self.y_axis.cross(self.x_axis).normal()

    def orthogonalize_z(self):
        """ z-axis will not change """
        self.z_axis.normalize()
        self.y_axis = self.x_axis.cross(self.z_axis).normal()
        self.x_axis = self.z_axis.cross(self.y_axis).normal()

    def get_opengl_matrix(self):
        """ return opengl transformation matrix """
        m = [0.] * 16
        #m[0:12:4] = self.x_axis
        #m[1:13:4] = self.y_axis
        #m[2:14:4] = self.z_axis
        #m[0:12:4] = self.x_axis
        #m[1:13:4] = self.y_axis
        #m[2:14:4] = self.z_axis

        m[0]     =  self.x_axis[0]
        m[0+4]   =  self.x_axis[1]
        m[0+4+4] =  self.x_axis[2]

        m[1]     =  self.y_axis[0]
        m[1+4]   =  self.y_axis[1]
        m[1+4+4] =  self.y_axis[2]

        m[2]     =  self.z_axis[0]
        m[2+4]   =  self.z_axis[1]
        m[2+4+4] =  self.z_axis[2]

        m[3+4+4+4] = 1.
        return m

    def get_opengl_matrix2(self):
        """
        return opengl transformation matrix. (axial-frame inverted)
        TODO: what do i mean with inverted?
        """
        m = [0.] * 16

        m[0]     =  self.x_axis[0]
        m[0+4]   =  self.y_axis[0]
        m[0+4+4] =  self.z_axis[0]

        m[1]     =  self.x_axis[1]
        m[1+4]   =  self.y_axis[1]
        m[1+4+4] =  self.z_axis[1]

        m[2]     =  self.x_axis[2]
        m[2+4]   =  self.y_axis[2]
        m[2+4+4] =  self.z_axis[2]

        m[3+4+4+4] = 1.
        return m
