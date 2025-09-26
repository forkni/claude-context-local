---
title: "Operator Operations Examples"
category: EXAMPLES
document_type: examples
difficulty: beginner
time_estimate: "30-40 minutes"
user_personas: ["script_developer", "beginner_programmer", "technical_artist"]
operators: ["all_operators", "baseCOMP", "constantCHOP", "constantTOP", "constantSOP", "constantDAT"]
concepts: ["operator_access", "hierarchy_navigation", "operator_creation", "operator_properties", "storage_patterns"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics"]
workflows: ["network_programming", "operator_manipulation", "dynamic_networks"]
keywords: ["op", "ops", "operator", "create", "destroy", "hierarchy", "navigation", "properties"]
tags: ["python", "operators", "fundamentals", "navigation", "creation", "examples"]
related_docs: ["CLASS_OP_Class", "PY_TD_Python_Examples_Reference", "TD_Operator", "EX_NODE_WIRING"]
example_count: 25
---

# TouchDesigner Python Examples: Operator Operations (OPs)

## Quick Reference

General operator operations form the foundation of TouchDesigner Python programming. This category covers 25 essential patterns for operator creation, manipulation, navigation, persistence, and management across the entire operator system.

**Key Operator Functions:**

- `op()` - Operator access and navigation
- `ops()` - Multiple operator queries
- `root`, `parent()`, `me` - Hierarchy navigation
- `create()`, `destroy()` - Operator lifecycle
- `families` - Operator type system access
- Storage and persistence patterns

**Core Operations:**

- Operator access and properties
- Creation and destruction
- Navigation and hierarchy
- Display and visual properties
- Comments and metadata
- Storage and persistence

---

## Operator Access and Properties

### Basic Operator Access

```python
# Get operators by different methods
root_op = root                    # Root operator access
parent_op = me.parent()          # Direct parent access
current_op = me                  # Self reference

# Operator properties
print(f"ID: {parent_op.id}")          # Unique identifier
print(f"Name: {parent_op.name}")      # Settable name
print(f"Path: {parent_op.path}")      # Full path
print(f"Color: {parent_op.color}")    # Node color (settable)

# Access by ID (persistent across sessions)
op_by_id = op(parent_op.id)
print(f"Retrieved by ID: {op_by_id}")
```

### Hierarchy Navigation

```python
# Parent hierarchy access
parent_1 = me.parent()        # Immediate parent
parent_2 = me.parent(2)       # Grandparent  
parent_3 = me.parent(3)       # Great-grandparent

# Children access
children = parent_op.children
print(f"Child count: {len(children)}")

for child in children:
    print(f"Child: {child.name} ({child.type})")

# First child access
if children:
    first_child = children[0]
    print(f"First child: {first_child}")
```

### Multiple Operator Queries

```python
# Query multiple operators with patterns
project_ops = ops("/project1/*")     # All children of project1
ui_ops = ops("/ui")                  # UI operators
combined = ops("/project1/*", "/ui") # Multiple paths

print(f"Found {len(combined)} operators")
for op_result in combined:
    print(f"  {op_result.path}")

# Filter by type
chop_ops = [op for op in parent_op.children if op.family == 'CHOP']
print(f"CHOP operators: {[c.name for c in chop_ops]}")
```

---

## Operator Creation and Lifecycle

### Creating Operators

```python
# Create operators in current component
parent_comp = me.parent()

# Create with auto-generated name
new_box = parent_comp.create(boxSOP)
print(f"Created: {new_box.name}")

# Create with specific name
named_box = parent_comp.create(boxSOP, 'my_box_123')
print(f"Named creation: {named_box}")

# Position the new operator
named_box.nodeX = me.nodeX - 200
named_box.nodeY = me.nodeY

# Set name with error handling
try:
    named_box.name = 'unique_name'
    print(f"Renamed to: {named_box.name}")
except:
    print("Name conflict! Choose a unique name.")
```

### Operator Destruction and Cleanup

```python
def safeDestroy(target_op, confirm=True):
    """Safely destroy operator with confirmation"""
    if confirm:
        # Use UI confirmation if available
        result = ui.messageBox('Confirm Delete', 
                              f'Delete operator "{target_op.name}"?',
                              buttons=['Delete', 'Cancel'])
        if result != 0:
            return False
    
    # Check for dependencies
    dependencies = []
    for child in root.findChildren(deep=True):
        for input_conn in child.inputs:
            if input_conn and input_conn.path == target_op.path:
                dependencies.append(child.path)
    
    if dependencies:
        print(f"Warning: {target_op.name} has dependencies: {dependencies}")
    
    # Perform destruction
    target_op.destroy()
    return True

# Usage
# safeDestroy(op('old_operator'))
```

---

## Operator Display and Visual Properties

### Display Flag Management

```python
# Display flag control
target_op = op('box1')
print(f"Current display: {target_op.display}")

# Toggle display
target_op.display = not target_op.display
print(f"New display: {target_op.display}")

# Set specific display state
target_op.display = True   # Show
target_op.display = False  # Hide
```

### Viewer Assignment

```python
# Viewer management
def assignToViewer(op_to_view, viewer_number=1):
    """Assign operator to specific viewer"""
    viewer_op = op(f'viewer{viewer_number}')
    if viewer_op:
        # Set viewer to display the operator
        viewer_op.par.operator = op_to_view
        print(f"Assigned {op_to_view.name} to viewer {viewer_number}")
    else:
        print(f"Viewer {viewer_number} not found")

# Usage
assignToViewer(op('render1'), 1)
```

### Comments and Metadata

```python
# Comment management
target_op = op('box1')
print(f"Current comment: {target_op.comment}")

# Dynamic comment with timestamp
frame_comment = f'Updated from Python at frame {absTime.frame}'
target_op.comment = frame_comment
print(f"New comment: {target_op.comment}")

# Metadata through comments
def setMetadata(target_op, metadata_dict):
    """Store metadata in operator comment"""
    import json
    metadata_json = json.dumps(metadata_dict)
    target_op.comment = f"METADATA: {metadata_json}"

def getMetadata(target_op):
    """Retrieve metadata from operator comment"""
    import json
    comment = target_op.comment
    if comment.startswith("METADATA: "):
        try:
            return json.loads(comment[10:])  # Remove "METADATA: " prefix
        except:
            return {}
    return {}

# Usage
setMetadata(op('constant1'), {'type': 'generator', 'version': '1.0'})
metadata = getMetadata(op('constant1'))
print(f"Metadata: {metadata}")
```

---

## Operator Type System and Families

### Family System Access

```python
# Access operator families
print("Available families:")
for family_name in families:
    print(f"  {family_name}")

# Family contents
dat_family = families['DAT']
print(f"DAT operators ({len(dat_family)}):")
for dat_type in dat_family:
    print(f"  {dat_type.type}: {dat_type.label} (family: {dat_type.family})")

# Find specific operator types
def findOperatorType(type_name):
    """Find operator type across all families"""
    for family_name, family_ops in families.items():
        for op_type in family_ops:
            if op_type.type.lower() == type_name.lower():
                return op_type, family_name
    return None, None

# Usage
op_type, family = findOperatorType('noise')
if op_type:
    print(f"Found {op_type.type} in {family} family")
```

### Type-Based Operations

```python
def createByType(parent_comp, type_name, name=None):
    """Create operator by type string"""
    op_type, family = findOperatorType(type_name)
    if not op_type:
        print(f"Operator type '{type_name}' not found")
        return None
    
    # Get the actual operator class
    op_class = getattr(sys.modules[__name__], type_name + family.upper(), None)
    if not op_class:
        print(f"Could not find class for {type_name}")
        return None
    
    # Create the operator
    return parent_comp.create(op_class, name)

def analyzeNetwork(parent_comp):
    """Analyze network composition by families"""
    family_counts = {}
    
    for child in parent_comp.children:
        family = child.family
        family_counts[family] = family_counts.get(family, 0) + 1
    
    print("Network composition:")
    for family, count in sorted(family_counts.items()):
        print(f"  {family}: {count} operators")
    
    return family_counts

# Usage
analyzeNetwork(op('/project1'))
```

---

## Storage and Persistence

### Operator Storage System

```python
# Store and fetch data with operators
def storeOperatorData(target_op, data_dict):
    """Store multiple data items in operator"""
    for key, value in data_dict.items():
        target_op.store(key, value)
        print(f"Stored {key} in {target_op.name}")

def fetchOperatorData(target_op, keys, defaults=None):
    """Fetch multiple data items from operator"""
    if defaults is None:
        defaults = {}
    
    results = {}
    for key in keys:
        default_val = defaults.get(key, None)
        results[key] = target_op.fetch(key, default_val)
    
    return results

# Usage
op_data = {
    'last_updated': absTime.frame,
    'user_settings': {'quality': 'high', 'enabled': True},
    'processing_stats': [1.2, 0.8, 1.5]
}

storeOperatorData(op('container1'), op_data)
retrieved = fetchOperatorData(op('container1'), 
                             ['last_updated', 'user_settings', 'missing_key'],
                             {'missing_key': 'default_value'})
print(f"Retrieved: {retrieved}")
```

### Persistent Configuration

```python
class OperatorConfig:
    """Manage operator configuration with persistence"""
    
    def __init__(self, target_op):
        self.target_op = target_op
        self.config_key = 'python_config'
    
    def save_config(self, config_dict):
        """Save configuration to operator storage"""
        import json
        config_json = json.dumps(config_dict)
        self.target_op.store(self.config_key, config_json)
        print(f"Config saved to {self.target_op.name}")
    
    def load_config(self, default_config=None):
        """Load configuration from operator storage"""
        import json
        if default_config is None:
            default_config = {}
        
        config_json = self.target_op.fetch(self.config_key, '{}')
        try:
            return json.loads(config_json)
        except:
            return default_config
    
    def update_config(self, updates):
        """Update specific configuration values"""
        config = self.load_config()
        config.update(updates)
        self.save_config(config)
        return config

# Usage
config_manager = OperatorConfig(op('base1'))
config_manager.save_config({'processing_mode': 'realtime', 'quality': 0.8})
current_config = config_manager.load_config()
print(f"Current config: {current_config}")
```

---

## Advanced Patterns

### Operator Selection and Filtering

```python
def selectOperators(parent_comp, criteria=None):
    """Advanced operator selection with multiple criteria"""
    if criteria is None:
        criteria = {}
    
    results = []
    for child in parent_comp.children:
        matches = True
        
        # Check family criteria
        if 'family' in criteria:
            if child.family not in criteria['family']:
                matches = False
        
        # Check name pattern criteria
        if 'name_contains' in criteria:
            if criteria['name_contains'].lower() not in child.name.lower():
                matches = False
        
        # Check has_inputs criteria
        if 'has_inputs' in criteria:
            has_inputs = len(child.inputs) > 0
            if has_inputs != criteria['has_inputs']:
                matches = False
        
        # Check display criteria
        if 'display' in criteria:
            if child.display != criteria['display']:
                matches = False
        
        if matches:
            results.append(child)
    
    return results

# Usage examples
chop_ops = selectOperators(op('/project1'), {'family': ['CHOP']})
displayed_ops = selectOperators(op('/project1'), {'display': True})
math_ops = selectOperators(op('/project1'), {'name_contains': 'math'})

print(f"Found {len(chop_ops)} CHOP operators")
print(f"Found {len(displayed_ops)} displayed operators")
print(f"Found {len(math_ops)} math-related operators")
```

### Operator Batch Operations

```python
def batchOperatorOperation(operators, operation, **kwargs):
    """Apply operation to multiple operators"""
    results = {}
    
    for op_target in operators:
        try:
            if operation == 'set_display':
                op_target.display = kwargs.get('display', True)
                results[op_target.name] = 'success'
            
            elif operation == 'set_color':
                op_target.color = kwargs.get('color', (1, 1, 1))
                results[op_target.name] = 'success'
            
            elif operation == 'add_comment':
                comment_text = kwargs.get('text', f'Batch update {absTime.frame}')
                op_target.comment = comment_text
                results[op_target.name] = 'success'
            
            elif operation == 'cook':
                op_target.cook()
                results[op_target.name] = 'success'
            
        except Exception as e:
            results[op_target.name] = f'error: {str(e)}'
    
    return results

# Usage
selected_ops = selectOperators(op('/project1'), {'family': ['CHOP', 'DAT']})
batch_results = batchOperatorOperation(selected_ops, 'set_color', color=(0.8, 0.8, 1.0))

print("Batch operation results:")
for op_name, result in batch_results.items():
    print(f"  {op_name}: {result}")
```

---

## Cross-References

**Related Documentation:**

- [EX_NODE_WIRING](./EX_NODE_WIRING.md) - Connection and wiring patterns
- [EX_EXTENSIONS](./EX_EXTENSIONS.md) - Component extension development
- [EX_PARAMETERS](./EX_PARAMETERS.md) - Parameter manipulation
- [CLASSES_/CLASS_OP](../CLASSES_/CLASS_OP.md) - Operator class reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Performance Notes:**

- Operator creation and destruction should be minimized in performance-critical code
- Use operator IDs for persistent references across sessions
- Batch operations are more efficient than individual operator manipulations
- Storage operations have overhead - consider caching frequently accessed data

---

## File References

**Source Files (25 total):**

- `OPs__Text__test_OP__td.txt` - Core operator access and manipulation
- `OPs__Text__test_families__td.txt` - Operator family system access
- `OPs__Text__test_Selection__td.txt` - Operator selection patterns
- `OPs__Text__test_copy_destroy__td.py` - Copy and destruction operations
- `OPs__Text__test_locate__td.txt` - Operator location and navigation
- `OPs__Text__test_save__td.txt` - Operator saving and persistence
- `OPs__Text__test_store_fetch__td.txt` - Storage system operations
- `OPs__Text__test_viewers__td.txt` - Viewer assignment patterns
- `OPs__Text__test_change__td.txt` - Change detection and monitoring
- `OPs__Text__reset_example__td.txt` - Reset and initialization patterns
- `OPs__Text__text1__td.txt` - Text operations
- `OPs__Text__text4_callbacks__td.py` - Callback integration
- `OPs__Table__table5__td.tsv` - Table data operations
- `button*__*Execute__*__td.py` - Button integration (4 files)
- `annotation__*__td.*` - Annotation system (3 files)
- `docsHelper__*__td.*` - Documentation helpers (3 files)
- `open_wiki*__*Execute__*__td.py` - Wiki integration (4 files)

**Operation Categories:**

- **Core Access**: Basic operator access, properties, and hierarchy
- **Lifecycle**: Creation, destruction, and management
- **Visual Properties**: Display, colors, comments, and metadata
- **Type System**: Family access and type-based operations
- **Persistence**: Storage, configuration, and data management

---

*This documentation covers essential TouchDesigner operator operations providing the foundation for all network manipulation, creation, and management tasks in Python.*
