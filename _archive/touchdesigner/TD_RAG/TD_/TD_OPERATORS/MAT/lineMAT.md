# MAT lineMAT

## Overview

The Line MAT renders 3D line segments, dots and vectors. The line width and color can be varied based on distance to the camera, using two models: a 1/z dropoff (z = distance from camera), or a near-far distance rolloff model, where you set the width and color at the near and far distances, and you vary three rolloff controls.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `depthinterpolationmodel` | Depth Interpolation Model | Menu | Depth Interpolation Model depthmodel  a menu to select how the width of line items changes by their distance from the camera. |
| `inversedistanceexponent` | Inverse Distance Exponent | Float | When the Depth Interpolation Model is Inverse Distance, this determines how fast the widths/sizes decrease with distance. If it is set to 1 (default), the width goes down at the rate of 1/r. If it ... |
| `distancenear` | Distance Near | Float | Specifies a near plane with a certain distance from the camera. |
| `distancefar` | Distance Far | Float | Specifies a far plane with a certain distance from the camera. |
| `widthnear` | Width Near | Float | Specifies a fixed width value when the distance from camera is less than or equal to Distance Near. See the Summary of this operator for an explantion of the treatment of line width. |
| `widthfar` | Width Far | Float | Specifies a fixed width value when the distance from the camera is equal or bigger than the Distance Far. Note when the Near-Far Range option is selected as the Depth Model, any point in between Di... |
| `widthaffectedbyfov` | Width Affected by FOV/OrthoWidth | Toggle | With this off (default), looking at a rendered image of a certain resolution, a line of with w will always be the same # of pixels wide as you change the field-of-view or ortho width. With this par... |
| `widthbias` | Width Bias | Float | Moves the S Curves bias backward or forward for width interpolation (only S Curve depth model). |
| `widthsteepness` | Width Steepness | Float | Controls the steepness of the S Curve for width interpolation (only S Curve depth model). The higher the value of the steepness, you will notice more dramatic changes (higher slope) in the curve wi... |
| `widthlinearize` | Width Linearize | Float | Control the amount of curvature in the curve for width interpolation (only S Curve depth model). |
| `colorbias` | Color Bias | Float | Moves the S Curves bias backward or forward for color interpolation. |
| `colorsteepness` | Color Steepness | Float | Controls the steepness of the S Curve for color interpolation. |
| `colorlinearize` | Color Linearize | Float | Control the amount of curvature in the curve for color interpolation. |
| `liftdirection` | Lift Direction | Menu | If a line is being drawn on a polygon or its edge (the polygon being in another Geometry COMP + shader), and you need to lift it off the surface to be fully visible, this specifies whether to displ... |
| `liftscale` | Lift Scale | Float | For lines that are drawn on top of filled polygons or along their edges, they may be cut off because they are rendered in the same place. To make it look good, you want to lift the line toward the ... |
| `numptsincircle` | Num Points in Circle | Int | When drawing Points in Circle (Polygon) mode, or drawing end-caps, or elbows between edges, this determines how many points you would draw in a full-circle arc to simulate a circular shape. The low... |
| `drawlines` | Draw Lines | Toggle | A toggle to draw the Line polygons. |
| `linejointtype` | Line Joint Type | Menu | A menu to select the joint type where two lines segments meet. |
| `miterthreshold` | Miter Threshold (deg) | Int | Specifies a threshold value in degrees for the Miter joint which alters the joint shape to Bevel joint if the angle between each two lines segments is bigger than this value. |
| `linestartcaptype` | Line Start Cap Type | Menu | A menu to Specify the end cap type at the Line start. You can control the size of each end cap type in the Cap page. |
| `lineendcaptype` | Line End Cap Type | Menu | A menu to Specify the end cap type at the Line end. |
| `lineendtaperstrength` | Line End Taper Strength | Float |  |
| `linenearcolor` | Line Near Color | RGB | Specifies the color value for the Line at the Distance Near plane and any location closer to camera. |
| `linenearalpha` | Line Near Alpha | Float | Specifies the alpha value for the Line at the Distance Near plane and any location closer to camera. |
| `specifylinefarcolor` | Specify Line Far Color | Toggle | A toggle to use the far color and interpolate the values between near and far color. |
| `linefarcolor` | Line Far Color | RGB | Specifies the color value for the Line at the Distance Far plane and beyond (farther from camera). |
| `linefaralpha` | Line Far Alpha | Float | Specifies the alpha value for the Line at the Distance Far plane and beyond (farther from camera). |
| `drawpoints` | Draw Points | Toggle | A toggle to draw the Points. |
| `pointtype` | Point Type | Menu | A menu to select the Point type. |
| `pointsizemultiplier` | Point Size Multiplier | Float | Specifies a scale coefficient to the size of the Point. By default, the point radius size equals to the width at the points location from the camera. |
| `pointnearcolor` | Point Near Color | RGB | Specifies the color value for the Point at the Distance Near plane and any location closer to camera. |
| `pointnearalpha` | Point Near Alpha | Float | Specifies the alpha value for the Point at the Distance Near plane and any location closer to camera. |
| `specifypointfarcolor` | Specify Point Far Color | Toggle | A toggle to use the far color and interpolate the values between near and far color. |
| `pointfarcolor` | Point Far Color | RGB | Specifies the color value for the Point at the Distance Far plane and beyond (farther from camera). |
| `pointfaralpha` | Point Far Alpha | Float | Specifies the alpha value for the Point at the Distance Far plane and beyond (farther from camera). |
| `pointliftdirection` | Point Lift Direction | Menu | A menu to select the the dirction to lift points.  See parameter Lift Direction. |
| `pointliftscale` | Point Lift Scale | Float | see parameter Lift Scale. |
| `drawvectors` | Draw Vectors | Toggle | A toggle to draw the Vectors at each point. |
| `scale` | Scale | Float | A scale value which applies on the length of the Vector. |
| `vectorstartcaptype` | Vector Start Cap Type | Menu | A menu to Specify the end cap type at the Vector start. You can control the size of each end cap type in the Cap page. |
| `vectorendcaptype` | Vector End Cap Type | Menu | A menu to Specify the end cap type at the Vector end. You can control the size of each end cap type in the Cap page. |
| `vectortaperstrength` | Vector Taper Strength | Float | : A coefficient to scale the width of end part of the Vector. |
| `vectornearcolor` | Vector Near Color | RGB | Specifies the color value for the Vector at the Distance Near plane and any location closer to camera. |
| `vectornearalpha` | Vector Near Alpha | Float | Specifies the alpha value for the Vector at the Distance Near plane and any location closer to camera. |
| `specifyvectorfarcolor` | Specify Vector Far Color | Toggle | A toggle to use the far color and interpolate the values between near and far color. |
| `vectorfarcolor` | Vector Far Color | RGB | Specifies the color value for the Vector at the Distance Far plane and beyond (farther from camera). |
| `vectorfaralpha` | Vector Far Alpha | Float | Specifies the alpha value for the Vector at the Distance Far plane and beyond (farther from camera). |
| `roundwidth` | Round Width | Float | Specifies a scale to the width of Round end caps. |
| `roundheight` | Round Height | Float | Specifies a scale to the height of Round end caps. |
| `squarewidth` | Square Width | Float | Specifies a scale to the width of Square end caps. |
| `squareheight` | Square Height | Float | Specifies a scale to the height of Square end caps. |
| `trianglewidth` | Triangle Width | Float | Specifies a scale to the width of Triangle end caps. |
| `triangleheight` | Triangle Height | Float | Specifies a scale to the height of Triangle end caps. |
| `arrowwidth` | Arrow Width | Float | Specifies a scale to the width of Arrow end caps. |
| `arrowheight` | Arrow Height | Float | Specifies a scale to the height (from the base of arrow to the head) of Arrow end caps. |
| `arrowtaillength` | Arrow Tail Length | Float | Specifies a scale to the tail length of Arrow end caps (the longer the tail the sharper it will look like). |
| `endcapwidthmultiplier` | End Cap Width Multiplier | Float | Normally end caps are the same width as the line. This parameter lets you make the cap wider/narrower than the line. |
| `endcapheightmultiplier` | End Cap Height Multiplier | Float | Normally the end caps extend farther than the end of the line by half of the width (making the end cap a half-circle, and similarly for square, triangular and arrow endcape). This parameter lets yo... |
| `startcappullback` | Start Caps Pullback | Float | By default (0), the start cap goes beyond the start point of the line so that the center of a circular startcap is right at the start point. Setting this to 1 makes the tip of the end cap positione... |
| `endcappullback` | End Caps Pullback | Float | By default (0), the end cap goes beyond the end point of the line so that the center of a circular endcap is right at the end point. Setting this to 1 makes the tip of the end cap positioned exactl... |
| `lineposatt` | Line Position Attribute | Str |  |
| `linewidthatt` | Line Width Attribute | Str |  |
| `linecoloratt` | Line Color Attribute | Str |  |
| `pointposatt` | Point Position Attribute | Str |  |
| `pointsizeatt` | Point Size Attribute | Str |  |
| `pointcoloratt` | Point Color Attribute | Str |  |
| `vectoratttype` | Vector Attribute Type | Menu | When drawing a vector at each point, this determines where to get the XYZ of the vector. By default it gets it from an attribute of the SOP, the point normal by default. But when instancing is used... |
| `vectoratt` | Vector Attribute | StrMenu | Specify the geometry Attribute to use to render the Vector. Some standard attribute are: N, P, Cd, uv, however it is possible to specify a custom attribute. Note that this value is case sensitive, ... |
| `vectorcusattribidx` | Vector Instance Custom Attribute Index | Int | When instancing is used, you can get the XYZ vector from an instance attribute. This is the index of the X value in the Instance OP. |
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
| `postmultalpha` | Post-Mult Color by Alpha | Toggle | Multiplies the color by alpha after all other operations have taken place. |
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
# Access the MAT lineMAT operator
linemat_op = op('linemat1')

# Get/set parameters
freq_value = linemat_op.par.active.eval()
linemat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
linemat_op = op('linemat1')
output_op = op('output1')

linemat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(linemat_op)
```

## Technical Details

### Operator Family

**MAT** - Material Operators - Shading and material definitions

### Parameter Count

This operator has **101** documented parameters.

## Navigation

- [Back to MAT Index](../MAT/MAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
