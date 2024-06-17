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
from dataclasses import dataclass
from typing import Union

from h3d_utilites.scripts.h3d_utils import replace_file_ext
from h3d_utilites.scripts.h3d_debug import H3dDebug


CABLE_SHAREABLE_PROFILE_NAME = 'h3d_cable_shareable_profile'
CABLE_BASENAME_SUFFIX = '_cable'
PROFILE_BASENAME_SUFFIX = '_profile'
DELIMITER = ':'

DEFAULT_CABLE_BASENAME = ''
DEFAULT_DIAMETER = 0.01
DEFAULT_COMPENSATION = 123.08
DEFAULT_MATERIAL_TAG = ''
DEFAULT_PATH_STEPS = 24
DEFAULT_POLYGON_TYPE = 1
DEFAULT_FLIP = False
DEFAULT_SIDES = 6

ID_DIAMETER = 'd'
ID_STEPS = 's'
ID_FLIP = 'f'
ID_POLYGON_TYPE = 't'
ID_SIDES = 'p'

CH_DIAMETER_NAME = 'diameter'
CH_DIAMETER_USERNAME = 'Diameter'
CH_COMP_NAME = 'compensation'
CH_COMPENSATION_USERNAME = 'Diameter Compensation'
CH_STEPS_NAME = 'steps'
CH_STEPS_USERNAME = 'Steps'
CH_SIDES_NAME = 'sides'
CH_SIDES_USERNAME = 'Sides'
CH_PTAG_NAME = 'materialtag'
CH_MATERIAL_TAG_USERNAME = 'Material Name'
CH_FLIP_NAME = 'flip'
CH_FLIP_USERNAME = 'Flip'
CH_POLYGON_TYPE_NAME = 'polytype'
CH_POLYGON_TYPE_USERNAME = 'Polygon Type (0-2)'

CMD_INDEPENDENT_PROFILE = 'independent'


@dataclass
class CableParams:
    diameter: float = DEFAULT_DIAMETER
    compensation: float = DEFAULT_COMPENSATION
    polygon_type: int = DEFAULT_POLYGON_TYPE
    steps: float = DEFAULT_PATH_STEPS
    sides = DEFAULT_SIDES
    flip: bool = DEFAULT_FLIP
    material_name: str = DEFAULT_MATERIAL_TAG
    basename = DEFAULT_CABLE_BASENAME


