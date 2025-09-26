---
title: "DAT Operations Examples"
category: EXAMPLES
document_type: examples
difficulty: beginner
time_estimate: "30-45 minutes"
user_personas: ["data_artist", "script_developer", "interactive_designer"]
operators: ["tableDAT", "textDAT", "scriptDAT", "constantDAT", "csvDAT", "xmlDAT", "jsonDAT"]
concepts: ["table_manipulation", "cell_access", "data_processing", "csv_operations", "text_processing"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics"]
workflows: ["data_driven_animation", "content_management", "configuration_systems"]
keywords: ["dat", "table", "cell", "data", "csv", "text", "manipulation"]
tags: ["python", "data", "table", "csv", "text", "examples"]
related_docs: ["CLASS_DAT_Class", "CLASS_tableDAT_Class", "EX_EXECUTE_DATS", "PY_TD_Python_Examples_Reference"]
example_count: 46
---

# TouchDesigner Python Examples: DAT Operations (DATs)

## Overview

Comprehensive examples for working with DAT (Data) operators in TouchDesigner. These examples demonstrate table manipulation, cell access, data processing, and common DAT operations.

**Source**: TouchDesigner Help > Python Examples > DATs  
**Example Count**: 46 files  
**Focus**: Data manipulation, table operations, cell access patterns

## Quick Reference

### Core Operations

- **[Table Access](#table-access)** - Reading and writing table data
- **[Cell Manipulation](#cell-manipulation)** - Individual cell operations
- **[Data Processing](#data-processing)** - Data transformation and analysis
- **[Table Management](#table-management)** - Creating, copying, and organizing tables

### Advanced Patterns  

- **[Scripting Integration](#scripting-integration)** - Using DATs in scripts
- **[Performance Tips](#performance-tips)** - Efficient DAT operations
- **[Common Patterns](#common-patterns)** - Frequently used techniques

---

## Table Access

### Basic Table Reading

**Source Files**: `test_table_manipulation.txt`, `test_cell_vs_string.py`

**Key Concepts**: Table object access, row/column indexing, cell referencing

```python
# Access table operator
table = op('table1')
print(f'Table: {table.numRows} rows, {table.numCols} columns')

# Access cells by index
cell = table[1, 3]  # Row 1, Column 3
print(f'Cell value: {cell}')

# Access by row label and column index  
cell = table['row_name', 1]
print(f'Named row access: {cell}')

# Access by column name
cell = table[0, 'column_name']
print(f'Named column access: {cell}')
```

**Use Cases**:

- Reading configuration data from tables
- Processing spreadsheet-like data
- Accessing lookup tables and datasets

### Cell vs String Operations

**Source File**: `test_cell_vs_string.py`

**Key Concepts**: Cell object behavior, string conversion, type handling

```python
table = op('table13')
cell1 = table[0,0]
cell2 = table[2,1]

# Cells act like strings in many contexts
print(cell1)  # Prints cell value
print(cell2 + ' and ' + cell1)  # String concatenation works

# Comparison operations
if cell1 == 'fred':
    print('Cell contains "fred"')

# See actual type with debug()
debug('Cell type info:', cell1)  # Shows Cell object details
print(f'String representation: {repr(cell1)}')
```

**Important Notes**:

- Cells behave like strings in most operations
- Use `debug()` or `repr()` to see actual Cell object
- Automatic string conversion in most contexts

---

## Cell Manipulation

### Writing to Cells

**Source Files**: `test_reset.txt`, `test_clear.txt`

```python
# Write to specific cells
table = op('table1')
table[0, 0] = 'New Value'
table['row1', 'col1'] = 42

# Clear cell contents
table[1, 1] = ''

# Reset entire table
table.clear()

# Add new rows/columns
table.appendRow(['val1', 'val2', 'val3'])
table.appendCol(['col_val1', 'col_val2'])
```

### Finding and Searching Cells

**Source File**: `test_cell_find.py`

```python
# Find cells containing specific values
table = op('data_table')

# Search for text in table
for row in range(table.numRows):
    for col in range(table.numCols):
        cell = table[row, col]
        if 'search_term' in str(cell):
            print(f'Found at row {row}, col {col}: {cell}')

# Find cell by value
def find_cell(table, value):
    for row in range(table.numRows):
        for col in range(table.numCols):
            if str(table[row, col]) == str(value):
                return (row, col)
    return None

position = find_cell(table, 'target_value')
if position:
    print(f'Found value at: {position}')
```

---

## Data Processing

### Numeric Cell Operations

**Source File**: `test_numeric_cells.py`

**Key Concepts**: Number handling, mathematical operations, type conversion

```python
# Working with numeric data
table = op('numeric_table')

# Convert cell to number
cell_value = float(table[0, 1])
result = cell_value * 2

# Write numeric result back
table[0, 2] = result

# Process entire column
for row in range(table.numRows):
    if row == 0: continue  # Skip header
    
    # Get numeric value
    try:
        value = float(table[row, 1])
        # Process and write back
        processed = value * 1.5
        table[row, 2] = processed
    except ValueError:
        table[row, 2] = 'Invalid'
```

### Table Copying and Duplication

**Source File**: `test_table_copy.py`

```python
# Copy table data
source_table = op('source')
dest_table = op('destination')

# Clear destination first
dest_table.clear()

# Copy all data
for row in range(source_table.numRows):
    row_data = []
    for col in range(source_table.numCols):
        row_data.append(source_table[row, col])
    dest_table.appendRow(row_data)

# Alternative: copy specific columns
def copy_columns(source, dest, col_indices):
    dest.clear()
    for row in range(source.numRows):
        row_data = [source[row, col] for col in col_indices]
        dest.appendRow(row_data)

# Copy columns 0, 2, 4 from source to destination
copy_columns(op('source'), op('dest'), [0, 2, 4])
```

---

## Table Management

### Table Sorting

**Source Files**: `test_sort1.txt`, `test_sort_with_header.txt`

```python
# Sort table by column
table = op('sortable_table')

# Simple sort (assumes no header)
def sort_table_by_column(table, col_index, reverse=False):
    # Get all rows as lists
    rows = []
    for row in range(table.numRows):
        row_data = [table[row, col] for col in range(table.numCols)]
        rows.append(row_data)
    
    # Sort by specified column
    rows.sort(key=lambda x: x[col_index], reverse=reverse)
    
    # Clear and rebuild table
    table.clear()
    for row_data in rows:
        table.appendRow(row_data)

# Sort with header preservation
def sort_with_header(table, col_index, reverse=False):
    # Save header row
    header = [table[0, col] for col in range(table.numCols)]
    
    # Get data rows
    data_rows = []
    for row in range(1, table.numRows):  # Skip header
        row_data = [table[row, col] for col in range(table.numCols)]
        data_rows.append(row_data)
    
    # Sort data
    data_rows.sort(key=lambda x: x[col_index], reverse=reverse)
    
    # Rebuild table
    table.clear()
    table.appendRow(header)  # Add header back
    for row_data in data_rows:
        table.appendRow(row_data)

# Usage examples
sort_table_by_column(op('data'), 1)  # Sort by column 1
sort_with_header(op('data_with_header'), 2, reverse=True)  # Reverse sort by column 2
```

### Data Reset and Clearing

**Source Files**: `test_reset.txt`, `test_clear1.txt`, `test_reset_tables.txt`

```python
# Different ways to clear/reset tables
table = op('target_table')

# Method 1: Clear all content
table.clear()

# Method 2: Reset to specific state
def reset_table_with_headers(table, headers):
    table.clear()
    table.appendRow(headers)

# Method 3: Selective clearing
def clear_data_keep_headers(table):
    if table.numRows > 1:
        # Keep first row (header), clear rest
        header = [table[0, col] for col in range(table.numCols)]
        table.clear()
        table.appendRow(header)

# Method 4: Clear specific columns
def clear_columns(table, col_indices):
    for row in range(table.numRows):
        for col in col_indices:
            table[row, col] = ''

# Usage examples
reset_table_with_headers(op('config'), ['Name', 'Value', 'Type'])
clear_data_keep_headers(op('results'))
clear_columns(op('data'), [2, 3, 4])  # Clear columns 2, 3, 4
```

---

## Scripting Integration

### Script DAT Usage

**Source Files**: `script1_script.txt`, `script2_script.txt`

**Key Concepts**: Using DATs in Script operators, data-driven scripting

```python
# Script DAT example - processing data tables
def process_data_table():
    # Get input table
    input_table = op('input_data')
    output_table = op('output_results')
    
    # Clear output
    output_table.clear()
    output_table.appendRow(['Item', 'Processed', 'Status'])
    
    # Process each row
    for row in range(1, input_table.numRows):  # Skip header
        item = input_table[row, 0]
        value = float(input_table[row, 1])
        
        # Process the value
        processed = value * 2.5 if value > 10 else value * 1.5
        status = 'High' if processed > 50 else 'Normal'
        
        # Add to output
        output_table.appendRow([item, processed, status])

# Call processing function
process_data_table()

# Set custom parameters based on table data
config_table = op('config')
for row in range(config_table.numRows):
    param_name = config_table[row, 0]
    param_value = config_table[row, 1]
    
    # Set parameter on parent component
    if hasattr(parent(), param_name):
        setattr(parent(), param_name, param_value)
```

### Data-Driven Operations

**Source Files**: Various test files demonstrating data-driven patterns

```python
# Use table data to control TouchDesigner operations
def control_from_table():
    control_table = op('control_data')
    
    for row in range(1, control_table.numRows):  # Skip header
        op_name = control_table[row, 0]
        param_name = control_table[row, 1] 
        param_value = control_table[row, 2]
        
        # Find the operator
        target_op = op(op_name)
        if target_op:
            # Set parameter
            par = getattr(target_op.par, param_name, None)
            if par:
                par.val = param_value

# Create dynamic UI from table data
def create_ui_from_table():
    ui_table = op('ui_config')
    container = op('dynamic_ui')
    
    # Clear existing UI
    for child in container.children:
        child.destroy()
    
    # Create UI elements from table
    for row in range(1, ui_table.numRows):
        element_type = ui_table[row, 0]  # 'button', 'slider', etc.
        element_name = ui_table[row, 1]
        element_label = ui_table[row, 2]
        
        # Create UI element based on type
        if element_type == 'button':
            btn = container.create(buttonCOMP, element_name)
            btn.par.text = element_label
        elif element_type == 'slider':
            slider = container.create(sliderCOMP, element_name)
            slider.par.label = element_label
```

---

## Performance Tips

### Efficient DAT Operations

**Best Practices**: Based on patterns observed in example files

```python
# Batch operations for better performance
def batch_cell_operations(table):
    # Bad: Individual cell operations
    # for row in range(table.numRows):
    #     for col in range(table.numCols):
    #         table[row, col] = process_value(table[row, col])
    
    # Good: Batch row operations
    for row in range(table.numRows):
        row_data = []
        for col in range(table.numCols):
            original = table[row, col]
            processed = process_value(original)
            row_data.append(processed)
        
        # Replace entire row at once
        table.replaceRow(row, row_data)

# Cache table references
def cache_table_refs():
    # Cache frequently accessed tables
    cached_tables = {
        'config': op('config_table'),
        'data': op('main_data'),
        'results': op('results_table')
    }
    
    # Use cached references
    for row in range(cached_tables['data'].numRows):
        # Process using cached reference
        pass

# Minimize string conversions
def efficient_numeric_processing(table):
    for row in range(table.numRows):
        # Direct numeric conversion when possible
        try:
            value = table[row, 1].val  # Use .val for numeric cells
        except:
            value = float(table[row, 1])  # Fallback to string conversion
        
        # Process numeric value
        result = value * 2
        table[row, 2] = result
```

---

## Common Patterns

### Configuration Table Pattern

```python
# Standard configuration table handling
def load_config():
    config = op('config')
    settings = {}
    
    for row in range(1, config.numRows):  # Skip header
        key = config[row, 0]
        value = config[row, 1]
        value_type = config[row, 2] if config.numCols > 2 else 'string'
        
        # Convert based on type
        if value_type == 'float':
            settings[key] = float(value)
        elif value_type == 'int':
            settings[key] = int(value)
        elif value_type == 'bool':
            settings[key] = str(value).lower() == 'true'
        else:
            settings[key] = str(value)
    
    return settings

# Usage
config = load_config()
opacity = config.get('opacity', 1.0)
enabled = config.get('enabled', True)
```

### Data Validation Pattern

```python
def validate_table_data(table, rules):
    """Validate table data against rules"""
    errors = []
    
    for row in range(1, table.numRows):  # Skip header
        for col, rule in enumerate(rules):
            cell_value = table[row, col]
            
            if rule['required'] and not cell_value:
                errors.append(f'Row {row}, Col {col}: Required field empty')
            
            if rule['type'] == 'number':
                try:
                    float(cell_value)
                except ValueError:
                    errors.append(f'Row {row}, Col {col}: Not a valid number')
            
            if 'range' in rule:
                try:
                    val = float(cell_value)
                    if not (rule['range'][0] <= val <= rule['range'][1]):
                        errors.append(f'Row {row}, Col {col}: Value out of range')
                except:
                    pass
    
    return errors

# Usage
validation_rules = [
    {'required': True, 'type': 'string'},
    {'required': True, 'type': 'number', 'range': [0, 100]},
    {'required': False, 'type': 'string'}
]

errors = validate_table_data(op('input_data'), validation_rules)
if errors:
    print('Validation errors:', errors)
```

---

## Cross-References

### Related Documentation

- **[CLASS_DAT_Class.md](../CLASSES_/CLASS_DAT_Class.md)** - Complete DAT API reference
- **[PY_Working_with_DATs_in_Python.md](../PYTHON_/PY_Working_with_DATs_in_Python.md)** - Conceptual DAT usage guide
- **[TD_/TD_OPERATORS/DAT/](../TD_/TD_OPERATORS/DAT/)** - DAT operator documentation

### Related Examples

- **[EX_EXECUTE_DATS.md](./EX_EXECUTE_DATS.md)** - Execute DAT patterns for monitoring tables
- **[EX_MODULES.md](./EX_MODULES.md)** - Using DATs in module systems
- **[EX_UI.md](./EX_UI.md)** - DAT-driven UI creation

### DAT Operators Commonly Used

- **Table DAT** - Manual table creation and editing
- **File In DAT** - Loading external data files
- **Script DAT** - Python scripting with table integration
- **Evaluate DAT** - Formula-based table processing

---

## File Reference

**Example Files Location**: `TD_PYTHON_Examples/Scripts/DATs/`

**Key Files**:

- `test_table_manipulation.txt` - Basic table operations
- `test_cell_vs_string.py` - Cell object behavior
- `test_numeric_cells.py` - Numeric data handling  
- `test_table_copy.py` - Table copying strategies
- `script1_script.txt` - Script DAT integration
- `test_sort1.txt` - Table sorting methods
- `test_reset.txt` - Table clearing and reset

**Total Examples**: 46 files covering all aspects of DAT manipulation in TouchDesigner.

---

*These examples provide practical, tested code for common DAT operations. Use them as starting points for your own data processing workflows in TouchDesigner.*
