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
from typing import Union
import inspect

from h3d_utilites.scripts.h3d_utils import replace_file_ext, is_preset_browser_opened, display_preset_browser
from h3d_utilites.scripts.h3d_debug import H3dDebug


CABLE_SHAREABLE_PROFILE_NAME = 'h3d_cable_shareable_profile'
CABLE_BASENAME_SUFFIX = '_cable'
PROFILE_BASENAME_SUFFIX = '_profile'
DELIMITER = ':'

DEFAULT_CABLE_BASENAME = ''
DEFAULT_DIAMETER = 0.01
DEFAULT_COMPENSATION = 1.2308
DEFAULT_MATERIAL_TAG = ''
DEFAULT_PATH_STEPS = 24
DEFAULT_POLYGON_TYPE = 1
DEFAULT_FLIP = True
DEFAULT_SIDES = 6

ID_DIAMETER = 'd'
ID_STEPS = 's'
ID_FLIP = 'f'
ID_POLYGON_TYPE = 't'
ID_SIDES = 'p'

CH_DIAMETER = 'ctrldiameter'
CH_DIAMETER_USERNAME = 'Diameter'
CH_COMP = 'ctrlcompensation'
CH_COMPENSATION_USERNAME = 'Diameter Compensation'
CH_STEPS = 'ctrlsteps'
CH_STEPS_USERNAME = 'Steps'
CH_SIDES = 'ctrlsides'
CH_SIDES_USERNAME = 'Sides'
CH_PTAG = 'ctrlmaterialtag'
CH_MATERIAL_TAG_USERNAME = 'Material Name'
CH_FLIP = 'ctrlflip'
CH_FLIP_USERNAME = 'Flip'
CH_POLYGON_TYPE = 'ctrlpolytype'
CH_POLYGON_TYPE_USERNAME = 'Polygon Type (0-2)'

CMD_INDEPENDENT_PROFILE = 'independent'

HIGHLIGHT_COLOR = 'orange'


class CableParams:
    diameter: float = DEFAULT_DIAMETER
    compensation: float = DEFAULT_COMPENSATION
    polygon_type: int = DEFAULT_POLYGON_TYPE
    steps: float = DEFAULT_PATH_STEPS
    sides = DEFAULT_SIDES
    flip: bool = True
    material_name: str = DEFAULT_MATERIAL_TAG
    basename = DEFAULT_CABLE_BASENAME


