#!/usr/bin/env python3
import sys, pathlib
from ruamel.yaml import YAML

def main():
    root = pathlib.Path(sys.argv[1]).resolve()
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 120

    files = list(root.rglob("*.yml")) + list(root.rglob("*.yaml"))
    # ignore .git and common artifact dirs
    files = [p for p in files if ".git" not in p.parts and "artifacts" not in p.parts]

    changed = 0
    for p in sorted(files):
        txt = p.read_text(encoding="utf-8")
        data = yaml.load(txt)
        from io import StringIO
        buf = StringIO()
        yaml.dump(data, buf)
        out = buf.getvalue()
        if out != txt:
            p.write_text(out, encoding="utf-8")
            changed += 1

    print(f"Formatted YAML files changed: {changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
