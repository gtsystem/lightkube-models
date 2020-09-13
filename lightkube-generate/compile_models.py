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


def execute(fname, path: Path, testdir: Path, compiler_major: str):
    with open(fname) as f:
        sw = json.load(f)

    p = path.joinpath("models")
    if p.exists():
        shutil.rmtree(p)
    p.mkdir()

    modules = defaultdict(list)

    for name, defi in sw["definitions"].items():
        model = Model(name, defi)
        modules[model.module].append(model)

    tmpl = get_template("models.tmpl")
    for module, models in modules.items():
        module_name = p.joinpath(f"{module}.py")
        with module_name.open("w") as fw:
            fw.write(tmpl.render(models=models, modules=collect_imports(Import(".", module), models)))
        print(f"Generated {module_name} with {len(models)} models")

    with testdir.joinpath("test_models.py").open('w') as fw:
        for module, models in modules.items():
            fw.write(f"from lightkube.models import {module}\n")

    spec_version = sw["info"]["version"].lstrip('v')
    with p.joinpath("__init__.py").open("w") as fw:
        fw.write(f'__version__ = "{spec_version}.{compiler_major}"\n')
