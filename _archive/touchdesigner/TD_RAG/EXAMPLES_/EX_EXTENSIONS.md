---
title: "Extension Development Examples"
category: EXAMPLES
document_type: examples
difficulty: advanced
time_estimate: "45-60 minutes"
user_personas: ["script_developer", "technical_artist", "system_architect"]
operators: ["baseCOMP", "containerCOMP", "scriptDAT"]
concepts: ["extensions", "tdf_properties", "code_organization", "storage_patterns", "function_promotion"]
prerequisites: ["Python_fundamentals", "TouchDesigner_Python_API", "object_oriented_programming"]
workflows: ["component_development", "advanced_scripting", "system_architecture"]
keywords: ["extensions", "tdf", "properties", "storage", "promotion", "class", "component"]
tags: ["python", "extensions", "tdf", "advanced", "architecture", "examples"]
related_docs: ["PY_Extensions", "EX_MODULES", "CLASS_COMP_Class", "PY_TD_Python_Examples_Reference"]
example_count: 35
---

# TouchDesigner Python Examples: Extension Development

## Overview

Comprehensive examples for developing component extensions in TouchDesigner. These examples demonstrate extension class creation, property management, function promotion, storage patterns, and advanced TDF (TouchDesigner Function) techniques.

**Source**: TouchDesigner Help > Python Examples > Extensions  
**Example Count**: 35 files  
**Focus**: Component extension architecture, TDF properties, code organization

## Quick Reference

### Core Extension Patterns

