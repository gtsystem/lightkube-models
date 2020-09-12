from pathlib import Path

from . import compile_resources
from . import compile_models


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate resources from k8s API swagger file")
    parser.add_argument("command", choices=('resources', 'models'), nargs='+', help="Specification file for Kubernetes")
    parser.add_argument("specs", help="Specification file for Kubernetes")
    parser.add_argument("-d", "--dest", help="Package directory", default="lightkube")
    parser.add_argument("-t", "--testdir", help="Directory where to generate the test file", default=".")
    args = parser.parse_args()

    if "resources" in args.command:
        compile_resources.execute(Path(args.specs), Path(args.dest), Path(args.testdir))
    if "models" in args.command:
        compile_models.execute(Path(args.specs), Path(args.dest), Path(args.testdir))

