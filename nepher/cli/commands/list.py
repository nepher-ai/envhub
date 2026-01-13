"""List environments command."""

import click
import json
from nepher.api.client import get_client
from nepher.cli.utils import print_error, print_info


@click.command(name="list")
@click.option("--category", help="Filter by category")
@click.option("--type", type=click.Choice(["usd", "preset"]), help="Filter by type")
@click.option("--benchmark", is_flag=True, help="List only benchmark environments")
@click.option("--search", help="Search query")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--limit", type=int, help="Maximum number of results")
def list_cmd(category: str, type: str, benchmark: bool, search: str, output_json: bool, limit: int):
    """List available environments."""
    try:
        client = get_client()
        envs = client.list_environments(
            category=category,
            type=type,
            benchmark=benchmark if benchmark else None,
            search=search,
            limit=limit,
        )

        if output_json:
            click.echo(json.dumps(envs, indent=2))
        else:
            if not envs:
                print_info("No environments found.")
                return

            print_info(f"Found {len(envs)} environment(s):\n")
            for env in envs:
                click.echo(f"  {env.get('id', 'N/A')}")
                click.echo(f"    Name: {env.get('original_name', 'N/A')}")
                click.echo(f"    Version: {env.get('version', 'N/A')}")
                click.echo(f"    Category: {env.get('category', 'N/A')}")
                click.echo(f"    Type: {env.get('type', 'N/A')}")
                click.echo(f"    Status: {env.get('status', 'N/A')}")
                if env.get("is_benchmark"):
                    click.echo("    Benchmark: Yes")
                if env.get("description"):
                    click.echo(f"    Description: {env.get('description')}")
                click.echo()

    except Exception as e:
        print_error(f"Failed to list environments: {str(e)}")

