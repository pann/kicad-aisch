#!/usr/bin/env python3
"""Extract specific components from easyeda2kicad shared library into a project-specific library.

easyeda2kicad appends all imports to a shared library at ~/Documents/Kicad/easyeda2kicad/.
This script extracts only the needed components and creates clean project-specific libraries
with correct naming and internal references.

Usage:
    python3 scripts/extract_easyeda_libs.py <project_dir> <project_name> <lcsc_id> [<lcsc_id> ...]

Example:
    python3 scripts/extract_easyeda_libs.py marklin-wifi-ctrl marklin-wifi-ctrl C2838502 C29981 C115465

Prerequisites:
    Components must already be imported via easyeda2kicad:
        easyeda2kicad --full --lcsc_id C2838502

Outputs:
    <project_dir>/<project_name>.kicad_sym       - Symbol library (only requested components)
    <project_dir>/<project_name>.pretty/          - Footprint library (only matching footprints)
    <project_dir>/<project_name>.3dshapes/        - 3D models (only matching models)
    <project_dir>/sym-lib-table                   - Symbol library table (created if missing)
    <project_dir>/fp-lib-table                    - Footprint library table (created if missing)
"""

import argparse
import re
import shutil
from pathlib import Path


EASYEDA_DIR = Path.home() / "Documents" / "Kicad" / "easyeda2kicad"
EASYEDA_SYM = EASYEDA_DIR / "easyeda2kicad.kicad_sym"
EASYEDA_PRETTY = EASYEDA_DIR / "easyeda2kicad.pretty"
EASYEDA_3D = EASYEDA_DIR / "easyeda2kicad.3dshapes"


def _count_unquoted_parens(line: str) -> tuple[int, int]:
    """Count parentheses that are outside of quoted strings."""
    opens = 0
    closes = 0
    in_quote = False
    for ch in line:
        if ch == '"':
            in_quote = not in_quote
        elif not in_quote:
            if ch == '(':
                opens += 1
            elif ch == ')':
                closes += 1
    return opens, closes


def parse_symbols(sym_file: Path) -> dict[str, str]:
    """Parse a kicad_sym file and return a dict of top-level symbol name -> text block.

    Uses parenthesis depth tracking (ignoring parens inside quoted strings)
    to correctly delimit each top-level symbol block.
    """
    content = sym_file.read_text()
    lines = content.split("\n")
    symbols = {}
    current_name = None
    current_lines = []
    sym_depth = 0

    for line in lines:
        opens, closes = _count_unquoted_parens(line)

        # Detect top-level symbol start: '  (symbol "NAME"' at lib level
        m = re.match(r'^  \(symbol "([^"]+)"', line)
        if m and sym_depth == 0:
            name = m.group(1)
            # Skip sub-symbols like "NAME_0_1" — these only appear inside a parent
            if not re.search(r"_\d+_\d+$", name):
                # Save previous symbol
                if current_name and current_lines:
                    symbols[current_name] = "\n".join(current_lines)
                current_name = name
                current_lines = [line]
                sym_depth = opens - closes
                continue

        if current_name:
            current_lines.append(line)
            sym_depth += opens - closes
            # Symbol block is complete when depth returns to 0
            if sym_depth <= 0:
                symbols[current_name] = "\n".join(current_lines)
                current_name = None
                current_lines = []
                sym_depth = 0

    # Save last symbol if file didn't end cleanly
    if current_name and current_lines:
        symbols[current_name] = "\n".join(current_lines)

    return symbols


def find_symbol_by_lcsc(symbols: dict[str, str], lcsc_id: str) -> tuple[str, str] | None:
    """Find a symbol that matches an LCSC ID.

    Searches for the ID in:
    - Symbol name suffix (e.g. "HT7533-1_C14289")
    - LCSC datasheet URL (e.g. "https://lcsc.com/product-detail/..._C14289.html")
    - LCSC property value
    Uses word-boundary matching to avoid false substring matches.
    """
    # Pattern matches the LCSC ID as a distinct token — preceded by non-alphanumeric or start,
    # followed by non-alphanumeric or end. Handles URLs, property values, and name suffixes.
    pattern = re.compile(r'(?:^|[^A-Za-z0-9])' + re.escape(lcsc_id) + r'(?:[^A-Za-z0-9]|$)')
    for name, text in symbols.items():
        if pattern.search(name) or pattern.search(text):
            return name, text
    return None


def extract_footprint_refs(symbol_text: str, old_lib: str = "easyeda2kicad") -> list[str]:
    """Extract footprint names referenced by a symbol."""
    pattern = rf'"{re.escape(old_lib)}:([^"]+)"'
    return re.findall(pattern, symbol_text)


def extract_3d_refs(footprint_file: Path) -> list[str]:
    """Extract 3D model filenames referenced by a footprint."""
    content = footprint_file.read_text()
    # Match patterns like easyeda2kicad.3dshapes/MODEL.wrl
    models = re.findall(r"easyeda2kicad\.3dshapes/([^\"]+\.(?:wrl|step))", content)
    # Also match with ${EASYEDA2KICAD} variable
    models += re.findall(r"\$\{EASYEDA2KICAD\}/easyeda2kicad\.3dshapes/([^\"]+\.(?:wrl|step))", content)
    return list(set(models))


