---
title: "Virtual File System"
category: "TD_"
document_type: "guide"
difficulty: "intermediate"
time_estimate: "10 minutes"
user_personas: ["developer", "component_builder", "media_manager"]
completion_signals: ["can_embed_a_file_in_a_tox", "understands_vfs_syntax"]
operators: ["MovieFileInTOP", "AudioFileInCHOP", "CPlusPlusTOP", "CPlusPlusSOP", "CPlusPlusCHOP"]
concepts: ["vfs", "virtual_file_system", "embedding_media", "portability", "privacy"]
prerequisites: []
workflows: ["creating_portable_components", "managing_project_media", "protecting_assets"]
keywords: ["vfs", "virtual", "file", "embed", "tox", "toe", "portable"]
tags: ["core", "concept", "workflow", "file_system", "vfs"]
related_docs:
- "CLASS_VFS_Class"
- "CLASS_VFSFile_Class"
- "TD_Privacy"
---

# Virtual File System

## Content
- [Overview](#overview)
- [Accessing Files](#accessing-files)
- [Details](#details)
- [Usage](#usage)
- [Examples](#examples)
- [Palette Example](#palette-example)

## Overview

TouchDesigner's Virtual File system (VFS) allows image, movie, audio, fonts, other media and any files to be embedded in a `.tox` or `.toe` file. You can open and read them as if they are files in the filesystem. This makes `.tox` and `.toe` files more portable if they depend on images or sounds or font files. It will of course make your `.tox` and `.toe` files larger by whatever the hard drive file size is, but one virtual file can be referred to by multiple OPs at the same time.

The palette component `virtualFile` in the `Tools` section lets you store virtual files without scripting.

## Accessing Files

Internal files can be addressed directly with the `vfs:` prefix. Example: `vfs:/project1:test.jpg`. This VFS address will work in any parameter that is used to point at external files. All Operators that open files, like the `Movie File In TOP` and `Audio File In CHOP` allow the VFS syntax in their file parameters.

## Details

Unlike locking a [TOP] where the image saved in the `.tox`/.`toe` is compressed with LZW, a `Movie File In TOP` that refers to a `.jpeg` file in VFS, it remains fully JPEG compressed. VFS can hold entire movie files and audio files including H.264 and `.mp3` files. It can also hold `.ttf` font files and in some circumstances, `.dll` files for the `CPlusPlus TOP`, `CPlusPlus SOP` and `CPlusPlus CHOP`.

Together with the [TD_Privacy] option (can be set using TouchDesigner Pro only), VFS allows for additional privacy of media built into your TouchDesigner `.tox`/.`toe` files.

## Usage

Two python classes give you full access to VFS functionality.

- [CLASS_VFS_Class] - describes a COMP's virtual file system.
- [CLASS_VFSFile_Class] - describes a virtual file contained within a virtual file system.

## Examples

See the above class wikis for full details.

- **Add a file from disk**
  ```python
  op('/base1').vfs.addFile('Banana.tif')
  ```
- **Add an image from TOP**
  ```python
  op('/base1').vfs.addByteArray(op('someTop').saveByteArray('.jpg'), 'imageName.jpg')
  ```
- **Delete an image**
  ```python
  op('/base1').vfs['Banana.tif'].destroy()
  ```
- **Save virtual file to disk**
  ```python
  op('/base1').vfs['Banana.tif'].export('diskFolderName')
  ```
- **Access virtual file in OP's file parameter (constant mode)**
  ```
  vfs:/base1:Banana.tif
  ```

## Palette Example

Use the `virtualFile` component in the Palette (under `Tools`) as a user interface for VFS. This allows you to use VFS without the scripting that is otherwise required.
