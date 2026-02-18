"""View environment command (Isaac Sim integration)."""

import argparse
import os
import sys
from typing import Optional
import click
from nepher.loader.registry import load_env, load_scene
from nepher.cli.utils import print_error, print_info, print_success

original_argv = None


def _check_isaaclab_installed():
    """Check if isaaclab is installed and raise error if not."""
    try:
        import isaaclab  # noqa: F401
    except ImportError:
        try:
            import isaacsim  # noqa: F401
            raise ImportError(
                "Isaac Lab is not installed. The 'view' command requires Isaac Lab to be installed.\n"
                "Please install Isaac Lab to use this command. See: https://isaac-sim.github.io/IsaacLab/"
            )
        except ImportError:
            from pathlib import Path
            script_paths = [
                Path(__file__).parent.parent.parent / "scripts" / "nepher_view.py",
                Path("envhub/scripts/nepher_view.py"),
                Path("scripts/nepher_view.py"),
            ]
            script_found = next((p for p in script_paths if p.exists()), None)
            if script_found:
                try:
                    script_found = str(script_found.relative_to(Path.cwd()))
                except ValueError:
                    script_found = str(script_found)
                help_msg = (
                    "Isaac Lab is not available in the current environment.\n\n"
                    "The 'view' command must be run through Isaac Lab's Python environment.\n"
                    f"Please use the script instead:\n\n"
                    f"  isaaclab.bat -p {script_found} <env_id> --category <category> [--scene <scene>]\n\n"
                    "Or on Linux/Mac:\n"
                    f"  ./isaaclab.sh -p {script_found} <env_id> --category <category> [--scene <scene>]\n\n"
                    "Example:\n"
                    f"  isaaclab.bat -p {script_found} digital-twin-warehouse-v1 --category navigation --scene small_warehouse"
                )
            else:
                help_msg = (
                    "Isaac Lab is not available in the current environment.\n\n"
                    "The 'view' command must be run through Isaac Lab's Python environment.\n"
                    "Please use the script 'scripts/nepher_view.py' with isaaclab.bat or isaaclab.sh.\n\n"
                    "Example:\n"
                    "  isaaclab.bat -p scripts/nepher_view.py <env_id> --category <category> [--scene <scene>]"
                )
            raise ImportError(help_msg)


def _spawn_usd_scene(scene_cfg, env_cache_path=None):
    """Spawn a USD scene in Isaac Sim."""
    import omni.usd
    from pxr import Gf, UsdGeom
    from pathlib import Path
    import isaaclab.sim as sim_utils
    
    if not scene_cfg.usd_path:
        raise ValueError("USD scene config missing usd_path")
    
    usd_path = Path(scene_cfg.usd_path)
    if not usd_path.is_absolute():
        usd_path = (env_cache_path / usd_path) if env_cache_path else usd_path.resolve()
    usd_path_str = str(usd_path.resolve())
    
    print_info(f"Loading USD scene: {usd_path_str}")
    stage = omni.usd.get_context().get_stage()
    
    if not stage.GetPrimAtPath("/World"):
        UsdGeom.Xform.Define(stage, "/World")
    
    scene_prim_path = "/World/Scene"
    scene_prim = stage.DefinePrim(scene_prim_path, "Xform")
    scene_prim.GetReferences().AddReference(usd_path_str)
    
    try:
        children = scene_prim.GetChildren()
        if children:
            print_info(f"USD scene reference loaded with {len(children)} top-level prims")
        elif scene_prim.IsValid():
            from pxr import Usd
            for child in Usd.PrimRange(scene_prim):
                if child != scene_prim:
                    print_info(f"Found prim in scene: {child.GetPath()}")
                    break
    except Exception as e:
        print_error(f"Warning: Could not verify USD scene loading: {e}")
    
    xform = UsdGeom.Xformable(scene_prim)
    
    def _apply_xform_op(attr_name, default_value, op_type):
        """Apply transform op if value differs from default."""
        value = getattr(scene_cfg, attr_name, None)
        if not value or value == default_value:
            return
        existing_ops = xform.GetOrderedXformOps()
        op = next((o for o in existing_ops if o.GetOpType() == op_type), None)
        if op is None:
            op = xform.AddTranslateOp() if op_type == UsdGeom.XformOp.TypeTranslate else xform.AddScaleOp()
        op.Set(Gf.Vec3d(*value))
    
    _apply_xform_op('usd_position', (0.0, 0.0, 0.0), UsdGeom.XformOp.TypeTranslate)
    _apply_xform_op('usd_scale', (1.0, 1.0, 1.0), UsdGeom.XformOp.TypeScale)
    
    print_success(f"USD scene loaded at {scene_prim_path}")
    
    sky_light_path = "/World/SkyLight"
    if not stage.GetPrimAtPath(sky_light_path):
        light_cfg = sim_utils.DomeLightCfg(intensity=1000.0, color=(1.0, 1.0, 1.0))
        light_cfg.func(sky_light_path, light_cfg)
        print_success("Added sky light")


