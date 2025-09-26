---
title: "Module Tutorials Examples"
category: EXAMPLES
document_type: tutorial
difficulty: beginner
time_estimate: "45-60 minutes"
user_personas: ["beginner_programmer", "script_developer", "learning_student"]
operators: ["textDAT", "scriptDAT", "tableDAT", "constantCHOP"]
concepts: ["module_creation", "progressive_learning", "function_development", "parameter_integration", "data_processing"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics"]
workflows: ["learning_pathway", "module_development", "progressive_tutorials"]
keywords: ["modules", "tutorials", "functions", "learning", "progressive", "development"]
tags: ["python", "modules", "tutorials", "learning", "progressive", "functions", "examples"]
related_docs: ["EX_MODULES", "MODULE_td", "PY_TD_Python_Examples_Reference", "PY_Extensions"]
example_count: 13
---

# TouchDesigner Python Examples: Module Tutorials Examples

## Quick Reference

TouchDesigner module tutorials provide progressive learning examples for creating and using Python modules. This category covers 13 essential patterns progressing from basic functions to advanced module organization, parameter integration, and data processing workflows.

**Learning Progression:**

- **Simple Functions** - Basic return values
- **TouchDesigner Integration** - Operator and channel access
- **Parameter Functions** - Parameterized operations
- **Data Processing** - Table and field operations
- **Advanced Modules** - Complex module structures

**Core Concepts:**

- Function definition and return values
- TouchDesigner operator integration
- Parameter passing and processing
- Data table operations
- Module organization patterns

---

## Basic Module Functions

### Simple Return Values

```python
# Module Tutorial 1: Basic function with return value
def simple():
    """Basic function returning a constant value"""
    a = 100
    return a

# Usage in TouchDesigner expressions
# In a parameter field: `mod('simpleMod1').simple()`
# Returns: 100
```

### Parameter Processing Functions

```python
# Module Tutorial 10: Function with parameters
def simple(val):
    """Process input value with scaling"""
    a = 10 * val
    return a

# Usage in TouchDesigner expressions  
# In a parameter field: `mod('simpleMod10').simple(0.5)`
# Returns: 5.0

# Can be used with dynamic values
# In a parameter field: `mod('simpleMod10').simple(absTime.seconds)`
# Returns: Current time * 10
```

---

## TouchDesigner Integration

### Operator Access in Modules

```python
# Module Tutorial 5: Accessing TouchDesigner operators
def simple():
    """Get value from TouchDesigner CHOP channel"""
    # Access CHOP operator and specific channel
    val = op('lfo1')['chan1']
    
    # Process the value
    a = 10 * val
    
    return a

# This pattern allows modules to:
# - Read from CHOP channels
# - Access operator data
# - Process TouchDesigner values
# - Return computed results
```

### Advanced Operator Integration

```python
# Enhanced operator access patterns
def getChannelValue(op_name, channel_name='chan1'):
    """Get channel value with error handling"""
    try:
        chop_op = op(op_name)
        if chop_op and len(chop_op.chans) > 0:
            if channel_name in chop_op.chans:
                return chop_op[channel_name].eval()
            else:
                # Return first channel if named channel not found
                return chop_op[0].eval()
        else:
            return 0.0
    except:
        return 0.0

def processOperatorData(op_name, multiplier=10):
    """Process data from any operator"""
    try:
        source_op = op(op_name)
        
        if source_op.family == 'CHOP':
            # Get first channel value
            val = source_op[0].eval() if len(source_op.chans) > 0 else 0
        elif source_op.family == 'DAT':
            # Get first cell value
            val = float(source_op[0, 0]) if source_op.numRows > 0 else 0
        elif source_op.family == 'TOP':
            # Get pixel value (simplified)
            val = source_op.width / 100.0  # Use width as example value
        else:
            val = 1.0  # Default value
            
        return val * multiplier
        
    except:
        return 0.0

# Usage examples:
# mod('advanced_module').getChannelValue('lfo1', 'speed')
# mod('advanced_module').processOperatorData('noise1', 5)
```

---

## Data Table Integration

### Table Data Processing

```python
# Module for table data operations
def processTableData(table_name):
    """Process data from a table DAT"""
    try:
        table_op = op(table_name)
        
        if not table_op or table_op.family != 'DAT':
            return []
        
        # Process all rows
        processed_data = []
        for row in range(table_op.numRows):
            row_data = []
            for col in range(table_op.numCols):
                cell_value = table_op[row, col]
                try:
                    # Try to convert to number
                    numeric_value = float(cell_value)
                    row_data.append(numeric_value)
                except:
                    # Keep as string if not numeric
                    row_data.append(str(cell_value))
            processed_data.append(row_data)
        
        return processed_data
        
    except Exception as e:
        print(f"Error processing table {table_name}: {e}")
        return []

def calculateTableStats(table_name):
    """Calculate statistics from numeric table data"""
    try:
        data = processTableData(table_name)
        
        numeric_values = []
        for row in data:
            for cell in row:
                if isinstance(cell, (int, float)):
                    numeric_values.append(cell)
        
        if not numeric_values:
            return {'count': 0, 'sum': 0, 'avg': 0, 'min': 0, 'max': 0}
        
        return {
            'count': len(numeric_values),
            'sum': sum(numeric_values),
            'avg': sum(numeric_values) / len(numeric_values),
            'min': min(numeric_values),
            'max': max(numeric_values)
        }
        
    except:
        return {'count': 0, 'sum': 0, 'avg': 0, 'min': 0, 'max': 0}

# Usage:
# mod('table_module').calculateTableStats('table1')
```

---

## Progressive Module Development

### Module Tutorial Progression

```python
# Following the tutorial progression from simpleMod1 to simpleMod10

# Tutorial 1: Basic constant
def tutorial1_basic():
    return 100

# Tutorial 2: Simple calculation
def tutorial2_calc():
    a = 50
    b = 25
    return a + b

# Tutorial 3: Using variables
def tutorial3_vars():
    base_value = 10
    multiplier = 5
    result = base_value * multiplier
    return result

# Tutorial 4: Conditional logic
def tutorial4_condition():
    current_frame = absTime.frame
    if current_frame % 60 == 0:
        return 1
    else:
        return 0

# Tutorial 5: Operator integration (as shown above)
def tutorial5_operator():
    val = op('lfo1')['chan1']
    return 10 * val

# Tutorial 6: Multiple operator access
def tutorial6_multi_ops():
    lfo_val = op('lfo1')['chan1'] if op('lfo1') else 0
    noise_val = op('noise1')['chan1'] if op('noise1') else 0
    return (lfo_val + noise_val) / 2

# Tutorial 7: Parameter-based processing
def tutorial7_params():
    # Get parameter from owner component
    try:
        owner_comp = me.parent()
        scale_param = owner_comp.par.scale.eval()
        return scale_param * 10
    except:
        return 10

# Tutorial 8: Time-based functions
def tutorial8_time():
    import math
    seconds = absTime.seconds
    return math.sin(seconds) * 100

# Tutorial 9: Complex data processing
def tutorial9_complex():
    frame = absTime.frame
    seconds = absTime.seconds
    
    # Combine frame and time data
    wave = math.sin(seconds * 2) * 50
    pulse = 1 if frame % 30 == 0 else 0
    
    return wave + (pulse * 20)

# Tutorial 10: Parameterized function (as shown above)
def tutorial10_params(val):
    return 10 * val
```

---

## Advanced Module Patterns

### Module Class Structure

```python
# Advanced module organization using classes
class TouchDesignerModule:
    """Professional TouchDesigner module structure"""
    
    def __init__(self):
        self.cache = {}
        self.last_frame = -1
    
    def simple(self, val=1.0):
        """Basic parameterized function"""
        return 10 * val
    
    def cached_operation(self, op_name):
        """Cached operator access for performance"""
        current_frame = absTime.frame
        
        # Check cache validity
        cache_key = f"{op_name}_{current_frame}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Clear old cache entries
        if current_frame != self.last_frame:
            self.cache.clear()
            self.last_frame = current_frame
        
        # Compute value
        try:
            result = op(op_name)[0].eval() if op(op_name) else 0
            self.cache[cache_key] = result
            return result
        except:
            return 0
    
    def multi_input_processor(self, *op_names):
        """Process multiple operators"""
        values = []
        for op_name in op_names:
            val = self.cached_operation(op_name)
            values.append(val)
        
        if not values:
            return 0
        
        return sum(values) / len(values)
    
    def parameter_mapper(self, input_val, input_range=(0, 1), output_range=(0, 100)):
        """Map input value from one range to another"""
        input_min, input_max = input_range
        output_min, output_max = output_range
        
        # Normalize input
        if input_max != input_min:
            normalized = (input_val - input_min) / (input_max - input_min)
        else:
            normalized = 0
        
        # Apply to output range
        return output_min + normalized * (output_max - output_min)

# Create global instance for module access
td_module = TouchDesignerModule()

# Provide simple access functions
def simple(val=1.0):
    return td_module.simple(val)

def cached_op(op_name):
    return td_module.cached_operation(op_name)

def multi_process(*op_names):
    return td_module.multi_input_processor(*op_names)

def map_value(val, in_range=(0, 1), out_range=(0, 100)):
    return td_module.parameter_mapper(val, in_range, out_range)
```

---

## Module Usage Patterns

### In Parameter Expressions

```python
# Direct function calls in parameter expressions
# Parameter field: mod('simpleMod1').simple()
# Parameter field: mod('simpleMod5').simple()
# Parameter field: mod('simpleMod10').simple(0.5)

# With TouchDesigner values
# Parameter field: mod('module').simple(absTime.seconds)
# Parameter field: mod('module').map_value(op('lfo1')[0], (0,1), (0,360))
```

### In Evaluate DATs

```python
# More complex module usage in Evaluate DAT
import importlib

# Reload module if needed during development
try:
    importlib.reload(mod('my_module'))
except:
    pass

# Use module functions
result1 = mod('my_module').simple()
result2 = mod('my_module').cached_op('lfo1')
result3 = mod('my_module').multi_process('lfo1', 'noise1', 'pattern1')

# Output results
print(f"Results: {result1}, {result2}, {result3}")

# Set parameter based on module result
op('transform1').par.rx = mod('my_module').map_value(
    mod('my_module').simple(), 
    (0, 100), 
    (0, 360)
)
```

### Module Testing and Debugging

```python
# Testing module functions
def test_module_functions():
    """Test all module functions"""
    test_results = {}
    
    # Test basic function
    try:
        result = mod('simpleMod1').simple()
        test_results['simple'] = {'success': True, 'result': result}
    except Exception as e:
        test_results['simple'] = {'success': False, 'error': str(e)}
    
    # Test parameterized function
    try:
        result = mod('simpleMod10').simple(2.5)
        test_results['simple_param'] = {'success': True, 'result': result}
    except Exception as e:
        test_results['simple_param'] = {'success': False, 'error': str(e)}
    
    # Test operator integration
    try:
        result = mod('simpleMod5').simple()
        test_results['operator_integration'] = {'success': True, 'result': result}
    except Exception as e:
        test_results['operator_integration'] = {'success': False, 'error': str(e)}
    
    return test_results

# Debug module performance
def benchmark_module(module_name, function_name, iterations=100):
    """Benchmark module function performance"""
    import time
    
    start_time = time.time()
    
    for i in range(iterations):
        try:
            result = getattr(mod(module_name), function_name)()
        except:
            pass
    
    end_time = time.time()
    avg_time = (end_time - start_time) / iterations
    
    print(f"Module {module_name}.{function_name}: {avg_time:.6f}s per call")
    
    return avg_time
```

---

## Cross-References

**Related Documentation:**

- [EX_MODULES](./EX_MODULES.md) - Module system fundamentals  
- [EX_DATS](./EX_DATS.md) - Data processing patterns
- [EX_EXECUTE_DATS](./EX_EXECUTE_DATS.md) - Evaluate DAT integration
- [CLASSES_/CLASS_mod](../CLASSES_/CLASS_mod.md) - Module system reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Learning Path:**

- Start with simple return functions (simpleMod1)
- Progress to operator integration (simpleMod5)  
- Advance to parameterized functions (simpleMod10)
- Build complex processing modules
- Implement caching and performance optimization

---

## File References

**Source Files (13 total):**

- `Module_tutorials__Text__simpleMod1__td.py` - Basic function with return value
- `Module_tutorials__Text__simpleMod2__td.py` - Simple calculations
- `Module_tutorials__Text__simpleMod3__td.py` - Variable usage patterns
- `Module_tutorials__Text__simpleMod4__td.py` - Conditional logic
- `Module_tutorials__Text__simpleMod5__td.py` - TouchDesigner operator integration
- `Module_tutorials__Text__simpleMod6__td.py` - Multiple operator access
- `Module_tutorials__Text__simpleMod7__td.py` - Parameter-based processing
- `Module_tutorials__Text__simpleMod8__td.py` - Time-based functions
- `Module_tutorials__Text__simpleMod9__td.py` - Complex data processing
- `Module_tutorials__Text__simpleMod10__td.py` - Parameterized functions
- `Module_tutorials__Text__text4_callbacks__td.py` - Callback integration
- `Module_tutorials__Table__table1__td.tsv` - Tutorial data table
- `Module_tutorials__Table__table2__td.tsv` - Additional data table

**Tutorial Categories:**

- **Basic Functions**: Return values and simple operations
- **TouchDesigner Integration**: Operator and channel access
- **Parameter Processing**: Input validation and transformation
- **Advanced Patterns**: Caching, classes, and performance optimization
- **Testing and Debugging**: Module validation and benchmarking

---

*This documentation covers TouchDesigner's module tutorial progression, providing a structured learning path from basic functions to advanced module development with TouchDesigner integration.*
