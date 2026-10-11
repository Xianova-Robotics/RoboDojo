"""Small shims so the RoboDojo env layer runs on Isaac Lab 2.3 (Isaac Sim 5.1) and 3.0 (Isaac Sim 6.x)."""

from __future__ import annotations

import importlib.util

# Isaac Lab 3.0 moved PhysX into the separate ``isaaclab_physx`` package.
IS_ISAACLAB3 = importlib.util.find_spec("isaaclab_physx") is not None


def make_physx_cfg():
    """Return a PhysX configuration object for the running Isaac Lab version.

    :return: ``PhysxCfg`` instance
    """
    if IS_ISAACLAB3:
        from isaaclab_physx.physics import PhysxCfg
    else:
        from isaaclab.sim import PhysxCfg
    return PhysxCfg()


def make_simulation_cfg(device: str, gravity: tuple[float, float, float]):
    """Return a SimulationCfg wired to a PhysX backend.

    :param device: simulation device string
    :param gravity: gravity vector
    :return: ``SimulationCfg`` instance
    """
    from isaaclab.sim import SimulationCfg

    if IS_ISAACLAB3:
        return SimulationCfg(device=device, gravity=gravity, physics=make_physx_cfg())
    return SimulationCfg(device=device, gravity=gravity, physx=make_physx_cfg())


def get_physx_cfg(sim_cfg):
    """Return the PhysX config held by a SimulationCfg.

    :param sim_cfg: ``SimulationCfg`` instance
    :return: PhysX config object
    """
    if IS_ISAACLAB3:
        if sim_cfg.physics is None:
            sim_cfg.physics = make_physx_cfg()
        return sim_cfg.physics
    return sim_cfg.physx


def apply_render_settings(sim_cfg, render_config: dict, frequency_settings: dict) -> None:
    """Apply RTX render quality settings.

    On Isaac Lab 2.3 these live on ``SimulationCfg.render``; on 3.0 the renderer is
    owned by camera sensors, so the equivalent carb settings are written directly.

    :param sim_cfg: ``SimulationCfg`` instance
    :param render_config: RoboDojo render section (RenderCfg field names)
    :param frequency_settings: extra carb settings for the Kit run loop
    """
    carb_settings = dict(render_config.get("carb_settings") or {})
    carb_settings.update(frequency_settings)

    if not IS_ISAACLAB3:
        render_cfg = sim_cfg.render
        for key, value in render_config.items():
            if key != "carb_settings":
                setattr(render_cfg, key, value)
        render_cfg.carb_settings = carb_settings
        return

    import carb.settings

    settings = carb.settings.get_settings()
    # Same precedence as Isaac Lab 2.3 ``SimulationContext._apply_render_settings_from_cfg``:
    # preset -> named fields -> raw carb settings -> antialiasing.
    rendering_mode = render_config.get("rendering_mode") or "balanced"
    if rendering_mode not in _RENDERING_MODE_PRESETS:
        raise ValueError(f"Unsupported rendering_mode '{rendering_mode}', expected {list(_RENDERING_MODE_PRESETS)}")
    for path, value in _RENDERING_MODE_PRESETS[rendering_mode].items():
        settings.set(path, value)
    for key, path in _RTX_FIELD_TO_SETTING.items():
        value = render_config.get(key)
        if value is not None:
            settings.set(path, value)
    for path, value in carb_settings.items():
        settings.set(_carb_path(path), value)
    antialiasing_mode = render_config.get("antialiasing_mode")
    if antialiasing_mode is not None:
        _enable_kit_extension("omni.replicator.core")
        import omni.replicator.core as rep

        rep.settings.set_render_rtx_realtime(antialiasing=antialiasing_mode)


