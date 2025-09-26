# TouchDesigner Operators Documentation

## Welcome
This folder contains comprehensive documentation for all 422 TouchDesigner operators, organized by family and converted from the official TouchDesigner summaries and parameter references.

## Quick Start
- **[OPERATORS_INDEX.md](OPERATORS_INDEX.md)** - Complete alphabetical listing of all operators
- **[Search by Family](#operator-families)** - Browse operators by type

## Operator Families

### CHOP - Channel Operators - Process and manipulate channel data
**128 operators** | [Browse CHOP Index](CHOP/CHOP_INDEX.md)

**Examples**: [CHOP Analyze](CHOP/CHOP_Analyze.md), [CHOP Angle](CHOP/CHOP_Angle.md), [CHOP Attribute](CHOP/CHOP_Attribute.md) + 125 more...

### TOP - Texture Operators - Process and manipulate image/texture data
**101 operators** | [Browse TOP Index](TOP/TOP_INDEX.md)

**Examples**: [TOP Add](TOP/TOP_Add.md), [TOP Analyze](TOP/TOP_Analyze.md), [TOP Anti Alias](TOP/TOP_Anti_Alias.md) + 98 more...

### SOP - Surface Operators - Process and manipulate 3D geometry
**102 operators** | [Browse SOP Index](SOP/SOP_INDEX.md)

**Examples**: [SOP Add](SOP/SOP_Add.md), [SOP Align](SOP/SOP_Align.md), [SOP Arm](SOP/SOP_Arm.md) + 99 more...

### DAT - Data Operators - Process and manipulate table/text data
**57 operators** | [Browse DAT Index](DAT/DAT_INDEX.md)

**Examples**: [DAT Art-Net](DAT/DAT_Art-Net.md), [DAT CHOP Execute](DAT/DAT_CHOP_Execute.md), [DAT CHOP to](DAT/DAT_CHOP_to.md) + 54 more...

### COMP - Component Operators - Container and UI components
**25 operators** | [Browse COMP Index](COMP/COMP_INDEX.md)

**Examples**: [COMP Ambient Light](COMP/COMP_Ambient_Light.md), [COMP Animation](COMP/COMP_Animation.md), [COMP Base](COMP/COMP_Base.md) + 22 more...

### MAT - Material Operators - Shading and material definitions
**9 operators** | [Browse MAT Index](MAT/MAT_INDEX.md)

**Examples**: [MAT Constant](MAT/MAT_Constant.md), [MAT Depth](MAT/MAT_Depth.md), [MAT GLSL](MAT/MAT_GLSL.md) + 6 more...


## Reference Files
Additional TouchDesigner references:
- [TouchDesigner Shortcuts](REFERENCE/TouchDesigner_Shortcuts.md)
- [TouchDesigner Commands](REFERENCE/TouchDesigner_Commands.md)
- [TouchDesigner Menus](REFERENCE/TouchDesigner_Menus.json)

## Usage in Claude Code
This documentation is optimized for the TouchDesigner Claude Code integration:
```bash
# Search for specific operators
python scripts/claude_code_integration.py help "Noise"

# Analyze TouchDesigner code
python scripts/claude_code_integration.py analyze "op('noise1').par.freq = 2.5"
```

## Statistics
- **Total Operators**: 422
- **Operator Families**: 6
- **Individual Markdown Files**: 422 (one per operator)
- **Index Files**: 6 (one per family)

---
*Documentation generated from TouchDesigner official summaries and parameter references*
