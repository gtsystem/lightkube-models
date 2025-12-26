import re
import shutil
from functools import total_ordering
from pathlib import Path

import httpx
import typer
from ruamel.yaml import YAML

app = typer.Typer(
    help="Fetch Kubernetes OpenAPI specifications and list available versions"
)


# Common CLI helpers
VERSION_ARG = typer.Argument(..., help="Kubernetes version to add (format X.Y.Z)")
VER_COUNT = 16
MAX_VERSIONS_OPT = typer.Option(
    VER_COUNT, "--max-versions", "-m", help="Maximum number of versions to keep"
)
# Common default paths
DEFAULT_WORKFLOW = ".github/workflows/python-package.yml"
DEFAULT_DOCS = "../lightkube/docs/resources-and-models.md"
DEFAULT_README = "../lightkube/README.md"
DEFAULT_SITE = "site"
DEFAULT_OPENAPI_DIR = "openapi"


@total_ordering
class Version:
    """Kubernetes version representation with comparison and validation."""

    VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")

    def __init__(self, version: str):
        """Parse and validate version string in format X.Y or X.Y.Z (patch is discarded)."""
        match = self.VERSION_PATTERN.match(version)
        if not match:
            raise ValueError(
                f"Version {version} must match expression \\d+.\\d+(.\\d+)?"
            )
        self.major = int(match.group(1))
        self.minor = int(match.group(2))

    def __str__(self) -> str:
        """Return version as X.Y string."""
        return f"{self.major}.{self.minor}"

    def __eq__(self, other) -> bool:
        """Compare versions for equality."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) == (other.major, other.minor)

    def __lt__(self, other) -> bool:
        """Compare versions for less than."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) < (other.major, other.minor)

    def distance_from(self, other: "Version") -> int:
        """Calculate version distance (major.minor only) from another version."""
        return (self.major * 100 + self.minor) - (other.major * 100 + other.minor)

    def is_within_last_n_versions(
        self, reference: "Version", max_versions: int
    ) -> bool:
        """Check if this version is within the last N versions from a reference version."""
        distance = reference.distance_from(self)
        return 0 <= distance < max_versions

    def oldest_version_in_range(self, max_versions: int) -> "Version":
        """Calculate the oldest version to keep within the last N versions."""
        oldest_minor = max(self.minor - (max_versions - 1), 0)
        return Version(f"{self.major}.{oldest_minor}")


def list_kubernetes_tags(count: int = 10) -> list[str]:
    """List the last N version tags from kubernetes/kubernetes repository."""
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


def fetch_spec(version: str, output_dir: str = DEFAULT_OPENAPI_DIR) -> Path:
    """Fetch Kubernetes OpenAPI spec for a given version."""
    # Validate version format
    Version(version)

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
    version: str, workflow_path: str = DEFAULT_WORKFLOW, max_versions: int = VER_COUNT
) -> Path:
    """Update GitHub workflow with new version and maintain only last N versions"""
    # Validate version format
    Version(version)

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
    version: str, docs_path: str = DEFAULT_DOCS, max_versions: int = VER_COUNT
) -> Path:
    """Update documentation file with new version link and maintain only last N versions"""
    # Validate version format
    ver = Version(version)

    docs_file = Path(docs_path)
    if not docs_file.exists():
        raise FileNotFoundError(f"Documentation file not found: {docs_path}")

    # Pattern to find version links
    version_pattern = (
        r"\[(\d+\.\d+)\]\(https://gtsystem\.github\.io/lightkube-models/\d+\.\d+\)"
    )

    # Read file line by line
    lines = docs_file.read_text().splitlines(keepends=True)
    new_lines = []
    first_version_idx = -1
    version_lines = []

    # First pass: separate version lines from other lines
    for line in lines:
        match = re.search(version_pattern, line)
        if match:
            line_ver = Version(match.group(1))

            if first_version_idx == -1:
                first_version_idx = len(new_lines)

            # Calculate distance from new version
            if line_ver.is_within_last_n_versions(ver, max_versions):
                version_lines.append(str(line_ver))
            else:
                print(f"Removed old version {line_ver}")
        else:
            # Non-version line
            if first_version_idx == -1 or not version_lines:
                # Before first version or no versions yet
                new_lines.append(line)
            # else: we're past the version block, will add later

    # Add new version if needed
    if version_lines[0] != str(ver):
        version_lines.insert(0, str(ver))
        print(f"Added version {version_lines[0]}")
    else:
        print(f"Version {ver} already in documentation")

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


