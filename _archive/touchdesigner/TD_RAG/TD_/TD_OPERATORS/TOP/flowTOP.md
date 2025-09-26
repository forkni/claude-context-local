# TOP flowTOP

## Overview

The Nvidia Flow TOP calculates the Flow simulation and renders it.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `initialize` | Initialize | Pulse | Initializes the simulation. |
| `start` | Start | Pulse | Starts the simulation playback. |
| `play` | Play | Toggle | The simulation only steps forward when Play = On, when off the simulation is paused. |
| `camera` | Camera | OBJ | Specify the Camera COMP to view the simulation from. Note: Must be camera with Projection = Perspective. |
| `emitters` | Flow Emitters | OBJ | Specify the Nvidia Flow Emitter COMPs to include in the simulation. |
| `simposition` | Sim Position | XYZ | The position of the simulation volume's center, in the world. The simulation cannot extend outside of the volume. |
| `simsize` | Sim Size | XYZ | The size of the simulation volume in the world. The simulation cannot extend outside of the volume. Also controls the size of simulation blocks, so the total number of blocks in the volume stays th... |
| `memusage` | Mem Usage | Float | Controls relative memory usage, the fraction of the total simulation blocks that will be allocated. Most simulations will not fill the simulation volume uniformly, so only a small value is needed. ... |
| `showblocks` | Show Blocks | Toggle | Displays the simulation blocks being used. Useful for debugging or optimizing your Flow simulation. Also shows the edges of the simulation volume. |
| `showemitbounds` | Show Emit Bounds | Toggle | Displays the bounds of the emitters. |
| `showshapes` | Show Shapes | Toggle | Displays the shapes of the emitters. |
| `speed` | Speed | Float | Controls the update rate of the simulation. |
| `maxsteps` | Max Simulation Steps | Int | Maximum number of simulation steps per update. A higher number of steps will increase quality for fast moving object at the cost of performance. |
| `rendermode` | Render Mode | Int | Provides two debug render modes in addition to the default of Density. Debug Density gives a "rainbow" render, where density is mapped to a colour, and Dubug Velocity converts velocity xyz to an rg... |
| `gravity` | Gravity | XYZ | Gravity direction for use with Buoyancy parameter, where amount controls strength of buoyancy force. |
| `veldamping` | Velocity Damping | Float | Higher values reduce velocity faster. Uses exponential decay curve. |
| `velfade` | Velocity Fade | Float | Compared to damping, fade reduces low velocity values faster. Fade velocity rate is in units per second. |
| `velmaccormackblend` | Vel MacCormack Blend | Float | Higher values make a sharper appearance, but with more artifacts. |
| `smokedamping` | Smoke Damping | Float | Higher values reduce smoke faster. Uses exponential decay curve. |
| `smokefade` | Smoke Fade | Float | Compared to damping, fade reduces low smoke values faster. Fade velocity rate is in units per second. |
| `smokemaccormackblend` | Smoke MacCormack Blend | Float | Higher values make a sharper appearance, but with more artifacts. |
| `tempdamping` | Temp Damping | Float | Higher values reduce temperature faster. Uses exponential decay curve. |
| `tempfade` | Temp Fade | Float | Compared to damping, fade reduces low temperature values faster. Fade velocity rate is in units per second. |
| `fueldamping` | Fuel Damping | Float | Higher values reduce fuel faster. Uses exponential decay curve. |
| `fuelfade` | Fuel Fade | Float | Compared to damping, fade reduces low fuel values faster. Fade velocity rate is in units per second. |
| `vortstrength` | Vorticity Strength | Float | Controls amount of rotation turbulence as a multiplier, a value of 0 will result in no vorticity. High values increase turbulent flow while low values increase laminar flow. |
| `vortfromvel` | Vorticity from Velocity | Float | Amount of vorticity added from velocity. |
| `vortfromsmoke` | Vorticity from Smoke | Float | Amount of vorticity added from smoke. |
| `vortfromtemp` | Vorticity from Temp | Float | Amount of vorticity added from temperature. |
| `vortfromfuel` | Vorticity from Fuel | Float | Amount of vorticity added from fuel. |
| `vortconstant` | Vorticity Constant | Float | The baseline vorticity in the simulation. |
| `ignitiontemp` | Ignition Temp | Float | Specify the minimum temperature required for combustion. |
| `burnpertemp` | Burn per Temp | Float | Control how much fuel is burned for a given temperature level. Lower Burn per Temp may result in some fuel not burning completely at a certain temperature. |
| `smokeperburn` | Smoke per Burn | Float | Controls amount of smoke generated for each unit of combustion (per burn). |
| `tempperburn` | Temp per Burn | Float | Controls amount of temperature generated for each unit of combustion (per burn). |
| `fuelperburn` | Fuel per Burn | Float | Controls amount of fuel used for each unit of combustion (per burn). |
| `buoyancy` | Buoyancy | Float | Works in conjunction with the parameter Gravity above which sets a vector for use by Buoyancy. Higher values result in greater effect by the Gravity parameter. |
| `coolingrate` | Cooling Rate | Float | The rate of cooling in the system, exponential. |
| `expansion` | Expansion | Float | Controls the amount the system's gaseous volume expands. |
| `velallocweight` | Velocity Alloc Weight | Float | If zero, block allocation and deallocation depend on an internal threshold and weighting of Velocity. If non-zero,  block allocation and deallocation will be affected by the value of Velocity Alloc... |
| `velallocthreshold` | Velocity Alloc Threshold | Float | If Velocity Alloc Weight is non-zero, block allocation and deallocation is based on this value. In particular, if the velocity magnitude is below this threshold, the block will be deallocated, unle... |
| `smokeallocweight` | Smoke Alloc Weight | Float | If zero, block allocation and deallocation depend on an internal threshold and weighting of Smoke density. If non-zero, smoke density affects block allocation and deallocation based on the value of... |
| `smokeallocthreshold` | Smoke Alloc Threshold | Float | If Smoke Alloc Weight is non-zero, block allocation and deallocation is based on this value. In particular, if the Smoke density is below this threshold, the block will be deallocated, unless veloc... |
| `fuelallocweight` | Fuel Alloc Weight | Float | If zero, block allocation and deallocation depend on an internal threshold and weighting of fuel density. If non-zero, fuel density affects block allocation and deallocation based on the value of F... |
| `fuelallocthreshold` | Fuel Alloc Threshold | Float | If Fuel Alloc Weight is non-zero, block allocation and deallocation is based on this value. In particular, if the Smoke density is below this threshold, the block will be deallocated, unless veloci... |
| `enableshadow` | Enable | Toggle | Enables Volume shadow rendering for the simulation. Shadowing generates light intensity values that overwrite the "burn" channel of the grid. Values range from 0 to 1, where 0 is fully shadowed. Sh... |
| `drawshadowdebug` | Draw Debug | Toggle | Displays the volume shadow blocks being used. Useful for debugging or optimizing. |
| `overrideemitter` | Override Emitter Intensity Mask | Toggle | Automatically adjusts the emitters' render material, so volume shadows are visible. Will override 'Burn Intensity Mask' and 'Intensity Bias' of emitters. |
| `light` | Light | OBJ | The light source used to generate volume shadow. The light should be a shadow caster. Only the position and orientation of the light are used, color and intensity are ignored. |
| `shadowresolution` | Shadow Resolution | Int | The resolution of the shadow map volume texture. The texture is allocated as a cube, so there will be space for shadowresolution^3 blocks. |
| `shadowminusage` | Min Memory Usage | Float | The initial fraction of volume shadow blocks to allocate memory for. |
| `shadowmaxusage` | Max Memory Usage | Float | The maximum fraction of volume shadow blocks to allocate memory for. |
| `shadowintensityscale` | Intensity Scale | Float | Scales how dark the shadow will be. |
| `shadowminintensity` | Min Intensity | Float | A lower limit for shadow intensity. |
| `shadowburnmask` | Burn Blend Mask | Float | Allows the burn value in the simulation to control the blend strength of the shadow. Postive values mean burn increases the blend strength, negative values mean burn decreases the blend strength |
| `shadowsmokemask` | Smoke Blend Mask | Float | Allows the smoke value in the simulation to control the blend strength of the shadow. Postive values mean smoke increases the blend strength, negative values mean smoke decreases the blend strength |
| `shadowtempmask` | Temp Blend Mask | Float | Allows the temperature value in the simulation to control the blend strength of the shadow. Postive values mean temp increases the blend strength, negative values mean temp decreases the blend stre... |
| `shadowfuelmask` | Fuel Blend Mask | Float | Allows the fuel value in the simulation to control the blend strength of the shadow. Postive values mean fuel increases the blend strength, negative values mean fuel decreases the blend strength |
| `shadowblendbias` | Blend Bias | Float | An offset that increases or decreases the blend strength by a constant amount. Parts of the grid with a blend value over 1 will have shadows. Parts of the grid with blend value under 1 will not hav... |
| `outputresolution` | Output Resolution | Menu | quickly change the resolution of the TOP's data. |
| `resolution` | Resolution | Int | Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size. The drop down menu ... |
| `resmenu` | Resolution Menu | Pulse | A drop-down menu with some commonly used resolutions. |
| `resmult` | Use Global Res Multiplier | Toggle | Uses the Global Resolution Multiplier found in Edit>Preferences>TOPs. This multiplies all the TOPs resolutions by the set amount. This is handy when working on computers with different hardware spe... |
| `outputaspect` | Output Aspect | Menu | Sets the image aspect ratio allowing any textures to be viewed in any size. Watch for unexpected results when compositing TOPs with different aspect ratios. (You can define images with non-square p... |
| `aspect` | Aspect | Float | Use when Output Aspect parameter is set to Custom Aspect. |
| `armenu` | Aspect Menu | Pulse | A drop-down menu with some commonly used aspect ratios. |
| `inputfiltertype` | Input Smoothness | Menu | This controls pixel filtering on the input image of the TOP. |
| `fillmode` | Fill Viewer | Menu | Determine how the TOP image is displayed in the viewer. NOTE:To get an understanding of how TOPs work with images, you will want to set this to Native Resolution as you lay down TOPs when starting ... |
| `filtertype` | Viewer Smoothness | Menu | This controls pixel filtering in the viewers. |
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. For every pass after the first it takes the result of the previous pass and replaces the node's first input with the result of the... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP flowTOP operator
flowtop_op = op('flowtop1')

# Get/set parameters
freq_value = flowtop_op.par.active.eval()
flowtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
flowtop_op = op('flowtop1')
output_op = op('output1')

flowtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(flowtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **72** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
