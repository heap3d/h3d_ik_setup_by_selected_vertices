#!/usr/bin/python
# ================================
# (C)2024 Dmytro Holub
# heap3d@gmail.com
# --------------------------------
# modo python
# create cable setup

import lx
import modo
import modo.constants as c


CABLE_SHAPE_NAME = 'h3d_cable_shape_circle'


def create_cable_shape() -> modo.Item:
    lx.eval('layer.new')
    shape: modo.Item
    shape, = modo.Scene().selectedByType(c.MESH_TYPE)
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


def is_general_curve(mesh):
    curves = mesh.geometry.polygons.iterByType('CURV')
    beziers = mesh.geometry.polygons.iterByType('BEZR')
    bsplines = mesh.geometry.polygons.iterByType('BSPL')

    return any((curves, beziers, bsplines))


def get_cable_shape():
    try:
        return modo.Scene().item(CABLE_SHAPE_NAME)
    except LookupError:
        return create_cable_shape()


def create_cable(curve, shape):
    if not is_general_curve(curve):
        print(f'Cable creation skipped for mesh <{curve.name}>. No curve found.')
        return

    # create curve sweep meshop
    cable_name = f'{curve.name}_cable'
    cable = modo.Scene().addMesh(cable_name)
    cable.select(replace=True)
    lx.eval('select.filepath "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" set')
    lx.eval('select.preset "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" mode:set')
    lx.eval('preset.do')
    curve_sweep, = modo.Scene().selectedByType(itype='curve.sweep')
    lx.eval(f'item.link curve.sweep.path {curve.id} {curve_sweep.id} posT:0 replace:false')
    lx.eval(f'item.link curve.sweep.prof {shape.id} {curve_sweep.id} posT:0 replace:false')
    curve_sweep.select(replace=True)
    lx.eval('item.channel (anySweeper)$extrudeShape linked')
    lx.eval('item.channel (anySweeper)$useSize false')
    # lx.eval(f'item.channel (anySweeper)$size {cable_shape_size}')
    # lx.eval(f'item.channel (anySweeper)$steps {cable_steps}')
    # lx.eval(f'item.channel (anySweeper)$flip {flip}')
    # create material tag meshop
    cable.select(replace=True)
    lx.eval('select.filepath "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" set')
    lx.eval('select.preset "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" mode:set')
    lx.eval('preset.do')
    # lx.eval(f'item.channel pmodel.materialTag.item$materialName {material_tag}')
    # create set polygon type meshop
    lx.eval('select.filepath "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" set')
    lx.eval('select.preset "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" mode:set')
    lx.eval('preset.do')
    lx.eval('item.channel poly.setType.meshop.item$type subd')
    # create controls
    cable.select(replace=True)
    lx.eval('channel.create shapesize distance username:"shape size"')
    lx.eval('channel.create flip boolean username:flip')
    lx.eval('channel.create cablesteps integer scalar false 0.0 false 0.0 0.0 username:"cable steps"')
    lx.eval('channel.create materialtag string username:"material tag"')
    lx.eval('')
    lx.eval('')
    lx.eval('')


def main():
    selected_meshes = modo.Scene().selectedByType(itype=c.MESH_TYPE)
    cable_shape = get_cable_shape()
    for mesh in selected_meshes:
        create_cable(curve=mesh, shape=cable_shape)


if __name__ == '__main__':
    main()
