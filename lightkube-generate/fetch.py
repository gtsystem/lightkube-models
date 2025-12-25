import re
import sys
from pathlib import Path

import httpx


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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m lightkube-generate.fetch <version>")
        print("Example: python -m lightkube-generate.fetch 1.35.0")
        sys.exit(1)

    try:
        fetch_spec(sys.argv[1])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
