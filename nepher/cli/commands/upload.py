"""Upload environment command."""

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import click

from nepher.api.client import get_client
from nepher.cli.utils import print_error, print_info, print_success
from nepher.storage.bundle import BundleManager, iter_bundle_files


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--category", required=True, help="Environment category")
@click.option("--benchmark", is_flag=True, help="Mark as benchmark environment")
@click.option("--force", is_flag=True, help="Force upload even if duplicate exists")
@click.option("--thumbnail", type=click.Path(exists=True), help="Thumbnail image path")
@click.option("--api-key", default=None, envvar="NEPHER_API_KEY", help="API key (defaults to stored credentials)")
def upload(path: str, category: str, benchmark: bool, force: bool, thumbnail: Optional[str], api_key: Optional[str]):
    """Upload an environment bundle (directory with manifest.yaml, or a .zip)."""
    temp_zip: Optional[Path] = None
    try:
        bundle_path = Path(path)

        print_info("Validating bundle...")
        if not BundleManager.validate_bundle(bundle_path):
            print_error("Invalid bundle: manifest.yaml not found at the bundle root")
            raise SystemExit(1)

        upload_path = bundle_path
        if bundle_path.is_dir():
            print_info("Creating bundle ZIP...")
            fd, name = tempfile.mkstemp(prefix=f"{bundle_path.name}-", suffix=".zip")
            os.close(fd)
            temp_zip = Path(name)
            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path, arcname in iter_bundle_files(bundle_path):
                    zipf.write(file_path, arcname.as_posix())
            upload_path = temp_zip

        print_info(f"Uploading {bundle_path.name}...")
        result = get_client(api_key=api_key).upload_environment(
            bundle_path=upload_path,
            category=category,
            benchmark=benchmark,
            force=force,
            duplicate_policy="reject",
            thumbnail=Path(thumbnail) if thumbnail else None,
        )

        print_success("Environment uploaded successfully!")
        click.echo(f"  Environment ID: {result.get('id', 'N/A')}")

    except SystemExit:
        raise
    except Exception as e:
        print_error(f"Failed to upload environment: {e}")
        raise SystemExit(1)
    finally:
        if temp_zip is not None:
            temp_zip.unlink(missing_ok=True)
