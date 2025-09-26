---
title: "Node Wiring Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "20-30 minutes"
user_personas: ["script_developer", "technical_artist", "system_architect"]
operators: ["all_operators", "mergeCHOP", "mergeTOP", "mergeSOP", "mergeDAT", "switchCHOP"]
concepts: ["network_connections", "node_wiring", "multi_input", "connector_management", "dynamic_networks"]
prerequisites: ["Python_fundamentals", "TouchDesigner_network_basics", "operator_concepts"]
workflows: ["dynamic_networks", "procedural_connections", "network_automation"]
keywords: ["connections", "wiring", "inputs", "outputs", "connectors", "multi-input", "network"]
tags: ["python", "network", "connections", "wiring", "automation", "examples"]
related_docs: ["CLASS_OP_Class", "EX_OPS", "TD_Network_Editor", "PY_TD_Python_Examples_Reference"]
example_count: 14
---

# TouchDesigner Python Examples: Node Wiring

## Quick Reference

TouchDesigner's connection system enables sophisticated network wiring through Python. This category covers 14 essential patterns for connecting operators, managing inputs/outputs, handling multi-inputs, and inspecting network connectivity.

**Key Connection Types:**

- **Input/Output Connections** - Standard operator wiring
- **COMP Connections** - Component-specific wiring
- **Multi-Input Systems** - Multiple source connections
- **Connector Management** - Low-level connection control

**Core Operations:**

- Connection inspection and analysis
- Dynamic wiring and rewiring
- Multi-input management
- Connector-level control
- Connection clearing and cleanup

---

## Connection Inspection

### Basic Connection Analysis

```python
# Inspect operator connections
target_op = op('geo2')

# Input operators (what's connected to this operator's inputs)
print("Input operators:", target_op.inputs)

# Output operators (what this operator connects to)
print("Output operators:", target_op.outputs)

# Input connectors (connection points)
print("Input connectors:", target_op.inputConnectors)

# Output connectors (connection points)  
print("Output connectors:", target_op.outputConnectors)

# Detailed connection information
for i, input_op in enumerate(target_op.inputs):
    if input_op:
        print(f"Input {i}: connected to {input_op.path}")
    else:
        print(f"Input {i}: not connected")
```

### COMP-Specific Connections

```python
# Components have additional connection types
comp_op = op('container1')

print("--- COMP-only connections ---")

# Input COMPs (components connected to this COMP's inputs)
print("Input COMPs:", comp_op.inputCOMPs)

# Output COMPs (components this COMP connects to)
print("Output COMPs:", comp_op.outputCOMPs)

# COMP connector objects
print("Input COMP connectors:", comp_op.inputCOMPConnectors)
print("Output COMP connectors:", comp_op.outputCOMPConnectors)

# COMP connection details
for i, comp_input in enumerate(comp_op.inputCOMPs):
    if comp_input:
        print(f"COMP Input {i}: {comp_input.path}")
```

---

## Basic Connection Operations

### Single Input Connections

```python
# Connect and disconnect single inputs
target_op = op('geo2')
source_op = op('abox1')

# Get specific input connector
input_connector = target_op.inputConnectors[0]

# Check if connected
if input_connector.connections:
    print("Input 0 is connected - disconnecting")
    input_connector.disconnect()
else:
    print("Input 0 is not connected - connecting")
    input_connector.connect(source_op)

# Alternative connection method
target_op.inputConnectors[1].connect(op('sphere1'))
```

### Connection State Management

```python
def toggleConnection(target_op, input_index, source_op):
    """Toggle connection state for specific input"""
    connector = target_op.inputConnectors[input_index]
    
    if connector.connections:
        print(f"Disconnecting input {input_index}")
        connector.disconnect()
        return False  # Now disconnected
    else:
        print(f"Connecting input {input_index} to {source_op.name}")
        connector.connect(source_op)
        return True   # Now connected

# Usage
is_connected = toggleConnection(op('merge1'), 0, op('noise1'))
print(f"Connection state: {is_connected}")
```

### Clear All Inputs

```python
def clearAllInputs(target_op):
    """Disconnect all inputs from an operator"""
    for i, connector in enumerate(target_op.inputConnectors):
        if connector.connections:
            print(f"Clearing input {i}")
            connector.disconnect()
    
    print(f"All inputs cleared for {target_op.name}")

# Usage
clearAllInputs(op('merge1'))
```

---

## Multi-Input Systems

### Multi-Input Connection Management

