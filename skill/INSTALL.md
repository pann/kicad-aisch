# Installation

## 1. Install required tools

```bash
# KiCad 9 (provides kicad-cli)
# Install from https://www.kicad.org/download/

# Python packages
pip install easyeda2kicad fpdf2

# Optional: for SVG-to-PNG visual verification
sudo apt install inkscape
```

## 2. Install the skill

Each Claude Code skill lives in its own subdirectory under `~/.claude/skills/`.
Copy this entire folder as `kicad-schematic`:

```bash
# Personal install (available in all projects)
cp -r skill/ ~/.claude/skills/kicad-schematic/

# OR project-local install (available only in one project)
cp -r skill/ <your-project>/.claude/skills/kicad-schematic/
```

The result should look like:

```
~/.claude/skills/
  kicad-schematic/
    SKILL.md
    INSTALL.md
    UserGuide.md
    scripts/
      kicad_sch_gen.py
      md_to_pdf.py
      extract_easyeda_libs.py
    examples/
      gen_connectors.py
      gen_power_supply.py
      ...
    workflow-templates/
      01-requirements-template.md
      ...
```

## 3. Verify

Start Claude Code and type `/kicad-schematic` — it should activate the skill.

## 4. Recommended companion skills

Install these separately if available:

- `kicad-file-format`
- `jlcpcb-bom-generate-from-kicad`
- `analyze-power-nets`
- `find-high-speed-nets`
- `plan-pcb-routing`
