# CHOP bulletsolverCHOP

## Overview

The Bullet Solver CHOP is used in conjunction with a Bullet Dynamics system. It outputs the solved results from a Bullet simulation and can include the results for the entire system (Bullet Solver COMP) or an individual actor (Actor COMP) within a system.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `comp` | Solver or Actor COMP | objref | A reference to either a Bullet Solver COMP or Actor COMP. If a Bullet Solver COMP is referenced then the CHOP will output the simulation results for all of its actors. If an Actor COMP is reference... |
| `xformspace` | Transform Space | dropmenu | The space in which to output the transformation values. That is, the transform values (translation/rotation) will be outputted relative to the selected space. |
| `collisioninfo` | Collision Info | toggle | Adds colliding, colliding_actor_id, colliding_body_id, and total_collisions channels to the CHOP. In order to track these values for a body, "Perform Contact Test" must be enabled on the Bullet Sol... |
| `trans` | Translation | toggle | Adds translation channels to the CHOP. |
| `rot` | Rotation | toggle | Adds rotation channels to the CHOP. |
| `scale` | Scale | toggle | Adds scale channels to the CHOP. |
| `linvel` | Linear Velocity | toggle | Adds linear velocity channels to the CHOP. |
| `angvel` | Angular Velocity | toggle | Adds angular velocity channels to the CHOP. |
| `rate` | Sample Rate | float | The sample rate of the CHOP. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP bulletsolverCHOP operator
bulletsolverchop_op = op('bulletsolverchop1')

# Get/set parameters
freq_value = bulletsolverchop_op.par.active.eval()
bulletsolverchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
bulletsolverchop_op = op('bulletsolverchop1')
output_op = op('output1')

bulletsolverchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(bulletsolverchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
