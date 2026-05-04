#!/usr/bin/env python3
"""
Insert LCSC, MPN, and (optionally) Source custom property fields into every
top-level (symbol ...) instance in each *.kicad_sch under a project directory.

Idempotent: re-running updates existing values rather than duplicating fields.

Used in Phase 7 of the kicad-schematic skill workflow: after the schematic
is otherwise complete and ERC-clean, this script populates per-component
metadata so KiCad's BOM exporter can emit a JLCPCB-ready CSV directly.

Usage:
    python3 inject_lcsc_fields.py \\
        --sch-dir <project>/<project_name> \\
        --bom <project>/bom.csv \\
        [--families <project>/bom_families.csv] \\
        [--skip-prefixes TP,H,NT,J,SW,L,FB] \\
        [--dry-run]

CSV formats:

  --bom (by-refdes lookup):
      Reference,MPN,LCSC,Source
      U205,AP2114H-3.3TRG1,C150716,
      U500,ADG1406BRUZ,,Consignment

  --families (by-Value+Footprint pattern):
      Value,Footprint,MPN,LCSC,Source
      100nF,C_0402_1005Metric,CL05B104KB54PNC,C307331,
      10uF,C_0805_2012Metric,CL21A106KAYNNNE,C15850,

  Range expansion: refdes ranges in --bom are written as `D208-D239` and
  expanded to D208, D209, ..., D239 at load time.

Source field is optional; leave empty for normal JLCPCB-stocked parts.
Set to "Consignment" (or any free text) for parts sourced outside JLCPCB.

Skip prefixes default to common non-electrical refdes (test points,
mounting holes, net ties, connectors, switches, inductors, ferrites).
Override with --skip-prefixes to include or exclude specific families.
"""
import argparse
import csv
import os
import re
import sys
from glob import glob


def find_instance_blocks(text):
    """Return list of (start_line, end_line) tuples for top-level (symbol ...)
    instances in a .kicad_sch file. A top-level symbol is at single-tab indent;
    library symbols inside (lib_symbols ...) are at double-tab indent and are
    correctly excluded."""
    lines = text.split("\n")
    instances = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("\t(symbol") and not line.startswith("\t\t"):
            depth = 0
            j = i
            started = False
            while j < len(lines):
                for ch in lines[j]:
                    if ch == "(":
                        depth += 1
                        started = True
                    elif ch == ")":
                        depth -= 1
                if started and depth == 0:
                    instances.append((i, j))
                    i = j + 1
                    break
                j += 1
            else:
                break
        else:
            i += 1
    return instances


def get_property_value(block_lines, name):
    """Return the value of a (property "name" "...") in the symbol block, or None."""
    pat = re.compile(r'\(property\s+"' + re.escape(name) + r'"\s+"([^"]*)"')
    for line in block_lines:
        m = pat.search(line)
        if m:
            return m.group(1)
    return None


def find_property_span(block_lines, name):
    """Return (start_idx, end_idx) inclusive for the (property "name" ...) S-expression
    in block_lines, or None if absent."""
    pat = re.compile(r'^(\t+)\(property\s+"' + re.escape(name) + r'"\s+')
    for idx, line in enumerate(block_lines):
        if not pat.match(line):
            continue
        depth = 0
        started = False
        for j in range(idx, len(block_lines)):
            for ch in block_lines[j]:
                if ch == "(":
                    depth += 1
                    started = True
                elif ch == ")":
                    depth -= 1
            if started and depth == 0:
                return (idx, j)
        return None
    return None


def make_property_block(name, value, indent="\t\t"):
    """Build a hidden (property "name" "value" ...) block at (0 0 0)."""
    return [
        f'{indent}(property "{name}" "{value}"',
        f'{indent}\t(at 0 0 0)',
        f'{indent}\t(effects',
        f'{indent}\t\t(font',
        f'{indent}\t\t\t(size 1.27 1.27)',
        f'{indent}\t\t)',
        f'{indent}\t\t(hide yes)',
        f'{indent}\t)',
        f'{indent})',
    ]