class CableLive:
    def __init__(self, mesh: modo.Item) -> None:
        self.params: CableParams = CableParams()
        self.curve_mesh: Union[modo.Item, None] = None
        self.cable_mesh: Union[modo.Item, None] = None
        self.profile_mesh: Union[modo.Item, None] = None
        self.prim_cylinder_item: Union[modo.Item, None] = None
        self.curve_sweep_mop: Union[modo.Item, None] = None
        self.set_polygon_type_mop: Union[modo.Item, None] = None
        self.material_tag_mop: Union[modo.Item, None] = None
        self.shareable_profile_mesh: Union[modo.Item, None] = None
        self.math_mult_chmod: Union[modo.Item, None] = None

        self.detect_mesh_setup(mesh)
        self.remove_cable_setup()

    def detect_mesh_setup(self, mesh: modo.Item):
        if CableLive.is_general_curve(mesh):
            self.curve_mesh = mesh
        ...

    def remove_cable_setup(self):
        modo.Scene().removeItems(self.cable_mesh)
        self.cable_mesh = None
        modo.Scene().removeItems(self.curve_sweep_mop)
        self.curve_sweep_mop = None
        modo.Scene().removeItems(self.set_polygon_type_mop)
        self.set_polygon_type_mop = None
        modo.Scene().removeItems(self.material_tag_mop)
        self.material_tag_mop = None
        modo.Scene().removeItems(self.shareable_profile_mesh)
        self.shareable_profile_mesh = None
        modo.Scene().removeItems(self.math_mult_chmod)
        self.math_mult_chmod = None

    @staticmethod
    def is_general_curve(mesh: modo.Item) -> bool:
        curves = mesh.geometry.polygons.iterByType('CURV')
        beziers = mesh.geometry.polygons.iterByType('BEZR')
        bsplines = mesh.geometry.polygons.iterByType('BSPL')

        return any((curves, beziers, bsplines))

    def create_prim_cylinder_item(self) -> modo.Item:
        h3dd.print_debug(f'{inspect.currentframe()}')
        is_preset_browser = is_preset_browser_opened()
        if not is_preset_browser:
            display_preset_browser(True)
        lx.eval('select.preset "[itemtypes]:MeshOperations/create/primitives/prim.cylinder.item.itemtype" mode:set')
        lx.eval('select.filepath "[itemtypes]:MeshOperations/create/primitives/prim.cylinder.item.itemtype" set')
        lx.eval('preset.do')
        lx.eval('item.channel prim.cylinder.item$cenX 0.0')
        lx.eval('item.channel prim.cylinder.item$cenY 0.0')
        lx.eval('item.channel prim.cylinder.item$cenZ 0.0')
        lx.eval(f'item.channel prim.cylinder.item$sizeX {self.params.diameter / 2}')
        lx.eval('item.channel prim.cylinder.item$sizeY 0.0')
        lx.eval(f'item.channel prim.cylinder.item$sizeZ {self.params.diameter / 2}')
        lx.eval('item.channel prim.cylinder.item$segments 1')
        lx.eval(f'item.channel prim.cylinder.item$sides {self.params.sides}')
        lx.eval('item.channel prim.cylinder.item$polType face')
        display_preset_browser(is_preset_browser)

        return modo.Scene().selectedByType('prim.cylinder.item')[0]

    def get_prim_cylinder_item(self, profile_mesh: modo.Item) -> modo.Item:
        h3dd.print_debug(f'{inspect.currentframe()}')
        h3dd.print_debug(f'{profile_mesh.name=} {profile_mesh.id=}', 1)
        deformers: list[modo.Item] = profile_mesh.itemGraph('deformers').reverse()  # type: ignore
        h3dd.print_items(deformers, 'deformers', 1)
        for deformer in deformers:
            if deformer.type == 'prim.cylinder.item':
                h3dd.print_debug(f'connected primitive found: {deformer=}', 1)
                return deformer

        h3dd.print_debug('no connected primitive found', 1)
        connected_prim = self.create_prim_cylinder_item()
        h3dd.print_debug(f'new primitive created: {connected_prim.name=} {connected_prim.id=}', 1)
        self.link_mesh_to_prim(profile_mesh, connected_prim)
        self.create_sides_control(profile_mesh, connected_prim)

        return connected_prim

    def create_sides_control(self, profile_mesh: modo.Item, connected_prim: modo.Item):
        h3dd.print_debug(f'{inspect.currentframe()}')
        profile_mesh.select(replace=True)
        h3dd.print_debug(f'profile_mesh selected: {profile_mesh.name=} {profile_mesh.id=}', 1)
        lx.eval(f'channel.create {CH_SIDES} integer username:"{CH_SIDES_USERNAME}"')
        h3dd.print_debug(f'channel created {CH_SIDES=} {CH_SIDES_USERNAME=}', 1)
        lx.eval(f'item.channel {CH_SIDES} "{self.params.sides}"')
        h3dd.print_debug(f'value set {CH_SIDES=} {self.params.sides=}', 1)
        lx.eval(f'channel.link add {{{profile_mesh.id}:{CH_SIDES}}} {{{connected_prim.id}:sides}}')
        h3dd.print_debug(f'channel linked {profile_mesh.id=}:{CH_SIDES=} {connected_prim.id=}:sides', 1)

    def link_mesh_to_prim(self, profile_mesh: modo.Item, connected_prim: modo.Item):
        h3dd.print_debug(f'{inspect.currentframe()}')
        lx.eval(f'item.link genInfluence {profile_mesh.id} {connected_prim.id} posT:0 replace:false')
        h3dd.print_debug(f'new primitive linked {profile_mesh.id=} {connected_prim.id=}', 1)

    def new_shareable_profile(self, name: str) -> modo.Item:
        h3dd.print_debug(f'{inspect.currentframe()}')
        lx.eval('layer.new')
        lx.eval(f'item.editorColor {HIGHLIGHT_COLOR}')
        profile = modo.Scene().selectedByType(c.MESH_TYPE)[0]
        if not profile:
            raise RuntimeError('Error creating profile mesh')

        self.prim_cylinder_item = self.create_prim_cylinder_item()
        h3dd.print_debug(f'prim_cylinder created: {self.prim_cylinder_item.name=} {self.prim_cylinder_item.id=}')
        self.link_mesh_to_prim(profile, self.prim_cylinder_item)
        self.create_sides_control(profile, self.prim_cylinder_item)
        profile.name = name

        return profile

    def get_shareable_profile(self, name: str) -> modo.Item:
        h3dd.print_debug(f'{inspect.currentframe()}')
        try:
            h3dd.print_debug('try block', 1)
            shareable_profile_mesh = modo.Scene().item(name)
            self.prim_cylinder_item = self.get_prim_cylinder_item(shareable_profile_mesh)
            return shareable_profile_mesh
        except LookupError:
            h3dd.print_debug('except block', 1)
            shareable_profile_mesh = self.new_shareable_profile(name)
            self.prim_cylinder_item = self.get_prim_cylinder_item(shareable_profile_mesh)
            return shareable_profile_mesh

    @staticmethod
    def meters(mm: Union[str, float, int]) -> float:
        return float(mm) / 1000

    def decode_parameters(self) -> None:
        if not self.curve_mesh:
            raise ValueError(f'{self.curve_mesh=}')
        # get basename and a string between square brackets <basename>[<parameters>]
        pattern = r'(.*)\[(.*)\]'
        matches = re.findall(pattern, self.curve_mesh.name)
        if not matches:
            tokens = []
        else:
            self.params.basename = matches[0][0].strip()
            tokens = matches[0][1].split(DELIMITER)

        for token in tokens:
            token_stripped = token.lower().strip()
            if token_stripped.isdigit():
                self.params.diameter = self.meters(token_stripped)
            elif token_stripped.startswith(ID_DIAMETER):
                self.params.diameter = self.meters(token_stripped[len(ID_DIAMETER):])
            elif token_stripped.startswith(ID_STEPS):
                self.params.steps = int(token_stripped[len(ID_STEPS):])
            elif token_stripped.startswith(ID_FLIP):
                if token_arg := token_stripped[len(ID_FLIP):]:
                    self.params.flip = int(token_arg) != 0
                else:
                    self.params.flip = True
            elif token_stripped.startswith(ID_POLYGON_TYPE):
                self.params.polygon_type = int(token_stripped[len(ID_POLYGON_TYPE):])
            elif token_stripped.startswith(ID_SIDES):
                self.params.sides = int(token_stripped[len(ID_SIDES):])
            else:
                self.params.material_name = token_stripped

    def create_cable_mesh(self) -> None:
        cable_name = f'{self.params.basename}{CABLE_BASENAME_SUFFIX}'
        self.cable_mesh = modo.Scene().addMesh(cable_name)

    def create_curve_sweep_mop(self) -> None:
        if not self.cable_mesh:
            raise ValueError(f'{self.cable_mesh=}')
        is_preset_browser = is_preset_browser_opened()
        if not is_preset_browser:
            display_preset_browser(True)
        self.cable_mesh.select(replace=True)
        lx.eval('select.filepath "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" set')
        lx.eval('select.preset "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" mode:set')
        lx.eval('preset.do')
        self.curve_sweep_mop = modo.Scene().selectedByType(itype='curve.sweep')[0]
        display_preset_browser(is_preset_browser)
        if not self.curve_sweep_mop:
            raise ValueError(f'{self.curve_sweep_mop=}')
        self.curve_sweep_mop.select(replace=True)
        lx.eval('item.channel (anySweeper)$extrudeShape linked')
        lx.eval('item.channel (anySweeper)$useSize false')

    def create_set_polygon_type_mop(self) -> None:
        is_preset_browser = is_preset_browser_opened()
        if not is_preset_browser:
            display_preset_browser(True)
        lx.eval('select.filepath "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" set')
        lx.eval('select.preset "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" mode:set')
        lx.eval('preset.do')
        self.set_polygon_type_mop = modo.Scene().selectedByType(itype='poly.setType.meshop.item')[0]
        display_preset_browser(is_preset_browser)

    def create_material_tag_mop(self) -> None:
        if not self.cable_mesh:
            raise ValueError(f'{__name__}: {self.cable_mesh=}')
        self.cable_mesh.select(replace=True)
        self.cable_mesh.select(replace=True)
        is_preset_browser = is_preset_browser_opened()
        if not is_preset_browser:
            display_preset_browser(True)
        lx.eval('select.filepath "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" set')
        lx.eval('select.preset "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" mode:set')
        lx.eval('preset.do')
        self.material_tag_mop = modo.Scene().selectedByType(itype='pmodel.materialTag.item')[0]
        display_preset_browser(is_preset_browser)

    def create_math_multiply_channel_mod(self) -> None:
        is_preset_browser = is_preset_browser_opened()
        if not is_preset_browser:
            display_preset_browser(True)
        lx.eval('select.filepath "[itemtypes]:ChannelModifiers/math/cmMathBasic(mul).itemtype" set')
        lx.eval('select.preset "[itemtypes]:ChannelModifiers/math/cmMathBasic(mul).itemtype" mode:set')
        lx.eval('preset.do')
        self.math_mult_chmod = modo.Scene().selectedByType(itype='cmMathBasic')[0]
        display_preset_browser(is_preset_browser)

    def create_cable_controls(self) -> None:
        if not self.cable_mesh:
            raise ValueError(f'{self.cable_mesh=}')
        self.cable_mesh.select(replace=True)
        lx.eval(f'channel.create {CH_DIAMETER} distance username:"{CH_DIAMETER_USERNAME}"')
        lx.eval(f'channel.create {CH_COMP} percent username:"{CH_COMPENSATION_USERNAME}"')
        lx.eval(f'channel.create {CH_POLYGON_TYPE} integer username:"{CH_POLYGON_TYPE_USERNAME}"')
        lx.eval(f'channel.create {CH_STEPS} integer username:"{CH_STEPS_USERNAME}"')
        lx.eval(f'channel.create {CH_FLIP} boolean username:"{CH_FLIP_USERNAME}"')
        lx.eval(f'channel.create {CH_PTAG} string username:"{CH_MATERIAL_TAG_USERNAME}"')

    def link_cable_channels(self) -> None:
        if not self.curve_sweep_mop:
            raise ValueError(f'{self.curve_sweep_mop=}')
        if not self.cable_mesh:
            raise ValueError(f'{self.cable_mesh=}')
        if not self.curve_mesh:
            raise ValueError(f'{self.curve_mesh=}')
        if not self.profile_mesh:
            raise ValueError(f'{self.profile_mesh=}')
        if not self.math_mult_chmod:
            raise ValueError(f'{self.math_mult_chmod=}')
        if not self.material_tag_mop:
            raise ValueError(f'{self.material_tag_mop=}')
        if not self.set_polygon_type_mop:
            raise ValueError(f'{self.set_polygon_type_mop=}')

        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_DIAMETER}}} {{{self.math_mult_chmod.id}:input1}}')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_COMP}}} {{{self.math_mult_chmod.id}:input2}}')
        lx.eval(f'channel.link replace {{{self.math_mult_chmod.id}:output}} {{{self.curve_sweep_mop.id}:size}}')
        lx.eval(f'item.link curve.sweep.path {self.curve_mesh.id} {self.curve_sweep_mop.id} posT:0 replace:false')
        lx.eval(f'item.link curve.sweep.prof {self.profile_mesh.id} {self.curve_sweep_mop.id} posT:0 replace:false')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_STEPS}}} {{{self.curve_sweep_mop.id}:steps}}')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_FLIP}}} {{{self.curve_sweep_mop.id}:flip}}')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_POLYGON_TYPE}}} {{{self.set_polygon_type_mop.id}:type}}')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_PTAG}}} {{{self.material_tag_mop.id}:materialName}}')

    def set_cable_control_channels(self) -> None:
        lx.eval(f'item.channel {CH_DIAMETER} "{self.params.diameter}"')
        lx.eval(f'item.channel {CH_COMP} "{self.params.compensation}"')
        lx.eval(f'item.channel {CH_POLYGON_TYPE} "{self.params.polygon_type}"')
        lx.eval(f'item.channel {CH_STEPS} "{self.params.steps}"')
        lx.eval(f'item.channel {CH_FLIP} "{self.params.flip}"')
        lx.eval(f'item.channel {CH_PTAG} "{self.params.material_name}"')

    def create_live_cable(self, is_profile_independent: bool) -> None:
        h3dd.print_debug(f'{inspect.currentframe()}')
        if not self.curve_mesh:
            raise ValueError(f'{self.curve_mesh=}')
        if not CableLive.is_general_curve(self.curve_mesh):
            print(f'Cable creation skipped for mesh <{self.curve_mesh.name}>. No curve found.')
            return

        # store preset browser status
        preset_browser_opened = is_preset_browser_opened()

        # open preset browser if not opened
        if not preset_browser_opened:
            display_preset_browser(True)

        self.decode_parameters()

        if not is_profile_independent:
            h3dd.print_debug('not is_profile_independent', 1)
            self.profile_mesh = self.get_shareable_profile(CABLE_SHAREABLE_PROFILE_NAME)
        else:
            h3dd.print_debug('is_profile_independent', 1)
            self.profile_mesh = self.new_shareable_profile(f'{self.params.basename}{PROFILE_BASENAME_SUFFIX}')

        self.create_cable_mesh()
        self.create_curve_sweep_mop()
        self.create_material_tag_mop()
        self.create_set_polygon_type_mop()
        self.create_math_multiply_channel_mod()
        self.create_cable_controls()
        self.link_cable_channels()
        self.set_cable_control_channels()

        # restore preset browser status
        display_preset_browser(preset_browser_opened)


def main():
    is_profile_independent: bool = False
    selected_meshes = modo.Scene().selectedByType(itype=c.MESH_TYPE)
    args = lx.args()
    if args:
        if CMD_INDEPENDENT_PROFILE in args:
            is_profile_independent = True
    # cable_shape = CableLive.get_shareable_cable_shape()
    # visible_channel = cable_shape.channel('visible')
    # if visible_channel:
    #     visible_channel.set('allOff')
    cables: list[CableLive] = []
    for mesh in selected_meshes:
        cable = CableLive(mesh)
        cable.create_live_cable(is_profile_independent)
        cables.append(cable)

    modo.Scene().deselect()
    if not cables:
        for item in selected_meshes:
            item.select()
        return

    for cable in cables:
        if cable.cable_mesh:
            cable.cable_mesh.select()
        lx.eval(f'item.editorColor {HIGHLIGHT_COLOR}')


if __name__ == '__main__':
    h3dd = H3dDebug(enable=True, file=replace_file_ext(modo.Scene().filename, ".log"))
    main()