def update_readme_versions(
    version: str, readme_path: str = DEFAULT_README, max_versions: int = VER_COUNT
) -> Path:
    """Update README file with new version range"""
    # Validate version format
    newest_ver = Version(version)

    readme_file = Path(readme_path)
    if not readme_file.exists():
        raise FileNotFoundError(f"README file not found: {readme_path}")

    oldest_version = newest_ver.oldest_version_in_range(max_versions)
    print(oldest_version, newest_ver)
    # Read the file
    content = readme_file.read_text()

    # Pattern to find version range in README
    # Matches: "1.20 to 1.35" or similar patterns
    version_range_pattern = r"(\d+\.\d+)\s+to\s+(\d+\.\d+)"

    def replace_version_range(match):
        return f"{oldest_version} to {newest_ver}"

    # Replace the version range
    new_content, count = re.subn(version_range_pattern, replace_version_range, content)

    if count > 0:
        readme_file.write_text(new_content)
        print(f"Updated version range to {oldest_version} to {newest_ver}")
        print(f"Updated {readme_file}")
    else:
        print(f"No version range pattern found in {readme_file}")

    return readme_file


def cleanup_site_dirs(
    version: str, site_path: str = DEFAULT_SITE, max_versions: int = VER_COUNT
) -> Path:
    """Clean up old version directories in site folder, keeping only last N versions"""
    # Validate version format
    ver = Version(version)

    site_dir = Path(site_path)
    if not site_dir.exists():
        raise FileNotFoundError(f"Site directory not found: {site_path}")

    # Pattern to match version directories (e.g., 1.35, 1.34, etc.)
    version_dir_pattern = re.compile(r"^(\d+)\.(\d+)$")

    # Iterate through directories and check if they should be deleted
    deleted_count = 0
    skipped_count = 0

    for item in site_dir.iterdir():
        if item.is_dir():
            match = version_dir_pattern.match(item.name)
            if match:
                dir_ver = Version(f"{match.group(1)}.{match.group(2)}")

                # Should delete if not within last N versions
                if not dir_ver.is_within_last_n_versions(ver, max_versions):
                    response = typer.confirm(
                        f"Delete directory '{item.name}'?", default=False
                    )
                    if response:
                        shutil.rmtree(item)
                        print(f"Deleted {item.name}")
                        deleted_count += 1
                    else:
                        print(f"Skipped {item.name}")
                        skipped_count += 1

    if deleted_count > 0 or skipped_count > 0:
        print(f"\nCleanup summary: {deleted_count} deleted, {skipped_count} skipped")
    else:
        print("No directories need cleanup")

    return site_dir


@app.command()
def fetch(
    version: str = VERSION_ARG,
    output_dir: str = typer.Option(
        DEFAULT_OPENAPI_DIR,
        "--output-dir",
        "-o",
        help="Directory to save the spec file",
    ),
) -> None:
    """Fetch Kubernetes OpenAPI spec for a given version."""
    output_file = fetch_spec(version, output_dir)
    typer.echo(f"✓ Successfully saved spec to {output_file}")


@app.command()
def list(count: int = typer.Argument(10, help="Number of tags to retrieve")) -> None:
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
    version: str = VERSION_ARG,
    workflow_path: str = typer.Option(
        DEFAULT_WORKFLOW,
        "--workflow",
        "-w",
        help="Path to workflow file",
    ),
    max_versions: int = MAX_VERSIONS_OPT,
) -> None:
    """Update GitHub workflow with new version and maintain only last N versions."""
    workflow_file = update_workflow_versions(version, workflow_path, max_versions)
    typer.echo(f"✓ Successfully updated {workflow_file}")


@app.command(name="update-docs")
def update_docs(
    version: str = VERSION_ARG,
    docs_path: str = typer.Option(
        DEFAULT_DOCS,
        "--docs",
        "-d",
        help="Path to documentation file",
    ),
    max_versions: int = MAX_VERSIONS_OPT,
) -> None:
    """Update documentation file with new version link and maintain only last N versions."""
    docs_file = update_docs_versions(version, docs_path, max_versions)
    typer.echo(f"✓ Successfully updated {docs_file}")


@app.command(name="update-readme")
def update_readme(
    version: str = VERSION_ARG,
    readme_path: str = typer.Option(
        DEFAULT_README, "--readme", "-r", help="Path to README file"
    ),
    max_versions: int = MAX_VERSIONS_OPT,
) -> None:
    """Update README file with new version range."""
    readme_file = update_readme_versions(version, readme_path, max_versions)
    typer.echo(f"✓ Successfully updated {readme_file}")


@app.command(name="cleanup-site")
def cleanup_site(
    version: str = VERSION_ARG,
    site_path: str = typer.Option(
        DEFAULT_SITE, "--site", "-s", help="Path to site directory"
    ),
    max_versions: int = MAX_VERSIONS_OPT,
) -> None:
    """Clean up old version directories in site folder."""
    site_dir = cleanup_site_dirs(version, site_path, max_versions)
    typer.echo(f"✓ Successfully cleaned up {site_dir}")


if __name__ == "__main__":
    app()