def update_or_insert_property(block_lines, name, value, insert_after_idx):
    """Update an existing property's value or insert a new property block.
    Returns (new_block_lines, action) where action ∈ {'updated', 'inserted', 'unchanged'}."""
    span = find_property_span(block_lines, name)
    if span is not None:
        start, end = span
        existing_val = get_property_value(block_lines[start:end + 1], name)
        if existing_val == value:
            return block_lines, "unchanged"
        first = block_lines[start]
        new_first = re.sub(
            r'^(\t+\(property\s+"' + re.escape(name) + r'"\s+")[^"]*(".*)$',
            r'\g<1>' + value.replace("\\", "\\\\") + r'\g<2>',
            first,
        )
        if new_first == first:
            raise RuntimeError(
                f"Failed to substitute value for property {name!r} in line: {first!r}"
            )
        new_lines = block_lines.copy()
        new_lines[start] = new_first
        return new_lines, "updated"
    else:
        new_block = make_property_block(name, value, indent="\t\t")
        new_lines = block_lines[:insert_after_idx + 1] + new_block + block_lines[insert_after_idx + 1:]
        return new_lines, "inserted"


def expand_refdes_range(spec):
    """Expand 'D208-D239' to ['D208', 'D209', ..., 'D239'].
    Plain refdes like 'U205' returns ['U205'].
    Comma-separated lists 'C407,C408' return both."""
    out = []
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        m = re.match(r"^([A-Za-z#]+)(\d+)\s*[-–]\s*\1?(\d+)$", piece)
        if m:
            prefix, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
            for n in range(lo, hi + 1):
                out.append(f"{prefix}{n}")
        else:
            out.append(piece)
    return out


def load_bom_csv(path):
    """Load a by-refdes BOM CSV. Returns dict: refdes -> (mpn, lcsc, source)."""
    refdes_map = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            refspec = row.get("Reference", "").strip()
            if not refspec or refspec.startswith("#"):
                continue
            mpn = row.get("MPN", "").strip()
            lcsc = row.get("LCSC", "").strip()
            source = row.get("Source", "").strip()
            for ref in expand_refdes_range(refspec):
                refdes_map[ref] = (mpn, lcsc, source)
    return refdes_map


def load_families_csv(path):
    """Load a family-rules CSV. Returns list of dicts with value/footprint patterns."""
    families = []
    if not path or not os.path.exists(path):
        return families
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            value = row.get("Value", "").strip()
            footprint = row.get("Footprint", "").strip()
            mpn = row.get("MPN", "").strip()
            lcsc = row.get("LCSC", "").strip()
            source = row.get("Source", "").strip()
            if not value or not footprint:
                continue
            families.append({
                "value": value,
                "footprint_substr": footprint,
                "mpn": mpn,
                "lcsc": lcsc,
                "source": source,
            })
    return families


def lookup_family(value, footprint, families):
    """Match (Value, Footprint) against family rules. Footprint match is substring;
    Value match is exact. First match wins."""
    for fam in families:
        if value.strip() == fam["value"] and fam["footprint_substr"] in footprint:
            return (fam["mpn"], fam["lcsc"], fam["source"])
    return None


def determine_lcsc_mpn(refdes, value, footprint, refdes_map, families, skip_prefixes):
    """Return (mpn, lcsc, source) or None if the refdes should be skipped."""
    if not refdes or refdes.startswith("#"):
        return None
    for prefix in skip_prefixes:
        if refdes.startswith(prefix):
            return None
    if refdes in refdes_map:
        return refdes_map[refdes]
    return lookup_family(value, footprint, families)


