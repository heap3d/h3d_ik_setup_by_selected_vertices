#!/usr/bin/python
# ================================
# (C)2024 Dmytro Holub
# heap3d@gmail.com
# --------------------------------
# modo python
# setup IK by selected vertices

from typing import Union

import modo
import modo.constants as c
import lx

from h3d_utilites.scripts.h3d_utils import parent_items_to, replace_file_ext
from h3d_utilites.scripts.h3d_debug import H3dDebug


def new_loc_at_vert(vertex: modo.meshgeometry.MeshVertex, parent: Union[modo.Item, None]) -> modo.Item:
    locator = modo.Scene().addItem(itype=c.LOCATOR_TYPE)
    lx.eval('item.channel locator$size 0.0')
    locator.position.set(vertex.position)
    if not parent:
        return locator
    parent_items_to(items=[locator], parent=parent)
    return locator


def make_ik_setup(mesh):
    # Create locators
    locator = None
    locators = []
    weight_containers = []
    vertices = mesh.geometry.vertices.selected
    h3dd.print_items(vertices, 'vertices:')
    if not vertices:
        h3dd.print_debug(f'no vertices selected in mesh:<{mesh.name}>')
    for vertex in vertices:
        locator = new_loc_at_vert(vertex=vertex, parent=locator)
        locators.append(locator)
        h3dd.print_debug(f'locator:{locator.name}')
        h3dd.print_items(locators, 'locators:')
        locator.name = f'{mesh.name}_joint'
        h3dd.print_debug(f'joint:{locator.name}')
        lx.eval('select.typeFrom vertex')
        vertex.select(replace=True)
        lx.eval('anim.setup on')
        lx.eval('weightCont.create')
        weight_cont, = modo.Scene().selectedByType(itype=c.WEIGHTCONTAINER_TYPE)
        weight_containers.append(weight_cont)
        gen_influence = modo.Scene().addItem(itype=c.GENINFLUENCE_TYPE)
        lx.eval(f'item.link genInfluence {weight_cont.id} {gen_influence.id} replace:true')
        lx.eval(f'item.link $infeff {locator.id} {gen_influence.id} posT:0 replace:false')
        # lx.eval('')
        lx.eval('anim.setup off')

    lx.eval('anim.setup on')
    # Align locators
    modo.Scene().deselect()
    for loc_sel in locators:
        loc_sel.select()
    lx.eval('!item.align orient:xyz')

    # Apply IK
    joint_first = locators[0]
    joint_last = locators[-1]

    joint_first.select(replace=True)
    joint_last.select()
    lx.eval('ikfb.assign')
    lx.eval('ikfb.goal')

    lx.eval('anim.setup off')

    # group IK set
    modo.Scene().deselect()
    for item in weight_containers:
        item.select()
    locators[0].select()
    lx.eval('layer.groupSelected')
    group, = modo.Scene().selectedByType(itype=c.GROUPLOCATOR_TYPE)
    group.name = f'{mesh.name}_IK_set'


def main():
    meshes = []
    meshes = modo.Scene().selectedByType(itype=c.MESH_TYPE)
    h3dd.print_items(meshes, 'selected meshes:')
    if not meshes:
        for mesh in modo.Scene().meshes:
            if mesh.geometry.vertices.selected:  # type: ignore
                meshes.append(mesh)
        h3dd.print_items(meshes, 'selected vertices in meshes:')

    if not meshes:
        print('Please select any vertices to proceed')
        return

    for mesh in meshes:
        make_ik_setup(mesh)


if __name__ == '__main__':
    h3dd = H3dDebug(
        enable=False, file=replace_file_ext(modo.Scene().filename, ".log")
    )
    main()
