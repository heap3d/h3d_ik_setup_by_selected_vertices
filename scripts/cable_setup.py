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
DEFAULT_MATERIAL = ''
DEFAULT_STEPS = 24
MAP_DIAMETER = 'diameter'
MAP_STEPS = 'steps'
MAP_FLIP = 'flip'
MAP_MATERIAL = 'material'
MAP_PROFILE_SIDES = 'sides'
MAP_POLYGON_TYPE = 'type'
MAP_DIAMETER_COMPENSATION = 'comp'
DELIMITER = ':'
ID_DIAMETER = 'd'
ID_STEPS = 's'
ID_FLIP = 'f'
ID_PROFILE_SIDES = 'p'
ID_POLYGON_TYPE = 't'
ID_DIAMETER_COMPENSATION = 'c'
CABLE_NAME_SUFFIX = '_cable'


class CableLive:
    def __init__(self, mesh: modo.Item) -> None:
        self.shape_size = DEFAULT_DIAMETER
        self.cable_steps = DEFAULT_STEPS
        self.flip = False
        self.material_tag = ''

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
        (shape,) = scene.selectedByType(c.MESH_TYPE)
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
            return CableLive.create_cable_shape()

    @staticmethod
    def is_general_curve(mesh):
        curves = mesh.geometry.polygons.iterByType('CURV')
        beziers = mesh.geometry.polygons.iterByType('BEZR')
        bsplines = mesh.geometry.polygons.iterByType('BSPL')

        return any((curves, beziers, bsplines))


def meters(mm_str):
    return float(mm_str) / 1000


def decode_name(name):
    pattern = r'(.*)\[(.*)\]'
    matches = re.findall(pattern, name)
    parameters = {
        MAP_DIAMETER: DEFAULT_DIAMETER,
        MAP_MATERIAL: DEFAULT_MATERIAL,
        MAP_STEPS: DEFAULT_STEPS,
        MAP_FLIP: False,
    }
    if not matches:
        mesh_name = name
        tokens = ''
    else:
        mesh_name = matches[0][0]
        tokens = matches[0][1].split(':')
    # tokens: str = name.split(':')
    for token in tokens:
        value = token.strip()
        if value.isdigit() or value.startswith(ID_DIAMETER):
            parameters[MAP_DIAMETER] = meters(value)
        elif value.startswith(ID_STEPS):
            parameters[MAP_STEPS] = int(value[1:])
        elif value == ID_FLIP:
            parameters[MAP_FLIP] = True
        else:
            parameters[MAP_MATERIAL] = value

    return *parameters.values(), mesh_name


def create_cable(curve_mesh, shape):
    if not CableLive.is_general_curve(curve_mesh):
        print(f'Cable creation skipped for mesh <{curve_mesh.name}>. No curve found.')
        return
    # store preset browser status
    preset_browser_opened = lx.eval(
        'layout.createOrClose PresetBrowser presetBrowserPalette ?'
    )
    if not preset_browser_opened:
        lx.eval(
            'layout.createOrClose PresetBrowser presetBrowserPalette true Presets '
            'width:800 height:600 persistent:true style:palette'
        )
    # get cable generation parameters
    diameter, material_tag_name, steps, flip, name_str = decode_name(curve_mesh.name)
    # create curve sweep meshop
    cable_name = f'{name_str.strip()}{CABLE_NAME_SUFFIX}'
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
    # create math multiply channel modifier
    lx.eval('select.filepath "[itemtypes]:ChannelModifiers/math/cmMathBasic(mul).itemtype" set')
    lx.eval('select.preset "[itemtypes]:ChannelModifiers/math/cmMathBasic(mul).itemtype" mode:set')
    lx.eval('preset.do')
    math_mult = scene.selectedByType(itype='cmMathBasic')[0]
    # create controls
    cable.select(replace=True)
    lx.eval(
        f'channel.create shapesize distance default:{diameter} username:"shape size"'
    )
    lx.eval('channel.create shapescale percent default:112.0 username:"shape compensation"')
    lx.eval(
        'channel.create cablesteps integer scalar false 0.0 false 0.0 0.0 username:"cable steps"'
    )
    lx.eval(f'channel.create flip boolean default:{float(flip)} username:flip')
    lx.eval(f'item.channel cablesteps "{steps}"')
    lx.eval('channel.create materialtag string username:"material tag"')
    lx.eval(f'item.channel materialtag "{material_tag_name}"')
    lx.eval(f'channel.link add {{{cable.id}:flip}} {{{curve_sweep.id}:flip}}')
    lx.eval(f'channel.link add {{{cable.id}:cablesteps}} {{{curve_sweep.id}:steps}}')
    lx.eval(
        f'channel.link add {{{cable.id}:materialtag}} {{{material_tag_node.id}:materialName}}'
    )
    lx.eval(f'channel.link add {{{cable.id}:shapescale}} {{{math_mult.id}:input2}}')
    lx.eval(f'channel.link add {{{cable.id}:shapesize}} {{{math_mult.id}:input1}}')
    lx.eval(f'channel.link replace {{{math_mult.id}:output}} {{{curve_sweep.id}:size}}')

    # restore preset browser status
    if not preset_browser_opened:
        lx.eval(
            'layout.createOrClose PresetBrowser presetBrowserPalette false Presets width:800 height:600 '
            'persistent:true style:palette'
        )


def main():
    selected_meshes = scene.selectedByType(itype=c.MESH_TYPE)
    cable_shape = CableLive.get_cable_shape()
    visible_channel = cable_shape.channel('visible')
    if visible_channel:
        visible_channel.set('allOff')
    for mesh in selected_meshes:
        # function to create live cable
        create_cable(curve_mesh=mesh, shape=cable_shape)


if __name__ == '__main__':
    scene = modo.Scene()
    h3dd = H3dDebug(enable=False, file=replace_file_ext(scene.filename, ".log"))
    main()
