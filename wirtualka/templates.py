"""Named presets, reused when making the next machine."""

import json

from .constants import ROOT, TEMPLATE_FILE
from .errors import NotFound, BladWirtualki
from .util import check_name

SKIP = {"name", "created", "iso", "note"}


def load_all():
    if not TEMPLATE_FILE.is_file():
        return {}
    try:
        return json.loads(TEMPLATE_FILE.read_text())
    except json.JSONDecodeError as error:
        raise BladWirtualki(f"popsute {TEMPLATE_FILE}: {error}") from None


def save(name, config):
    check_name(name)
    ROOT.mkdir(parents=True, exist_ok=True)
    data = load_all()
    data[name] = {k: v for k, v in config.to_dict().items() if k not in SKIP}
    TEMPLATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def apply(name, config):
    data = load_all()
    if name not in data:
        raise NotFound(f"nie ma szablonu '{name}' (zobacz: wirtualka --template-list)")
    for key, value in data[name].items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config


def delete(name):
    data = load_all()
    if name not in data:
        raise NotFound(f"nie ma szablonu '{name}'")
    del data[name]
    TEMPLATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
