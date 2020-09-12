import json
import shutil
from collections import defaultdict
import re
from pathlib import Path
from typing import NamedTuple, Iterable, Dict, List, Optional

from .get_template import get_template

RE_PATH = re.compile("/apis?(?P<group>/.*?)?/(?P<version>v[^/]*)(?P<watch>/watch)?"
                     "(?P<ns>/namespaces/{namespace})?/(?P<plural>[^/]*)"
                     "(?:/{name}(?P<action>/[^/]*)?)?")


class ApiKey(NamedTuple):
    group: str
    version: str
    plural: str


class Resource(NamedTuple):
    group: str
    version: str
    kind: str

    def definition(self):
        return f"res.ResourceDef{tuple(self)}"

    @property
    def py_import(self):
        group, version, name = self
        if group == '':
            group = 'core'
        group = group.split(".", 1)[0]
        return f"{group}_{version}"

    @property
    def py_full_class(self):
        return f"{self.py_import}.{self.kind}"


class SpecPath(NamedTuple):
    path: str
    group_key: ApiKey
    resource: Resource
    methods: list
    module: str
    namespaced: bool
    sub_action: str

    def to_subaction(self):
        return SubAction(self.sub_action, usorted(self.methods), self.resource)


class SubAction(NamedTuple):
    name: str
    actions:  List
    resource: Resource


class Compiled(NamedTuple):
    resource: Resource
    plural: str
    module: str
    namespaced: bool
    actions: list
    sub_actions: List[SubAction]


class Class(NamedTuple):
    name: str
    properties: Dict[str, str]
    actions: Dict[str, str]
    classes: List[str]
    model_import: str


def extract(fname: Path):
    """Extract the main information from each path entry"""
    with fname.open() as f:
        sw = json.load(f)

    for path, defi in sw["paths"].items():
        g = RE_PATH.match(path)
        if g is None:
            continue
        path_match = g.groupdict()
        if path_match["watch"]:     # watch apis are deprecated
            continue

        key = ApiKey((path_match["group"] or "").lstrip("/"), path_match["version"], path_match["plural"])
        if not key.plural:
            #print(key)
            continue

        methods = []
        resource = None
        tags = set()
        namespaced = path_match["ns"] is not None
        sub_action = path_match["action"].lstrip("/") if path_match["action"] else None
        for method, mdef in defi.items():
            if method != "parameters":
                action = mdef.get('x-kubernetes-action', method)
                if action != 'connect':     # TODO: add support for connect
                    methods.append(action)
                if resource is None:
                    resource = mdef.get("x-kubernetes-group-version-kind")
                tags.update(set(mdef.get('tags', [])))
                if "parameters" in mdef:
                    for parameter in mdef["parameters"]:
                        if parameter["name"] == "watch":
                            methods.append("watch")
                            break
            else:
                for parameter in mdef:
                    if parameter["name"] == "watch":
                        methods.append("watch")
        if resource:
            resource = Resource(**resource)
        else:
            print(path)

        if methods:     # at least one method
            yield SpecPath(
                path=path,
                group_key=key,
                resource=resource,
                methods=methods,
                module=tags.pop(),
                namespaced=namespaced,
                sub_action=sub_action
            )


def aggregate(it: Iterable[SpecPath]):
    resources = defaultdict(list)
    for ele in it:
        key = ele.group_key
        resources[key].append(ele)
    return resources


def usorted(l):
    return sorted(set(l))


def compile_one(key: ApiKey, elements: List[SpecPath]) -> Optional[Compiled]:
    namespaced = False
    module = None
    resource = None
    for ele in elements:
        if ele.namespaced:
            namespaced = True
        if ele.resource and ele.sub_action is None:
            resource = ele.resource
        if not module and ele.module:
            module = ele.module

    if resource is None:
        return

    sub_actions = []
    actions = set()
    for ele in elements:
        if ele.sub_action:
            sub_actions.append(ele.to_subaction())
        elif namespaced and not ele.namespaced:
            actions.update([f"global_{m}" for m in ele.methods])
        else:
            actions.update(ele.methods)

    if resource:
        return Compiled(
            resource=resource,
            plural=key.plural,
            module=module,
            namespaced=namespaced,
            actions=usorted(actions),
            sub_actions=sub_actions
        )


def get_classes(compiled: Compiled):
    res = compiled.resource

    class_ = "NamespacedSubResource" if compiled.namespaced else "GlobalSubResource"
    actions = {}
    for suba in compiled.sub_actions:
        kind = res.kind + suba.name.capitalize()
        sres = suba.resource

        yield Class(
            name=kind,
            properties=dict(
                resource=sres.definition(), parent=res.definition(),
                plural=repr(compiled.plural), verbs=suba.actions, action=repr(suba.name),
            ),
            actions={},
            classes=[class_, f"m_{sres.py_full_class}"],
            model_import=sres.py_import
        )
        actions[suba.name.capitalize()] = kind

    if 'global_list' in compiled.actions:
        class_ = "NamespacedResourceG"
    else:
        class_ = "NamespacedResource" if compiled.namespaced else "GlobalResource"

    yield Class(
        name=res.kind,
        properties=dict(resource=res.definition(), plural=repr(compiled.plural), verbs=compiled.actions),
        actions=actions,
        classes=[class_, f"m_{res.py_full_class}"],
        model_import=res.py_import
    )


def compile_resources(apikey_to_paths: Dict[ApiKey, List[SpecPath]], path: Path, test_fname: Path):
    p = path.joinpath("resources")
    if p.exists():
        shutil.rmtree(p)
    p.mkdir()
    modules = defaultdict(list)
    for api_key, elements in apikey_to_paths.items():
        c = compile_one(api_key, elements)
        if c:
            modules[c.module].append(c)

    tmpl = get_template("resources.tmpl")
    for module, compiled_res in modules.items():
        module_name = p.joinpath(f"{module}.py")

        imports = set()
        classes = []
        for c in compiled_res:
            for cls in get_classes(c):
                classes.append(cls)
                imports.add(cls.model_import)

        imports = [f"{t} as m_{t}" for t in sorted(imports)]

        with module_name.open('w') as fw:
            fw.write(tmpl.render(objects=classes, imports=imports))
        print(f"Generated {module_name} with {len(classes)} resources")

    with test_fname.open('w') as fw:
        for module in modules.keys():
            fw.write(f"from lightkube.resources import {module}\n")


def execute(specs: Path, dest: Path, testdir: Path):
    compile_resources(aggregate(extract(specs)), dest, testdir.joinpath("test_resources.py"))
