# TouchDesigner Python Learning Guide & Reference Index

> **📚 Practical Examples Location**: The categorized Python examples are now organized in:  
> `TD_RAG/EXAMPLES_/` - 17 categorized .md files with 342 practical examples  
> This guide provides learning pathways, cross-category analysis, and comprehensive patterns for TouchDesigner Python development.

## Overview

This learning guide synthesizes TouchDesigner's official Python examples into educational pathways and cross-category insights. It serves as both a learning progression for TouchDesigner Python development and a comprehensive index to the practical examples found in the EXAMPLES_ folder.

**Key Features:**

- **Learning Pathways**: Structured progression from beginner to advanced
- **Cross-Category Analysis**: How different systems integrate together
- **Quick Reference Tables**: Fast access to specific functionality
- **Best Practices**: Patterns that work across all TouchDesigner development
- **Implementation Strategies**: Real-world integration approaches

---

## Learning Pathways

### Beginner Path: Foundation Concepts

**Start Here** → Build Core Understanding → Practice Integration

#### Step 1: Core TouchDesigner Python Patterns

**Reference**: [EX_BUILTINS.md](../EXAMPLES_/EX_BUILTINS.md)  
**Examples**: 19 foundational patterns  
**Time Investment**: 2-3 hours

**Essential Concepts to Master:**

- TouchDesigner globals (`op()`, `parent()`, `me`, `absTime`)
- Built-in utilities (`tdu`, `licenses`, `monitors`)
- Time and frame access patterns
- System integration basics

**Key Examples to Study:**

- Monitor system integration → **EX_BUILTINS.md** sections 1.4, 1.8
- License system access → **EX_BUILTINS.md** section 1.9
- Time and frame patterns → **EX_BUILTINS.md** section 1.7

#### Step 2: Event Handling & Callbacks

**Reference**: [EX_CALLBACKS.md](../EXAMPLES_/EX_CALLBACKS.md) + [EX_EXECUTE_DATS.md](../EXAMPLES_/EX_EXECUTE_DATS.md)  
**Examples**: 19 callback patterns + 26 execute patterns  
**Time Investment**: 4-5 hours

**Essential Concepts to Master:**

- Parameter change detection (`onValueChange`, `onPulse`)
- UI interaction callbacks (`onOffToOn`, `whileOn`)
- Network communication callbacks (OSC, TCP/IP, UDP)
- Lifecycle events (`onCreate`, `onFrameStart`, `onDestroy`)

**Learning Progression:**

1. **Start with Parameter Callbacks** → **EX_EXECUTE_DATS.md** section 4.6
2. **Learn UI Callbacks** → **EX_CALLBACKS.md** section 5.2, **EX_EXECUTE_DATS.md** section 4.5  
3. **Master Network Callbacks** → **EX_CALLBACKS.md** section 5.1
4. **Practice System Callbacks** → **EX_EXECUTE_DATS.md** sections 4.3-4.4

#### Step 3: Component Development

**Reference**: [EX_EXTENSIONS.md](../EXAMPLES_/EX_EXTENSIONS.md)  
**Examples**: 35 extension patterns  
**Time Investment**: 6-8 hours

**Essential Concepts to Master:**

- Extension class structure and `__init__` patterns
- Property promotion (capitalized vs lowercase)
- Dependency management (dependable vs non-dependable)
- Storage patterns (TDFunctions vs StorageManager)

**Learning Progression:**

1. **Basic Extensions** → **EX_EXTENSIONS.md** section 3.1
2. **Property Management** → **EX_EXTENSIONS.md** sections 3.2-3.3
3. **Storage Patterns** → **EX_EXTENSIONS.md** section 3.4
4. **Best Practices** → **EX_EXTENSIONS.md** section 3.6

### Intermediate Path: Data & UI Systems

#### Step 4: Data Processing Mastery

**Reference**: [EX_DATS.md](../EXAMPLES_/EX_DATS.md) + [EX_CHOPS.md](../EXAMPLES_/EX_CHOPS.md) + [EX_SOPS.md](../EXAMPLES_/EX_SOPS.md)  
**Examples**: 46 + 12 + 16 = 74 data patterns  
**Time Investment**: 5-6 hours