class CableLive:
    def __init__(self, mesh: modo.Item) -> None:
        self.params: CableParams = CableParams()
        self.curve_mesh: Union[modo.Item, None] = None
        self.cable_mesh: Union[modo.Item, None] = None
        self.profile_mesh: Union[modo.Item, None] = None
        self.curve_sweep_mop: Union[modo.Item, None] = None
        self.set_polygon_type_mop: Union[modo.Item, None] = None
        self.material_tag_mop: Union[modo.Item, None] = None
        self.shareable_profile_mesh: Union[modo.Item, None] = None
        self.math_mult_chmod: Union[modo.Item, None] = None

        self.detect_mesh_setup(mesh)
        self.strip_cable_setup()

    def detect_mesh_setup(self, mesh: modo.Item):
        if CableLive.is_general_curve(mesh):
            self.curve_mesh = mesh
        ...

    def strip_cable_setup(self):
        scene.removeItems(self.cable_mesh)
        self.cable_mesh = None
        scene.removeItems(self.curve_sweep_mop)
        self.curve_sweep_mop = None
        scene.removeItems(self.set_polygon_type_mop)
        self.set_polygon_type_mop = None
        scene.removeItems(self.material_tag_mop)
        self.material_tag_mop = None
        scene.removeItems(self.shareable_profile_mesh)
        self.shareable_profile_mesh = None
        scene.removeItems(self.math_mult_chmod)
        self.math_mult_chmod = None

    @staticmethod
    def is_general_curve(mesh: modo.Item) -> bool:
        curves = mesh.geometry.polygons.iterByType('CURV')
        beziers = mesh.geometry.polygons.iterByType('BEZR')
        bsplines = mesh.geometry.polygons.iterByType('BSPL')

        return any((curves, beziers, bsplines))

    def new_profile_mesh(self, name: str) -> modo.Item:
        lx.eval('layer.new')
        profile: modo.Item
        profile = scene.selectedByType(c.MESH_TYPE)[0]
        if not profile:
            raise RuntimeError('Error creating profile mesh')
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
        profile.name = name

        return profile

    def get_shareable_profile(self, name: str) -> modo.Item:
        try:
            return scene.item(name)
        except LookupError:
            return self.new_profile_mesh(name)

    @staticmethod
    def meters(mm: Union[str, float, int]) -> float:
        return float(mm) / 1000

    def decode_parameters(self) -> None:
        if not self.curve_mesh:
            raise ValueError(f'{self.curve_mesh = }')
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
            elif token_stripped == ID_FLIP:
                self.params.flip = True
            elif token_stripped.startswith(ID_POLYGON_TYPE):
                self.params.polygon_type = int(token_stripped[len(ID_POLYGON_TYPE):])
            elif token_stripped.startswith(ID_SIDES):
                self.params.sides = int(token_stripped[len(ID_SIDES):])
            else:
                self.params.material_name = token_stripped

    def create_cable_mesh(self) -> None:
        cable_name = f'{self.params.basename}{CABLE_BASENAME_SUFFIX}'
        self.cable_mesh = scene.addMesh(cable_name)

    def create_curve_sweep_mop(self) -> None:
        if not self.cable_mesh:
            raise ValueError(f'{self.cable_mesh = }')
        self.cable_mesh.select(replace=True)
        lx.eval('select.filepath "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" set')
        lx.eval('select.preset "[itemtypes]:MeshOperations/curve/curve.sweep.itemtype" mode:set')
        lx.eval('preset.do')
        self.curve_sweep_mop = scene.selectedByType(itype='curve.sweep')[0]
        if not self.curve_sweep_mop:
            raise ValueError(f'{self.curve_sweep_mop = }')
        self.curve_sweep_mop.select(replace=True)
        lx.eval('item.channel (anySweeper)$extrudeShape linked')
        lx.eval('item.channel (anySweeper)$useSize false')

    def create_set_polygon_type_mop(self) -> None:
        lx.eval('select.filepath "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" set')
        lx.eval('select.preset "[itemtypes]:MeshOperations/polygon/poly.setType.meshop.item.itemtype" mode:set')
        lx.eval('preset.do')
        # lx.eval('item.channel poly.setType.meshop.item$type subd')
        self.material_tag_mop = scene.selectedByType(itype='pmodel.materialTag.item')[0]

    def create_material_tag_mop(self) -> None:
        if not self.cable_mesh:
            raise ValueError(f'{__name__}: {self.cable_mesh = }')
        self.cable_mesh.select(replace=True)
        self.cable_mesh.select(replace=True)
        lx.eval('select.filepath "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" set')
        lx.eval('select.preset "[itemtypes]:MeshOperations/polygon/pmodel.materialTag.item.itemtype" mode:set')
        lx.eval('preset.do')
        self.material_tag_mop = scene.selectedByType(itype='pmodel.materialTag.item')[0]

    def create_math_multiply_channel_mod(self) -> None:
        lx.eval('select.filepath "[itemtypes]:ChannelModifiers/math/cmMathBasic(mul).itemtype" set')
        lx.eval('select.preset "[itemtypes]:ChannelModifiers/math/cmMathBasic(mul).itemtype" mode:set')
        lx.eval('preset.do')
        self.create_math_multiply_channel_mod = scene.selectedByType(itype='cmMathBasic')[0]

    def create_controls(self) -> None:
        if not self.cable_mesh:
            raise ValueError(f'{self.cable_mesh = }')
        self.cable_mesh.select(replace=True)
        lx.eval(f'channel.create {CH_DIAMETER_NAME} distance username:"{CH_DIAMETER_USERNAME}"')
        lx.eval(f'channel.create {CH_COMP_NAME} percent username:"{CH_COMPENSATION_USERNAME}"')
        lx.eval(f'channel.create {CH_POLYGON_TYPE_NAME} integer username:"{CH_POLYGON_TYPE_USERNAME}"')
        lx.eval(f'channel.create {CH_STEPS_NAME} integer username:"{CH_STEPS_USERNAME}"')
        lx.eval(f'channel.create {CH_SIDES_NAME} integer username:"{CH_SIDES_USERNAME}"')
        lx.eval(f'channel.create {CH_FLIP_NAME} boolean username:"{CH_FLIP_USERNAME}"')
        lx.eval(f'channel.create {CH_PTAG_NAME} string username:"{CH_MATERIAL_TAG_USERNAME}"')

    def link_channels(self) -> None:
        if not self.curve_sweep_mop:
            raise ValueError(f'{self.curve_sweep_mop = }')
        if not self.cable_mesh:
            raise ValueError(f'{self.cable_mesh = }')
        if not self.curve_mesh:
            raise ValueError(f'{self.curve_mesh = }')
        if not self.profile_mesh:
            raise ValueError(f'{self.profile_mesh = }')
        if not self.math_mult_chmod:
            raise ValueError(f'{self.math_mult_chmod = }')
        if not self.material_tag_mop:
            raise ValueError(f'{self.material_tag_mop = }')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_DIAMETER_NAME}}} {{{self.math_mult_chmod.id}:input1}}')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_COMP_NAME}}} {{{self.math_mult_chmod.id}:input2}}')
        lx.eval(f'channel.link replace {{{self.math_mult_chmod.id}:output}} {{{self.curve_sweep_mop.id}:size}}')
        lx.eval(f'item.link curve.sweep.path {self.curve_mesh.id} {self.curve_sweep_mop.id} posT:0 replace:false')
        lx.eval(f'item.link curve.sweep.prof {self.profile_mesh.id} {self.curve_sweep_mop.id} posT:0 replace:false')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_STEPS_NAME}}} {{{self.curve_sweep_mop.id}:steps}}')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_FLIP_NAME}}} {{{self.curve_sweep_mop.id}:flip}}')
        lx.eval(f'channel.link add {{{self.cable_mesh.id}:{CH_PTAG_NAME}}} {{{self.material_tag_mop.id}:materialName}}')

    def set_control_channels(self) -> None:
        lx.eval(f'item.channel {CH_DIAMETER_NAME} "{self.params.diameter}"')
        lx.eval(f'item.channel {CH_COMP_NAME} "{self.params.compensation}"')
        lx.eval(f'item.channel {CH_POLYGON_TYPE_NAME} "{self.params.polygon_type}"')
        lx.eval(f'item.channel {CH_STEPS_NAME} "{self.params.steps}"')
        lx.eval(f'item.channel {CH_SIDES_NAME} "{self.params.sides}"')
        lx.eval(f'item.channel {CH_FLIP_NAME} "{self.params.flip}"')
        lx.eval(f'item.channel {CH_PTAG_NAME} "{self.params.material_name}"')

    def create_live_cable(self, is_profile_independent: bool) -> None:
        if not self.curve_mesh:
            raise ValueError(f'{self.curve_mesh = }')
        if not CableLive.is_general_curve(self.curve_mesh):
            print(f'Cable creation skipped for mesh <{self.curve_mesh.name}>. No curve found.')
            return

        # store preset browser status
        preset_browser_opened = lx.eval('layout.createOrClose PresetBrowser presetBrowserPalette ?')

        # open preset browser if not opened
        if not preset_browser_opened:
            lx.eval(
                'layout.createOrClose PresetBrowser presetBrowserPalette true Presets '
                'width:800 height:600 persistent:true style:palette'
            )

        self.decode_parameters()

        if not is_profile_independent:
            self.profile_mesh = self.get_shareable_profile(CABLE_SHAREABLE_PROFILE_NAME)
        else:
            self.profile_mesh = self.new_profile_mesh(f'{self.params.basename}{PROFILE_BASENAME_SUFFIX}')

        self.create_cable_mesh()
        self.create_curve_sweep_mop()
        self.create_material_tag_mop()
        self.create_set_polygon_type_mop()
        self.create_math_multiply_channel_mod()
        self.create_controls()
        self.link_channels()
        self.set_control_channels()

        # restore preset browser status
        if not preset_browser_opened:
            lx.eval(
                'layout.createOrClose PresetBrowser presetBrowserPalette false Presets width:800 height:600 '
                'persistent:true style:palette'
            )


def main():
    is_profile_independent: bool = False
    selected_meshes = scene.selectedByType(itype=c.MESH_TYPE)
    args = lx.args()
    if args:
        if CMD_INDEPENDENT_PROFILE in args:
            is_profile_independent = True
    # cable_shape = CableLive.get_shareable_cable_shape()
    # visible_channel = cable_shape.channel('visible')
    # if visible_channel:
    #     visible_channel.set('allOff')
    for mesh in selected_meshes:
        cable = CableLive(mesh)
        cable.create_live_cable(is_profile_independent)


if __name__ == '__main__':
    scene = modo.Scene()
    h3dd = H3dDebug(enable=False, file=replace_file_ext(scene.filename, ".log"))
    main()
