import numpy
import math

import src.utils.util as util


def translation_matrix(xyz_trans, mat=None):
    res = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
    for i in range(0, len(xyz_trans)):
        res.itemset((i, 3), float(xyz_trans[i]))
    return res


def scale_matrix(xyz_scale, mat=None):
    res = mat if mat is not None else numpy.identity(4, dtype=numpy.float32)
    for i in range(0, len(xyz_scale)):
        res.itemset((i, i), float(xyz_scale[i]))
    return res


def xrot_matrix(xrot):
    """returns: A matrix that rotates about the x-axis, from positive z towards positive y."""
    Rx = numpy.identity(4, dtype=numpy.float32)
    Rx.itemset((1, 1), math.cos(xrot))
    Rx.itemset((2, 1), -math.sin(xrot))
    Rx.itemset((1, 2), math.sin(xrot))
    Rx.itemset((2, 2), math.cos(xrot))
    return Rx


def yrot_matrix(yrot):
    """returns: A matrix that rotates about the y-axis, from positive z towards positive x."""
    Ry = numpy.identity(4, dtype=numpy.float32)
    Ry.itemset((0, 0), math.cos(-yrot))  # need to be negative for reasons unknown
    Ry.itemset((2, 0), math.sin(-yrot))
    Ry.itemset((0, 2), -math.sin(-yrot))
    Ry.itemset((2, 2), math.cos(-yrot))
    return Ry


def zrot_matrix(zrot):
    """returns: A matrix that rotates about the z-axis, from positive x towards positive y."""
    Rz = numpy.identity(4, dtype=numpy.float32)
    Rz.itemset((0, 0), math.cos(zrot))
    Rz.itemset((1, 0), -math.sin(zrot))
    Rz.itemset((0, 1), math.sin(zrot))
    Rz.itemset((1, 1), math.cos(zrot))
    return Rz


def rotation_matrix(xyz_rot, axis_order=(2, 1, 0)):
    """
        x = pitch
        y = yaw
        z = roll
    """
    Rx = xrot_matrix(xyz_rot[0] if len(xyz_rot) >= 1 else 0)
    Ry = yrot_matrix(xyz_rot[1] if len(xyz_rot) >= 2 else 0)
    Rz = zrot_matrix(xyz_rot[2] if len(xyz_rot) >= 3 else 0)

    mats = [Rx, Ry, Rz]
    M1 = mats[axis_order[0]]
    M2 = mats[axis_order[1]]
    M3 = mats[axis_order[2]]
    return M3.dot(M2).dot(M1)


def get_xyz_rot_to_face_direction(direction, do_yaw=True, do_pitch=True, up_vec=(0, 1, 0)):
    # TODO roll stuff
    xrot, yrot, zrot = (0, 0, 0)
    if do_pitch:
        xz_vs_y = (util.mag((direction[0], direction[2])), direction[1])
        pitch_correction = util.angle_between((1, 0), xz_vs_y, signed=True)
        xrot += pitch_correction

    if do_yaw:
        yaw_correction = -util.angle_between((0, 1), (direction[0], direction[2]), signed=True)
        yrot += yaw_correction

    return (xrot, yrot, zrot)


def ortho_matrix(left, right, bottom, top, near_val, far_val):
    res = numpy.identity(4, dtype=numpy.float32)
    res.itemset((0, 0), float(2 / (right - left)))
    res.itemset((1, 1), float(2 / (top - bottom)))
    res.itemset((2, 2), float(-2 / (far_val - near_val)))

    t_x = -(right + left) / (right - left)
    t_y = -(top + bottom) / (top - bottom)
    t_z = -(far_val + near_val) / (far_val - near_val)
    res.itemset((0, 3), float(t_x))
    res.itemset((1, 3), float(t_y))
    res.itemset((2, 3), float(t_z))

    return res


# yoinked from OpenGL's gluPerspective
def perspective_matrix(fovy, aspect, z_near, z_far):
    f = 1 / math.tan(fovy / 2)
    res = numpy.identity(4, dtype=numpy.float32)
    res.itemset((0, 0), f / aspect)
    res.itemset((1, 1), f)
    res.itemset((2, 2), (z_far + z_near) / (z_near - z_far))
    res.itemset((3, 2), (2 * z_far * z_near) / (z_near - z_far))
    res.itemset((2, 3), -1)
    res.itemset((3, 3), 0)
    return res


# yoinked from gluLookAt
def get_matrix_looking_at(eye_xyz, target_xyz, up_vec):
    F = (
        target_xyz[0] - eye_xyz[0],
        target_xyz[1] - eye_xyz[1],
        target_xyz[2] - eye_xyz[2]
    )
    f = util.set_length(F, 1)
    up_norm = util.set_length(up_vec, 1)
    s = util.cross_prod(f, up_norm)
    u = util.cross_prod(util.set_length(s, 1), f)
    res = numpy.array([[s[0], s[1], s[2], 0],
                       [u[0], u[1], u[2], 0],
                       [-f[0], -f[1], -f[2], 0],
                       [0, 0, 0, 1]], dtype=numpy.float32)
    return res


def get_matrix_looking_at2(eye_xyz, target_xyz, up_vec):
    n = util.set_length(util.sub(eye_xyz, target_xyz), 1)
    u = util.set_length(util.cross_prod(up_vec, n), 1)
    v = util.cross_prod(n, u)
    res = numpy.array([[u[0], u[1], u[2], util.dot_prod(util.negate(u), eye_xyz)],
                       [v[0], v[1], v[2], util.dot_prod(util.negate(v), eye_xyz)],
                       [n[0], n[1], n[2], util.dot_prod(util.negate(n), eye_xyz)],
                       [0, 0, 0, 1]], dtype=numpy.float32)
    return res


def rotation_about_vector(u, rads):
    # Rodrigues rotation formula:
    u = util.set_length(u, 1)
    I = numpy.identity(4, dtype=numpy.float32)
    W = numpy.array([[    0, -u[2],  u[1], 0],
                     [ u[2],     0, -u[0], 0],
                     [-u[1],  u[0],     0, 0],
                     [    0,     0,     0, 1]], dtype=numpy.float32)
    M = I + math.sin(rads) * W + (2 * math.sin(rads / 2) ** 2) * W.dot(W)

    M.itemset((3, 3), 1)
    return M


# yoinked from https://www.learnopencv.com/rotation-matrix-to-euler-angles/
def get_xyz_rotations(R):
    """
    :param R: a rotation matrix.
    :return: the x, y, z rotations of the matrix.
    """
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    if sy <= 0.00001:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0
    else:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    return (x, y, z)


def rotate_to_direction(v1, v2, up_vec):
    """
    :param v1: base unit vector
    :param v2: target unit vector
    :param axial_rot: rotation along the axis of the target vector.
    :return: A rotation matrix that brings v1 to v2, with an optional axial rotation as well.
    """
    z_rot = util.angle_between((v1[0], v1[1]), (v2[0], v2[1]))
    y_rot = util.angle_between((v1[0], v1[2]), (v2[0], v2[2]))
    x_rot = util.angle_between((v1[0], v1[2]), (v2[0], v2[2]))