def process_file(path, refdes_map, families, skip_prefixes, dry_run=False):
    """Inject LCSC/MPN/Source fields into every symbol in one .kicad_sch file."""
    with open(path, "r") as f:
        text = f.read()
    lines = text.split("\n")
    instances = find_instance_blocks(text)

    stats = {"updated": 0, "inserted": 0, "unchanged": 0, "skipped": 0}
    skipped_refs = []

    for start, end in reversed(instances):
        block_lines = lines[start:end + 1]
        ref = get_property_value(block_lines, "Reference")
        val = get_property_value(block_lines, "Value")
        fp = get_property_value(block_lines, "Footprint")

        match = determine_lcsc_mpn(ref, val or "", fp or "", refdes_map, families, skip_prefixes)
        if match is None:
            stats["skipped"] += 1
            skipped_refs.append((ref, val, fp))
            continue

        mpn, lcsc, source = match

        desc_span = find_property_span(block_lines, "Description")
        if desc_span is None:
            raise RuntimeError(
                f"Symbol {ref!r} in {path} missing Description property — "
                f"cannot determine where to insert LCSC/MPN."
            )
        insert_after = desc_span[1]

        new_block = block_lines

        # Insert/update LCSC, then MPN, then Source (if non-empty).
        for fname, fval in [("LCSC", lcsc), ("MPN", mpn)]:
            new_block, act = update_or_insert_property(new_block, fname, fval, insert_after)
            stats[act] = stats.get(act, 0) + 1
            span = find_property_span(new_block, fname)
            insert_after = span[1]

        if source:
            new_block, act = update_or_insert_property(new_block, "Source", source, insert_after)
            stats[act] = stats.get(act, 0) + 1

        lines = lines[:start] + new_block + lines[end + 1:]

    new_text = "\n".join(lines)
    changed = new_text != text
    if changed and not dry_run:
        with open(path, "w") as f:
            f.write(new_text)
    return stats, skipped_refs, changed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sch-dir", required=True, help="Directory containing *.kicad_sch files")
    ap.add_argument("--bom", required=True, help="By-refdes BOM CSV (Reference,MPN,LCSC,Source)")
    ap.add_argument("--families", help="Optional family-rules CSV (Value,Footprint,MPN,LCSC,Source)")
    ap.add_argument(
        "--skip-prefixes",
        default="TP,H,NT,J,SW,L,FB",
        help="Comma-separated refdes prefixes to skip (default: TP,H,NT,J,SW,L,FB)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Compute changes but don't write files")
    args = ap.parse_args()

    refdes_map = load_bom_csv(args.bom)
    families = load_families_csv(args.families) if args.families else []
    skip_prefixes = [p.strip() for p in args.skip_prefixes.split(",") if p.strip()]

    print(f"Loaded {len(refdes_map)} refdes entries from {args.bom}")
    if families:
        print(f"Loaded {len(families)} family rules from {args.families}")
    print(f"Skip prefixes: {skip_prefixes}")
    print(f"{'DRY RUN — no files written' if args.dry_run else 'Writing changes to disk'}")
    print()

    files = sorted(glob(os.path.join(args.sch_dir, "*.kicad_sch")))
    if not files:
        print(f"ERROR: no *.kicad_sch files in {args.sch_dir}", file=sys.stderr)
        return 1

    grand_total = {"updated": 0, "inserted": 0, "unchanged": 0, "skipped": 0}
    all_skipped = []
    files_changed = 0

    for path in files:
        fn = os.path.basename(path)
        stats, skipped, changed = process_file(
            path, refdes_map, families, skip_prefixes, dry_run=args.dry_run
        )
        if changed:
            files_changed += 1
        print(f"{fn}: {stats}")
        for k, v in stats.items():
            grand_total[k] = grand_total.get(k, 0) + v
        for ref, val, fp in skipped:
            all_skipped.append((fn, ref, val, fp))

    print("---")
    print(f"TOTAL: {grand_total}")
    print(f"Files changed: {files_changed} / {len(files)}")

    if all_skipped:
        print()
        print(f"Skipped instances ({len(all_skipped)}) — refdes prefix matched skip-list, "
              f"or no BOM/family entry:")
        for fn, ref, val, fp in all_skipped:
            print(f"  {fn:30s}  {ref or '(no ref)':10s}  {val or '':20s}  {fp or ''}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
