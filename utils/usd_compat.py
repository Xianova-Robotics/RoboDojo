"""Isaac Sim helpers whose import location changed between 5.1 and 6.x."""

from __future__ import annotations

try:
    from isaacsim.replicator.behavior.utils.scene_utils import create_mdl_material
except ImportError:
    import omni.kit.commands
    import omni.usd
    from pxr import Sdf, UsdShade

    def create_mdl_material(mtl_url: str, mtl_name: str, mtl_path: str) -> UsdShade.Material:
        """Create an MDL material prim (vendored from Isaac Sim 5.1 ``scene_utils``).

        :param mtl_url: MDL file URL
        :param mtl_name: MDL material name inside the file
        :param mtl_path: prim path for the new material
        :return: the created ``UsdShade.Material``
        """
        omni.kit.commands.execute("CreateMdlMaterialPrim", mtl_url=mtl_url, mtl_name=mtl_name, mtl_path=mtl_path)
        stage = omni.usd.get_context().get_stage()
        mtl_prim = stage.GetPrimAtPath(mtl_path)
        shader = UsdShade.Shader(omni.usd.get_shader_from_material(mtl_prim, get_prim=True))
        shader.CreateInput("diffuse_texture", Sdf.ValueTypeNames.Asset)
        shader.CreateInput("project_uvw", Sdf.ValueTypeNames.Bool)
        shader.CreateInput("texture_scale", Sdf.ValueTypeNames.Float2)
        shader.CreateInput("texture_rotate", Sdf.ValueTypeNames.Float)
        return UsdShade.Material(mtl_prim)


__all__ = ["create_mdl_material"]
