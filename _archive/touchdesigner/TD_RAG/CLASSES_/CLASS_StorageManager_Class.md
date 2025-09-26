---
title: "StorageManager Class"
category: CLASS
document_type: reference
difficulty: advanced
time_estimate: 20-25 minutes
user_personas: ["script_developer", "advanced_user", "component_builder"]
operators: []
concepts: ["storage", "dependency", "data_management", "extensions", "properties"]
prerequisites: ["Python_fundamentals", "component_scripting", "CLASS_Dependency"]
workflows: ["managing_persistent_data", "building_complex_components", "reactive_systems"]
keywords: ["storage", "storagemanager", "dependency", "dependdict", "dependlist", "dependset"]
tags: ["python", "api", "core", "storage", "dependency", "utility"]
related_docs:
- MODULE_TDStoreTools
- CLASS_Dependency
- MODULE_TDFunctions
---

# StorageManager Class

## Content

- [Summary](#summary)
- [Adding StorageManager to an Extension](#adding-storagemanager-to-an-extension)
- [The Stored Items List](#the-stored-items-list)
- [Accessing Stored Items](#accessing-stored-items)
  - [Access via StorageManager Object](#access-via-storagemanager-object)
  - [Access via Properties](#access-via-properties)
- [Limitations to StorageManager](#limitations-to-storagemanager)
- [Constructor](#constructor)
- [Methods](#methods)
- [Members](#members)

## Summary

`StorageManager` is a Python utility class designed to make Storage easy to use in Python Extensions. It also has a number of useful features for creating Python properties and dependable collections. Although `StorageManager` performs some complex Python tasks, using it in your extension is easy, and this article will give you a working knowledge of its use. An intermediate understanding of Python is assumed throughout.

TIP: if you want to use the property and dependability features of `StorageManager`, but don't need the values to be kept in Storage (between saves and extension initializations), consider using the `createProperty` function in [MODULE_TDFunctions].

For technical class details see [MODULE_TDStoreTools]

## Adding StorageManager to an Extension

`StorageManager` is meant for use in Python extensions. The common way to include it in your extension is as follows:

```python
from TDStoreTools import StorageManager

class ExampleExt:
    def __init__(self, ownerComp):
        # The component to which this extension is attached
        self.ownerComp = ownerComp

        storedItems = [
            # Stored Items List goes here
        ]
        self.stored = StorageManager(self, ownerComp, storedItems)
```

Notice that the import statement at the top imports `StorageManager`. Then, in the `__init__` method, a `storedItems` list is created. This list contains dictionaries of information about each item to be stored. We then pass the extension (`self`), the component whose storage will be used (`ownerComp`), and the `storedItems` list to the `StorageManager` class constructor.

## The Stored Items List

The most important thing for you to set up when using `StorageManager` is the stored items list. Each entry in the list contains an item dictionary with information about the item to be stored. There are five keys which can be defined in each item's dictionary:

- `name` - the name of the item to be stored. This is the only required key. If lower case, this stored value's property will not be promoted.
- `default` - the default value of the item to be stored. If not provided, `None` will be used.
- `property` - if True, an associated property will be created to access this value. More on this below. Defaults to `True`.
- `readOnly` - if True, the created property will be a read only value. No effect if property key is false. Defaults to `False`.
- `dependable` - if True, the value will be deeply dependable if it is a container. Non-containers are always dependable and this has no effect. Defaults to `False`.

The items defined in this list will be created in your Component's Storage dictionary, and will thus be saved on disk when your .toe is saved. They will also retain their values when your extension is reinitialized. Let's look at some example item dictionaries before going into further detail about each dictionary attribute:

```python
{'name': 'Value0'}
# A stored value called "Value0". Default values will be used for other
# dictionary keys, so it is exactly equivalent to:
{'name': 'Value0', 'default': None, 'property': True, 'readOnly': False, 'dependable': False}

{'name': 'value0', 'default': 23}
# A stored value much like "Value0" above, but it won't be promoted, and its
# starting value will be 23.

{'name': 'ValueList', 'default': [1, 8, 42], 'dependable': True}
# A stored, deeply dependable list that will start with contents [1, 8, 42]

{'name': 'ID', 'readOnly': True}
# A stored value called "ID" whose promoted property will be read only.

{'name': 'Internal', 'property': False}
# A stored value called "Internal" that will not be accessible via property,
# but only through Component storage or the StorageManager object.
```

## Accessing Stored Items

There are a number of ways to access items stored by `StorageManager`, depending on the way the items are set up in the stored item list. For the following examples, let's say that you have an extension set up like this:

```python
from TDStoreTools import StorageManager

class ExampleExt:
    def __init__(self, ownerComp):
        # The component to which this extension is attached
        self.ownerComp = ownerComp

        storedItems = [
            {'name': 'value0'},
            {'name': 'Value1', 'default':0},
            {'name': 'ID', 'readOnly': True},
            {'name': 'Internal', 'property': False}
        ]
        self.stored = StorageManager(self, ownerComp, storedItems)
```

### Access via StorageManager Object

All stored items are available via the `StorageManager` object itself, which operates like a dictionary keyed by the stored items' names. As an example, here is a function that would work in `ExampleExt` to print and increment `Value1`:

```python
def changeValue(self):
    print(self.stored['Value1'])
    self.stored['Value1'] += 1
```

Stored items can be read and written in this way whether or not they are defined as read only or having a property associated with them.

### Access via Properties

If a stored item has a property associated with it, it can be accessed more directly. A stored item's property will have the same name as the stored item, so, duplicating the example above, `Value1` can also be accessed in this way:

```python
def changeValue(self):
    print(self.Value1)
    self.Value1 += 1
```

If the stored item is set up as read only, it cannot be changed through its property. Looking back to the extension definition above, notice that the `ID` stored value is set to read only. This means that you can do something like

```python
print(self.ID)
```

but

```python
self.ID = 5
```

would cause an error. If you want to change `ID`, you'd do it like this:

```python
self.stored['ID'] = 5
```

If your extension is promoted, any members or methods that start with a capital letter will be accessible directly via the Component they are attached to. This is true of properties as well, so if `ExampleExt` were promoted on a Component in root named "exampleComp", you could do something like this:

```python
op('/exampleComp').Value1 = 12
```

Note: in our example extension, this method of access would not work with `value0` because it is lower case, with `ID` because it is read only, or with `Internal` because it has no property associated with it.

## Limitations to StorageManager

Only objects that can be saved by Python can be stored using `StorageManager`. This includes most built-in Python objects, but does not include many TouchDesigner objects, notably Operators. If you want to store an Operator, the easiest way is to store its path instead. You will get an error if you attempt to store a dis-allowed object.

## Constructor

`class StorageManager(extension, ownerComp, storedItems=None, restoreAllDefaults=False, sync=True, locked=True)` → `StorageManager instance`

Create a new `StorageManager` instance. `StorageManager` will store data in `ownerComp.storage[<extension class name>]`. NOTE: this means that if a Component has two extensions with the same class name, they will share the same storage dictionary!

- `extension` - The extension to associate this `StorageManager` with.
- `ownerComp` - The Component to associate this `StorageManager` with.
- `storedItems` - A list of stored item definition dicts.
- `restoreAllDefaults` - Set all stored items to their defaults.
- `sync` - if True, clear old items that are no longer defined and set to default value if they are new.

## Methods

### restoreAllDefaults()

`restoreAllDefaults()`

> Restore all storage items to their default values as defined during init.

### restoreDefault()

`restoreDefault(storageItem)`

> Restore `storageItem` to its default value as defined during init .
>
> - `storageItem` - name of storage item to restore to default value.

## Members

### extension

> The extension that this `StorageManager` is associated with.

### ownerComp

> The Component that this `StorageManager` is associated with.