**Learning Focus:**

- Table operations and cell manipulation (**EX_DATS.md**)
- Channel data processing (**EX_CHOPS.md**)  
- 3D geometry manipulation (**EX_SOPS.md**)

#### Step 5: UI Development

**Reference**: [EX_UI.md](../EXAMPLES_/EX_UI.md) + [EX_PANELS.md](../EXAMPLES_/EX_PANELS.md) + [EX_PARAMETERS.md](../EXAMPLES_/EX_PARAMETERS.md)  
**Examples**: 15 + 15 + 13 = 43 UI patterns  
**Time Investment**: 4-5 hours

**Learning Focus:**

- Dialog and interface creation (**EX_UI.md**)
- Interactive panel components (**EX_PANELS.md**)
- Parameter manipulation strategies (**EX_PARAMETERS.md**)

### Advanced Path: System Integration

#### Step 6: Network & Communication

**Reference**: [EX_OSC_UDP.md](../EXAMPLES_/EX_OSC_UDP.md)  
**Examples**: 19 network patterns  
**Time Investment**: 3-4 hours

#### Step 7: Module Systems & Code Organization

**Reference**: [EX_MODULES.md](../EXAMPLES_/EX_MODULES.md) + [EX_MODULE_TUTORIALS.md](../EXAMPLES_/EX_MODULE_TUTORIALS.md)  
**Examples**: 19 + 13 = 32 organization patterns  
**Time Investment**: 4-5 hours

#### Step 8: Professional Development

**Reference**: [EX_DEBUG.md](../EXAMPLES_/EX_DEBUG.md) + [EX_UNDO.md](../EXAMPLES_/EX_UNDO.md) + [EX_EXAMINE_DATS.md](../EXAMPLES_/EX_EXAMINE_DATS.md)  
**Examples**: 10 + 15 + 10 = 35 professional patterns  
**Time Investment**: 3-4 hours

---

## Quick Reference by Development Task

### UI Development Task Map

| **Task** | **Primary Reference** | **Key Concepts** | **Integration Points** |
|----------|----------------------|------------------|----------------------|
| **Interactive Controls** | EX_PANELS.md | Panel state management | → EX_CALLBACKS.md (events) |
| **Parameter Interfaces** | EX_PARAMETERS.md | Parameter manipulation | → EX_EXTENSIONS.md (properties) |
| **Dialog Systems** | EX_UI.md | Dialog creation patterns | → EX_MODULES.md (reusable components) |
| **Real-time Updates** | EX_EXECUTE_DATS.md | Frame-based execution | → EX_DATS.md (data sync) |

### Data Processing Task Map

| **Task** | **Primary Reference** | **Key Concepts** | **Integration Points** |
|----------|----------------------|------------------|----------------------|
| **Table Operations** | EX_DATS.md | Cell access, manipulation | → EX_UI.md (table displays) |
| **Channel Processing** | EX_CHOPS.md | Sample manipulation | → EX_CALLBACKS.md (value changes) |
| **3D Geometry** | EX_SOPS.md | Point/primitive operations | → EX_PARAMETERS.md (controls) |
| **Network Data** | EX_OSC_UDP.md | Protocol handling | → EX_CALLBACKS.md (message events) |

### Component Development Task Map

| **Task** | **Primary Reference** | **Key Concepts** | **Integration Points** |
|----------|----------------------|------------------|----------------------|
| **Basic Extensions** | EX_EXTENSIONS.md | Class structure | → EX_MODULES.md (organization) |
| **Event Handling** | EX_CALLBACKS.md | Callback patterns | → EX_EXTENSIONS.md (methods) |
| **State Management** | EX_EXTENSIONS.md | Storage patterns | → EX_DATS.md (persistence) |
| **API Design** | EX_EXTENSIONS.md | Promotion strategies | → EX_MODULES.md (interfaces) |

---

## Cross-Category Integration Patterns

### Callback + Extension Integration

