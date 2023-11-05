import re
from typing import NamedTuple
import keyword

RE_MODEL = re.compile("^.*[.](apis?|pkg)[.]")
RE_NEW_LINE = re.compile(r"\n\s*\n")
KEYWORDS = set(keyword.kwlist)


class Schema(NamedTuple):
    name: str
    module: str = None

    def full_name(self):
        if self.module:
            return f"{self.module}.{self.name}"
        return None


def schema_name(orig_name) -> Schema:
    module = RE_MODEL.sub("", orig_name)
    parts = module.split(".")
    assert len(parts) <= 3
    if len(parts) == 3:
        module = f"{parts[0]}_{parts[1]}"
    else:
        module = parts[0]
    model = parts[-1]
    return Schema(module=module, name=model)


def make_prop_name(p_name):
    if p_name in KEYWORDS:
        return f'{p_name}_'
    p_name = p_name.replace('$', 'd_')
    p_name = p_name.replace('-', '_')
    return p_name


def get_module_from_property_def(defi):
    if '$ref' in defi:
        return Import(".", schema_name(defi['$ref']).module)
    elif 'items' in defi and '$ref' in defi['items']:
        return Import(".", schema_name(defi['items']['$ref']).module)


class Import(NamedTuple):
    from_module: str
    module: str


class Property(NamedTuple):
    name: str
    type: str
    required: bool
    import_module: Import
    alias: str = None
    description: str = ""

    @property
    def default_repr(self):
        if not self.alias:
            return ' = None' if not self.required else ''
        else:
            if not self.required:
                return f' = field(metadata={{"json": "{self.alias}"}}, default=None)'
            return f' = field(metadata={{"json": "{self.alias}"}})'


class Model:
    OAS_TO_PY = {
        'string': 'str',
        'integer': 'int',
        'number': 'float',
        'boolean': 'bool',
        'object': 'dict'
    }

    def __init__(self, name, defi):
        sc = schema_name(name)
        self.module = sc.module
        self.name = sc.name
        self.import_module = None
        self.type = None
        self.description = defi.get("description")
        if 'properties' in defi:
            self.properties = self.get_props(defi)
        else:
            self.properties = None
            if 'type' not in defi:  # reference to any json type
                self.type = 'Any'
                self.import_module = Import('typing', 'Any')
            elif defi['type'] == 'object':
                self.type = 'Dict'
                self.import_module = Import('typing', 'Dict')
            elif defi['type'] == 'string':
                if 'format' not in defi:
                    self.type = 'str'
                elif defi['format'] == 'date-time':
                    self.type = 'datetime'
                    self.import_module = Import('datetime', 'datetime')
                elif defi['format'] == 'int-or-string':
                    self.type = 'Union[int, str]'
                    self.import_module = Import('typing', 'Union')

    @property
    def has_properties(self):
        return bool(self.properties)

    def get_props(self, defi):
        required = set(defi.get('required', []))
        properties = []
        for p_name, p_defi in defi['properties'].items():
            req = p_name in required
            p_type = self.to_pytype(p_defi, required=req)
            real_name = make_prop_name(p_name)
            desc = p_defi.get("description")
            if desc:
                desc = RE_NEW_LINE.sub("\n", desc)
            properties.append(Property(
                name=real_name,
                type=p_type,
                required=req,
                import_module=get_module_from_property_def(p_defi),
                alias=p_name if p_name != real_name else None,
                description=desc
            ))

        properties.sort(key=lambda x: x.required, reverse=True)
        return properties

    def to_pytype(self, defi, required=True):
        if not required:
            return f'Optional[{self.to_pytype(defi)}]'
        if 'items' in defi:
            return f'List[{self.to_pytype(defi["items"])}]'

        if '$ref' in defi:
            sc = schema_name(defi['$ref'])
            if sc.module == self.module:
                return sc.name
            else:
                return f'{sc.module}.{sc.name}'

        if 'type' in defi:
            return self.OAS_TO_PY[defi['type']]

