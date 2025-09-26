# SOP lsystemSOP

## Overview

The Lsystem SOP implements L-systems (Lindenmayer-systems, named after Aristid Lindenmayer (1925-1989)), allow definition of complex shapes through the use of iteration.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | Provides two options for output geometry: |
| `generations` | Generations | Float | Determines the number of times to apply the rules to the initial string. This value controls the growth of the L-system. Place a time-based function here to animate the L-system growth. |
| `randscale` | Random Scale | Float | Random Scale as a percentage. This will apply a random scale to the changing geometry's lengths, angles and thickness. |
| `randseed` | Random Seed | Int | Random Seed for the SOP. This value can be used to select different sequences of random values. |
| `contangl` | Continuous Angles | Toggle | Calculates the incremental angles of branches, if a non-integer generational value is used. If the Generations field is animating, this should be set to ensure smooth growth. |
| `contlength` | Continuous Length | Toggle | Calculates the incremental lengths of the geometry points if a non-integer generational value is used. As with Continuous Angles, if the Generations field is animating, this should be set to ensure... |
| `contwidth` | Continuous Width | Toggle | Calculates the incremental lengths of the geometry points if a non-integer generational value is used. As with Continuous Angles, if the Generations field is animating, this should be set to ensure... |
| `docolor` | Apply Color | Toggle | Use a TOP to apply color to the L-system as it grows. |
| `colormap` | Image File | TOP | Defines a TOP to use when the Apply Color button is selected. Also see the ` and # turtle operators. |
| `inc` | UV Increment | UV | Defines the default color U, V index increments when the turtle symbols ` or # are used. |
| `pointwidth` | Point Width Attribute | Toggle | Adds a point width attribute to each point in the geometry. This width is effected by the Thickness and Thickness Scale parameters on the Tube Page. |
| `rows` | Rows | Int | The first option sets the number of tube sides and the second sets the number of divisions per step length if tube geometry is selected. |
| `cols` | Columns | Int | The first option sets the number of tube sides and the second sets the number of divisions per step length if tube geometry is selected. |
| `tension` | Tension | Float | Tension defines the smoothness of branching corners. |
| `smooth` | Branch Blend | Float | Enabling this option allows a child branch to be continuously joined to its parent branch. |
| `thickinit` | Thickness | Float | This number defines the default tube thickness. |
| `thickscale` | Thickness Scale | Float | This number is the scale factor used with the ! or ? operator. |
| `dotexture` | Apply Tube Texture Coordinates | Toggle | When enabled, UV texture coordinates are applied to the tube segments, such that the texture wraps smoothly and continuously over branches. |
| `vertinc` | Vertical Increment | Float | Defines the vertical spacing of texture coordinates over tube geometry when tube texture is applied. |
| `stepinit` | Step Size | Float | Step Size allows you to define the default length of the edges when new geometry is generated. |
| `stepscale` | Step Size Scale | Float | Step Size Scale defines the scale by which the geometry will be modified by the " or _ (double quote, or underscore) turtle operators. |
| `angleinit` | Angle | Float | Angle defines the default turning angle for turns, rolls and pitches. |
| `anglescale` | Angle Scale | Float | Angle Scale allows you to enter the scaling factor to be employed when the ; or @ operators are used. |
| `varb` | Variable b | Float | Substitutes user-defined b, c and d variables in rules or premise. These variables are expanded and so may include system variables such as $F and $T. |
| `varc` | Variable c | Float | Substitutes user-defined b, c and d variables in rules or premise. These variables are expanded and so may include system variables such as $F and $T. |
| `vard` | Variable d | Float | Substitutes user-defined b, c and d variables in rules or premise. These variables are expanded and so may include system variables such as $F and $T. |
| `gravity` | Gravity | Float | This parameter determines the amount of gravity applied to the geometry via the T (tropism vector) turtle operator. Tropism is when a plant bends or curves in response to an external stimulus. L-sy... |
| `pictop` | Pic Image TOP | TOP | This is the TOP which the pic() function uses. See #Expressions L-system Specific Expression Functions below. |
| `grpprefix` | Group Prefix | Str | If the production g(n) is encountered, all subsequent geometry is included in a primitive group prefixed with this label and ending with the ascii value of n. See #CreateGroup Creating Groups withi... |
| `chanprefix` | Channel Prefix | Str | If the expression chan(n) is encountered, it is replaced with the local channel prefixed with this label and ending with the ascii value of n. |
| `stampa` | Leaf Param A | Str | You can determine which parameters are used by leaves. See #CreateGroup Creating Groups within L-systems below for an example. |
| `stampb` | Leaf Param B | Str | You can determine which parameters are used by leaves. See #CreateGroup Creating Groups within L-systems below for an example. |
| `stampc` | Leaf Param C | Str | You can determine which parameters are used by leaves. See #CreateGroup Creating Groups within L-systems below for an example. |
| `rules` | Rules DAT | DAT | Path to the DAT defining the rules for the LSystem.   Context Ignore context_ignore: - Defining this in the Rules DAT specifies all characters which are to be skipped when testing context sensitivi... |

## Usage Examples

### Basic Usage

```python
# Access the SOP lsystemSOP operator
lsystemsop_op = op('lsystemsop1')

# Get/set parameters
freq_value = lsystemsop_op.par.active.eval()
lsystemsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lsystemsop_op = op('lsystemsop1')
output_op = op('output1')

lsystemsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lsystemsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **34** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
