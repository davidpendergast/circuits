# grafkom1Framework.py
from OpenGL.GL import *  # move this to line 1
from OpenGL.GLU import *
import pygame
import math
import numpy


def load_texture(filename):
    """ This fuctions will return the id for the texture"""
    textureSurface = pygame.image.load(filename)
    textureData = pygame.image.tostring(textureSurface, "RGBA", 1)
    width = textureSurface.get_width()
    height = textureSurface.get_height()
    ID = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, ID)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, textureData)
    return ID


class ObjData(object):

    def __init__(self, fileName, texture_id):
        self.texture_id = texture_id
        self.vertices = []
        self.triangle_faces = []
        self.normals = []
        self.texture_coords = []
        ##
        try:
            f = open(fileName)
            for line in f:
                if line[:2] == "v ":
                    index1 = line.find(" ") + 1
                    index2 = line.find(" ", index1 + 1)
                    index3 = line.find(" ", index2 + 1)

                    vertex = (float(line[index1:index2]), float(line[index2:index3]), float(line[index3:-1]))
                    vertex = (round(vertex[0], 2), round(vertex[1], 2), round(vertex[2], 2))
                    self.vertices.append(vertex)

                elif line[:2] == "vn":
                    index1 = line.find(" ") + 1  # first number index;
                    index2 = line.find(" ", index1 + 1)  # second number index;
                    index3 = line.find(" ", index2 + 1)  # third number index;

                    normal = (float(line[index1:index2]), float(line[index2:index3]), float(line[index3:-1]))
                    normal = (round(normal[0], 2), round(normal[1], 2), round(normal[2], 2))
                    self.normals.append(normal)

                elif line[:2] == "vt":
                    index1 = line.find(" ") + 1  # first number index;
                    index2 = line.find(" ", index1 + 1)  # second number index;
                    coords = (float(line[index1:index2]), float(line[index2:-1]))
                    self.texture_coords.append(coords)

                elif line[0] == "f":
                    i = line.find(" ") + 1
                    face = []
                    for item in range(line.count(" ")):
                        if line.find(" ", i) == -1:
                            face.append(tuple(int(j) for j in line[i:-1].split("/")))
                            break
                        face_text = line[i:line.find(" ", i)]
                        face.append(tuple(int(j) for j in face_text.split("/")))

                        i = line.find(" ", i) + 1
                    self.triangle_faces.append(tuple(face))

            f.close()
        except IOError:
            print(".obj file not found.")

    def render_wireframe(self):
        if len(self.triangle_faces) > 0:
            ##
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glBegin(GL_TRIANGLES)
            for face in self.triangle_faces:
                for f in face:
                    vertexDraw = self.vertices[int(f[0]) - 1]
                    if int(f[0]) % 3 == 1:
                        glColor4f(0.282, 0.239, 0.545, 0.35)
                    elif int(f[0]) % 3 == 2:
                        glColor4f(0.729, 0.333, 0.827, 0.35)
                    else:
                        glColor4f(0.545, 0.000, 0.545, 0.35)
                    glVertex3fv(vertexDraw)
            glEnd()

    def render_texture(self, xform=None):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        if xform is not None:
            glPushMatrix()
            glMultMatrixf(xform)

        glBegin(GL_TRIANGLES)
        for face in self.triangle_faces:
            for f in face:
                vertex = self.vertices[int(f[0]) - 1]
                texture = self.texture_coords[int(f[1]) - 1]
                normal = self.normals[int(f[2]) - 1]
                glTexCoord2fv(texture)
                glNormal3fv(normal)
                glVertex3fv(vertex)
        glEnd()

        if xform is not None:
            glPopMatrix()

        glDisable(GL_TEXTURE_2D)


class Object3D:

    def __init__(self, obj_data: ObjData):
        self.model = obj_data

        self.translation = [0, 0, 0]
        self.rotation = [0, 0, 0]
        self.scale = [1, 1, 1]

    def get_xform(self):
        # translation matrix
        T = numpy.identity(4, dtype=numpy.float32)
        T.itemset((3, 0), self.translation[0])
        T.itemset((3, 1), self.translation[1])
        T.itemset((3, 2), self.translation[2])

        # rotation matrices
        Rx = numpy.identity(4, dtype=numpy.float32)
        Rx.itemset((1, 1), math.cos(self.rotation[0]))
        Rx.itemset((2, 1), -math.sin(self.rotation[0]))
        Rx.itemset((1, 2), math.sin(self.rotation[0]))
        Rx.itemset((2, 2), math.cos(self.rotation[0]))

        Ry = numpy.identity(4, dtype=numpy.float32)
        Ry.itemset((0, 0), math.cos(self.rotation[1]))
        Ry.itemset((2, 0), math.sin(self.rotation[1]))
        Ry.itemset((0, 2), -math.sin(self.rotation[1]))
        Ry.itemset((2, 2), math.cos(self.rotation[1]))

        Rz = numpy.identity(4, dtype=numpy.float32)
        Rz.itemset((0, 0), math.cos(self.rotation[2]))
        Rz.itemset((1, 0), -math.sin(self.rotation[2]))
        Rz.itemset((0, 1), math.sin(self.rotation[2]))
        Rz.itemset((1, 1), math.cos(self.rotation[2]))

        # scale matrix
        S = numpy.identity(4, dtype=numpy.float32)
        S.itemset((0, 0), self.scale[0])
        S.itemset((1, 1), self.scale[1])
        S.itemset((2, 2), self.scale[2])

        return T.dot(Rx).dot(Ry).dot(Rz).dot(S)

    def render_texture(self):
        self.model.render_texture(self.get_xform())


