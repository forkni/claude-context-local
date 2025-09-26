# MAT pbrMAT

## Overview

The PBR MAT creates a material using a Physically Based Rendering (PBR) lighting model.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `basecolor` | Base Color | RGB | Base color of the texture, used to calculate diffuse and specular contributions. |
| `specularlevel` | Specular Level | Float | The amount of contribution the Specular Level Map adds to the material. |
| `metallic` | Metallic | Float | The amount of contribution the Metallic Map adds to the material. |
| `roughness` | Roughness | Float | The amount of contribution the Roughness Map adds to the material. Used to calculate specular D, R, and F (blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_notes_v2.pdf pa... |
| `ambientocclusion` | Ambient Occlusion | Float | The amount of contribution the Ambient Occlusion Map adds to the material. Ambient Occlusion affects the contribution from the Environement Light COMP. |
| `envlightquality` | Env Light Quality | Float | The sampling quality of the Environment Light with the material. |
| `emit` | Emit | RGB | This is the color that the material will emit even if there is no light. |
| `constant` | Constant | RGB | Adds to the final color. Where there are point colors, finalcolor += Point Color * Constant Color. This behaves like there is ambient illumination of 1 1 1. It is not affected by textures or transp... |
| `frontfacelit` | Polygon Front Faces | Menu | Controls how the polygon's normal is used to light the front face of the polygon. For more information refer to the Two-Sided Lighting article. |
| `backfacelit` | Polygon Back Faces | Menu | Back Face's backfacelit - Controls how the polygon's normal is used to light the back face of the polygon. For more information refer to the Two-Sided Lighting article. |
| `outputshader` | Output Shader... | Pulse | This button will bring up a dialog that will create a GLSL MAT and Text DATs with shader code that this PBR MAT is currently using. Since shaders are dependent on the number and type of lights, it ... |
| `substance` | Substance TOP | TOP | Reference a Substance TOP containing an .sbsar file. Referencing the TOP will automatically unpack all enabled textures without having to manually fill in any of the below texture maps. Manually fi... |
| `basecolormap` | Base Color Map | TOP | Clicking on the arrows to the right of the map field will open the Texture Sampling Parameters for Color Map.  The other Map parameters below will have their own Texture Sampling Parameters as well. |
| `specularlevelmap` | Specular Level Map | TOP | Specifies a specular level map. |
| `metallicmap` | Metallic Map | TOP | Specifies a metallic texture map. This is equivalent to the Metallic map in Substance Designer. |
| `roughnessmap` | Roughness Map | TOP | Specifies a roughness texture map. This is equivalent to the Roughness map in Substance Designer. |
| `ambientocclusionmap` | Ambient Occlusion Map | TOP | Specifies a ambient occlusion texture map. This is equivalent to the Ambient Occlusion map in Substance Designer. Ambient Occlusion affects the contribution from the Environement Light COMP. |
| `normalmap` | Normal Map (Bump) | TOP | Uses a Normal Map from TOPs to create a 'bump map' effect. Bump-mapping simulates bumps or wrinkles in a surface to give it a 3D depth effect. Your geometry must have tangent attributes created for... |
| `bumpscale` | Bump Scale | Float | A multiplier for the 'bump effect' created by the Normal Map parameter. |
| `heightmapenable` | Enable Height Map | Toggle | Enables height mapping. |
| `heightmap` | Height Map | TOP | Specifies a height texture map. This is equivalent to the Height map in Substance Designer. The height map is used in conjunction with the normal map to perform parallax mapping. |
| `parallaxscale` | Parallax Scale | Float | Scale value applied to the height map. Can be used to increase or exaggerate the effect. |
| `parallaxocclusion` | Parallax Occlusion | Toggle | Enables parallax occlusion, an enhancement of the parallax mapping technique used with the height map. Parallax occlusion improves the quality of the texture offsetting in parallax mapping so that ... |
| `displaceverts` | Displace Vertices | Toggle | When Enable Height Map above is On, setting Displace Vertices to On will enable true displacement mapping where the vertices of the geometry are displaced based on the Height Map texture and the pa... |
| `displacescale` | Displace Scale | Float | A multiplier for the displacement amount. |
| `displacemid` | Displace Midpoint | Float | Sets the middle point of displacement map as the start position for the displacement effect. |
| `emitmap` | Emit Map | TOP | Specifies a TOP texture that is multiplied with the Emit color parameter of the material. The object must have texture coordinates. The alpha of this map is ignored. |
| `alphamap` | Alpha Map | TOP | This map multiplies the alpha of the object. It uses the red channel of the map, other channels are ignored. |
| `alphamode` | Uniform Alpha | Toggle | Turning this off will make the alpha change depending on orientation of each polygon's normal compared to the camera. Normals that are pointing at the camera will results in the polygon having an a... |
| `alphafront` | Alpha Front | Float | The opacity of the material. This parameter is multiplied by point alpha of the object (as will as any other alpha source). |
| `alphaside` | Alpha Side | Float | This is used for non-uniform alpha. It is the alpha value polygons that are facing away from the camera will get. |
| `rolloff` | Alpha Rolloff | Float | Controls how the alpha changes from Alpha Front to Alpha Side. |
| `postmultalpha` | Post-Mult Color by Alpha | Toggle | Multiplies the color by alpha after all other operations have taken place. |
| `rimlight` | Rim Light | Sequence | Sequence of rim light info |
| `shadowstrength` | Shadow Strength | Float | This parameter will control how much being in a shadow will change the color of the lighting. At 1 the object will take on the Shadow Color parameter, at 0 it will behave as if it's not in a shadow... |
| `shadowcolor` | Shadow Color | RGB | The color that will be used in shadowed areas. |
| `darknessemit` | Darkness Emit | Toggle | The Phong MAT calculates the current brightness of color of the objects, after taking into account lights, rim lights, emission etc. It then uses this brightness (between 0-1) and fades in the Dark... |
| `darknessemitcolor` | Darkness Emit Color | RGB | The color that is used for areas that are in darkness. |
| `darknessemitmap` | Darkness Emit Map | TOP | This map multiplies the Darkness Emit Color. This maps alpha is not used. |
| `writecameradepthtoalpha` | Write Camera Space Depth to Alpha | Toggle | This cause the camera space depth of the pixel to be written to the alpha channel of the output TOP. This value can be useful for post-processing effects, but ofcourse you will not have the result ... |
| `applypointcolor` | Apply Point Color | Toggle | Normally the color attribute (Cd[4]) coming from the SOP is used in the lighting calculation, you can turn off using the color attribute by un-checking this parameter. |
| `instancetexture` | Instance Texture | StrMenu | When provider per-instance textures in the Geometry COMP, this parameter selects which map the instance texture will be applied as. |
| `color` | Color Buffer | Sequence | Sequence of color buffers |
| `dodeform` | Deform | Toggle | Enables deforms on this material. |
| `deformdata` | Get Bone Data: | Menu | Specifies where the deform bone data will be obtained. |
| `targetsop` | SOP with Capture Data | OP | Specifies the SOP that contains the deform capture attributes. |
| `pcaptpath` | pCaptPath Attrib | Str | Specifies the name of the pCaptPath attribute to use. When your geometry has been put through a Bone Group SOP, the attributes will be split into names like pCaptPath0, pCaptPath1. You can only ren... |
| `pcaptdata` | pCaptData Attrib | Str | Much like pCaptPath Attrib. |
| `skelrootpath` | Skeleton Root Path | Object | Specifies the path to the COMP where the root of the skeleton is located. |
| `mat` | MAT | MAT | When obtaining deform data from a MAT or a Deform In MAT, this is where that MAT is specified. |
| `blending` | Blending (Transparency) | Toggle | This toggle enables and disables blending. However see the wiki article Transparency. |
| `blendop` | Blend Operation | Menu |  |
| `srcblend` | Source Color * | Menu | This value is multiplied by the color value of the pixel that is being written to the Color-Buffer (also know as the Source Color). |
| `destblend` | Destination Color * | Menu | This value is multiplied by the color value of the pixel currently in the Color-Buffer (also known as the Destination Color). |
| `separatealphafunc` | Separate Alpha Function | Toggle | This toggle enables and disables separate blending options for the alpha values. |
| `blendopa` | Alpha Blend Operation | Menu |  |
| `srcblenda` | Source Alpha * | Menu | This value is multiplied by the alpha value of the pixel that is being written to the Color-Buffer (also know as the Source Alpha). |
| `destblenda` | Destination Alpha * | Menu | This value is multiplied by the alpha value of the pixel currently in the Color-Buffer (also known as the Destination Alpha). |
| `blendconstant` | Blend Constant Color | RGB |  |
| `blendconstanta` | Blend Constant Alpha | Float |  |
| `legacyalphabehavior` | Legacy Alpha Behavior | Toggle |  |
| `pointcolorpremult` | Point Color Pre-Multiply | Menu |  |
| `depthtest` | Depth Test | Toggle | Enables and disables the Depth-Test. If the depth-test is disabled, depths values aren't written to the Depth-Buffer. |
| `depthfunc` | Depth Test Function | Menu | The depth value of the pixel being drawn is compared to the depth value currently in the depth-buffer using this function. If the test passes then the pixel is drawn to the Frame-Buffer. If the tes... |
| `depthwriting` | Write Depth Values | Toggle | If Write Depth Values is on, pixels that pass the depth-test will write their depth value to the Depth-Buffer. If this isn't on then no changes will be made to the Depth-Buffer, regardless of if th... |
| `alphatest` | Discard Pixels Based on Alpha | Toggle | This enables or disables the pixel alpha test. |
| `alphafunc` | Keep Pixels with Alpha | Menu | This menu works in conjunction with the Alpha Threshold parameter below in determining which pixels to keep based on their alpha value. |
| `alphathreshold` | Alpha Threshold | Float | This value is what the pixel's alpha is compared to to determine if the pixel should be drawn. Pixels with alpha greater than the Alpha Threshold will be drawn. Pixels with alpha less than or equal... |
| `wireframe` | Wire Frame | Menu | Enables and disables wire-frame rendering with the option of OpenGL Tesselated or Topology based wireframes. |
| `wirewidth` | Line Width | Float | This value is the width that the wires will be. This value is in pixels. |
| `cullface` | Cull Face | Menu | Selects which faces to render. |
| `polygonoffset` | Polygon Depth Offset | Toggle | Turns on the polygon offset feature. |
| `polygonoffsetfactor` | Offset Factor | Float |  |
| `polygonoffsetunits` | Offset Units | Float |  |

## Usage Examples

### Basic Usage

```python
# Access the MAT pbrMAT operator
pbrmat_op = op('pbrmat1')

# Get/set parameters
freq_value = pbrmat_op.par.active.eval()
pbrmat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pbrmat_op = op('pbrmat1')
output_op = op('output1')

pbrmat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pbrmat_op)
```

## Technical Details

### Operator Family

**MAT** - Material Operators - Shading and material definitions

### Parameter Count

This operator has **74** documented parameters.

## Navigation

- [Back to MAT Index](../MAT/MAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
