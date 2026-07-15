import bpy
import bmesh
from mathutils.bvhtree import BVHTree

from ... import session


class SurfaceProjection:

    def __init__(self):
        self.template = session.template_mesh
        self.target = session.target_mesh
        self.bvh = None

    def build_bvh(self):
        # Build a BVH tree from the target mesh

        bm = bmesh.new()
        bm.from_mesh(self.target.data)
        bm.transform(self.target.matrix_world)

        self.bvh = BVHTree.FromBMesh(bm)

        bm.free()

    def project(self):
        # Project every template vertex onto the target surface

        if self.template is None:
            return

        if self.target is None:
            return

        self.build_bvh()

        mesh = self.template.data

        for vertex in mesh.vertices:

            world_position = self.template.matrix_world @ vertex.co

            location, normal, index, distance = self.bvh.find_nearest(world_position)

            if location is None:
                continue

            vertex.co = self.template.matrix_world.inverted() @ location

        mesh.update()