```python
# Multi-input operators (Merge, Math, etc.)
merge_op = op('merge2')
source_ops = [op('zbox1'), op('zbox2'), op('zbox3'), op('zbox4')]

# setInputs is the preferred method for multi-inputs
def cycleThroughConnections():
    """Cycle through different connection configurations"""
    current_inputs = merge_op.inputs
    
    if op('zbox1') in current_inputs:
        print("Connecting zbox2 and zbox4")
        merge_op.setInputs([op('zbox2'), op('zbox4')])
    
    elif op('zbox2') in current_inputs:
        print("Connecting zbox3 and zbox4") 
        merge_op.setInputs([op('zbox3'), op('zbox4')])
    
    else:
        print("Connecting zbox1 and zbox4")
        merge_op.setInputs([op('zbox1'), op('zbox4')])

# Execute cycle
cycleThroughConnections()
```

### Dynamic Multi-Input Management

```python
class MultiInputManager:
    """Manage multi-input operator connections"""
    
    def __init__(self, multi_input_op):
        self.op = multi_input_op
        self.source_pool = []
    
    def addSourceToPool(self, source_op):
        """Add operator to available source pool"""
        if source_op not in self.source_pool:
            self.source_pool.append(source_op)
            print(f"Added {source_op.name} to source pool")
    
    def removeSourceFromPool(self, source_op):
        """Remove operator from source pool"""
        if source_op in self.source_pool:
            self.source_pool.remove(source_op)
            print(f"Removed {source_op.name} from source pool")
    
    def setRandomInputs(self, count=2):
        """Set random selection of inputs from pool"""
        import random
        
        if len(self.source_pool) < count:
            print(f"Not enough sources in pool ({len(self.source_pool)} < {count})")
            return
        
        selected = random.sample(self.source_pool, count)
        self.op.setInputs(selected)
        print(f"Connected random inputs: {[s.name for s in selected]}")
    
    def setInputsByPattern(self, pattern='alternating'):
        """Set inputs based on pattern"""
        if pattern == 'alternating':
            # Every other source
            selected = self.source_pool[::2]
        elif pattern == 'first_n':
            # First N sources
            selected = self.source_pool[:3]
        elif pattern == 'all':
            # All sources
            selected = self.source_pool
        else:
            selected = []
        
        if selected:
            self.op.setInputs(selected)
            print(f"Pattern '{pattern}': {[s.name for s in selected]}")

# Usage
manager = MultiInputManager(op('merge1'))
for i in range(1, 5):
    manager.addSourceToPool(op(f'noise{i}'))

manager.setRandomInputs(2)
manager.setInputsByPattern('alternating')
```

---

## Advanced Connection Patterns

### Connection Inspection and Analysis

```python
def analyzeConnections(target_op):
    """Comprehensive connection analysis"""
    analysis = {
        'input_count': len(target_op.inputConnectors),
        'output_count': len(target_op.outputConnectors),
        'connected_inputs': 0,
        'connected_outputs': 0,
        'input_sources': [],
        'output_destinations': []
    }
    
    # Analyze inputs
    for i, connector in enumerate(target_op.inputConnectors):
        if connector.connections:
            analysis['connected_inputs'] += 1
            source_op = target_op.inputs[i]
            if source_op:
                analysis['input_sources'].append({
                    'index': i,
                    'source': source_op.path,
                    'type': source_op.type
                })
    
    # Analyze outputs  
    for i, output_op in enumerate(target_op.outputs):
        if output_op:
            analysis['connected_outputs'] += 1
            analysis['output_destinations'].append({
                'index': i,
                'destination': output_op.path,
                'type': output_op.type
            })
    
    return analysis

# Usage and reporting
def reportConnections(target_op):
    """Generate connection report"""
    analysis = analyzeConnections(target_op)
    
    print(f"Connection Analysis for {target_op.name}:")
    print(f"  Inputs: {analysis['connected_inputs']}/{analysis['input_count']} connected")
    print(f"  Outputs: {analysis['connected_outputs']}/{analysis['output_count']} connected")
    
    print("  Input Sources:")
    for source in analysis['input_sources']:
        print(f"    [{source['index']}] {source['source']} ({source['type']})")
    
    print("  Output Destinations:")
    for dest in analysis['output_destinations']:
        print(f"    [{dest['index']}] {dest['destination']} ({dest['type']})")

# Generate report
reportConnections(op('merge1'))
```

### Connection Validation

