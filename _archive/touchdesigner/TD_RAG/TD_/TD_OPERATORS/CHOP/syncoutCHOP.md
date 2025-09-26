# CHOP syncoutCHOP

## Overview

The Sync In CHOP and Sync Out CHOP are used to keep timelines in two or more TouchDesigner processes within a single frame of each other. One process will contain a Sync Out CHOP while one or more other processes contain Sync In CHOPs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Whether or not the CHOP is currently attempting to synchronize itself. |
| `multicastaddress` | Multicast Address | Str | An IP address to communicate on (224.0.0.1). |
| `port` | Network Port | Int | The network port associated with the address. |
| `localaddress` | Local Address | StrMenu | Specify an IP address to send from, useful when the system has mulitple NICs (Network Interface Card) and you want to select which one to use. |
| `localportmode` | Local Port Mode | Menu | Choose between automatically or manually selecting local port to use. |
| `localport` | Local Port | Int | When the above parameter is set to 'Manual', enter the port number to use here. |
| `timeout` | Timeout (msec) | Int | The maximum amount of time the CHOP will wait for synchronization signals from the other Sync CHOPs. This value is expressed in milliseconds. |
| `clienttimeouts` | Client Timeouts (Consecutive) | Int | The maximum number of consecutive timeouts a client must generate until it is ignored, causing no further timeouts. It will remain ignored until it replies on time again or this CHOP is reset. |
| `banclients` | Ban Clients | Toggle | Enables permanent banning of clients. |
| `banclienttimeouts` | Total Timeouts | Int | The maximum number of timeouts a client must generate until it is permanently ignored. Only a reset will allow it to be included again. |
| `clearstats` | Clear Stats | Pulse | Pressing this button will clear all banned lists, as well as totals reported in an Info CHOP. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP syncoutCHOP operator
syncoutchop_op = op('syncoutchop1')

# Get/set parameters
freq_value = syncoutchop_op.par.active.eval()
syncoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
syncoutchop_op = op('syncoutchop1')
output_op = op('output1')

syncoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(syncoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
