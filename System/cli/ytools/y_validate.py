#!/usr/bin/env python3
import sys, pathlib, json
from ruamel.yaml import YAML

def load_schema(schema_path: pathlib.Path):
    import jsonschema
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return schema, jsonschema

def yaml_to_obj(path: pathlib.Path):
    yaml = YAML(typ="safe")
    return yaml.load(path.read_text(encoding="utf-8"))

def main():
    root = pathlib.Path(sys.argv[1]).resolve()
    schema_path = root / "schema" / "schema.json"
    use_schema = schema_path.exists()

    schema = None
    jsonschema = None
    if use_schema:
        schema, jsonschema = load_schema(schema_path)

    files = list(root.rglob("*.yml")) + list(root.rglob("*.yaml"))
    files = [p for p in files if ".git" not in p.parts and "artifacts" not in p.parts]

    errors = 0
    for p in sorted(files):
        try:
            obj = yaml_to_obj(p)
        except Exception as e:
            print(f"[YAML PARSE ERROR] {p}: {e}")
            errors += 1
            continue

        if use_schema:
            try:
                jsonschema.validate(instance=obj, schema=schema)
            except Exception as e:
                print(f"[SCHEMA ERROR] {p}: {e}")
                errors += 1

    if use_schema:
        print(f"Validation done (with schema). Errors: {errors}")
    else:
        print(f"Validation done (YAML parse only; no schema found at {schema_path}). Errors: {errors}")

    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
