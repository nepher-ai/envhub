"""Upload environment command."""

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
import click
from nepher.api.client import get_client
from nepher.storage.bundle import BundleManager
from nepher.cli.utils import print_error, print_success, print_info


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--category", required=True, help="Environment category")
@click.option("--benchmark", is_flag=True, help="Mark as benchmark environment")
@click.option("--force", is_flag=True, help="Force upload even if duplicate exists")
@click.option("--thumbnail", type=click.Path(exists=True), help="Thumbnail image path")
def upload(path: str, category: str, benchmark: bool, force: bool, thumbnail: Optional[str]):
    """Upload an environment bundle."""
    temp_zip = None
    try:
        bundle_path = Path(path)
        if not bundle_path.exists():
            print_error(f"Bundle not found: {bundle_path}")
            return

        print_info("Validating bundle...")
        if not BundleManager.validate_bundle(bundle_path):
            print_error("Invalid bundle: manifest.yaml not found")
            return

        upload_path = bundle_path
        if bundle_path.is_dir():
            print_info("Creating bundle ZIP...")
            temp_dir = tempfile.gettempdir()
            zip_name = f"{bundle_path.name}.zip"
            temp_zip = Path(temp_dir) / zip_name
            
            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in bundle_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(bundle_path)
                        zipf.write(file_path, arcname)
            
            upload_path = temp_zip

        print_info(f"Uploading {bundle_path.name}...")

        client = get_client()
        result = client.upload_environment(
            bundle_path=upload_path,
            category=category,
            benchmark=benchmark,
            force=force,
            duplicate_policy="reject",
            thumbnail=Path(thumbnail) if thumbnail else None,
        )

        print_success(f"Environment uploaded successfully!")
        click.echo(f"  Environment ID: {result.get('id', 'N/A')}")

    except Exception as e:
        print_error(f"Failed to upload environment: {str(e)}")
    finally:
        if temp_zip and temp_zip.exists():
            temp_zip.unlink()

