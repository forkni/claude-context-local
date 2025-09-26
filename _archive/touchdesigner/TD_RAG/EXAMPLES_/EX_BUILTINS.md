---
title: "TouchDesigner Built-in Objects Examples"
category: EXAMPLES
document_type: examples
difficulty: beginner
time_estimate: "15-25 minutes"
user_personas: ["script_developer", "beginner_programmer", "technical_artist"]
operators: ["scriptDAT", "executeDAT", "textDAT"]
concepts: ["builtin_objects", "global_access", "time_system", "project_info", "utilities", "system_monitoring"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics"]
workflows: ["scripting_fundamentals", "system_integration", "debugging"]
keywords: ["builtins", "absTime", "root", "me", "tdu", "project", "ui", "monitors", "licenses"]
tags: ["python", "builtins", "fundamentals", "time", "system", "utilities", "examples"]
related_docs: ["CLASS_AbsTime_Class", "CLASS_Project_Class", "CLASS_App_Class", "PY_TD_Python_Examples_Reference"]
example_count: 19
---

# TouchDesigner Python Examples: Built-in Objects

## Quick Reference

TouchDesigner provides essential built-in Python objects accessible globally without imports. This category covers 19 core patterns for accessing time, project info, utilities, licensing, system monitoring, and documentation helpers.

**Key Built-in Objects:**

- `absTime` - Global timeline access
- `root` - Project root and timing
- `me` - Current component reference
- `tdu` - TouchDesigner utilities
- `licenses` - License information
- `monitors` - System monitoring
- `project` - Project-level operations
- `ui` - User interface utilities

**Core Patterns:**

- Time and frame access
- System information queries
- Utility functions (file types, name validation)
- License and monitoring data
- Documentation helper integration

---

## Time and Frame Access

### Global Time Objects

```python
# Global timeline (always use for absolute time)
print(f"Global frame: {absTime.frame}")
print(f"Global seconds: {absTime.seconds}")
print(f"Project rate: {root.time.rate}")

# Component-local time (can differ from global)
print(f"Local frame: {me.time.frame}")
print(f"Local seconds: {me.time.seconds}")
```

**Best Practice**: Always use `absTime` for absolute timeline references, `me.time` only for component-specific timing.

### Frame Rate and Project Info

```python
# Project timing information
frame_rate = root.time.rate
current_frame = absTime.frame
elapsed_seconds = absTime.seconds

# Frame-based calculations
frames_per_second = frame_rate
time_at_frame = current_frame / frame_rate
```

---

## TouchDesigner Utilities (tdu)

### File Type Management

```python
# Get supported file types
print("All file types:", tdu.fileTypes.keys())
print("Movie formats:", tdu.fileTypes['movie'])
print("Image formats:", tdu.fileTypes['image'])
print("Audio formats:", tdu.fileTypes['audio'])

# File extension validation
if 'mov' in tdu.fileTypes['movie']:
    print("MOV files supported")
```

### Name Validation and Legalization

```python
# Clean operator names for TD compatibility
raw_name = "My Component #1 (v2.0)"
clean_name = tdu.validName(raw_name)
print(f"Legalized name: {clean_name}")  # Returns: My_Component_1_v2_0

# Use for dynamic operator creation
op_name = tdu.validName(user_input)
new_op = parent().create(baseOP, op_name)
```

### Digit and Number Utilities

```python
# Number formatting and validation
test_number = 12345.6789
formatted = tdu.digits(test_number, 3)  # 3 decimal places
print(f"Formatted: {formatted}")

# Numeric string validation
if tdu.isValidNumber("123.45"):
    value = float("123.45")
```

---

## System Monitoring and Information

### License Information

```python
# Check TouchDesigner license type
license_type = licenses.current
print(f"License: {license_type}")

# License capabilities
print("Available licenses:")
for lic in licenses.all:
    print(f"  {lic.name}: {lic.features}")

# Feature availability check
if licenses.current.canSave:
    # Save operations allowed
    project.save()
```

### Monitor System Information

```python
# System monitors access
monitor_count = len(monitors)
print(f"Connected monitors: {monitor_count}")

# Monitor details
for i, monitor in enumerate(monitors):
    print(f"Monitor {i}:")
    print(f"  Resolution: {monitor.width}x{monitor.height}")
    print(f"  Position: ({monitor.x}, {monitor.y})")
    print(f"  Primary: {monitor.isPrimary}")
```

### Performance Monitoring Callbacks

```python
# Monitor system callbacks (monitors1_callbacks)
def onMonitorChange():
    """Called when monitor configuration changes"""
    print(f"Monitor setup changed: {len(monitors)} monitors")
    
    # Update UI layouts for new monitor config
    for window in ui.windows:
        window.refresh()

def onSystemChange():
    """System-level change notification"""
    # Refresh system-dependent settings
    op('system_info').par.refresh.pulse()
```

---

## Documentation Helper System

### DocsHelper Integration

```python
# Access TouchDesigner documentation system
DocsHelper = op.TDResources.mod.DocsHelper.DocsHelper

# Open operator documentation
def openOpDocs(op_name):
    """Open TouchDesigner docs for specific operator"""
    DocsHelper.openOperatorHelp(op_name)

# Open wiki pages
def openWikiPage(page_name):
    """Open TouchDesigner wiki page"""
    DocsHelper.openWiki(page_name)
```

### Parameter Execute Integration

```python
# Documentation button callbacks (parexec patterns)
def onValueChange(par, prev):
    """Parameter execute for docs buttons"""
    if par.name == 'Helppulse':
        # Open help for current operator
        owner_op = par.owner
        DocsHelper.openOperatorHelp(owner_op.type)
    
    elif par.name == 'Wikipulse':
        # Open wiki page
        DocsHelper.openWiki('Main_Page')

def onPulse(par):
    """Pulse parameter for instant actions"""
    if par.name == 'Opendocs':
        # Open documentation with current context
        current_op = me.parent()
        DocsHelper.openOperatorHelp(current_op.type)
```

### Panel Execute Integration

```python
# Panel-based documentation access (panelexec patterns)
def onValueChange(panelValue, prev):
    """Panel execute for documentation UI"""
    if panelValue.name == 'Docbutton':
        # Documentation button pressed
        target_op = parent().par.Targetop.eval()
        if target_op:
            DocsHelper.openOperatorHelp(target_op.type)
    
    elif panelValue.name == 'Wikibutton':
        # Wiki button pressed
        wiki_page = parent().par.Wikipage.eval()
        DocsHelper.openWiki(wiki_page)
```

---

## Advanced Patterns

### System State Monitoring

```python
def monitorSystemHealth():
    """Comprehensive system monitoring"""
    health_report = {
        'timeline': {
            'frame': absTime.frame,
            'seconds': absTime.seconds,
            'rate': root.time.rate
        },
        'license': {
            'type': licenses.current.name,
            'can_save': licenses.current.canSave,
            'features': list(licenses.current.features)
        },
        'monitors': [
            {
                'id': i,
                'resolution': f"{m.width}x{m.height}",
                'primary': m.isPrimary
            }
            for i, m in enumerate(monitors)
        ]
    }
    return health_report
```

### Context-Aware Documentation

```python
class ContextualDocsHelper:
    """Enhanced documentation with context awareness"""
    
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.docs_helper = op.TDResources.mod.DocsHelper.DocsHelper
    
    def openRelevantDocs(self, target_op=None):
        """Open documentation based on context"""
        if not target_op:
            target_op = self.ownerComp
        
        # Open operator-specific documentation
        self.docs_helper.openOperatorHelp(target_op.type)
        
        # Log documentation access
        print(f"Opened docs for {target_op.type} at frame {absTime.frame}")
    
    def openContextualWiki(self, context=""):
        """Open wiki with contextual page selection"""
        if context == "networking":
            self.docs_helper.openWiki("Networking")
        elif context == "python":
            self.docs_helper.openWiki("Python")
        else:
            self.docs_helper.openWiki("Main_Page")
```

### Utility Function Library

```python
def createUtilityFunctions():
    """Collection of utility functions using TD built-ins"""
    
    def safeOpName(name):
        """Create safe operator name with validation"""
        safe_name = tdu.validName(name)
        if not safe_name:
            safe_name = f"op_{absTime.frame}"
        return safe_name
    
    def timeStampedName(base_name):
        """Create timestamped name"""
        frame_str = str(absTime.frame).zfill(6)
        return f"{tdu.validName(base_name)}_{frame_str}"
    
    def systemCapabilities():
        """Query system capabilities"""
        return {
            'can_save': licenses.current.canSave,
            'monitor_count': len(monitors),
            'file_types': list(tdu.fileTypes.keys()),
            'current_frame': absTime.frame,
            'frame_rate': root.time.rate
        }
    
    return {
        'safeOpName': safeOpName,
        'timeStampedName': timeStampedName,
        'systemCapabilities': systemCapabilities
    }
```

---

## Cross-References

**Related Documentation:**

- [EX_EXTENSIONS](./EX_EXTENSIONS.md) - Extension development patterns
- [EX_EXECUTE_DATS](./EX_EXECUTE_DATS.md) - Execute DAT integration
- [EX_UI](./EX_UI.md) - User interface patterns
- [CLASSES_/CLASS_tdu](../CLASSES_/CLASS_tdu.md) - TouchDesigner utilities reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Performance Notes:**

- Built-in objects are optimized for frequent access
- `absTime` queries are lightweight and suitable for every frame
- License queries should be cached for performance-critical code
- Monitor queries are best cached and updated on system changes

---

## File References

**Source Files (19 total):**

- `Builtins__Text__test_time__td.txt` - Time and frame access patterns
- `Builtins__Text__test_misc__td.txt` - tdu utilities and file types
- `Builtins__Text__test_licences__td.txt` - License information access
- `Builtins__Text__test_monitors__td.txt` - Monitor system queries
- `Builtins__Text__test_tdu_contents__td.py` - tdu module contents
- `docsHelper__Text__DocsHelper__td.py` - Documentation helper integration
- `open_wiki*__ParExecute__parexec1__td.py` - Parameter execute for documentation (6 files)
- `open_wiki*__PanelExecute__panelexec1__td.py` - Panel execute for documentation (6 files)
- `annotation__*__td.*` - Annotation system integration (3 files)

**Pattern Categories:**

- **Time Access**: Global and local timeline patterns
- **System Info**: License, monitor, and capability queries  
- **Utilities**: File types, name validation, formatting
- **Documentation**: Wiki and help system integration
- **Monitoring**: System change detection and callbacks

---

*This documentation covers essential TouchDesigner built-in objects providing system access, utilities, and documentation integration. These patterns form the foundation for all TouchDesigner Python development.*