class Scene3D:

    def __init__(self, texture_id):
        self.angle = 0
        self.coordinates = [0, 0, -65]  # [x,y,z]
        self.obj = Object3D(ObjData("assets/3d_scenes/ship.obj", texture_id))

    def render_scene(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.1, 0.1, 0.1, 0.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        #look_dir = (math.sin(math.radians(self.angle)), 0.4, math.cos(math.radians(self.angle)) * -1)
        # coords = self.coordinates

        look_dir = (-0.61, 0.39, -0.69)
        coords = (-4.84, 0, -9.95)
        gluLookAt(0, 0, 0, look_dir[0], look_dir[1], look_dir[2], 0, 1, 0)
        glTranslatef(coords[0], coords[1], coords[2])

        mat = numpy.ndarray([4, 4], dtype=numpy.float32)
        glGetFloatv(GL_MODELVIEW_MATRIX, mat)
        print("GL_MODELVIEW_MATRIX={}".format(mat))

        #self.obj.rotation[0] += 0.01
        #self.obj.rotation[1] += 0.02
        #self.obj.rotation[2] += 0.03
        self.obj.render_texture()

    def move_forward(self, n):
        self.coordinates[2] += n * math.cos(math.radians(self.angle))
        self.coordinates[0] -= n * math.sin(math.radians(self.angle))

    def move_back(self, n):
        self.coordinates[2] -= n * math.cos(math.radians(self.angle))
        self.coordinates[0] += n * math.sin(math.radians(self.angle))

    def move_left(self, n):
        self.coordinates[0] += n * math.cos(math.radians(self.angle))
        self.coordinates[2] += n * math.sin(math.radians(self.angle))

    def move_right(self, n):
        self.coordinates[0] -= n * math.cos(math.radians(self.angle))
        self.coordinates[2] -= n * math.sin(math.radians(self.angle))

    def rotate(self, n):
        self.angle += n


def main():
    pygame.init()
    pygame.display.set_mode((640, 480), pygame.DOUBLEBUF | pygame.OPENGL)
    pygame.display.set_caption("Teddy - Tugas Grafkom 1")
    clock = pygame.time.Clock()

    # Feature checker
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glEnable(GL_CULL_FACE)

    glMatrixMode(GL_PROJECTION)
    gluPerspective(45.0, float(800) / 600, .1, 1000.)

    mat = numpy.ndarray([4, 4], dtype=numpy.float32)
    glGetFloatv(GL_PROJECTION_MATRIX, mat)
    print("GL_PROJECTION_MATRIX={}".format(mat))

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    texture_id = load_texture("assets/textures/ship_texture.png")

    scene = Scene3D(texture_id)

    done = False
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    scene.move_left(10)
                elif event.key == pygame.K_RIGHT:
                    scene.move_right(10)
                elif event.key == pygame.K_UP:
                    scene.move_forward(10)
                elif event.key == pygame.K_DOWN:
                    scene.move_back(10)
                elif event.key == pygame.K_1:
                    scene.rotate(-10)
                elif event.key == pygame.K_2:
                    scene.rotate(10)

        move_speed = 2.5
        rotate_speed = 2

        held = pygame.key.get_pressed()
        if held[pygame.K_e]:
            scene.rotate(rotate_speed)
        if held[pygame.K_q]:
            scene.rotate(-rotate_speed)

        if held[pygame.K_w]:
            scene.move_forward(move_speed)
        if held[pygame.K_a]:
            scene.move_left(move_speed)
        if held[pygame.K_s]:
            scene.move_forward(-move_speed)
        if held[pygame.K_d]:
            scene.move_right(move_speed)

        scene.render_scene()

        pygame.display.flip()
        clock.tick(30)
    pygame.quit()


if __name__ == "__main__":
    main()