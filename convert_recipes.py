#!/usr/bin/env python3
"""
Convert legacy recipes.yaml (mapping-style) -> v3.5 list-style recipe file.

Usage:
    python convert_recipes.py \
        --old recipes.yaml \
        --raw raw_goods.yaml \
        --produced produced_goods.yaml \
        --out recipes_converted.yaml
"""
import argparse, math, yaml, sys
from pathlib import Path

def load_goods(paths):
    per_kg = {}
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        data = yaml.safe_load(p.read_text()) or {}
        goods = data.get('goods', {}) or {}
        for gid, g in goods.items():
            measure = g.get('measure', {}) or {}
            per_unit = measure.get('per_unit_kg')
            discrete = measure.get('discrete', False)
            per_kg[gid] = {
                'per_unit_kg': float(per_unit) if per_unit is not None else 1.0,
                'discrete': bool(discrete)
            }
    return per_kg

def convert_amounts(mapping, per_kg_map, warnings):
    out = {}
    for item, amt in (mapping or {}).items():
        if item not in per_kg_map:
            warnings.append(f"Unknown good '{item}' — using per_unit_kg=1.0 (fix or map manually).")
            per = 1.0
        else:
            per = per_kg_map[item]['per_unit_kg']
        # amt is in units of the old schema; convert to kg
        out[item] = float(amt) * float(per)
    return out

def convert_recipe(old_id, old_obj, per_kg_map, warnings):
    # old_obj expected to be a dict
    new = {}
    new['id'] = old_id
    new['facility'] = old_obj.get('facility')
    new['inputs'] = convert_amounts(old_obj.get('inputs', {}), per_kg_map, warnings)
    new['outputs'] = convert_amounts(old_obj.get('outputs', {}), per_kg_map, warnings)
    new['byproducts'] = convert_amounts(old_obj.get('byproducts', {}) or {}, per_kg_map, warnings)

    # time conversion
    if 'cycle_time_s' in old_obj:
        new['cycle_time_minutes'] = math.ceil(float(old_obj['cycle_time_s']) / 60.0)
    else:
        new['cycle_time_minutes'] = old_obj.get('cycle_time_minutes', 60)

    # workers/labor mapping
    new['workers_required'] = int(old_obj.get('labor', old_obj.get('workers_required', 1)))

    # skill mapping: best-effort; set defaults
    new['skill_used'] = old_obj.get('skill_used', old_obj.get('skill', '')) or ''
    # old schemas sometimes have requirements.min_tier — we conservatively map to min_skill=0
    new['min_skill'] = int(old_obj.get('min_skill', 0))

    # waste chance: default 0.0
    new['waste_chance'] = float(old_obj.get('waste_chance', 0.0))

    return new

def main(args):
    oldp = Path(args.old)
    if not oldp.exists():
        print("Old recipes file not found:", oldp, file=sys.stderr)
        sys.exit(2)

    old = yaml.safe_load(oldp.read_text())
    old_recipes = old.get('recipes', {})

    per_kg_map = load_goods([args.raw, args.produced])
    warnings = []
    new_recipes = []

    # handle both mapping and list legacy shapes
    if isinstance(old_recipes, dict):
        for rid, robj in old_recipes.items():
            new_recipes.append(convert_recipe(rid, robj, per_kg_map, warnings))
    elif isinstance(old_recipes, list):
        # already list-style but might be old vX style -> convert entries by id
        for entry in old_recipes:
            rid = entry.get('id') or entry.get('name') or 'unnamed'
            new_recipes.append(convert_recipe(rid, entry, per_kg_map, warnings))
    else:
        raise RuntimeError("Unknown recipes shape in old file")

    out = {
        'schema_version': "3.5",
        'file': Path(args.out).name,
        'recipes': new_recipes
    }

    Path(args.out).write_text(yaml.safe_dump(out, sort_keys=False))
    print(f"✓ WROTE {args.out} ({len(new_recipes)} recipes converted)")
    if warnings:
        print("\n⚠ WARNINGS (review):")
        for w in sorted(set(warnings)):
            print(" -", w)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--old', required=True)
    p.add_argument('--raw', required=True)
    p.add_argument('--produced', required=True)
    p.add_argument('--out', required=True)
    main(p.parse_args())
