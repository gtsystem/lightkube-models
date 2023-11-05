import json
import re
from collections import defaultdict
from typing import List
import shutil
from pathlib import Path

from .get_template import get_template
from .model import Model, Import

RE_MODEL = re.compile("^.*[.](apis?|pkg)[.]")


def collect_imports(module: Import, models: List[Model]):
    imports = set()
    for model in models:
        if model.has_properties:
            for prop in model.properties:
                if prop.import_module:
                    imports.add(prop.import_module)
        else:
            if model.import_module:
                imports.add(model.import_module)

    if module in imports:
        imports.remove(module)
    return imports


def build_module(path: Path, modules, version, compiler_major):
    p = path.joinpath("models")
    if p.exists():
        shutil.rmtree(p)
    p.mkdir()

    tmpl = get_template("models.tmpl")

    for module, models in modules.items():
        module_name = p.joinpath(f"{module}.py")
        with module_name.open("w") as fw:
            fw.write(
                tmpl.render(models=models, modules=collect_imports(Import(".", module), models)))
        print(f"Generated {module_name} with {len(models)} models")

    with p.joinpath("__init__.py").open("w") as fw:
        fw.write(f'__version__ = "{version}.{compiler_major}"\n')

    schema_file = Path(__file__).parent.joinpath("templates", "schema.py")
    shutil.copy(schema_file, p.joinpath("_schema.py"))


def sort_key(module_name):
    """
    v1alpha1 -> 1.-2.1
    v1alpha2 -> 1.-2.2
    v1beta1 -> 1.-1.1
    v1beta2 -> 1.-1.2
    v1 -> 1.2.0
    """
    try:
        version = module_name.split("_v", 1)[1]
    except:
        version = "1"
    version = version.replace("alpha", ".-2.").replace("beta", ".-1.")
    version = [int(x) for x in version.split(".")]
    version += [0] * (3 - len(version))
    return tuple(version)


def build_docs(docsdir: Path, modules, version):
    version = version.rsplit(".", 1)[0]
    docsdir = docsdir.joinpath("models")
    if docsdir.exists():
        shutil.rmtree(docsdir)
    docsdir.mkdir()
    docs_tmpl = get_template("models_docs.tmpl")
    for module, models in modules.items():
        with docsdir.joinpath(f"{module}.md").open("w") as fw:
            fw.write(docs_tmpl.render(models=models, module=module))

    docs_tmpl_idx = get_template("models_docs_index.tmpl")
    models_to_opts = defaultdict(list)
    for module, models in modules.items():
        for model in models:
            models_to_opts[model.name].append(module)
    for opts in models_to_opts.values():
        opts.sort(key=sort_key, reverse=True)

    with docsdir.joinpath(f"index.md").open("w") as fw:
        fw.write(docs_tmpl_idx.render(version=version, models_to_opts=sorted(models_to_opts.items())))


def build_docs_index(docsdir: Path, version):
    docs_tmpl = get_template("docs_index.tmpl")
    with docsdir.joinpath(f"index.md").open("w") as fw:
        fw.write(docs_tmpl.render(version=version))


def build_tests(testdir, modules):
    with testdir.joinpath("test_models.py").open('w') as fw:
        for module, models in modules.items():
            fw.write(f"from lightkube.models import {module}\n")


def execute(fname, path: Path, testdir: Path, docsdir: Path, compiler_major: str):
    with open(fname) as f:
        sw = json.load(f)

    spec_version = sw["info"]["version"].lstrip('v')
    modules = defaultdict(list)

    for name, defi in sw["definitions"].items():
        model = Model(name, defi)
        modules[model.module].append(model)

    if not docsdir.exists():
        docsdir.mkdir()
    build_module(path, modules, spec_version, compiler_major)
    build_docs(docsdir, modules, spec_version)
    build_tests(testdir, modules)
    build_docs_index(docsdir, spec_version)