**Primary Files**: [EX_CALLBACKS.md](../EXAMPLES_/EX_CALLBACKS.md) + [EX_EXTENSIONS.md](../EXAMPLES_/EX_EXTENSIONS.md)

**Integration Pattern**: Extensions often use callbacks to handle events. This is a fundamental TouchDesigner pattern.

```python
# Extension with embedded callback handling
class MyExtension:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        
    def onValueChange(self, par, prev):  # Callback method in extension
        """Handle parameter changes"""
        self.updateDisplay(par.eval())
        
    def updateDisplay(self, value):      # Extension method
        """Update UI based on parameter"""
        self.ownerComp.op('display').par.text = str(value)
```

**Cross-Reference Locations**:

- **Callback Patterns** → EX_CALLBACKS.md sections 5.2-5.5
- **Extension Methods** → EX_EXTENSIONS.md section 3.1
- **Storage Integration** → EX_EXTENSIONS.md section 3.4

### UI + Data Processing Integration

**Primary Files**: [EX_UI.md](../EXAMPLES_/EX_UI.md) + [EX_DATS.md](../EXAMPLES_/EX_DATS.md) + [EX_PANELS.md](../EXAMPLES_/EX_PANELS.md)

**Integration Pattern**: User interfaces drive data processing through parameter changes and panel interactions.

```python
# Panel callback that triggers data processing
def onValueChange(panelValue, prev=None):
    """Panel drives table updates"""
    # Update data table
    table = op('dataTable')
    table[1, 0] = panelValue.val
    
    # Trigger processing
    op('processScript').run(panelValue.val)
```

**Cross-Reference Locations**:

- **Panel Events** → EX_PANELS.md sections covering value changes
- **Table Operations** → EX_DATS.md sections 2.1-2.8
- **Real-time Updates** → EX_EXECUTE_DATS.md frame-based patterns

### Network + Callback Integration

**Primary Files**: [EX_OSC_UDP.md](../EXAMPLES_/EX_OSC_UDP.md) + [EX_CALLBACKS.md](../EXAMPLES_/EX_CALLBACKS.md)

**Integration Pattern**: Network data reception triggers callback chains for processing and UI updates.

```python
# OSC callback that updates multiple systems
def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    """Network data drives system updates"""
    if address == '/control/volume':
        volume = args[0] if args else 0.0
        # Update audio system
        op('audiodevout1').par.volume = volume
        # Update UI display
        parent().Volume = volume  # Extension property
        # Log to data table
        log_table = op('logTable')
        log_table.appendRow([timeStamp, address, volume])
```

**Cross-Reference Locations**:

- **OSC Patterns** → EX_OSC_UDP.md network communication
- **Multi-system Updates** → EX_CALLBACKS.md section 5.1
- **Data Logging** → EX_DATS.md table operations

---

## Best Practices Synthesis

### TouchDesigner Python Development Principles

#### 1. **Start Simple, Build Complexity**

- **Foundation** → EX_BUILTINS.md: Master TD globals before advanced patterns
- **Events** → EX_CALLBACKS.md: Understand event flow before building systems
- **Components** → EX_EXTENSIONS.md: Learn extension basics before complex architectures

#### 2. **Integration-First Thinking**

- **Never build in isolation**: Every component connects to others
- **Design for callbacks**: Assume your code will need event handling
- **Plan for data flow**: Know how information moves through your system

#### 3. **Performance Considerations**

- **Use non-dependable properties** when auto-update isn't needed → EX_EXTENSIONS.md section 3.2
- **Batch operations** instead of per-frame processing → EX_EXECUTE_DATS.md patterns
- **Monitor cook times** during development → EX_DEBUG.md section 6.2

#### 4. **Error Handling Patterns**

```python
# TouchDesigner-specific error handling
def safe_operator_access(op_path):
    """Safe operator access pattern"""
    try:
        target_op = op(op_path)
        if target_op is None:
            debug(f"Warning: Operator '{op_path}' not found")
            return None
        return target_op
    except Exception as e:
        debug(f"Error accessing '{op_path}': {e}")
        return None
```

