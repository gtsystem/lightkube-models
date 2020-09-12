from pathlib import Path

from jinja2 import Template


def get_template(template_name):
    fname = Path(__file__).parent.joinpath("templates", template_name)
    with open(fname) as f:
        return Template(f.read(), trim_blocks=True, lstrip_blocks=True)
