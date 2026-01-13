"""View environment command (Isaac Sim integration)."""

import click
from nepher.loader.registry import load_env, load_scene
from nepher.cli.utils import print_error, print_info


def _check_isaaclab_installed():
    """Check if isaaclab is installed and raise error if not."""
    try:
        import isaaclab  # noqa: F401
    except ImportError:
        raise ImportError(
            "Isaac Lab is not installed. The 'view' command requires Isaac Lab to be installed.\n"
            "Please install Isaac Lab to use this command. See: https://isaac-sim.github.io/IsaacLab/"
        )


@click.command()
@click.argument("env_id")
@click.option("--category", required=True, help="Environment category")
@click.option("--scene", help="Scene name or index")
def view(env_id: str, category: str, scene: str):
    """View environment in Isaac Sim (requires isaaclab)."""
    try:
        # Check if isaaclab is installed
        _check_isaaclab_installed()
        
        # Load environment
        env = load_env(env_id, category)

        if scene:
            # Load specific scene
            scene_cfg = load_scene(env, scene, category)
            print_info(f"Loaded scene: {scene}")
            # In production, this would launch Isaac Sim with the scene
            click.echo("Isaac Sim integration not yet implemented.")
        else:
            print_info(f"Environment: {env.name}")
            click.echo(f"  Scenes: {len(env.get_all_scenes())}")
            # In production, this would show available scenes

    except Exception as e:
        print_error(f"Failed to view environment: {str(e)}")

