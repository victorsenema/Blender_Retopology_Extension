import bpy
from ..core.session import anchors


def anchor_handler(scene):

    for anchor in anchors:
        anchor.update_position()