```python
def validateConnections(target_op):
    """Validate operator connections for common issues"""
    issues = []
    
    # Check for missing critical inputs
    if len(target_op.inputs) == 0 and target_op.type not in ['constant', 'noise', 'pattern']:
        issues.append("No inputs connected (may need source)")
    
    # Check for unused outputs
    connected_outputs = [o for o in target_op.outputs if o is not None]
    if len(connected_outputs) == 0:
        issues.append("No outputs connected (result not used)")
    
    # Check for type mismatches
    for i, input_op in enumerate(target_op.inputs):
        if input_op:
            # Basic family compatibility check
            if hasattr(target_op, 'family') and hasattr(input_op, 'family'):
                if target_op.family == 'CHOP' and input_op.family == 'TOP':
                    issues.append(f"Input {i}: Potential type mismatch (TOP->CHOP)")
    
    # Check for circular references
    def check_circular(op, visited=None):
        if visited is None:
            visited = set()
        
        if op.id in visited:
            return True
        
        visited.add(op.id)
        
        for input_op in op.inputs:
            if input_op and check_circular(input_op, visited.copy()):
                return True
        
        return False
    
    if check_circular(target_op):
        issues.append("Potential circular reference detected")
    
    return issues

# Validate and report
def runConnectionValidation(target_op):
    """Run validation and report results"""
    issues = validateConnections(target_op)
    
    if issues:
        print(f"Connection Issues for {target_op.name}:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"No connection issues found for {target_op.name}")

# Usage
runConnectionValidation(op('merge1'))
```

### Batch Connection Operations  

```python
def batchConnect(targets, source_op, input_index=0):
    """Connect single source to multiple targets"""
    results = {}
    
    for target in targets:
        try:
            if input_index < len(target.inputConnectors):
                target.inputConnectors[input_index].connect(source_op)
                results[target.name] = 'connected'
            else:
                results[target.name] = 'invalid_input_index'
        except Exception as e:
            results[target.name] = f'error: {str(e)}'
    
    return results

def chainOperators(operators):
    """Chain operators in sequence (output to next input)"""
    if len(operators) < 2:
        print("Need at least 2 operators to chain")
        return
    
    for i in range(len(operators) - 1):
        source = operators[i]
        target = operators[i + 1]
        
        try:
            target.inputConnectors[0].connect(source)
            print(f"Connected {source.name} -> {target.name}")
        except Exception as e:
            print(f"Failed to connect {source.name} -> {target.name}: {e}")

# Usage examples
noise_ops = [op(f'noise{i}') for i in range(1, 4)]
merge_result = batchConnect([op('merge1'), op('merge2')], op('constant1'), 0)
print("Batch connection results:", merge_result)

# Chain noise -> math -> output
processing_chain = [op('noise1'), op('math1'), op('out1')]
chainOperators(processing_chain)
```

---

## Cross-References

**Related Documentation:**

- [EX_OPS](./EX_OPS.md) - General operator operations
- [EX_CHOPS](./EX_CHOPS.md) - CHOP-specific patterns
- [EX_SOPS](./EX_SOPS.md) - SOP-specific patterns
- [CLASSES_/CLASS_Connector](../CLASSES_/CLASS_Connector.md) - Connector class reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Performance Notes:**

- Connection operations should be batched when possible
- Use `setInputs()` for multi-input operators rather than individual connections
- Connection validation can be expensive - use sparingly in real-time applications
- Circular reference checks should be limited to critical paths

---

## File References

**Source Files (14 total):**

- `Node_wiring__Text__test_connections__td.txt` - Basic connection inspection and manipulation
- `Node_wiring__Text__test_multiInputs__td.txt` - Multi-input connection patterns
- `Node_wiring__Text__test_clearInputs__td.txt` - Input clearing operations
- `Node_wiring__Text__test_manyInputs__td.txt` - Large-scale input management
- `Node_wiring__Text__test_pickOutputs__td.py` - Output selection patterns
- `Node_wiring__Text__adat3__td.txt` - Advanced data connection patterns
- `Node_wiring__Text__text4_callbacks__td.py` - Connection callback integration
- `geo2__In__in*__td.dat` - Input data sources (2 files)
- `geo2__Out__out*__td.dat` - Output data destinations (2 files)
- `annotation__*__td.*` - Annotation system (3 files)
- `docsHelper__*__td.*` - Documentation helpers (3 files)
- `open_wiki__*Execute__*__td.py` - Wiki integration (2 files)

**Connection Categories:**

- **Basic Connections**: Single input/output wiring
- **Multi-Input Systems**: Multiple source connection management
- **Connection Analysis**: Inspection and validation tools
- **Batch Operations**: Multiple operator connection management
- **COMP Connections**: Component-specific wiring patterns

---

*This documentation covers TouchDesigner's comprehensive node wiring system for creating and managing complex network connections with Python control.*