- **[Basic Extension Creation](#basic-extension-creation)** - Foundation extension class structure
- **[TDF Properties](#tdf-properties)** - createProperty patterns and property types
- **[Storage Extensions](#storage-extensions)** - Persistent data management with StorageManager
- **[Function Promotion](#function-promotion)** - Making extension methods accessible

### Advanced Patterns  

- **[Property Types](#property-types)** - Dependable, non-dependable, and read-only properties
- **[Extension Testing](#extension-testing)** - Debugging and testing extension behavior
- **[Conflict Resolution](#conflict-resolution)** - Managing naming conflicts between extensions
- **[Best Practices](#best-practices)** - Patterns for robust extension development

---

## Basic Extension Creation

### Simple Extension Class

**Source Files**: `ExampleExt.py`, `test_extensions.py`

**Key Concepts**: Extension class structure, **init** method, ownerComp reference

```python
class ExampleExt:
    """A simple example extension"""
    def __init__(self, ownerComp):
        """__init__ method always runs on creation"""
        self.ownerComp = ownerComp  # the component with the extension
        
        # Promoted member (capitalized)
        self.H = 'value h' 
        
        # Non-promoted member (lowercase)
        self.i = 'value i'
        
    def Double(self, v):
        """promoted doubling function"""
        return v*2
                
    def g(self):
        """non-promoted function"""
        return 34

    def F(self):
        """promoted function"""
        return 'F1'
```

**Key Rules**:

- **Capitalized members/methods** → Promoted (accessible from component)
- **Lowercase members/methods** → Non-promoted (internal only)
- Always store `ownerComp` reference for component access
- `__init__` runs automatically when extension loads

### Accessing Extensions

**Source File**: `test_extensions.py`

```python
# Get list of extension objects on a component
debug(op('base1').extensions)

# Access promoted members directly
component = op('base1')
result = component.Double(6)  # Calls promoted function

# Access specific extension when conflicts exist
result = ext.ExampleExt.F() + ext.Example2Ext.F()
```

**Extension Access Patterns**:

- `component.MethodName()` - Direct access to promoted methods
- `ext.ExtensionName.method()` - Specific extension access
- `component.extensions` - List all extension objects

---

## TDF Properties

### Basic Property Creation

**Source File**: `CustomExt.py`

**Key Concepts**: createProperty function, property types, dependency management

```python
import TDFunctions 

class CustomExt:
    """
    CustomExt shows the use of createProperty
    """
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp

        # Basic dependable property (default settings)
        TDFunctions.createProperty(self, 
                name='DependableVal')     # name of property
                # uses defaults: value=None, dependable=True, readOnly=False

        self.DependableVal = 0  # simple member access

        # Non-dependable property
        TDFunctions.createProperty(self, 
                name='NonDependableVal',
                value=0,
                dependable=False) 

        # Read-only property
        TDFunctions.createProperty(self, 
                name='ReadOnlyVal',
                readOnly=True)     

        self._ReadOnlyVal.val = 55  # more complicated to access

        # List property with dependency tracking
        TDFunctions.createProperty(self, 
                name='DependableList',     # name of property
                value=[1,2,3],             # starting value (optional)
                dependable=True,           # dependable (optional)
                readOnly=False)            # readOnly (optional)

        # Deep dependable list (tracks nested changes)
        TDFunctions.createProperty(self, 
                name='DeepDependableList', 
                value=[10,20,30],             
                dependable='deep')
```

### Property Types and Behavior

**Dependable Properties**:

- Changes trigger network updates
- Component cooks when property changes
- Use for values that affect rendering/processing

**Non-Dependable Properties**:

- Changes don't trigger network updates
- Use for UI state, temporary values
- Better performance for frequently changing data

**Read-Only Properties**:

- Cannot be modified externally
- Access via `_PropertyName.val` internally
- Use for computed values, status information

**Deep Dependable**:

- Tracks changes inside lists/objects
- More overhead but comprehensive tracking
- Use when nested data affects component behavior

---

## Storage Extensions

### Persistent Data with StorageManager

**Source File**: `StorageExt.py`

**Key Concepts**: StorageManager, persistent properties, data survival across saves

```python
from TDStoreTools import StorageManager

class StorageExt:
    """
    StorageExt description
    """
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp

        # stored items (persistent across saves and re-initialization):
        storedItems = [
            # Only 'name' is required
            # 'dependable' can also be "deep"
            {'name': 'StoredProperty', 'default': 10, 'readOnly': False,
                             'property': True, 'dependable': True},
        ]        
        self.stored = StorageManager(self, ownerComp, storedItems)

    def setStoredProperty(self):
        # example of setting
        self.StoredProperty = 20  # easy access
        
    def resetAllStoredValuesToDefault(self):
        # example of using StorageManager object
        self.stored.restoreAllDefaults()
```

### StorageManager Configuration

**StoredItem Dictionary Options**:

```python
storedItem = {
    'name': 'PropertyName',        # Required: property name
    'default': 0,                  # Default value
    'readOnly': False,             # Whether property is read-only  
    'property': True,              # Create as TDF property
    'dependable': True             # 'deep', True, or False
}
```

**Storage Behavior**:

- Data survives file saves/loads
- Persists through extension reinitialization
- Cut/paste operations preserve stored values
- Use for user preferences, configuration data

### Testing Stored Properties

**Source File**: `test_storedProperty.txt`

```python
# Modify stored property
op('container2').StoredProperty += 1

# Reiniting extensions doesn't reset data
# (unlike createProperty-based properties)
op('container2').par.reinitextensions.pulse()

# Value remains after:
# - Save/reload file
# - Cut/paste operator
# - Extension reinitialization
```

---

## Function Promotion

### Promoted vs Non-Promoted Functions

**Source Files**: `promoted_function.py`, `nonpromoted_function.py`

**Key Concepts**: Capitalization rules, accessibility patterns

```python
class ExampleExt:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        
        # Promoted member (accessible externally)
        self.PublicValue = 42
        
        # Non-promoted member (internal only)
        self.private_value = 99
    
    def PublicMethod(self, value):
        """PROMOTED: Capitalized methods are accessible externally"""
        return value * 2
    
    def private_method(self):
        """NON-PROMOTED: Lowercase methods are internal only"""
        return self.private_value

# Usage from component:
component = op('my_component')
result = component.PublicMethod(5)  # Works - promoted
# component.private_method()        # Error - not promoted

# Access through extension object:
result = component.ext.ExampleExt.private_method()  # Works
```

**Promotion Rules**:

- **Capitalized** → Promoted (externally accessible)
- **Lowercase** → Non-promoted (internal only)  
- Use promotion for public API, keep internals private
- Access non-promoted via `ext.ExtensionName.method()`

### Function Conflict Resolution

**Source Files**: `promoted_function_conflict.py`, `promoted_function_conflict_resolved.py`

**Key Concepts**: Multiple extensions, naming conflicts, explicit access

```python
# When multiple extensions have same method name:

# This causes conflict if both extensions have F() method
result = parent().F()  # Ambiguous - which extension's F()?

# Resolution: Use explicit extension reference
result1 = ext.ExampleExt.F()   # Specific extension
result2 = ext.Example2Ext.F()  # Different extension
combined = ext.ExampleExt.F() + ext.Example2Ext.F()

# Best practice: Use unique method names to avoid conflicts
class MyExt:
    def MyExt_ProcessData(self):  # Prefixed with extension name
        pass
        
    def UniqueMethodName(self):   # Descriptive, unique name
        pass
```

---

## Property Types

### Testing Different Property Behaviors

**Source Files**: Various `test_update*` and `test_change*` files

### Dependable Properties

```python
# Dependable properties trigger network updates
def test_dependable_updates():
    component = op('container')
    
    # Changing dependable property triggers cook
    component.DependableVal = 50    # Network cooks
    
    # List operations also trigger updates
    component.DependableList.append(4)     # Network cooks
    component.DependableList[0] = 99       # Network cooks
```

### Non-Dependable Properties

```python
# Non-dependable properties don't trigger updates
def test_nondependable_updates():
    component = op('container')
    
    # Changing non-dependable property - no cook
    component.NonDependableVal = 75    # No network update
    
    # Good for UI state, counters, temporary data
    component.NonDependableCounter += 1   # No overhead
```

### Deep Dependable Properties  

```python
# Deep dependable tracks nested changes
def test_deep_dependable():
    component = op('container')
    
    # All of these trigger network updates:
    component.DeepDependableList[0] = 999         # Nested change detected
    component.DeepDependableList.append([1,2,3]) # Addition detected
    component.DeepDependableList[2][1] = 'nested' # Deep nesting tracked
    
    # Use for complex data structures that affect rendering
```

### Read-Only Properties

```python
# Read-only properties for computed values
class ComputedExt:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        
        TDFunctions.createProperty(self,
                name='Status',
                readOnly=True)
                
        self.update_status()
    
    def update_status(self):
        # Internal update of read-only property
        current_frame = absTime.frame
        self._Status.val = f'Frame: {current_frame}'
    
    def GetStatus(self):
        """Promoted method to access computed value"""
        self.update_status()
        return self.Status

# Usage:
status = component.GetStatus()  # Returns current computed value
# component.Status = "new"      # Error - read-only
```

---

## Extension Testing

### Testing Extension Functionality

**Source File**: `test_extensions.py`

```python
# Get all extensions on a component
extensions = op('base1').extensions
debug('Extensions:', extensions)

# Test extension methods
component = op('base1')

# Test promoted functions
result = component.Double(6)
print(f'Double result: {result}')

# Test promoted properties
component.H = 'new value'
print(f'Property H: {component.H}')

# Test non-promoted access
non_promoted = component.ext.ExampleExt.g()
print(f'Non-promoted result: {non_promoted}')
```

### Property Testing Patterns

```python
def test_extension_properties():
    """Comprehensive property testing"""
    comp = op('test_component')
    
    # Test dependable property
    original_val = comp.DependableVal
    comp.DependableVal = 999
    assert comp.DependableVal == 999, "Dependable property assignment failed"
    
    # Test non-dependable property
    comp.NonDependableVal = 123  
    assert comp.NonDependableVal == 123, "Non-dependable property failed"
    
    # Test list operations
    original_list = comp.DependableList.copy()
    comp.DependableList.append(999)
    assert 999 in comp.DependableList, "List append failed"
    
    # Test read-only property (should be accessible but not settable)
    try:
        comp.ReadOnlyVal = 999  # Should fail
        assert False, "Read-only property allowed modification"
    except:
        pass  # Expected behavior
        
    print("All property tests passed")

# Run tests
test_extension_properties()
```

### Extension Lifecycle Testing

```python
def test_extension_lifecycle():
    """Test extension behavior through component lifecycle"""
    comp = op('test_component')
    
    # Set initial values
    comp.StoredProperty = 555
    comp.DependableVal = 777
    
    # Test extension reinitialization
    comp.par.reinitextensions.pulse()
    
    # StorageManager properties survive reinitialization
    assert comp.StoredProperty == 555, "Stored property lost on reinit"
    
    # createProperty-based properties reset to defaults
    # (unless you implement custom persistence)
    print("Extension lifecycle test passed")

test_extension_lifecycle()
```

---

## Best Practices

### Extension Architecture Patterns

```python
# Recommended extension structure
import TDFunctions
from TDStoreTools import StorageManager

class MyComponentExt:
    """
    MyComponent Extension
    
    Provides enhanced functionality for MyComponent including:
    - Data processing capabilities
    - Configuration management  
    - Event handling
    """
    
    def __init__(self, ownerComp: 'COMP') -> None:
        # Store component reference
        self.ownerComp = ownerComp
        
        # Initialize properties
        self._init_properties()
        
        # Initialize storage
        self._init_storage()
        
        # Initialize internal state
        self._internal_counter = 0  # Non-promoted internal state
        
    def _init_properties(self):
        """Initialize TDF properties"""
        # Public configuration properties
        TDFunctions.createProperty(self,
                name='Enabled',
                value=True,
                dependable=True)
                
        TDFunctions.createProperty(self,
                name='ProcessingMode', 
                value='normal',
                dependable=True)
        
        # Read-only status properties
        TDFunctions.createProperty(self,
                name='Status',
                readOnly=True)
                
        self._Status.val = 'Initialized'
    
    def _init_storage(self):
        """Initialize persistent storage"""
        storedItems = [
            {'name': 'UserPreferences', 'default': {}, 'property': True},
            {'name': 'LastConfiguration', 'default': '', 'property': True},
        ]
        self.stored = StorageManager(self, self.ownerComp, storedItems)
    
    # PUBLIC API (Promoted Methods)
    
    def ProcessData(self, data):
        """Process input data based on current configuration"""
        if not self.Enabled:
            return None
            
        mode = self.ProcessingMode
        if mode == 'advanced':
            return self._advanced_processing(data)
        else:
            return self._normal_processing(data)
    
    def SaveConfiguration(self, config):
        """Save configuration to persistent storage"""
        self.LastConfiguration = str(config)
        self._Status.val = 'Configuration Saved'
    
    def GetStatus(self):
        """Get current component status"""
        return f'{self.Status} | Mode: {self.ProcessingMode}'
    
    # PRIVATE METHODS (Non-promoted)
    
    def _normal_processing(self, data):
        """Internal processing method"""
        self._internal_counter += 1
        return data * 2
    
    def _advanced_processing(self, data):
        """Advanced internal processing"""
        self._internal_counter += 1
        return data ** 2 + self._internal_counter
```

### Error Handling in Extensions

```python
class SafeExtension:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        try:
            self._initialize_safely()
        except Exception as e:
            debug(f'Extension initialization error: {e}')
            self._fallback_initialization()
    
    def _initialize_safely(self):
        """Initialize with error checking"""
        # Check if required operators exist
        required_ops = ['data_input', 'config_table']
        for op_name in required_ops:
            if not self.ownerComp.op(op_name):
                raise LookupError(f'Required operator "{op_name}" not found')
        
        # Initialize properties
        TDFunctions.createProperty(self, name='SafeProperty', value=0)
    
    def _fallback_initialization(self):
        """Fallback initialization if primary fails"""
        TDFunctions.createProperty(self, name='SafeProperty', value=-1)
        debug('Extension initialized in fallback mode')
    
    def SafeMethod(self, value):
        """Method with error handling"""
        try:
            return self._process_value(value)
        except Exception as e:
            debug(f'SafeMethod error: {e}')
            return None
    
    def _process_value(self, value):
        """Internal processing with potential errors"""
        if not isinstance(value, (int, float)):
            raise TypeError(f'Expected number, got {type(value)}')
        return value * self.SafeProperty
```

### Performance Considerations

```python
class PerformantExtension:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        
        # Cache frequently accessed operators
        self._data_op = ownerComp.op('data')
        self._output_op = ownerComp.op('output')
        
        # Use non-dependable for frequently changing data
        TDFunctions.createProperty(self,
                name='FrameCounter',
                value=0,
                dependable=False)  # No network updates
        
        # Use dependable for configuration
        TDFunctions.createProperty(self,
                name='Quality',
                value=1.0,
                dependable=True)   # Triggers updates when changed
    
    def FastUpdate(self):
        """High-performance update method"""
        # Non-dependable property - no cook overhead
        self.FrameCounter += 1
        
        # Cache expensive computations
        if not hasattr(self, '_cached_config'):
            self._cached_config = self._compute_expensive_config()
        
        # Use cached values
        return self._cached_config * self.Quality
    
    def InvalidateCache(self):
        """Call when configuration changes"""
        if hasattr(self, '_cached_config'):
            delattr(self, '_cached_config')
```

---

## Cross-References

### Related Documentation

- **[CLASS_Extension_Class.md](../CLASSES_/CLASS_Extension_Class.md)** - Extension class API reference
- **[PY_Extensions.md](../PYTHON_/PY_Extensions.md)** - Extension development concepts
- **[PY_TD_Function_Reference.md](../PYTHON_/PY_TD_Function_Reference.md)** - TDFunctions documentation
- **[MODULE_TDStoreTools.md](../MODULE_/MODULE_TDStoreTools.md)** - StorageManager reference

### Related Examples

- **[EX_MODULES.md](./EX_MODULES.md)** - Module system integration with extensions
- **[EX_CALLBACKS.md](./EX_CALLBACKS.md)** - Extension callback patterns
- **[EX_PARAMETERS.md](./EX_PARAMETERS.md)** - Parameter manipulation in extensions

### Extension-Compatible Components

Extensions can be added to any COMP operator:

- **Container COMP** - Most common extension host
- **Base COMP** - For reusable extension components  
- **Panel COMPs** - UI-specific extensions
- **Custom Components** - Specialized behavior extensions

---

## File Reference

**Example Files Location**: `TD_PYTHON_Examples/Scripts/Extensions/`

**Key Files**:

- `ExampleExt.py` - Basic extension class template
- `CustomExt.py` - TDF property examples
- `StorageExt.py` - StorageManager usage patterns
- `promoted_function.py` - Function promotion examples
- `test_extensions.py` - Extension testing patterns
- `test_*Property.txt` - Property behavior tests

**Total Examples**: 35 files covering all aspects of extension development from basic class creation to advanced property management and storage patterns.

---

*These examples provide the foundation for creating robust, reusable component extensions in TouchDesigner. Use them as templates for your own extension development projects.*
