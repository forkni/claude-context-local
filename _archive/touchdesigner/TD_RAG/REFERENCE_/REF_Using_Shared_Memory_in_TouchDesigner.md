---
category: HARDWARE
document_type: guide
difficulty: beginner
time_estimate: 15-25 minutes
operators:
- SharedMem_In_TOP
- SharedMem_Out_TOP
- SharedMem_In_CHOP
- SharedMem_Out_CHOP
concepts:
- shared_memory
- inter-process_communication
- c++_integration
- memory_locking
- mutex
- data_synchronization
prerequisites:
- c++_programming
- memory_management_concepts
- touchdesigner_pro_license
workflows:
- external_application_integration
- high_speed_data_transfer
- custom_c++_application_development
keywords:
- shared memory
- ipc
- c++
- UT_SharedMem
- UT_Mutex
- external application
- data exchange
- lock
- mutex
- unicode
- LPCWSTR
tags:
- c++
- ipc
- windows
- pro_license
- commercial_license
- sdk
relationships:
  REF_WriteSharedMemoryTOP: strong
  REF_WriteSharedMemoryCHOP: strong
  SharedMem_In_TOP: strong
  SharedMem_Out_TOP: strong
  SharedMem_In_CHOP: strong
  SharedMem_Out_CHOP: strong
related_docs:
- REF_WriteSharedMemoryTOP
- REF_WriteSharedMemoryCHOP
hierarchy:
  secondary: ipc",
  tertiary: shared_memory_cpp
question_patterns:
- Hardware setup guide?
- Multi-monitor configuration?
- Installation requirements?
- Hardware compatibility?
common_use_cases:
- external_application_integration
- high_speed_data_transfer
- custom_c++_application_development
---

# Using Shared Memory in TouchDesigner

<!-- TD-META
category: HARDWARE
document_type: guide
operators: [SharedMem_In_TOP, SharedMem_Out_TOP, SharedMem_In_CHOP, SharedMem_Out_CHOP]
concepts: [shared_memory, inter-process_communication, c++_integration, memory_locking, mutex, data_synchronization]
prerequisites: [c++_programming, memory_management_concepts, touchdesigner_pro_license]
workflows: [external_application_integration, high_speed_data_transfer, custom_c++_application_development]
related: [REF_WriteSharedMemoryTOP, REF_WriteSharedMemoryCHOP]
relationships: {
  "REF_WriteSharedMemoryTOP": "strong",
  "REF_WriteSharedMemoryCHOP": "strong",
  "SharedMem_In_TOP": "strong",
  "SharedMem_Out_TOP": "strong",
  "SharedMem_In_CHOP": "strong",
  "SharedMem_Out_CHOP": "strong"
}
hierarchy:
  "primary": "interop",
  "secondary": "ipc",
  "tertiary": "shared_memory_cpp"
keywords: [shared memory, ipc, c++, UT_SharedMem, UT_Mutex, external application, data exchange, lock, mutex, unicode, LPCWSTR]
tags: [c++, ipc, windows, pro_license, commercial_license, sdk]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Hardware setup guide for TouchDesigner installations
**Difficulty**: Beginner
**Time to read**: 15-25 minutes
**Use for**: external_application_integration, high_speed_data_transfer, custom_c++_application_development

**Common Questions Answered**:

- "Hardware setup guide?" → [See relevant section]
- "Multi-monitor configuration?" → [See relevant section]
- "Installation requirements?" → [See relevant section]
- "Hardware compatibility?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [C++ Programming] → [Memory Management Concepts] → [Touchdesigner Pro License]
**This document**: HARDWARE reference/guide
**Next steps**: [REF WriteSharedMemoryTOP] → [REF WriteSharedMemoryCHOP]

**Related Topics**: external application integration, high speed data transfer, custom c++ application development

## Summary

Guide for using shared memory in TouchDesigner, covering the basics of creating and managing shared memory segments for inter-process communication.

## Relationship Justification

Strong connection to shared memory as the primary topic. Links to related articles for specific OPs that utilize shared memory.

## Content

- [Overview](#overview)
- [Source Files](#source-files)
  - [UT_SharedMem](#ut_sharedmem)
  - [UT_Mutex](#ut_mutex)
- [Compile Issues and Considerations](#compile-issues-and-considerations)
  - [Unicode](#unicode)
- [Related Articles](#related-articles)

## Overview

Various OPs in TouchDesigner are able to send and receive data via shared memory, which is a fast way to send data between two different processes. This guide will help you make your own app that can send or receive data from TouchDesigner. This guide gives the basics on how to setup and use shared memory. More specific articles for each OP type will tell you how to write/read from this shared memory so that the processes can talk to each other correctly.

**NOTE:** You need to have TouchDesigner Commercial or Pro to have access to the Shared Memory nodes.

## Source Files

C++ source code is supplied to make this task much easier. You can get the source files from `Samples/SharedMem` in your TouchDesigner Install directory.

### UT_SharedMem

This class does everything that needs to be done to manage shared memory. If you are the sender you need to create the shared memory by also specifying the size of the shared memory. This size needs to be big enough to hold all of the data you need to write. The amount of data depends on the type of OP you are working with. Refer to that OP's article for more information. If you are the receiver, you only specify the name of the shared memory. This name matches the name that you give the parameter in the shared memory OP.

Create a shared memory to send data like this:

```cpp
UT_SharedMem *shm = new UT_SharedMem(ShmString(L"mymemoryname"), myRequiredSize); // figure out the size based on the OP
```

or for the receiver:

```cpp
UT_SharedMem *shm = new UT_SharedMem(ShmString(L"mymemoryname"));
```

Check the state of the shared memory using:

```cpp
UT_SharedMemError err = shm->getErrorState();
if (err != UT_SHM_ERR_NONE)
{ 
   // an error occured 
}
```

Before you read or write to the memory, you need to lock it. If it's able to lock the memory then you can get the pointer to the memory and use it. Once you have this pointer, what you do with it depends on the type of OP you are communicating with. Finally, unlock once done read/writing the data.

```cpp
if (!shm->lock())
{
    // error
}
else
{
    void *data = shm->getMemory();
    
    // Use the data here
    
    // Unlock it when done
    shm->unlock();
}
```

### UT_Mutex

`UT_Mutex` is a class to lock/unlock the shared memory segment to make sure two processes aren't accessing it at the same time. You don't need to use this class yourself, it'll be used by `UT_SharedMem` though, so make sure to include and compile it in your project.

## Compile Issues and Considerations

### Unicode

In the 2018.20000 builds and earlier, the UT_SharedMem class is not written with Unicode support. If you get errors involving LPCWSTR types or other Unicode types, it means you are compiling with Unicode support turned on, but using the older source/header files from 2018.20000 and earlier builds. Go to the project properties, 'General' page, and for 'Character Set' select 'Not Set'. If you require Unicode support, use the header files from 2019.10000 series of builds, or later.

This has been changed in the 2019.10000 series of builds, and the class is written to be unicode compliant.

## Related Articles

[REF_WriteSharedMemoryTOP], [REF_WriteSharedMemoryCHOP]
