---
title: "TDStoreTools"
category: MODULE
document_type: reference
difficulty: advanced
time_estimate: 25-30 minutes
user_personas: ["script_developer", "advanced_user", "component_builder"]
operators: []
concepts: ["storage", "dependency", "data_management", "extensions"]
prerequisites: ["Python_fundamentals", "component_scripting", "CLASS_Dependency"]
workflows: ["managing_persistent_data", "building_complex_components", "reactive_systems"]
keywords: ["storage", "storagemanager", "dependency", "dependdict", "dependlist", "dependset"]
tags: ["python", "api", "core", "storage", "dependency", "utility"]
related_docs:
- CLASS_Dependency
- CLASS_StorageManager
---

# TDStoreTools

## Content

- [Summary](#summary)
- [StorageManager Class](#storagemanager-class)
  - [Constructor](#constructor)
  - [Methods](#methods)
  - [Members](#members)
- [Deeply Dependable Collections](#deeply-dependable-collections)
  - [DependMixin Class](#dependmixin-class)
    - [Members](#members-1)
  - [DependDict Class](#dependdict-class)
    - [Methods](#methods-1)
  - [DependList Class](#dependlist-class)
    - [Methods](#methods-2)
  - [DependSet Class](#dependset-class)
    - [Methods](#methods-3)

## Summary

The `TDStoreTools` module provides the important `StorageManager` utility class for use with TouchDesigner's Storage system. It also holds the deeply dependable collections `DependDict`, `DependList`, and `DependSet`.

To use `TDStoreTools` put the following line at the top of your Python script:

```python
import TDStoreTools
```

or more commonly, if you are just going to use `StorageManager`, use this at the top of your script:

```python
from TDStoreTools import StorageManager
```

## StorageManager Class

For a primer on `StorageManager` usage, see: `StorageManager Class`

`StorageManager` is a Python utility class designed to make Storage easy to use in Python Extensions. It also has a number of useful features for creating Python properties and dependable collections.

`StorageManager` is derived from the Python `MutableMapping` class in the `collections` container. This means it operates very much like a Python dictionary, and items can be accessed using the `data = storageManager[<key>]` format.

### Constructor

`class StorageManager(extension, ownerComp, storedItems=None, restoreAllDefaults=False, sync=True, locked=True)` → `StorageManager instance`

Create a new `StorageManager` instance. `StorageManager` will store data in `ownerComp.storage[<extension class name>]`. NOTE: this means that if a Component has two extensions with the same class name, they will share the same storage dictionary!

- `extension` - The extension to associate this `StorageManager` with.
- `ownerComp` - The Component to associate this `StorageManager` with.
- `storedItems` - A list of stored item definition dicts.
- `restoreAllDefaults` - Set all stored items to their defaults.
- `sync` - if True, clear old items that are no longer defined and set to default value if they are new.

### Methods

#### restoreAllDefaults()

`restoreAllDefaults()`

> Restore all storage items to their default values as defined during init.

#### restoreDefault()

`restoreDefault(storageItem)`

> Restore `storageItem` to its default value as defined during init .
>
> - `storageItem` - name of storage item to restore to default value.

### Members

#### extension

> The extension that this `StorageManager` is associated with.

#### ownerComp

> The Component that this `StorageManager` is associated with.

## Deeply Dependable Collections

Often when working with Python extensions, you will want to store your data in `Dependency` objects so that expressions referencing the data will update when the data changes. This becomes trickier with Python collections (list, dict, set) because they are mutable objects.

When the contents of a collection changes, it doesn't change the object itself. This means that even if the collection is wrapped in a dependency object, changing the contents of the collection will not cause expressions referencing it to update. This is where deeply dependable collections come in. These special collections will cause updates even when only their contents change. In addition, they work recursively, so collections created within them will also be deeply dependable.

Accessing deeply dependable collections works just like accessing their standard Python counterparts, and returned values will have all dependency wrappers stripped away so they can be used normally. They also have all the usual methods and members of their core Python counterparts. The functions and members in the sections below are in addition to those available in the standard Python objects.

Note: Deeply dependable collections will operate a bit more slowly than their non-dependable counter-parts. Gotcha: Note that deeply dependable collections may have problems if a single deeply dependable collection exists in multiple other deeply dependable collections. This will rarely be necessary, but might come into play in very complex data.

### DependMixin Class

All dependable collections are derived from the `DependMixin` class, and thus share these common features:

#### Members

##### myMainDep

> The main dependency wrapper around the collection.

##### parentDep

> If dependable collection is inside another dependable collection, this contains its parent dependable collection. Otherwise `None`.

### DependDict Class

`DependDict` is a deeply dependable version of the python `dict` class.

#### Methods

##### getRaw()

`getRaw(self, key=None)`

> get entire `DependDict` or a value from the `DependDict` with all dependencies removed.
>
> - `key` - the key of the value to return. If `None`, return entire dictionary.

##### getDependency()

`getDependency(self, key)`

> get a value from the `DependDict` with dependencies intact.
>
> - `key` - the key of the value to return.

##### setItem()

`setItem(key, item, raw=False)`

> set an item in the dictionary.
>
> - `key` - the key whose value will be set to item
> - `item` - the item
> - `raw` - if True, and item is a collection, the collection will not be made into a deeply dependable collection.

### DependList Class

`DependList` is a deeply dependable version of the python `list` class.

#### Methods

##### getRaw()

`getRaw(self, index=None)`

> get entire `DependList` or a value from the `DependList` with all dependencies removed.
>
> - `index` - the index of the value to return. If `None`, return entire list.

##### getDependency()

`getDependency(self, index)`

> get a value from the `DependList` with dependencies intact.
>
> - `index` - the index of the value to return.

##### setItem()

`setItem(index, item, raw=False)`

> set an item in the list.
>
> - `index` - the index of the item to be set
> - `item` - the item
> - `raw` - if True, and item is a collection, the collection will not be made into a deeply dependable collection.

##### append()

`append(item, raw=False)`

> add an item to end of list.
>
> - `item` - the new item
> - `raw` - if True, and item is a collection, the collection will not be made into a deeply dependable collection.

##### insert()

`insert(index, item, raw=False)`

> insert an item into the list.
>
> - `index` - the index where the new item will be inserted
> - `item` - the new item
> - `raw` - if True, and item is a collection, the collection will not be made into a deeply dependable collection.

### DependSet Class

`DependSet` is a deeply dependable version of the python `set` class.

#### Methods

##### getRaw()

`getRaw(self)`

> get entire `DependSet` with all dependencies removed.