def main():
    parser = argparse.ArgumentParser(
        description="Extract easyeda2kicad components into project-specific libraries"
    )
    parser.add_argument("project_dir", help="Project directory path")
    parser.add_argument("project_name", help="Project name (used for library naming)")
    parser.add_argument("lcsc_ids", nargs="+", help="LCSC part IDs to extract (e.g. C2838502)")
    parser.add_argument(
        "--source", default=str(EASYEDA_DIR),
        help=f"Source easyeda2kicad directory (default: {EASYEDA_DIR})"
    )
    parser.add_argument(
        "--no-lib-tables", action="store_true",
        help="Do not create sym-lib-table and fp-lib-table"
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    project_name = args.project_name
    source_dir = Path(args.source)
    source_sym = source_dir / "easyeda2kicad.kicad_sym"
    source_pretty = source_dir / "easyeda2kicad.pretty"
    source_3d = source_dir / "easyeda2kicad.3dshapes"

    if not source_sym.exists():
        print(f"ERROR: Symbol library not found: {source_sym}")
        return 1

    # Parse all symbols
    all_symbols = parse_symbols(source_sym)
    print(f"Source library contains {len(all_symbols)} top-level symbols")

    # Find symbols matching requested LCSC IDs
    extracted_symbols = []
    needed_footprints = []
    for lcsc_id in args.lcsc_ids:
        result = find_symbol_by_lcsc(all_symbols, lcsc_id)
        if result:
            name, text = result
            extracted_symbols.append((name, text))
            fps = extract_footprint_refs(text)
            needed_footprints.extend(fps)
            print(f"  FOUND: {name} (LCSC {lcsc_id}) -> footprints: {fps}")
        else:
            print(f"  WARNING: No symbol found for LCSC {lcsc_id}")

    if not extracted_symbols:
        print("ERROR: No symbols found for any of the requested LCSC IDs")
        return 1

    # --- Write symbol library ---
    out_sym = project_dir / f"{project_name}.kicad_sym"
    header = (
        "(kicad_symbol_lib\n"
        "  (version 20211014)\n"
        "  (generator https://github.com/uPesy/easyeda2kicad.py)\n"
    )
    body = ""
    for name, text in extracted_symbols:
        # Update footprint references to project name
        updated_text = text.replace("easyeda2kicad:", f"{project_name}:")
        body += updated_text + "\n"
    out_sym.write_text(header + body + ")\n")
    print(f"\nWrote symbol library: {out_sym} ({len(extracted_symbols)} symbols)")

    # --- Copy footprints ---
    out_pretty = project_dir / f"{project_name}.pretty"
    out_pretty.mkdir(exist_ok=True)
    # Clean existing files
    for f in out_pretty.glob("*.kicad_mod"):
        f.unlink()

    needed_3d = []
    for fp_name in needed_footprints:
        src_fp = source_pretty / f"{fp_name}.kicad_mod"
        if src_fp.exists():
            dst_fp = out_pretty / f"{fp_name}.kicad_mod"
            content = src_fp.read_text()
            # Update library name reference
            content = content.replace("easyeda2kicad:", f"{project_name}:")
            # Update 3D model path to use project-relative
            content = re.sub(
                r"\$\{EASYEDA2KICAD\}/easyeda2kicad\.3dshapes/",
                f"${{KIPRJMOD}}/{project_name}.3dshapes/",
                content,
            )
            dst_fp.write_text(content)
            print(f"  Copied footprint: {fp_name}")
            # Find 3D model references
            models = extract_3d_refs(src_fp)
            needed_3d.extend(models)
        else:
            print(f"  WARNING: Footprint not found: {src_fp}")

    print(f"Wrote footprint library: {out_pretty} ({len(needed_footprints)} footprints)")

    # --- Copy 3D models ---
    out_3d = project_dir / f"{project_name}.3dshapes"
    out_3d.mkdir(exist_ok=True)
    # Clean existing files
    for f in out_3d.iterdir():
        f.unlink()

    # Also look for .step counterparts of .wrl files and vice versa
    all_3d_files = set()
    for model in needed_3d:
        all_3d_files.add(model)
        base = model.rsplit(".", 1)[0]
        all_3d_files.add(f"{base}.wrl")
        all_3d_files.add(f"{base}.step")

    copied_3d = 0
    for model_name in sorted(all_3d_files):
        src_3d = source_3d / model_name
        if src_3d.exists():
            shutil.copy2(src_3d, out_3d / model_name)
            copied_3d += 1

    print(f"Wrote 3D models: {out_3d} ({copied_3d} files)")

    # --- Create library tables ---
    if not args.no_lib_tables:
        sym_table = project_dir / "sym-lib-table"
        if not sym_table.exists():
            sym_table.write_text(
                "(sym_lib_table\n"
                "  (version 7)\n"
                f'  (lib (name "{project_name}")(type "KiCad")'
                f'(uri "${{KIPRJMOD}}/{project_name}.kicad_sym")'
                '(options "")(descr "Project-specific imported symbols"))\n'
                ")\n"
            )
            print(f"Created: {sym_table}")
        else:
            print(f"Skipped (exists): {sym_table}")

        fp_table = project_dir / "fp-lib-table"
        if not fp_table.exists():
            fp_table.write_text(
                "(fp_lib_table\n"
                "  (version 7)\n"
                f'  (lib (name "{project_name}")(type "KiCad")'
                f'(uri "${{KIPRJMOD}}/{project_name}.pretty")'
                '(options "")(descr "Project-specific imported footprints"))\n'
                ")\n"
            )
            print(f"Created: {fp_table}")
        else:
            print(f"Skipped (exists): {fp_table}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
