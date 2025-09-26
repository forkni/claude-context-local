# CHOP audiorenderCHOP

## Overview

The Audio Render CHOP uses the Steam Audio SDK to spatially render audio based on the full transforms of a listener and an audio source.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turns the Audio Render on or off. |
| `mode` | Mode | Menu | This menu determines which Steam Audio mode to use. |
| `outputformat` | Output Format | Menu | The output format of the audio. |
| `attenuation` | Enable Attenuation | Toggle | Attenuate the sound based on relative distance. |
| `ambisonicsorder` | Ambisonics Order | Int | Ambisonics order of the output buffer. |
| `mappingtable` | Mapping Table | DAT | A DAT Table that specifies the various speakers in the setup and their position. The Table must have 3 columns named x, y, z. Each row specifies an individual speaker, and the 3 columns specify its... |
| `listenerobject` | Listener Object COMP | Object | A COMP that represents the listening head. Must be a COMP that contains transform data, such as a Geometry or Camera COMP. |
| `source` | Source | Sequence | Sequence of the audio sources. |
| `source0object` | Object COMP | Object | A COMP that represents the source of the sound. Must be a COMP that contains transform data, such as a Geometry or Camera COMP. |
| `source0directivity` | Enable Directivity | Toggle | Turns directivity on or off. When disabled, sound will emit from the source from all directions (ie. omnidirectional) |
| `source0dipoleweight` | Dipole Weight | Float | The weight of the dipole to blend in the directivity pattern. 0 = pure omnidirectional, 1 = pure dipole, 0.5 = cardioid directivity pattern. |
| `source0dipolepower` | Dipole Power | Float | The sharpness of the dipole. Higher values make the sound direction narrower. |
| `update` | Update Meshes | Toggle | When enabled, any static mesh changes will automatically be updated in the simulation |
| `updatepulse` | Update Meshes Pulse | Pulse | When pulse, will update the static meshes in the simulation if they changed. |
| `mesh` | Mesh | Sequence | Sequence of static meshes. |
| `mesh0object` | Mesh COMP | Object | The COMP for the mesh. COMPs must contain geometries in triangle polygon form. Meshes will only be added to the scene if the COMP's display flag is on. |
| `mesh0absorb` | Absorption | Float | Frequency dependent absorption: 3-band air absorption coefficients. Essentially, how much sound the static mesh absorbs. |
| `mesh0scatter` | Scattering | Float | Scatters sound in random directions for reflections. 0 = pure specular, 1 = pure diffuse. |
| `mesh0trans` | Transmission | Float | Frequency dependent transmission: 3-band EQ coefficients for transmission. Essentially, how much sound can pass through the static mesh. |
| `airabsorb` | Enable Air Absorption | Toggle | Turns air absorption on or off for all sources. Air absorption is how much sound is lost over the distance travelling from source to listener. |
| `occlusion` | Enable Occlusion | Toggle | Turns raycast occlusion on or off for all meshes. If a single ray from listener to source is occluded, then the source is considered occluded. |
| `numsurfaces` | Number of Surfaces | Int | Maximum number of surfaces, starting from closest surface to the listener, whose transmission coefficients will be considered when calculating the total sound transmission. |
| `reflection` | Enable Reflection | Toggle | Turns reflection on or off for all meshes. |
| `diffsamp` | Diffuse Samples | Int | Number of directions to generate for reflecting rays. |
| `duration` | Duration | Float | Duration in seconds of the impulse responses generated. |
| `refambixord` | Ambisonics Order | Int | Ambisonics order of the impulse responses generated. |
| `numrays` | Number of Rays | Int | Number of rays to trace from the listener. |
| `numthreads` | Number of Threads | Int | Number of threads used for real-time reflection simulations. |
| `numbounces` | Number of Bounces | Int | Number of times each ray is reflected off a surface. |
| `irmindist` | Irradiance Min Distance | Float | The minimum distance used to calculate how much sound energy reaches a surface from a source. |
| `enablebake` | Enable Bake | Toggle | Turns baking on or off. Baking is useful as an optimization tool when calculating reflections. Bake pulse must be pressed to start baking. Turning baking off will disable any bakes that are current... |
| `bake` | Bake | Pulse | Immediately start baking. Once complete, reflections will automatically used the baked data. |
| `probedist` | Probes Distance | Float | The spacing between two neighboring probes. |
| `yoffset` | Y-Offset from Surface | Float | The height above the surface of a geometry all probes will be generated at. |
| `size` | Size of Spawn Box | XYZ | Size of the spawn box along the X, Y, and Z axes where probes will be generated. |
| `origin` | Origin of Spawn Box | XYZ | These X,Y, and Z Values determine where the center of the spawn box is located. |
| `lstnrdist` | Distance from Listener | Float | The maximum distance from the listener where baked data will be stored for probes. |
| `savedur` | Save Duration | Float | Duration in seconds of the impulse responses saved at each probe. |
| `batchsize` | Batch Size | Int | Number of probes to bake simultaneously. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiorenderCHOP operator
audiorenderchop_op = op('audiorenderchop1')

# Get/set parameters
freq_value = audiorenderchop_op.par.active.eval()
audiorenderchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiorenderchop_op = op('audiorenderchop1')
output_op = op('output1')

audiorenderchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiorenderchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **45** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
