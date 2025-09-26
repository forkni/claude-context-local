# TouchDesigner Python Examples Index

## Overview

This section contains **342 practical Python examples** from TouchDesigner's official "Help > Python Examples" menu. These examples demonstrate real-world Python usage patterns, best practices, and common solutions for TouchDesigner development.

**Source**: TouchDesigner Help > Python Examples (official Derivative examples)  
**Organization**: 17 categories covering all major Python use cases  
**Format**: Code snippets with explanations, use cases, and cross-references

## Quick Navigation by Task

### Working with Data

- **[DAT Operations](#ex_dats)** (46 examples) - Table manipulation, cell access, data processing
- **[CHOP Operations](#ex_chops)** (12 examples) - Channel data processing and manipulation
- **[SOP Operations](#ex_sops)** (16 examples) - 3D geometry manipulation and point processing

### System Integration

- **[Callbacks](#ex_callbacks)** (19 examples) - Event handling, triggers, and response patterns
- **[Execute DATs](#ex_execute_dats)** (26 examples) - Frame-based execution and event processing
- **[Network Communication](#ex_osc_udp)** (19 examples) - OSC, UDP, and network protocols

### Advanced Development

- **[Extensions](#ex_extensions)** (35 examples) - Component extension development
- **[Modules](#ex_modules)** (19 examples) - Module system and code organization
- **[Module Tutorials](#ex_module_tutorials)** (13 examples) - Step-by-step module development

### User Interface

- **[UI Development](#ex_ui)** (15 examples) - User interface creation and interaction
- **[Panels](#ex_panels)** (15 examples) - Panel components and interactive controls
- **[Parameters](#ex_parameters)** (13 examples) - Parameter manipulation and control

### Development Tools

- **[Debug Techniques](#ex_debug)** (10 examples) - Debugging strategies and tools
- **[DAT Examination](#ex_examine_dats)** (10 examples) - Runtime inspection and analysis
- **[Undo System](#ex_undo)** (15 examples) - Undo/redo implementation

### Core Systems

- **[Built-ins](#ex_builtins)** (19 examples) - Core TouchDesigner Python patterns
- **[Operator Management](#ex_ops)** (25 examples) - General operator operations
- **[Node Wiring](#ex_node_wiring)** (14 examples) - Network connection management
- **[Script DAT Network Examples](./SCRIPT_DAT_NETWORK_EXAMPLES/SCRIPT_DAT_NETWORK_EXAMPLES_INDEX.md)** (8 examples) - Procedural data generation and manipulation using the scriptDAT.

---

## Category Details

### EX_DATS {#ex_dats}

**File**: [EX_DATS.md](./EX_DATS.md)  
**Examples**: 46 files  
**Focus**: Data manipulation, table operations, cell access

**Key Topics**:

- Table creation and manipulation
- Cell reading/writing operations
- Data type conversion and handling
- Table sorting and searching
- CSV/TSV file operations

**Most Useful Examples**:

- Cell vs String operations
- Table copy and manipulation
- Numeric cell handling
- Data reset and clearing

### EX_EXTENSIONS {#ex_extensions}

**File**: [EX_EXTENSIONS.md](./EX_EXTENSIONS.md)  
**Examples**: 35 files  
**Focus**: Component extension development

**Key Topics**:

- Extension class creation
- Property definition and management
- Method promotion and conflicts
- Storage and dependency management
- TDF (TouchDesigner Function) patterns

**Most Useful Examples**:

- Custom extension creation
- Storage extension patterns
- Dependable vs non-dependable properties
- Function promotion strategies

### EX_CALLBACKS {#ex_callbacks}

**File**: [EX_CALLBACKS.md](./EX_CALLBACKS.md)  
**Examples**: 19 files  
**Focus**: Event handling and callback patterns

**Key Topics**:

- Parameter change detection
- Panel interaction callbacks
- Network message handling
- Component lifecycle events
- Drag-and-drop operations

**Most Useful Examples**:

- OSC message callbacks
- TCP/IP data handling
- Container drag-drop
- List component callbacks

### EX_EXECUTE_DATS {#ex_execute_dats}

**File**: [EX_EXECUTE_DATS.md](./EX_EXECUTE_DATS.md)  
**Examples**: 26 files  
**Focus**: Frame-based execution patterns

**Key Topics**:

- CHOP Execute patterns
- DAT Execute monitoring
- OP Execute lifecycle
- Panel Execute handling
- Parameter Execute callbacks

**Most Useful Examples**:

- Frame-based processing
- Value change monitoring
- Component state tracking
- Event-driven operations

### EX_MODULES {#ex_modules}

**File**: [EX_MODULES.md](./EX_MODULES.md)  
**Examples**: 19 files  
**Focus**: Module system and code organization

**Key Topics**:

- Module import strategies
- Built-in module usage
- DAT module patterns
- Utility module creation
- Dependency management

**Most Useful Examples**:

- Module import patterns
- Utility function organization
- Code reuse strategies
- Built-in system access

### EX_OSC_UDP {#ex_osc_udp}

**File**: [EX_OSC_UDP.md](./EX_OSC_UDP.md)  
**Examples**: 19 files  
**Focus**: Network communication protocols

**Key Topics**:

- OSC message sending/receiving
- UDP data transmission
- Byte data handling
- Network protocol patterns
- Real-time communication

**Most Useful Examples**:

- OSC message formatting
- UDP data streaming
- Network callback handling
- Protocol implementation

### EX_UI {#ex_ui}

**File**: [EX_UI.md](./EX_UI.md)  
**Examples**: 15 files  
**Focus**: User interface development

**Key Topics**:

- Dialog creation
- File selection interfaces
- Color pickers and options
- Status and feedback systems
- Pane and window management

**Most Useful Examples**:

- File chooser dialogs
- Message box creation
- Status bar updates
- UI color management

### EX_PANELS {#ex_panels}

**File**: [EX_PANELS.md](./EX_PANELS.md)  
**Examples**: 15 files  
**Focus**: Interactive panel components

**Key Topics**:

- Panel value management
- Keyboard focus handling
- Click simulation
- Table component styling
- Interactive controls

**Most Useful Examples**:

- Panel state management
- Focus control strategies
- Table cell styling
- User interaction patterns

### EX_BUILTINS {#ex_builtins}

**File**: [EX_BUILTINS.md](./EX_BUILTINS.md)  
**Examples**: 19 files  
**Focus**: Core TouchDesigner Python patterns

**Key Topics**:

- Built-in module access
- System information retrieval
- Time and monitor queries
- License checking
- Core utility functions

**Most Useful Examples**:

- Monitor information access
- System time queries
- Built-in function usage
- License status checking

## Remaining Categories

### Smaller Focused Categories

- **[EX_OPS.md](./EX_OPS.md)** (25 files) - General operator operations and management
- **[EX_NODE_WIRING.md](./EX_NODE_WIRING.md)** (14 files) - Network connection and wiring
- **[EX_SOPS.md](./EX_SOPS.md)** (16 files) - 3D geometry and SOP manipulation  
- **[EX_UNDO.md](./EX_UNDO.md)** (15 files) - Undo/redo system implementation
- **[EX_PARAMETERS.md](./EX_PARAMETERS.md)** (13 files) - Parameter manipulation patterns
- **[EX_MODULE_TUTORIALS.md](./EX_MODULE_TUTORIALS.md)** (13 files) - Progressive module tutorials
- **[EX_CHOPS.md](./EX_CHOPS.md)** (12 files) - Channel operator manipulation
- **[EX_DEBUG.md](./EX_DEBUG.md)** (10 files) - Debugging techniques and strategies
- **[EX_EXAMINE_DATS.md](./EX_EXAMINE_DATS.md)** (10 files) - Runtime inspection methods

## Cross-References to Documentation

### Related Documentation Sections

- **API Reference**: [CLASSES_/](../CLASSES_/) - Class documentation for methods used in examples
- **Python Guide**: [PYTHON_/PY_TD_Python_Examples_Reference.md](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Comprehensive pattern analysis
- **Extensions**: [PYTHON_/PY_Extensions.md](../PYTHON_/PY_Extensions.md) - Extension development concepts
- **Callbacks**: [PYTHON_/PY_CallbacksExtExtension.md](../PYTHON_/PY_CallbacksExtExtension.md) - Callback system overview

### Find Examples by Operator Type

- **CHOP Examples** → EX_CHOPS.md + related operator docs in [TD_/TD_OPERATORS/CHOP/](../TD_/TD_OPERATORS/CHOP/)
- **DAT Examples** → EX_DATS.md + EX_EXECUTE_DATS.md + [TD_/TD_OPERATORS/DAT/](../TD_/TD_OPERATORS/DAT/)
- **SOP Examples** → EX_SOPS.md + [TD_/TD_OPERATORS/SOP/](../TD_/TD_OPERATORS/SOP/)
- **UI Examples** → EX_UI.md + EX_PANELS.md + [TD_/TD_OPERATORS/COMP/](../TD_/TD_OPERATORS/COMP/)

### Find Examples by Development Task

- **Component Development** → EX_EXTENSIONS.md + [PYTHON_/PY_Extensions.md](../PYTHON_/PY_Extensions.md)
- **Network Programming** → EX_OSC_UDP.md + EX_CALLBACKS.md
- **Data Processing** → EX_DATS.md + EX_CHOPS.md + EX_SOPS.md
- **UI Development** → EX_UI.md + EX_PANELS.md + EX_PARAMETERS.md
- **System Integration** → EX_EXECUTE_DATS.md + EX_MODULES.md + EX_BUILTINS.md

## Usage Guidelines

### Finding the Right Example

1. **Start with task-based navigation** above to find relevant category
2. **Check cross-references** to related documentation for context
3. **Look at specific example files** for code patterns
4. **Reference API documentation** for method details

### Example File Format

Each example file contains:

- **Header metadata** with source information
- **Commented code** explaining functionality
- **Use case context** when applicable
- **Key concepts** demonstrated

### Integration with TouchDesigner

- Examples assume standard TouchDesigner Python environment
- No `import td` needed - TD globals available
- Code designed for use in Text DATs, Execute DATs, Extensions
- Paths and references use standard TD operator syntax

## Statistics

- **Total Examples**: 342 files
- **Categories**: 17 distinct areas
- **Code Languages**: Python (.py) and text examples (.txt)
- **Source**: Official TouchDesigner Help documentation
- **Coverage**: All major TouchDesigner Python development patterns

---

*These examples complement the theoretical documentation in PYTHON_/ and CLASSES_/ folders, providing practical, working code for common TouchDesigner development tasks.*