# Carb settings of Isaac Lab 2.3 ``apps/rendering_modes/{mode}.kit`` (dropped in 3.0).
_RENDERING_MODE_PRESETS = {
    "performance": {
        "/rtx/translucency/enabled": False,
        "/rtx/reflections/enabled": False,
        "/rtx/reflections/denoiser/enabled": False,
        "/rtx/directLighting/sampledLighting/denoisingTechnique": 0,
        "/rtx/directLighting/sampledLighting/enabled": False,
        "/rtx/sceneDb/ambientLightIntensity": 1.0,
        "/rtx/shadows/enabled": True,
        "/rtx/indirectDiffuse/enabled": False,
        "/rtx/indirectDiffuse/denoiser/enabled": False,
        "/rtx/domeLight/upperLowerStrategy": 3,
        "/rtx/ambientOcclusion/enabled": False,
        "/rtx/ambientOcclusion/denoiserMode": 1,
        "/rtx/raytracing/subpixel/mode": 0,
        "/rtx/raytracing/cached/enabled": False,
        "/rtx-transient/dlssg/enabled": False,
        "/rtx-transient/dldenoiser/enabled": False,
        "/rtx/post/dlss/execMode": 0,
        "/rtx/pathtracing/maxSamplesPerLaunch": 1000000,
        "/rtx/viewTile/limit": 1000000,
    },
    "balanced": {
        "/rtx/translucency/enabled": False,
        "/rtx/reflections/enabled": False,
        "/rtx/reflections/denoiser/enabled": True,
        "/rtx/directLighting/sampledLighting/enabled": True,
        "/rtx/sceneDb/ambientLightIntensity": 1.0,
        "/rtx/shadows/enabled": True,
        "/rtx/indirectDiffuse/enabled": False,
        "/rtx/indirectDiffuse/denoiser/enabled": True,
        "/rtx/ambientOcclusion/enabled": False,
        "/rtx/ambientOcclusion/denoiserMode": 1,
        "/rtx/raytracing/subpixel/mode": 0,
        "/rtx/raytracing/cached/enabled": True,
        "/rtx-transient/dlssg/enabled": False,
        "/rtx-transient/dldenoiser/enabled": True,
        "/rtx/post/dlss/execMode": 1,
        "/rtx/pathtracing/maxSamplesPerLaunch": 1000000,
        "/rtx/viewTile/limit": 1000000,
    },
    "quality": {
        "/rtx/translucency/enabled": True,
        "/rtx/reflections/enabled": True,
        "/rtx/reflections/denoiser/enabled": True,
        "/rtx/directLighting/sampledLighting/enabled": True,
        "/rtx/sceneDb/ambientLightIntensity": 1.0,
        "/rtx/shadows/enabled": True,
        "/rtx/indirectDiffuse/enabled": True,
        "/rtx/indirectDiffuse/denoiser/enabled": True,
        "/rtx/ambientOcclusion/enabled": True,
        "/rtx/ambientOcclusion/denoiserMode": 0,
        "/rtx/raytracing/subpixel/mode": 1,
        "/rtx/raytracing/cached/enabled": True,
        "/rtx-transient/dlssg/enabled": False,
        "/rtx-transient/dldenoiser/enabled": True,
        "/rtx/post/dlss/execMode": 2,
        "/rtx/pathtracing/maxSamplesPerLaunch": 1000000,
        "/rtx/viewTile/limit": 1000000,
    },
}

_RTX_FIELD_TO_SETTING = {
    "enable_translucency": "/rtx/translucency/enabled",
    "enable_reflections": "/rtx/reflections/enabled",
    "enable_global_illumination": "/rtx/indirectDiffuse/enabled",
    "enable_dlssg": "/rtx-transient/dlssg/enabled",
    "enable_dl_denoiser": "/rtx-transient/dldenoiser/enabled",
    "dlss_mode": "/rtx/post/dlss/execMode",
    "enable_direct_lighting": "/rtx/directLighting/enabled",
    "samples_per_pixel": "/rtx/directLighting/sampledLighting/samplesPerPixel",
    "enable_shadows": "/rtx/shadows/enabled",
    "enable_ambient_occlusion": "/rtx/ambientOcclusion/enabled",
    "dome_light_upper_lower_strategy": "/rtx/domeLight/upperLowerStrategy",
}


