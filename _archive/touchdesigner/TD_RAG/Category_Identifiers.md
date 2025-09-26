# TouchDesigner Knowledge Base Index

## Category Identifiers

**File/Folder Prefixes Used Throughout the Knowledge Base:**

- **CLASS_** - TouchDesigner Python class references and API documentation
- **EX_** - Practical Python examples and hands-on code patterns
- **GLSL_** - GLSL shader programming, graphics, and rendering information
- **HARDWARE_** - Hardware setup, integration, and multi-system configuration
- **MODULE_** - Python module references and system modules
- **PERF_** - Performance optimization, monitoring, and tuning guides
- **PY_** - Python programming documentation and TouchDesigner Python integration
- **REF_** - General reference materials, commands, and cross-platform guides
- **STYLEGUIDES_** - TouchDesigner development style guides, coding standards, and best practices
- **TD_** - TouchDesigner-specific documentation, operators, and system information

## Directory Structure Overview

```
/TD_RAG/
├── CLASSES_/           # TouchDesigner Python Classes (40 files)
├── EXAMPLES_/          # Practical Python Examples (21 files including advanced patterns)
│   ├── EXAMPLES_INDEX.md         # Master examples navigation
│   ├── EX_DATS.md               # Data manipulation examples
│   ├── EX_EXTENSIONS.md         # Extension development patterns
│   ├── EX_EXECUTE_DATS.md       # Execute DAT patterns
│   ├── EX_CALLBACKS.md          # Callback patterns
│   ├── EX_MODULES.md            # Module system examples
│   ├── EX_OSC_UDP.md            # Network communication
│   ├── EX_BUILTINS.md           # Core TD Python patterns
│   ├── EX_Advanced_Python_API_Patterns.md  # Advanced API implementations
│   ├── EX_Audio_Reactive_Systems.md        # Audio processing patterns
│   ├── EX_File_IO_Data_Processing.md       # File handling and data processing
│   ├── EX_Network_OSC_Communication.md     # Enhanced network communication
│   ├── EX_GLSL_Shader_Integration_Patterns.md  # GLSL integration patterns
│   └── [+ 8 more categories]     # UI, Panels, SOPs, OPs, Node Wiring, etc.
├── GLSL_/             # GLSL Shaders & Graphics (14 files)
├── HARDWARE_/         # Hardware Integration (2 files)
├── MODULE_/           # Python Modules (5 files)
├── PERFORMANCE_/      # Performance & Optimization (4 files)
├── PYTHON_/           # Python Programming (16 files)
├── REFERENCE_/        # General References (31 files)
├── STYLEGUIDES_/      # TouchDesigner Development Style Guides (13 files)
├── TD_/               # TouchDesigner Core Documentation
│   ├── TD_MENUS.md           # Menu structure and commands
│   └── TD_OPERATORS/         # Complete operator documentation (422 operators)
│       ├── OPERATORS_INDEX.md    # Master index with all operators
│       ├── CHOP/ + CHOP_INDEX.md # Channel Operators (169 files)
│       ├── TOP/ + TOP_INDEX.md   # Texture Operators (141 files)
│       ├── SOP/ + SOP_INDEX.md   # Surface Operators (113 files)
│       ├── DAT/ + DAT_INDEX.md   # Data Operators (74 files)
│       ├── COMP/ + COMP_INDEX.md # Component Operators (44 files)
│       ├── MAT/ + MAT_INDEX.md   # Material Operators (15 files)
│       └── README.md             # Usage and navigation guide
└── Category_Identifiers.md   # This index file
```

## Content Organization

### CLASSES_/ - TouchDesigner Python API Classes (40 files)

Complete Python class references for TouchDesigner's API including:

- Core classes: OP, CHOP, TOP, SOP, DAT, COMP, Par
- System classes: App, Project, UI, Preferences
- Specialized classes: CUDAMemory, Matrix, Vector, Timecode
- Network classes: WebDAT, WebsocketDAT

### GLSL_/ - Graphics Programming Documentation (14 files)

Advanced GLSL shader programming for TouchDesigner:

- TouchDesigner GLSL integration and workflow
- Built-in functions, data types, and structures
- Advanced techniques: ray marching, deferred lighting
- Compute shaders and atomic functions
- Production-ready shader templates for Panel COMP integration

### HARDWARE_/ - System Integration (2 files)

Hardware setup and multi-system configuration:

- Multiple monitor configuration and display management
- Computer synchronization for multi-machine setups

### MODULE_/ - Python Module References (5 files)

TouchDesigner Python module system:

- Core modules: td, TDFunctions, TDJSON
- Development tools: DebugModule, TDStoreTools

### PERFORMANCE_/ - Optimization Guides (4 files)

Performance tuning and monitoring:

- System optimization strategies
- Performance monitoring tools and dialogs
- Early depth test optimization
- System resource monitoring

### PYTHON_/ - Python Programming (16 files)

Comprehensive Python programming in TouchDesigner:

- Extensions, callbacks, and custom parameters
- Working with CHOPs, DATs, and operators
- Python patterns, tips, and best practices
- Complete Python examples reference with enhanced code-first patterns
- Production-ready TouchDesigner code examples with comprehensive error handling

### REFERENCE_/ - General Documentation (31 files)

Cross-platform references and general guides:

- Keyboard shortcuts and command references
- Core concepts: Cook, Parameter, Render, Cache
- Technical references: Pixel formats, shared memory
- Troubleshooting and startup configuration

### STYLEGUIDES_/ - TouchDesigner Development Style Guides (13 files)

Comprehensive TouchDesigner-specific style guides and development best practices:

- **Node Organization**: Naming conventions, sizing standards, and wiring practices
- **Python Development**: Extensions, modules, docstrings, and coding standards
- **Project Architecture**: Organization patterns, scaffolding, and external TOX management
- **Documentation**: Network comments, GLSL code documentation, and logging practices
- **System Setup**: Configuration standards, preferences, and auto-complete integration
- **Code-First Development**: Production-ready code generation patterns and conventions

### TD_/ - TouchDesigner Core Documentation

TouchDesigner-specific system documentation:

#### TD_MENUS.md

Complete TouchDesigner menu structure with:

- 39 menu items with commands and keyboard shortcuts
- Internal command reference for automation
- Hierarchical menu organization

#### TD_OPERATORS/ - Complete Operator Documentation System (422 operators)

Comprehensive operator reference with two-tier navigation:

**Master Index:**

- `OPERATORS_INDEX.md` - All 422 operators with complete descriptions
- Organized by family with metadata (Type, Category)
- Relative path navigation to family indexes

**Family Organization:**

- **CHOP** (Channel Operators): 169 operators - Process channel data streams
- **TOP** (Texture Operators): 141 operators - Process images and textures  
- **SOP** (Surface Operators): 113 operators - Process 3D geometry
- **DAT** (Data Operators): 74 operators - Process table and text data
- **COMP** (Component Operators): 44 operators - Container and UI components
- **MAT** (Material Operators): 15 operators - Shading and materials

## Navigation Guide

### Finding Documentation by Type

- **API Programming** → CLASSES_/ + PYTHON_/ + MODULE_/
- **Shader Programming** → GLSL_/ + REFERENCE_/REF_*GLSL*
- **Operator Reference** → TD_/TD_OPERATORS/
- **Performance Issues** → PERFORMANCE_/ + REFERENCE_/REF_*Performance*
- **System Setup** → HARDWARE_/ + REFERENCE_/REF_*startup*
- **Menu Commands** → TD_/TD_MENUS.md + REFERENCE_/REF_*Shortcuts*
- **Style & Best Practices** → STYLEGUIDES_/

### Cross-References

- Most files include "Related" sections linking to relevant documentation
- OPERATORS_INDEX.md provides family-based navigation
- Individual operator files (when generated) will cross-reference similar functionality

### File Naming Patterns

- **Descriptive names** after prefix (e.g., `PY_Working_with_CHOPs_in_Python.md`)
- **Class references** use exact class names (e.g., `CLASS_CHOP_Class.md`)
- **Operators** use lowercase with operator type (e.g., `noiseTOP.md`, `mathCHOP.md`)

## External Resources

**Conversion Scripts:** Located in `/Conversion_Python_Help_Scripts/`

- Python scripts for converting TD data formats to Markdown
- Original source files archived in TD_SOURCE/ subfolder
- Metadata validation and conversion utilities

**Total Documentation:** 736 files covering all aspects of TouchDesigner development from basic concepts to advanced programming techniques.

## RAG System Optimization Components

**Additional Project Files:** The TouchDesigner RAG system has been enhanced with optimization components located outside the core TD_RAG documentation:

- **EVALUATION_FRAMEWORK/**: Performance testing and evaluation files (9 files)
  - TouchDesigner_Code_Focused_Test_Dataset.md (80 queries)
  - RAG_Performance_Evaluation_Framework.md (testing methodology)
  - Code_Focus_Dataset_Comparison.md (gap analysis)
  - TouchDesigner_Code_Focused_Forum_Analysis.md (real-world patterns)
  - RAG_Post_Improvement_Test_Results_2025.md (post-optimization results)
  - API_Accuracy_Audit_Results.md (baseline performance data)

**System Status:** This documentation system has undergone comprehensive optimization (Phase 1-3) focused on transforming from educational content to production-ready code generation, with demonstrated 97% success rate (+42% improvement over baseline) in TouchDesigner code generation tasks.