#### 5. **Storage Strategy Selection**

| **Use Case** | **Method** | **Reference** | **Persistence** |
|--------------|------------|---------------|----------------|
| UI State | createProperty | EX_EXTENSIONS.md 3.2 | Resets on reinit |
| User Preferences | StorageManager | EX_EXTENSIONS.md 3.4 | Survives reinit |
| Session Data | Component storage | Built-in patterns | Project-based |
| Cache Data | Module storage | EX_MODULES.md | Session-only |

---

## Advanced Development Patterns

### Component Extension Architecture

**Reference**: [EX_EXTENSIONS.md](../EXAMPLES_/EX_EXTENSIONS.md) sections 3.1-3.6

**Professional Extension Template**:

```python
from TDStoreTools import StorageManager
import TDFunctions

class ProfessionalExtension:
    """Production-ready extension template"""
    
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        
        # Initialize storage for persistent data
        self._init_storage()
        
        # Initialize properties for reactive data
        self._init_properties()
        
        # Initialize internal state
        self._active = True
        
    def _init_storage(self):
        """Initialize persistent storage"""
        stored_items = [
            {'name': 'UserPreferences', 'default': {}, 'property': True},
            {'name': 'LastSession', 'default': '', 'property': True}
        ]
        self.stored = StorageManager(self, self.ownerComp, stored_items)
    
    def _init_properties(self):
        """Initialize reactive properties"""
        TDFunctions.createProperty(self, 'ActiveState', value=True, dependable=True)
        TDFunctions.createProperty(self, 'DataCache', value=[], dependable='deep')
    
    # Promoted public API (capitalized)
    def ProcessData(self, data):
        """Main processing function"""
        if not self.ActiveState:
            return None
        return self._internal_process(data)
    
    def UpdatePreferences(self, prefs_dict):
        """Update user preferences"""
        self.UserPreferences = {**self.UserPreferences, **prefs_dict}
    
    # Private implementation (lowercase)
    def _internal_process(self, data):
        """Internal processing logic"""
        # Implementation details
        return processed_data
```

### Network-Driven Architecture

**Reference**: [EX_OSC_UDP.md](../EXAMPLES_/EX_OSC_UDP.md) + [EX_CALLBACKS.md](../EXAMPLES_/EX_CALLBACKS.md)

**Multi-Protocol Handler Pattern**:

```python
# Unified network message handler
def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    """OSC message router"""
    handler = parent().ext.NetworkHandler
    handler.RouteMessage('osc', address, args, peer)

def onReceive(dat, rowIndex, message, bytes, peer):
    """TCP/UDP message router"""
    handler = parent().ext.NetworkHandler
    handler.RouteMessage('tcp', message, None, peer)

class NetworkHandler:
    """Centralized network message handling"""
    
    def RouteMessage(self, protocol, address_or_message, args, peer):
        """Route messages to appropriate handlers"""
        if protocol == 'osc':
            self._handle_osc(address_or_message, args, peer)
        elif protocol == 'tcp':
            self._handle_tcp(address_or_message, peer)
    
    def _handle_osc(self, address, args, peer):
        """OSC-specific handling"""
        # Route based on address patterns
        pass
    
    def _handle_tcp(self, message, peer):
        """TCP-specific handling"""
        # Parse and route TCP messages
        pass
```

---

## Quick Reference Tables

### Callback Signature Reference

| **Callback Type** | **Signature** | **Use Case** | **File Reference** |
|------------------|---------------|--------------|-------------------|
| Parameter Change | `onValueChange(par, prev)` | Parameter monitoring | EX_EXECUTE_DATS.md 4.6 |
| Panel Change | `onValueChange(panelValue, prev=None)` | UI interaction | EX_EXECUTE_DATS.md 4.5 |
| CHOP State | `onOffToOn(channel, sampleIndex, val, prev)` | State transitions | EX_EXECUTE_DATS.md 4.1 |
| Text Edit | `onTextEdit(comp)` | Real-time editing | EX_CALLBACKS.md 5.5 |
| OSC Message | `onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer)` | Network data | EX_CALLBACKS.md 5.1 |
| TCP Data | `onReceive(dat, rowIndex, message, bytes, peer)` | Network streams | EX_CALLBACKS.md 5.1 |

