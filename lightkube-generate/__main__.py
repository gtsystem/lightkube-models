from pathlib import Path

from . import compile_resources, compile_models, __version__


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate resources from k8s API swagger file")
    parser.add_argument("command", choices=('resources', 'models'), nargs='+', help="Specification file for Kubernetes")
    parser.add_argument("specs", help="Specification file for Kubernetes")
    parser.add_argument("-d", "--dest", help="Package directory", default="lightkube")
    parser.add_argument("--docs", help="Docs directory", default="docs")
    parser.add_argument("-t", "--testdir", help="Directory where to generate the test file", default=".")
    args = parser.parse_args()

    compiler_major = __version__.split(".", 1)[0]
    if "resources" in args.command:
        compile_resources.execute(Path(args.specs), Path(args.dest), Path(args.testdir), Path(args.docs), compiler_major)
    if "models" in args.command:
        compile_models.execute(Path(args.specs), Path(args.dest), Path(args.testdir), Path(args.docs), compiler_major)

