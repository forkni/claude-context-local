# MAT phongMAT

## Overview

The Phong MAT creates a material using the Phong Shading model.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `ambdiff` | Ambient uses Diffuse | Toggle | Uses the Diffuse parameter for Ambient when checked. |
| `diff` | Diffuse | RGB | The color of the diffuse light reflected from the material. |
| `amb` | Ambient | RGB | The color of the ambient light reflected from the material. |
| `spec` | Specular | RGB | The color of the specular light reflected from the material. This changes the color of the highlights on shiney objects. |
| `emit` | Emit | RGB | This is the color that the material will emit even if there is no light. |
| `constant` | Constant | RGB | Adds to the final color. Where there are point colors, finalcolor += Point Color * Constant Color. This behaves like there is ambient illumination of 1 1 1. It is not affected by textures or transp... |
| `shininess` | Shininess | Float | Controls the specular highlights (glossyness) of an object. Higher settings are more glossy, like plastic or shiny metal. Lower settings give more of a matte finish. |
| `colormap` | Color Map | TOP | Specifies a TOP texture that is multiplied by the results of all of the lighting calculations. The alpha of this map is used as a part of calculating the objects alpha.  Clicking on the arrows to t... |
| `normalmap` | Normal Map (Bump) | TOP | Uses a Normal Map from TOPs to create a 'bump map' effect. Bump-mapping simulates bumps or wrinkles in a surface to give it a 3D depth effect. Your geometry must have tangent attributes created for... |
| `bumpscale` | Bump Scale | Float | A multiplier for the 'bump effect' created by the Normal Map parameter. |
| `heightmapenable` | Enable Height Map | Toggle | Enables height mapping. |
| `heightmap` | Height Map | TOP | Specifies a height texture map. The height map is used in conjunction with the normal map to perform parallax mapping. |
| `parallaxscale` | Parallax Scale | Float | Scale value applied to the height map. Can be used to increase or exaggerate the effect. |
| `parallaxocclusion` | Parallax Occlusion | Toggle | Enables parallax occlusion, an enhancement of the parallax mapping technique used with the height map. Parallax occlusion improves the quality of the texture offsetting in parallax mapping so that ... |
| `displaceverts` | Displace Vertices | Toggle | When Enable Height Map above is On, setting Displace Vertices to On will enable true displacement mapping where the vertices of the geometry are displaced based on the Height Map texture and the pa... |
| `displacescale` | Displace Scale | Float | A multiplier for the displacement amount. |
| `displacemid` | Displace Midpoint | Float | Sets the middle point of displacement map as the start position for the displacement effect. |
| `diffusemap` | Diffuse Map | TOP | Specifies a TOP that multiples the Diffuse Color. The object must have texture coordinates. The alpha of this map is ignored. |
| `specmap` | Specular Map | TOP | Specifies a TOP texture that is multiplied with the Specular color parameter of the material. The object must have texture coordinates. The alpha of this map is ignored. |
| `emitmap` | Emit Map | TOP | Specifies a TOP texture that is multiplied with the Emit color parameter of the material. The object must have texture coordinates. The alpha of this map is ignored. |
| `envmap` | Environment Map | TOP | Uses a TOP texture to define an environment map for the material. Environment mapping simulates an object reflecting its surroundings. The TOP defined in this parameter is the texture that will be ... |
| `envmapcolor` | Environment Map Color | RGB | This color is multiplied with the texture specified by the Environment Map parameter above. |
| `envmaprotate` | Environment Map Rotate | XYZ | Rotate the texture specified by the Environment Map parameter above. |
| `envmaptype2d` | Environment Map 2D Type | Menu | Select between using a sphere map or an equirectangular map as the Environment Map type. |
| `frontfacelit` | Polygon Front Faces | Menu | Controls how the polygon's normal is used to light the front face of the polygon. For more information refer to the Two-Sided Lighting article. |
| `backfacelit` | Polygon Back Faces | Menu | Controls how the polygon's normal is used to light the back face of the polygon. For more information refer to the Two-Sided Lighting article. |
| `outputshader` | Output Shader... | Pulse | This button will bring up a dialog that will create a GLSL MAT and Text DATs with shader code that matches whatever effect this Phong MAT is currently creating. Since shaders are dependent on the n... |
| `alphamap` | Alpha Map | TOP | This map multiplies the alpha of the object. It uses the red channel of the map, other channels are ignored. |
| `alphamode` | Uniform Alpha | Toggle | Turning this off will make the alpha change depending on orientation of each polygon's normal compared to the camera. Normals that are pointing at the camera will results in the polygon having an a... |
| `alphafront` | Alpha Front | Float | The opacity of the material. This parameter is multiplied by point alpha of the object (as will as any other alpha source). |
| `alphaside` | Alpha Side | Float | This is used for non-uniform alpha. It is the alpha value polygons that are facing away from the camera will get. |
| `rolloff` | Alpha Rolloff | Float | Controls how the alpha changes from Alpha Front to Alpha Side. |
| `postmultalpha` | Post-Mult Color by Alpha | Toggle | Multiplies the color by alpha after all other operations have taken place. |
| `alphamultlight` | Mult Alpha by Light Luminance | Toggle | When this is enabled, the luminance of the lighting will be multiplied by the alpha, to decrease/increase it. |
| `multitexturing` | Multi-Texturing (Disables Color Map) | Toggle | Enables multi-texturing. This disables the Color Map parameter. |
| `texture1` | Texture 1 | TOP | You can specify up to 4 textures for multi-texturing. |
| `texture2` | Texture 2 | TOP | You can specify up to 4 textures for multi-texturing. |
| `texture3` | Texture 3 | TOP | You can specify up to 4 textures for multi-texturing. |
| `texture4` | Texture 4 | TOP | You can specify up to 4 textures for multi-texturing. |
| `multitexexpr` | GLSL Expression | Str | GLSL code that combines the texture images (look to the start of this section for more details). This parameter can be left blank (which means the maps will just be multiplied together). |
| `rimlight` | Rim Light | Sequence | Sequence of rim light info |
| `shadowstrength` | Shadow Strength | Float | This parameter will control how much being in a shadow will change the color of the lighting. At 1 the object will take on the Shadow Color parameter, at 0 it will behave as if it's not in a shadow... |
| `shadowcolor` | Shadow Color | RGB | The color that will be used in shadowed areas. |
| `darknessemit` | Darkness Emit | Toggle | The Phong MAT calculates the current brightness of color of the objects, after taking into account lights, rim lights, emission etc. It then uses this brightness (between 0-1) and fades in the Dark... |
| `darknessemitcolor` | Darkness Emit Color | RGB | The color that is used for areas that are in darkness. |
| `darknessemitmap` | Darkness Emit Map | TOP | This map multiplies the Darkness Emit Color. This maps alpha is not used. |
| `spec2` | Secondary Specular | RGB | Adds a secondary specular highlight color. |
| `shininess2` | Secondary Shininess | Float | Controls the secondary specular highlights (glossyness) of an object. Higher settings are more glossy, like plastic or shiny metal. Lower settings give more of a matte finish. |
| `writecameradepthtoalpha` | Write Camera Space Depth to Alpha | Toggle | This causes the camera space depth of the pixel to be written to the alpha channel of the output TOP. This value can be useful for post-processing effects, but ofcourse you will not have the result... |
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
# Access the MAT phongMAT operator
phongmat_op = op('phongmat1')

# Get/set parameters
freq_value = phongmat_op.par.active.eval()
phongmat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
phongmat_op = op('phongmat1')
output_op = op('output1')

phongmat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(phongmat_op)
```

## Technical Details

### Operator Family

**MAT** - Material Operators - Shading and material definitions

### Parameter Count

This operator has **83** documented parameters.

## Navigation

- [Back to MAT Index](../MAT/MAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