### Data Operation Quick Reference

| **Operation** | **Method** | **Example** | **File Reference** |
|---------------|------------|-------------|-------------------|
| Table Access | `table[row, col]` | `value = op('table1')[0, 0]` | EX_DATS.md 2.2 |
| Cell Search | `table.findCell(pattern)` | `cell = table.findCell('p*')` | EX_DATS.md 2.3 |
| Row Operations | `table.appendRow(data)` | `table.appendRow(['a', 'b', 'c'])` | EX_DATS.md 2.2 |
| Channel Access | `chop.chan(name)` | `volume = op('audio1').chan('volume')` | EX_CHOPS.md patterns |
| Point Access | `sop.point(index)` | `pos = op('geo1').point(0).P` | EX_SOPS.md patterns |

### Extension Property Types

| **Property Type** | **Creation** | **Behavior** | **Use Case** | **Reference** |
|------------------|--------------|--------------|--------------|---------------|
| Dependable | `createProperty(self, 'Name')` | Auto-updates downstream | UI controls | EX_EXTENSIONS.md 3.2 |
| Non-Dependable | `createProperty(self, 'Name', dependable=False)` | Manual cook required | Performance optimization | EX_EXTENSIONS.md 3.2 |
| Deep Dependable | `createProperty(self, 'Name', dependable='deep')` | Item-level updates | Lists/dicts | EX_EXTENSIONS.md 3.2 |
| Stored | `StorageManager` | Survives reinit/reload | User preferences | EX_EXTENSIONS.md 3.4 |

---

## File Organization Summary

### Primary Learning Files (342 examples total)

| **Category** | **File** | **Examples** | **Learning Focus** |
|--------------|----------|--------------|-------------------|
| **Core Patterns** | EX_BUILTINS.md | 19 | TouchDesigner fundamentals |
| **Event Handling** | EX_CALLBACKS.md | 19 | Callback patterns |
| **Frame Execution** | EX_EXECUTE_DATS.md | 26 | Execute DAT patterns |
| **Component Development** | EX_EXTENSIONS.md | 35 | Extension architecture |
| **Data Processing** | EX_DATS.md | 46 | Table operations |
| **Network Communication** | EX_OSC_UDP.md | 19 | Network protocols |
| **Code Organization** | EX_MODULES.md | 19 | Module system |
| **User Interface** | EX_UI.md | 15 | Dialog and interface |
| **Interactive Controls** | EX_PANELS.md | 15 | Panel components |
| **3D Operations** | EX_SOPS.md | 16 | Geometry manipulation |
| **Channel Processing** | EX_CHOPS.md | 12 | Channel operations |
| **Parameter Control** | EX_PARAMETERS.md | 13 | Parameter manipulation |
| **Development Tools** | EX_DEBUG.md | 10 | Debugging techniques |
| **System Analysis** | EX_EXAMINE_DATS.md | 10 | Runtime inspection |
| **History Management** | EX_UNDO.md | 15 | Undo/redo systems |
| **Operator Management** | EX_OPS.md | 25 | General operations |
| **Network Wiring** | EX_NODE_WIRING.md | 14 | Connection management |
| **Progressive Tutorials** | EX_MODULE_TUTORIALS.md | 13 | Step-by-step learning |

### Integration with TouchDesigner Documentation

- **Class Reference** → [CLASSES_/](../CLASSES_/) - Method signatures and object details
- **Operator Details** → [TD_/TD_OPERATORS/](../TD_/TD_OPERATORS/) - Operator-specific parameters
- **GLSL Programming** → [GLSL_/](../GLSL_/) - Shader development patterns
- **Performance Guides** → [PERFORMANCE_/](../PERFORMANCE_/) - Optimization strategies

---

*This learning guide provides structured pathways through TouchDesigner Python development, from basic concepts to professional-grade architectures. Each reference links to practical, working examples that demonstrate real-world patterns and integration strategies.*
