try:
    from lightkube.core.schema import DictMixin, field, dataclass

except ImportError:
    # Support for older version of lightkube that lack this class
    from dataclasses import dataclass, field
    from typing import Union, get_type_hints
    from ..core.dataclasses_dict import DataclassDictMixIn as DictMixin, get_args, get_origin
    from ..core import dataclasses_dict

    NoneType = type(None)

    def _remove_optional(tp):
       if get_origin(tp) is Union:
         args = get_args(tp)
         if args[1] is NoneType:
           return args[0]
       return tp

    def _get_type_hints(cl):
        types = get_type_hints(cl)
        return {k: _remove_optional(v) for k, v in types.items()}

    # patch dataclasses_dict so that Optional is removed as it's not supported by old lightkube versions
    dataclasses_dict.get_type_hints = _get_type_hints
