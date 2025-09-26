# DAT webrtcDAT

## Overview

A WebRTC DAT represents a peer on one end of any number of WebRTC peer-to-peer connections. Each connection is represented in TouchDesigner by a generated UUID. The UUID must be passed to WebrtcDAT Class connection-level python methods. The WebRTC DAT output is a table formatted with a row per connection, with columns: id (ie. UUID), connection_sta

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When active, can connect to peers and send media/data. When deactivated, all existing connections will be closed. |
| `reset` | Reset | Pulse | Resets the peer associated with the DAT. Equivalent to deactivating then reactivating the active parameter. |
| `bitratelimits` | Custom Bit Rate Limits | Toggle | When enabled, custom min/max bit rates can be specified. These max bit rate limits are expressed in kbps and apply to all tracks associated with the WebRTC DAT. |
| `minbitrate` | Minimum Bit Rate (kbps) | Int | Minimum bit rate for all tracks associated with the WebRTC DAT. |
| `maxbitrate` | Maximum Bit Rate (kbps) | Int | Maximum bit rate for all tracks associated with the WebRTC DAT. |
| `callbacks` | Callbacks DAT | DAT | Reference to a DAT containing WebRTC callbacks. |
| `stun` | STUN Server URL | Str | URL of the STUN server. See WebRTC#ICE for more details regarding STUN. |
| `username` | TURN Username | Str | Username for access to the specified TURN servers. |
| `password` | TURN Password | Str | Password for access to the specified TURN servers. |
| `turn` | TURN Server | Sequence | Sequence of TURN server urls. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT webrtcDAT operator
webrtcdat_op = op('webrtcdat1')

# Get/set parameters
freq_value = webrtcdat_op.par.active.eval()
webrtcdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
webrtcdat_op = op('webrtcdat1')
output_op = op('output1')

webrtcdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(webrtcdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