def _spawn_preset_scene(scene_cfg):
    """Spawn a preset scene in Isaac Sim."""
    import isaaclab.sim as sim_utils
    import omni.usd
    from pxr import Gf, UsdGeom
    from isaaclab.terrains import TerrainImporter
    
    print_info("Spawning preset scene...")
    
    stage = omni.usd.get_context().get_stage()
    if not stage.GetPrimAtPath("/World"):
        UsdGeom.Xform.Define(stage, "/World")
    
    terrain_cfg = scene_cfg.get_terrain_cfg()
    if terrain_cfg:
        if not getattr(terrain_cfg, 'prim_path', None):
            terrain_cfg.prim_path = "/World/Terrain"
        TerrainImporter(terrain_cfg)
        print_success(f"Terrain spawned (type: {terrain_cfg.terrain_type})")
    
    if hasattr(scene_cfg, 'get_light_cfgs'):
        for name, light_cfg in (scene_cfg.get_light_cfgs() or {}).items():
            prim_path = getattr(light_cfg, 'prim_path', f"/World/Lights/{name}")
            if getattr(light_cfg, 'spawn', None) is not None:
                light_cfg.spawn.func(prim_path, light_cfg.spawn)
                print_success(f"Light '{name}' spawned at {prim_path}")
    
    if hasattr(scene_cfg, 'get_obstacle_cfgs'):
        obstacle_cfgs = scene_cfg.get_obstacle_cfgs()
        if obstacle_cfgs:
            env_prim_path = "/World/envs/env_0"
            for path in ["/World/envs", env_prim_path]:
                if not stage.GetPrimAtPath(path):
                    UsdGeom.Xform.Define(stage, path)
            
            for name, obs_cfg in obstacle_cfgs.items():
                prim_path = getattr(obs_cfg, 'prim_path', f"{env_prim_path}/{name}").replace(
                    "{ENV_REGEX_NS}", env_prim_path
                )
                if getattr(obs_cfg, 'spawn', None) is not None:
                    obs_cfg.spawn.func(prim_path, obs_cfg.spawn)
                    init_state = getattr(obs_cfg, 'init_state', None)
                    if init_state is not None:
                        prim = stage.GetPrimAtPath(prim_path)
                        if prim.IsValid():
                            xformable = UsdGeom.Xformable(prim)
                            xformable.ClearXformOpOrder()
                            
                            if getattr(init_state, 'pos', None) is not None:
                                pos = init_state.pos
                                xformable.AddTranslateOp().Set(Gf.Vec3d(pos[0], pos[1], pos[2]))
                            
                            rot = getattr(init_state, 'rot', None)
                            if rot is not None:
                                import math
                                if len(rot) == 4:
                                    xformable.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(
                                        Gf.Quatd(rot[0], rot[1], rot[2], rot[3])
                                    )
                                elif len(rot) == 3:
                                    xformable.AddRotateXYZOp(UsdGeom.XformOp.PrecisionDouble).Set(
                                        Gf.Vec3d(math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
                                    )
            print_success(f"Spawned {len(obstacle_cfgs)} obstacles")
    
    sky_light_path = "/World/SkyLight"
    if not stage.GetPrimAtPath(sky_light_path):
        light_cfg = sim_utils.DomeLightCfg(intensity=1000.0, color=(1.0, 1.0, 1.0))
        light_cfg.func(sky_light_path, light_cfg)
        print_success("Added default sky light")


def _setup_app_launcher():
    """Set up AppLauncher and return the simulation app.
    
    This function extracts AppLauncher arguments from the original sys.argv
    and creates the AppLauncher instance. It should be called before importing
    any Isaac Lab modules that require the app to be running.
    
    Returns:
        The SimulationApp instance from the AppLauncher.
    """
    _check_isaaclab_installed()
    
    from isaaclab.app import AppLauncher
    
    argv_to_parse = original_argv if original_argv is not None else sys.argv
    
    app_launcher_args = []
    i = 1  # Skip script name
    while i < len(argv_to_parse):
        arg = argv_to_parse[i]
        if arg in ("--category", "--scene"):
            i += 2 if i + 1 < len(argv_to_parse) else 1
            continue
        if not arg.startswith("--") and i == 1:
            i += 1
            continue
        app_launcher_args.append(arg)
        i += 1
    
    parser = argparse.ArgumentParser()
    AppLauncher.add_app_launcher_args(parser)
    args_cli = parser.parse_args(app_launcher_args)
    
    app_launcher = AppLauncher(args_cli)
    return app_launcher.app


@click.command()
@click.argument("env_id")
@click.option("--category", default=None, help="Environment category (optional, resolved from manifest)")
@click.option("--scene", help="Scene name or index")
def view(env_id: str, category: Optional[str], scene: Optional[str]):
    """View environment in Isaac Sim (requires isaaclab)."""
    simulation_app = None
    try:
        simulation_app = _setup_app_launcher()
        
        import isaaclab.sim as sim_utils
        from isaaclab.sim import SimulationContext
        import omni.usd
        
        env = load_env(env_id, category)

        if scene:
            scene_cfg = load_scene(env, scene, category)
            print_info(f"Loaded scene: {scene}")
            
            usd_path = getattr(scene_cfg, 'usd_path', None)
            
            sim_cfg = sim_utils.SimulationCfg(dt=0.01)
            if usd_path:
                _spawn_usd_scene(scene_cfg, env_cache_path=env.cache_path)
                sim = SimulationContext(sim_cfg)
                sim.set_camera_view(eye=[30.0, 30.0, 20.0], target=[0.0, 0.0, 0.0])
            else:
                sim = SimulationContext(sim_cfg)
                _spawn_preset_scene(scene_cfg)
                sim.set_camera_view(eye=[15.0, 15.0, 12.0], target=[0.0, 0.0, 0.0])
            
            sim.reset()
            
            print_success("Scene loaded successfully!")
            click.echo("\n" + "=" * 60)
            click.echo("Camera Controls:")
            click.echo("   • Left-click + drag: Rotate view")
            click.echo("   • Right-click + drag: Pan view")
            click.echo("   • Scroll: Zoom in/out")
            click.echo("   • F: Focus on selection")
            click.echo("\nPress Ctrl+C in terminal to exit")
            click.echo("=" * 60)
            
            try:
                simulation_app = sim.app
                click.echo("\nRunning simulation...\n   (Press Ctrl+C to exit)")
                if simulation_app and hasattr(simulation_app, 'is_running'):
                    while simulation_app.is_running():
                        sim.step()
                else:
                    while not sim.is_stopped():
                        sim.step()
            except KeyboardInterrupt:
                click.echo("\n\nExiting...")
            except Exception as e:
                if os.getenv("NEPHER_DEBUG"):
                    import traceback
                    traceback.print_exc()
                click.echo(f"\nWarning: Could not start simulation loop: {e}")
                click.echo("   Scene is loaded. You can interact with it in the Isaac Sim viewport.")
        else:
            print_info(f"Environment: {env.name}")
            click.echo(f"  Scenes: {len(env.get_all_scenes())}")
            click.echo("\nAvailable scenes:")
            for i, scene_obj in enumerate(env.get_all_scenes()):
                click.echo(f"  [{i}] {scene_obj.name}")

    except KeyboardInterrupt:
        click.echo("\n\nExiting...")
    except Exception as e:
        import traceback
        print_error(f"Failed to view environment: {str(e)}")
        if __debug__ or os.getenv("NEPHER_DEBUG"):
            click.echo(f"Exception type: {type(e).__name__}")
            traceback.print_exc()
    finally:
        if simulation_app is not None:
            simulation_app.close()

