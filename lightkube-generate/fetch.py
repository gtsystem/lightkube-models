import re
from pathlib import Path

import httpx
import typer

app = typer.Typer(
    help="Fetch Kubernetes OpenAPI specifications and list available versions"
)


def list_kubernetes_tags(count: int = 10) -> list[str]:
    """List the last N version tags from kubernetes/kubernetes repository.

    Args:
        count: Number of tags to retrieve (default: 10)

    Returns:
        List of version strings (without 'v' prefix), sorted from newest to oldest

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = "https://api.github.com/repos/kubernetes/kubernetes/tags"
    params = {"per_page": count * 2}

    print(f"Fetching last {count} tags from kubernetes/kubernetes...")

    response = httpx.get(url, params=params, follow_redirects=True)
    response.raise_for_status()

    tags_data = response.json()
    print(tags_data)
    # Extract version numbers, removing 'v' prefix
    versions = []
    for tag in tags_data:
        tag_name = tag.get("name", "")
        if tag_name.startswith("v"):
            # Remove 'v' prefix and filter for valid version format
            version = tag_name[1:]
            if re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", version):
                versions.append(version)

    return versions[:count]


def fetch_spec(version: str, output_dir: str = "openapi") -> Path:
    """Fetch Kubernetes OpenAPI spec for a given version.

    Args:
        version: Kubernetes version in format X.Y.Z (without 'v' prefix)
        output_dir: Directory to save the spec file (default: 'openapi')

    Returns:
        Path to the saved spec file

    Raises:
        ValueError: If version format is invalid
        httpx.HTTPError: If download fails
    """
    # Validate version format
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", version):
        raise ValueError(f"Version {version} must match expression \\d+.\\d+.\\d")

    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Download spec
    url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/refs/tags/v{version}/api/openapi-spec/swagger.json"
    print(f"Fetching spec from {url}...")

    response = httpx.get(url, follow_redirects=True)
    response.raise_for_status()

    # Replace 'unversioned' with the version
    content = response.text.replace("unversioned", f"v{version}")

    # Save to file
    output_file = output_path / f"kubernetes_v{version}.json"
    output_file.write_text(content)

    print(f"Saved spec to {output_file}")
    return output_file


@app.command()
def fetch(
    version: str = typer.Argument(
        ..., help="Kubernetes version in format X.Y.Z (without 'v' prefix)"
    ),
    output_dir: str = typer.Option(
        "openapi", "--output-dir", "-o", help="Directory to save the spec file"
    ),
) -> None:
    """Fetch Kubernetes OpenAPI spec for a given version."""
    try:
        output_file = fetch_spec(version, output_dir)
        typer.echo(f"✓ Successfully saved spec to {output_file}")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        typer.echo(f"HTTP Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def list(
    count: int = typer.Argument(10, help="Number of tags to retrieve"),
) -> None:
    """List the last N version tags from kubernetes/kubernetes repository."""
    try:
        versions = list_kubernetes_tags(count)
        typer.echo(f"\nLast {len(versions)} Kubernetes versions:")
        for version in versions:
            typer.echo(f"  {version}")
    except httpx.HTTPError as e:
        typer.echo(f"HTTP Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
