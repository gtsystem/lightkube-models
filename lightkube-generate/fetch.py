import re
from pathlib import Path

import httpx
import typer
from ruamel.yaml import YAML

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


def update_workflow_versions(
    version: str,
    workflow_path: str = ".github/workflows/python-package.yml",
    max_versions: int = 16,
) -> Path:
    """Update GitHub workflow with new version and maintain only last N versions.

    Args:
        version: New Kubernetes version to add (format X.Y.Z)
        workflow_path: Path to the workflow YAML file
        max_versions: Maximum number of versions to keep (default: 16)

    Returns:
        Path to the updated workflow file

    Raises:
        ValueError: If version format is invalid
        FileNotFoundError: If workflow file doesn't exist
    """
    # Validate version format
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", version):
        raise ValueError(f"Version {version} must match expression \\d+.\\d+.\\d")

    workflow_file = Path(workflow_path)
    if not workflow_file.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    # Initialize YAML with roundtrip mode to preserve formatting
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    # Read workflow file
    with open(workflow_file) as f:
        workflow = yaml.load(f)

    # Get current versions from matrix
    matrix = workflow["jobs"]["build"]["strategy"]["matrix"]
    current_versions = matrix.get("kube-version", [])

    # Add new version if not already present
    if version not in current_versions:
        current_versions.append(version)
        print(f"Added version {version}")
    else:
        print(f"Version {version} already in workflow")

    # Keep only the last max_versions
    if len(current_versions) > max_versions:
        current_versions = current_versions[-max_versions:]

    # Update workflow
    matrix["kube-version"] = current_versions

    # Write back to file
    with open(workflow_file, "w") as f:
        yaml.dump(workflow, f)

    print(f"Updated {workflow_file} with {len(current_versions)} versions")
    return workflow_file


def update_docs_versions(
    version: str,
    docs_path: str = "../lightkube/docs/resources-and-models.md",
    max_versions: int = 16,
) -> Path:
    """Update documentation file with new version link and maintain only last N versions.

    Args:
        version: New Kubernetes version to add (format X.Y.Z)
        docs_path: Path to the documentation markdown file
        max_versions: Maximum number of versions to keep (default: 16)

    Returns:
        Path to the updated documentation file

    Raises:
        ValueError: If version format is invalid
        FileNotFoundError: If documentation file doesn't exist
    """
    # Validate version format
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", version):
        raise ValueError(f"Version {version} must match expression \\d+.\\d+.\\d")

    docs_file = Path(docs_path)
    if not docs_file.exists():
        raise FileNotFoundError(f"Documentation file not found: {docs_path}")

    # Extract major.minor version for the link
    parts = version.split(".")
    new_major = int(parts[0])
    new_minor = int(parts[1])
    new_version_str = f"{new_major}.{new_minor}"

    # Pattern to find version links
    version_pattern = (
        r"\[(\d+)\.(\d+)\]\(https://gtsystem\.github\.io/lightkube-models/\d+\.\d+\)"
    )

    # Read file line by line
    lines = docs_file.read_text().splitlines(keepends=True)
    new_lines = []
    first_version_idx = -1
    version_already_exists = False
    version_lines = []

    # First pass: separate version lines from other lines
    for line in lines:
        match = re.search(version_pattern, line)
        if match:
            line_major = int(match.group(1))
            line_minor = int(match.group(2))
            line_version_str = f"{line_major}.{line_minor}"

            if first_version_idx == -1:
                first_version_idx = len(new_lines)

            if line_version_str == new_version_str:
                version_already_exists = True

            # Calculate distance from new version
            version_distance = (new_major * 100 + new_minor) - (
                line_major * 100 + line_minor
            )

            # Keep if within range
            if version_distance < max_versions and version_distance >= 0:
                version_lines.append(line_version_str)
            else:
                print(f"Removed old version {line_version_str}")
        else:
            # Non-version line
            if first_version_idx == -1 or not version_lines:
                # Before first version or no versions yet
                new_lines.append(line)
            # else: we're past the version block, will add later

    # Add new version if needed
    if not version_already_exists:
        version_lines.insert(0, new_version_str)
        print(f"Added version {new_version_str}")
    else:
        print(f"Version {new_version_str} already in documentation")

    # Reconstruct version block with proper punctuation
    for i, ver in enumerate(version_lines):
        is_last = i == len(version_lines) - 1
        ending = "." if is_last else ","
        new_lines.insert(
            first_version_idx + i,
            f"[{ver}](https://gtsystem.github.io/lightkube-models/{ver}){ending}\n",
        )

    # Add remaining lines after version block
    in_version_block = False
    for line in lines:
        if re.search(version_pattern, line):
            in_version_block = True
        elif in_version_block:
            # Past the version block
            new_lines.append(line)

    # Write back to file
    docs_file.write_text("".join(new_lines))

    print(f"Updated {docs_file}")
    return docs_file


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
    output_file = fetch_spec(version, output_dir)
    typer.echo(f"✓ Successfully saved spec to {output_file}")


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


@app.command(name="update-workflow")
def update_workflow(
    version: str = typer.Argument(..., help="Kubernetes version to add (format X.Y.Z)"),
    workflow_path: str = typer.Option(
        ".github/workflows/python-package.yml",
        "--workflow",
        "-w",
        help="Path to workflow file",
    ),
    max_versions: int = typer.Option(
        16, "--max-versions", "-m", help="Maximum number of versions to keep"
    ),
) -> None:
    """Update GitHub workflow with new version and maintain only last N versions."""
    workflow_file = update_workflow_versions(version, workflow_path, max_versions)
    typer.echo(f"✓ Successfully updated {workflow_file}")


@app.command(name="update-docs")
def update_docs(
    version: str = typer.Argument(..., help="Kubernetes version to add (format X.Y.Z)"),
    docs_path: str = typer.Option(
        "../lightkube/docs/resources-and-models.md",
        "--docs",
        "-d",
        help="Path to documentation file",
    ),
    max_versions: int = typer.Option(
        16, "--max-versions", "-m", help="Maximum number of versions to keep"
    ),
) -> None:
    """Update documentation file with new version link and maintain only last N versions."""
    docs_file = update_docs_versions(version, docs_path, max_versions)
    typer.echo(f"✓ Successfully updated {docs_file}")


if __name__ == "__main__":
    app()
