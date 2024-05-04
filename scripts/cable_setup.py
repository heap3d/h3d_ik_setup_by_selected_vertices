#!/usr/bin/python
# ================================
# (C)2024 Dmytro Holub
# heap3d@gmail.com
# --------------------------------
# modo python
# create cable setup
# usage:
# - select curve mesh
# - run command

import lx
import modo
import modo.constants as c
import re

from h3d_utilites.scripts.h3d_utils import replace_file_ext
from h3d_utilites.scripts.h3d_debug import H3dDebug


CABLE_SHAPE_NAME = 'h3d_cable_shape_circle'
DEFAULT_DIAMETER = 0.01
DEFAULT_STEPS = 24


class LiveCable:
    def __init__(self, mesh: modo.Item) -> None:
        self.shape_size = None
        self.cable_steps = None
        self.flip = None
        self.material_tag = None

    def decode_name(self):
        ...

    def encode_name(self):
        ...

    def generate_cable(self):
        ...

    def strip_cable_meshops(self):
        ...

    @staticmethod
    def create_cable_shape() -> modo.Item:
        lx.eval('layer.new')
        shape: modo.Item
        shape = scene.selectedByType(c.MESH_TYPE)[0]
        if not shape:
            raise RuntimeError('Error creating cable shape')
        lx.eval('tool.set prim.cylinder on')
        lx.eval('tool.setAttr prim.cylinder cenX 0.0')
        lx.eval('tool.setAttr prim.cylinder cenY 0.0')
        lx.eval('tool.setAttr prim.cylinder cenZ 0.0')
        lx.eval('tool.setAttr prim.cylinder sizeX 0.5')
        lx.eval('tool.setAttr prim.cylinder sizeY 0.0')
        lx.eval('tool.setAttr prim.cylinder sizeZ 0.5')
        lx.eval('tool.setAttr prim.cylinder axis y')
        lx.eval('tool.setAttr prim.cylinder sides 8')
        lx.eval('tool.doApply')
        lx.eval('tool.set prim.cylinder off 0')
        shape.name = CABLE_SHAPE_NAME

        return shape

    @staticmethod
    def get_cable_shape():
        try:
            return scene.item(CABLE_SHAPE_NAME)

        except LookupError:
            return LiveCable.create_cable_shape()

    @staticmethod
    def is_general_curve(mesh):
        curves = mesh.geometry.polygons.iterByType('CURV')
        beziers = mesh.geometry.polygons.iterByType('BEZR')
        bsplines = mesh.geometry.polygons.iterByType('BSPL')

        return any((curves, beziers, bsplines))


def decode_name(name):
    pattern = r".*\[(\d+)?\s?:?\s?(.*)\]"
    result: list[str] = re.findall(pattern, name)
    if not result:
        h3dd.print_debug(f'not result: {result = }')
        return DEFAULT_DIAMETER, ''

    if len(result) == 1:
        if result[0].isdigit():
            h3dd.print_debug(f'{len(result) = } {result = }')
            return float(result[0]), ''

        else:
            h3dd.print_debug(f'else len: {len(result) = } {result = }')
            return DEFAULT_DIAMETER, result[0]

    else:
        h3dd.print_debug(f'else: {result = }')
        return float(result[0]), result[1]


def create_cable(curve_mesh, shape):
    if not LiveCable.is_general_curve(curve_mesh):
        print(f'Cable creation skipped for mesh <{curve_mesh.name}>. No curve found.')
        return
    # stroe preset browser status
    preset_browser_opened = lx.eval(
        'layout.createOrClose PresetBrowser presetBrowserPalette ?'
    )
    if not preset_browser_opened:
        lx.eval(
            'layout.createOrClose PresetBrowser presetBrowserPalette true Presets '
            'width:800 height:600 persistent:true style:palette'
        )
    # create curve sweep meshop
    cable_name = f'{curve_mesh.name}_cable'
    cable = scene.addMesh(cable_name)
    cable.select(replace=True)
    lx.eval(
        'select.filepath "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" set'
    )
    lx.eval(
        'select.preset "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" mode:set'
    )
    lx.eval('preset.do')
    curve_sweep = scene.selectedByType(itype='curve.sweep')[0]
    lx.eval(
        f'item.link curve.sweep.path {curve_mesh.id} {curve_sweep.id} posT:0 replace:false'
    )
    lx.eval(
        f'item.link curve.sweep.prof {shape.id} {curve_sweep.id} posT:0 replace:false'
    )
    curve_sweep.select(replace=True)
    lx.eval('item.channel (anySweeper)$extrudeShape linked')
    lx.eval('item.channel (anySweeper)$useSize false')
    # create material tag meshop
    cable.select(replace=True)
    lx.eval(
        'select.filepath "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" set'
    )
    lx.eval(
        'select.preset "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" mode:set'
    )
    lx.eval('preset.do')
    material_tag_node = scene.selectedByType(itype='pmodel.materialTag.item')[0]
    # create set polygon type meshop
    lx.eval(
        'select.filepath "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" set'
    )
    lx.eval(
        'select.preset "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" mode:set'
    )
    lx.eval('preset.do')
    lx.eval('item.channel poly.setType.meshop.item$type subd')
    # create controls
    diameter, material_tag_name = decode_name(curve_mesh.name)
    material_tag_name = material_tag_name.strip()
    cable.select(replace=True)
    lx.eval(
        f'channel.create shapesize distance default:{diameter} username:"shape size"'
    )
    lx.eval('channel.create flip boolean username:flip')
    lx.eval(
        'channel.create cablesteps integer scalar false 0.0 false 0.0 0.0 username:"cable steps"'
    )
    lx.eval(f'item.channel cablesteps "{DEFAULT_STEPS}"')
    lx.eval('channel.create materialtag string username:"material tag"')
    lx.eval(f'item.channel materialtag "{material_tag_name}"')
    lx.eval(f'channel.link add {{{cable.id}:shapesize}} {{{curve_sweep.id}:size}}')
    lx.eval(f'channel.link add {{{cable.id}:flip}} {{{curve_sweep.id}:flip}}')
    lx.eval(f'channel.link add {{{cable.id}:cablesteps}} {{{curve_sweep.id}:steps}}')
    lx.eval(
        f'channel.link add {{{cable.id}:materialtag}} {{{material_tag_node.id}:materialName}}'
    )
    # restore preset browser status
    if not preset_browser_opened:
        lx.eval(
            'layout.createOrClose PresetBrowser presetBrowserPalette false Presets width:800 height:600 '
            'persistent:true style:palette'
        )


def main():
    selected_meshes = scene.selectedByType(itype=c.MESH_TYPE)
    for mesh in selected_meshes:
        LiveCable(mesh=mesh).generate_cable()


if __name__ == '__main__':
    scene = modo.Scene()
    h3dd = H3dDebug(enable=True, file=replace_file_ext(scene.filename, ".log"))
    main()