def _carb_path(key: str) -> str:
    """Convert a 2.3-style ``carb_settings`` key to a carb path.

    :param key: ``/a/b`` path, ``a_b`` python style or ``a.b`` kit-file style
    :return: carb setting path
    """
    if key.startswith("/"):
        return key
    if "_" in key:
        return "/" + key.replace("_", "/")
    if "." in key:
        return "/" + key.replace(".", "/")
    return key


def _enable_kit_extension(ext_id: str) -> None:
    """Enable a Kit extension immediately if it is not already loaded.

    :param ext_id: Kit extension id
    """
    import omni.kit.app

    manager = omni.kit.app.get_app().get_extension_manager()
    if not manager.is_extension_enabled(ext_id):
        manager.set_extension_enabled_immediate(ext_id, True)


def enable_rtx_sensor_rendering() -> None:
    """Mark the simulation as driving RTX sensors and attach the RTX Hydra engine.

    Isaac Lab 3.0 only does this when one of its own ``Camera`` sensors is created; RoboDojo
    builds Replicator render products itself, so the equivalent flags are set here. Must run
    after the ``SimulationContext`` exists and before ``sim.reset()``.
    """
    if not IS_ISAACLAB3:
        return

    import carb.settings

    settings = carb.settings.get_settings()
    settings.set_bool("/isaaclab/render/rtx_sensors", True)
    settings.set_bool("/physics/fabricUpdateTransformations", True)

    _enable_kit_extension("omni.replicator.core")
    from isaaclab_physx.renderers.isaac_rtx_renderer_utils import ensure_rtx_hydra_engine_attached

    ensure_rtx_hydra_engine_attached()


def render_sim(sim_context) -> None:
    """Render one frame so Replicator annotators receive fresh data.

    On Isaac Lab 3.0 ``SimulationContext.render`` no longer pumps the Kit app loop in headless
    mode (camera sensors do it on demand), so the RTX pump is triggered explicitly.

    :param sim_context: Isaac Lab ``SimulationContext``
    """
    sim_context.render()
    if IS_ISAACLAB3:
        from isaaclab_physx.renderers.isaac_rtx_renderer_utils import ensure_isaac_rtx_render_update

        ensure_isaac_rtx_render_update(force=True)


def ensure_legacy_physics_view(sim_context) -> None:
    """Give the legacy ``isaacsim.core.prims`` wrappers a physics tensor view.

    Isaac Lab 3.0 launches Kit with the SimulationManager default callbacks disabled
    and keeps its own warp-frontend view, so ``SimulationManager.get_physics_sim_view()``
    stays ``None``. This creates the torch-frontend view the legacy prims expect, the same
    way ``SimulationManager.initialize_physics`` would, without re-running physics warm-up.

    :param sim_context: Isaac Lab ``SimulationContext`` after ``reset()``
    """
    if not IS_ISAACLAB3:
        return

    import omni.physics.tensors
    from isaacsim.core.simulation_manager import SimulationManager

    if SimulationManager.get_physics_sim_view() is not None:
        return

    from isaaclab.sim.utils.stage import get_current_stage_id

    if SimulationManager.get_backend() == "numpy":
        SimulationManager.set_backend("torch")
    view = omni.physics.tensors.create_simulation_view(SimulationManager.get_backend(), stage_id=get_current_stage_id())
    view.set_subspace_roots("/")
    SimulationManager._physics_sim_view = view
    SimulationManager._warmup_needed = False
    SimulationManager._simulation_view_created = True


def release_legacy_physics_view() -> None:
    """Invalidate the view created by :func:`ensure_legacy_physics_view` before the stage is closed."""
    if not IS_ISAACLAB3:
        return

    from isaacsim.core.simulation_manager import SimulationManager

    view = SimulationManager._physics_sim_view
    if view is not None:
        try:
            view.invalidate()
        except Exception:
            pass
        SimulationManager._physics_sim_view = None
        SimulationManager._warmup_needed = True
        SimulationManager._simulation_view_created = False
