# TOP - Texture Operators - Process and manipulate image/texture data

[← Back to All Operators](../OPERATORS_INDEX.md)

## Overview

Texture Operators - Process and manipulate image/texture data in TouchDesigner. This family contains 101 operators.

## All TOP Operators

#### Add

**Category**: General
**Description**: Composites the input images together by adding the pixel values. Output = Input1 + Input2. It clamps a color channel if the sum exceeds 1.
**Documentation**: [Full Details](./Add.md)
**Related**: _To be added_

#### Analyze

**Category**: General
**Description**: Takes any image and determines various characteristics of it, such as the average pixel color, or the pixel with the maximum luminance.
**Documentation**: [Full Details](./Analyze.md)
**Related**: _To be added_

#### Anti Alias

**Category**: General
**Description**: The Anti-Alias TOP uses a screen space antialiasing technique called `SMAA: Enhanced Subpixel Morphological Antialiasing´.
**Documentation**: [Full Details](./Anti_Alias.md)
**Related**: _To be added_

#### Blob Track

**Category**: General
**Description**: Is implemented using source code from OpenCV, much of which was ported to the GPU for faster performance.
**Documentation**: [Full Details](./Blob_Track.md)
**Related**: _To be added_

#### Blur

**Category**: General
**Description**: Blurs the image with various kernel filters and radii. It can do multi-pass blurs and can do horizontal-only or vertical-only blurs.
**Documentation**: [Full Details](./Blur.md)
**Related**: _To be added_

#### CHOP to

**Category**: General
**Description**: Puts CHOP channels into a TOP image. The full 32-bit floating point numbers of a CHOP are converted to 32-bit floating point pixel values by setting the TOP's Pixel Format to 32-bit floats.
**Documentation**: [Full Details](./CHOP_to.md)
**Related**: _To be added_

#### CPlusPlus

**Category**: General
**Description**: Allows you to make custom TOP operators by writing your own .dll using C++. Note : The CPlusPlus TOP is only available in TouchDesigner Commercial and TouchDesigner Pro .
**Documentation**: [Full Details](./CPlusPlus.md)
**Related**: _To be added_

#### CUDA

**Category**: General
**Description**: Runs a CUDA program on a NVIDIA GPU (8000 series and later, full list here ). The use a CUDA TOP, you'll need to write a CUDA DLL .
**Documentation**: [Full Details](./CUDA.md)
**Related**: _To be added_

#### Cache

**Category**: General
**Description**: Stores a sequence of images into GPU memory. These cached images can be read by the graphics card much faster than an image cache in main memory or reading images off disk.
**Documentation**: [Full Details](./Cache.md)
**Related**: _To be added_

#### Cache Select

**Category**: General
**Description**: Grabs an image from a Cache TOP based on the index parameter. This gives direct, random access to any image stored in a Cache TOP.
**Documentation**: [Full Details](./Cache_Select.md)
**Related**: _To be added_

#### Channel Mix

**Category**: General
**Description**: Allows mixing of the input RGBA channels to any other color channel of the output. For example, the pixels in the blue channel of the input can be added to the output's red channel, added or subtracted by the amount in Red parameter's blue column.
**Documentation**: [Full Details](./Channel_Mix.md)
**Related**: _To be added_

#### Chroma Key

**Category**: General
**Description**: Pulls a key matte from the image using Hue, Saturation, and Value settings. If a pixel falls between the Min and Max parameters for all three settings, then it is included in the key.
**Documentation**: [Full Details](./Chroma_Key.md)
**Related**: _To be added_

#### Circle

**Category**: General
**Description**: Can be used to generate circles, ellipses and N-sided polygons. The shapes can be customized with different sizes, rotation and positioning.
**Documentation**: [Full Details](./Circle.md)
**Related**: _To be added_

#### Composite

**Category**: General
**Description**: Is a multi-input TOP that will perform a composite operation for each input. Select the composite operation using the Operation parameter on the Composite parameter page.
**Documentation**: [Full Details](./Composite.md)
**Related**: _To be added_

#### Constant

**Category**: General
**Description**: Sets the red, green, blue, and alpha (r, g, b, and a) channels individually. It is commonly used to create a solid color TOP image.
**Documentation**: [Full Details](./Constant.md)
**Related**: _To be added_

#### Convolve

**Category**: General
**Description**: Uses a DAT table containing numeric coefficients.  For each pixel, it combines its RGBA values and it's neighboring pixels' RGBA values by multiplying the values by the corresponding coefficients in the table, adding the results together.
**Documentation**: [Full Details](./Convolve.md)
**Related**: _To be added_

#### Corner Pin

**Category**: General
**Description**: Can perform two operations. The Extract page lets you specify a sub-section of the image to use by moving 4 points.
**Documentation**: [Full Details](./Corner_Pin.md)
**Related**: _To be added_

#### Crop

**Category**: General
**Description**: Crops an image by defining the position of the left, right, bottom, and top edges of the image. The cropped part of the image is discarded, thus reducing the resolution of the image.
**Documentation**: [Full Details](./Crop.md)
**Related**: _To be added_

#### Cross

**Category**: General
**Description**: Blends between the two input images based on the value of the Cross parameter (refered to as Cross_value below).
**Documentation**: [Full Details](./Cross.md)
**Related**: _To be added_

#### Cube Map

**Category**: General
**Description**: Builds a texture map in the Cube Map internal texture format. It accepts a vertical cross image, or 1 input per side of the cube.
**Documentation**: [Full Details](./Cube_Map.md)
**Related**: _To be added_

#### Depth

**Category**: General
**Description**: Reads an image containing depth information from a scene described in a specified Render TOP . The resulting image is black (0) at pixels where the surface is at the near depth value (Camera's parameter "Near").
**Documentation**: [Full Details](./Depth.md)
**Related**: _To be added_

#### Difference

**Category**: General
**Description**: Performs a difference composite on its two input images.
**Documentation**: [Full Details](./Difference.md)
**Related**: _To be added_

#### DirectX In

**Category**: General
**Description**: Brings DirectX textures from other applications into TouchDesigner.  This feature is only available on Windows 7 or greater, accessed through the DirectX Sharing Resources feature.
**Documentation**: [Full Details](./DirectX_In.md)
**Related**: _To be added_

#### DirectX Out

**Category**: General
**Description**: Creates textures that a DirectX application can access, or any instance of TouchDesigner with a DirectX In TOP.
**Documentation**: [Full Details](./DirectX_Out.md)
**Related**: _To be added_

#### Displace

**Category**: General
**Description**: Will cause one image to be warped by another image. A pixel of the output image at (Uo,Vo) gets its RGBA value from a different pixel (Ui, Vi) of the Source Image by using the second input image (the Displace Image).
**Documentation**: [Full Details](./Displace.md)
**Related**: _To be added_

#### Edge

**Category**: General
**Description**: Finds edges in an image and highlights them. For each pixel, it looks at the values at neighboring pixels, and where differences are greater than a threshold, the output's value is higher.
**Documentation**: [Full Details](./Edge.md)
**Related**: _To be added_

#### Emboss

**Category**: General
**Description**: Creates the effect that an image is embossed in a thin sheet of metal. Edges in the image will appear raised.
**Documentation**: [Full Details](./Emboss.md)
**Related**: _To be added_

#### Feedback

**Category**: General
**Description**: Can be used to create feedback effects in TOPs. The Feedback TOP's input image will be passed through whenever Feedback is bypassed (by setting the Bypass Feedback parameter = 1).
**Documentation**: [Full Details](./Feedback.md)
**Related**: _To be added_

#### Fit

**Category**: General
**Description**: Re-sizes its input to the resolution set on the Common Page using the method specified in the Fit parameter menu.
**Documentation**: [Full Details](./Fit.md)
**Related**: _To be added_

#### Flip

**Category**: General
**Description**: Will Flip an image in X and/or Y. It also offers a Flop option to turn each row of pixels into a column.
**Documentation**: [Full Details](./Flip.md)
**Related**: _To be added_

#### GLSL

**Category**: General
**Description**: Renders a GLSL shader into a TOP image. Use the Info DAT to check for compile errors in your shaders.
**Documentation**: [Full Details](./GLSL.md)
**Related**: _To be added_

#### GLSL Multi

**Category**: General
**Description**: Renders a GLSL shader into a TOP image. Its parameters and functionality are identical to the.
**Documentation**: [Full Details](./GLSL_Multi.md)
**Related**: _To be added_

#### HSV Adjust

**Category**: General
**Description**: Adjust color values using hue, saturation, and value controls. If you change the Hue Offset, Saturation Multiplier and Value Multiplier without changing any of the other parameters then you will modify the color of all pixels in the image.
**Documentation**: [Full Details](./HSV_Adjust.md)
**Related**: _To be added_

#### HSV to RGB

**Category**: General
**Description**: Converts an image from HSV color channels to RGB color channels.
**Documentation**: [Full Details](./HSV_to_RGB.md)
**Related**: _To be added_

#### In

**Category**: General
**Description**: Is used to create a TOP input in a Component. Component inputs are positioned alphanumerically on the left side of the Component.
**Documentation**: [Full Details](./In.md)
**Related**: _To be added_

#### Inside

**Category**: General
**Description**: Places Input1 'inside' Input2. The alpha of Input2 is used to determine what parts of the Input1 image are visible.
**Documentation**: [Full Details](./Inside.md)
**Related**: _To be added_

#### Kinect

**Category**: General
**Description**: Captures video from the Kinect depth camera or RGB color camera. NOTE: This TOP works with the Kinect for Windows hardware and supports the Kinect2.
**Documentation**: [Full Details](./Kinect.md)
**Related**: _To be added_

#### Leap Motion

**Category**: General
**Description**: Gets the image from the Leap Motion Controller's cameras.  To enable this feature the option Allow Images must be turned on in the Leap Motion Control Panel.
**Documentation**: [Full Details](./Leap_Motion.md)
**Related**: _To be added_

#### Level

**Category**: General
**Description**: Adjusts image contrast, brightness, gamma, black level, color range, quantization, opacity and more.
**Documentation**: [Full Details](./Level.md)
**Related**: _To be added_

#### Lookup

**Category**: General
**Description**: Replaces color values in the TOP image connected to its first input with values derived from a lookup table created from its second intput or a lookup table created using the CHOP parameter.
**Documentation**: [Full Details](./Lookup.md)
**Related**: _To be added_

#### Luma Blur

**Category**: General
**Description**: Blurs image on a per-pixel basis depending on the luminance or greyscale value of its second input. The image is blurred with separate parameters for white and black filter sizes, which correspond to the white and black luminance values of the second input.
**Documentation**: [Full Details](./Luma_Blur.md)
**Related**: _To be added_

#### Luma Level

**Category**: General
**Description**: Adjusts image brightness, gamma, black level, quantization, opacity and more. It has similar parameters to the Level TOP, but it maintains the hue and saturation more accurately when you use Gamma and Black Level.
**Documentation**: [Full Details](./Luma_Level.md)
**Related**: _To be added_

#### Math

**Category**: General
**Description**: Performs specific mathematical operations on the pixels of the input image.
**Documentation**: [Full Details](./Math.md)
**Related**: _To be added_

#### Matte

**Category**: General
**Description**: Composites input1 over input2 using the alpha channel of input3 as a matte. White (one) pixels in input3's alpha channel will draw input1 over input2, black (or zero) will make input1 transparent, leaving the input2 image at that pixel.
**Documentation**: [Full Details](./Matte.md)
**Related**: _To be added_

#### Monochrome

**Category**: General
**Description**: Changes an image to greyscale colors. You can choose from a number of different methods to convert the image to greyscale using the RGB and Alpha menus.
**Documentation**: [Full Details](./Monochrome.md)
**Related**: _To be added_

#### Movie File In

**Category**: General
**Description**: Loads movies, still images, or a sequence of still images into TOPs. It will read images in .jpg, .gif, .
**Documentation**: [Full Details](./Movie_File_In.md)
**Related**: _To be added_

#### Movie File Out

**Category**: General
**Description**: Saves a TOP stream out to a QuickTime or MP4 ( .mp4 ) movie in a variety of formats, plus the Animation, Cineform and Hap Q video codecs.
**Documentation**: [Full Details](./Movie_File_Out.md)
**Related**: _To be added_

#### Multiply

**Category**: General
**Description**: Performs a multiply operation on Input1 and Input2.
**Documentation**: [Full Details](./Multiply.md)
**Related**: _To be added_

#### Noise

**Category**: General
**Description**: Generates a variety of noise patterns including sparse, alligator and random. It currently runs on the CPU and passes its images to the GPU.
**Documentation**: [Full Details](./Noise.md)
**Related**: _To be added_

#### Normal Map

**Category**: General
**Description**: Takes an input image and creates a normal map by finding edges in the image. This can then be used for bump mapping (See Phong MAT ).
**Documentation**: [Full Details](./Normal_Map.md)
**Related**: _To be added_

#### Null

**Category**: General
**Description**: Has no effect on the image. It is an instance of the TOP connected to its input. The Null TOP is often used when making reference to a TOP network, allowing new TOPs to be added to the network (upstream) without the need to update the reference.
**Documentation**: [Full Details](./Null.md)
**Related**: _To be added_

#### OP Viewer

**Category**: General
**Description**: Can display the Node Viewer for any other operator as a TOP image. If the operator source is a Panel Component, panel interaction through the TOP image is also supported.
**Documentation**: [Full Details](./OP_Viewer.md)
**Related**: _To be added_

#### Oculus Rift

**Category**: General
**Description**: Note - The Oculus SDK has changed a lot over since the DK1. The original DK1 used the Oculus Rift TOP to do the barrel distortion.
**Documentation**: [Full Details](./Oculus_Rift.md)
**Related**: _To be added_

#### Out

**Category**: General
**Description**: Is used to create a TOP output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.
**Documentation**: [Full Details](./Out.md)
**Related**: _To be added_

#### Outside

**Category**: General
**Description**: Places Input1 'outside' Input2. Input1 is visible in the output wherever Input2's alpha is <1. This is the opposite operation to the Inside TOP.
**Documentation**: [Full Details](./Outside.md)
**Related**: _To be added_

#### Over

**Category**: General
**Description**: Places Input1 'over' Input2. The alpha of Input1 is used to determine what parts of the Input2 image are visible in the result.
**Documentation**: [Full Details](./Over.md)
**Related**: _To be added_

#### Pack

**Category**: General
**Description**: Note: Only in builds 48000 or later.
**Documentation**: [Full Details](./Pack.md)
**Related**: _To be added_

#### Photoshop In

**Category**: General
**Description**: Can stream the output from Photoshop CS6 into TouchDesigner.  Photoshop can be running on the same computer as TouchDesigner or any other computer on the network.
**Documentation**: [Full Details](./Photoshop_In.md)
**Related**: _To be added_

#### Point File In

**Category**: General
**Description**: Loads 3D point data into TOPs from either a single file or a sequence of files. Points are composed of one or more floating point values such as XYZ positions, RGB color values, 3D normals, scanner intensity, etc. Supports OBJ, PLY, EXR, PTS, and more.
**Documentation**: [Full Details](./Point_File_In.md)
**Related**: _To be added_

#### Point File Select

**Category**: General
**Description**: Creates additional output images from a point file loaded into a Point File In TOP. Useful when the point data file has more than 4 channels e.g. XYZ position and RGB colors.
**Documentation**: [Full Details](./Point_File_Select.md)
**Related**: _To be added_

#### Point Transform

**Category**: General
**Description**: Treats the RGB values of the input image as a point cloud of XYZ positions or vectors and performs 3D transformations and alignments.
**Documentation**: [Full Details](./Point_Transform.md)
**Related**: _To be added_

#### Projection

**Category**: General
**Description**: Takes a Cube Map created with a Render TOP and converts that to a fisheye projection suitable for domes, and a "equirectangular" projection, where u-v is latitude-longitude, suitable for spheres.
**Documentation**: [Full Details](./Projection.md)
**Related**: _To be added_

#### RGB Key

**Category**: General
**Description**: Pulls a key from the image using Red, Green, and Blue channel settings. If a pixel falls between the Min and Max parameters for all three settings, then it is included in the key.
**Documentation**: [Full Details](./RGB_Key.md)
**Related**: _To be added_

#### RGB to HSV

**Category**: General
**Description**: The RGV to HSV TOP converts the image from RGB to HSV colorspace. The R channel becomes Hue, the G channel becomes Saturation, and the B channel becomes Value.
**Documentation**: [Full Details](./RGB_to_HSV.md)
**Related**: _To be added_

#### Ramp

**Category**: General
**Description**: Allows you to interactively create vertical, horizontal, radial, and circular ramps. Using the ramp bar and the color picker, you can add as many color tabs to the ramp as you like, each with its own color and alpha values.
**Documentation**: [Full Details](./Ramp.md)
**Related**: _To be added_

#### RealSense

**Category**: General
**Description**: Connects to RealSense devices and outputs color, depth and IR data from it. See also RealSense CHOP.
**Documentation**: [Full Details](./RealSense.md)
**Related**: _To be added_

#### Rectangle

**Category**: General
**Description**: Can be used to generate Rectangles with rounded corners. The shapes can be customized with different sizes, rotation and positioning.
**Documentation**: [Full Details](./Rectangle.md)
**Related**: _To be added_

#### Remap

**Category**: General
**Description**: Uses the second input to warp the first input. For every pixel of the output, it uses the red channel and green channel of the second input to choose which pixel to pick from the first input.
**Documentation**: [Full Details](./Remap.md)
**Related**: _To be added_

#### Render

**Category**: General
**Description**: Is used to render all 3D scenes in TouchDesigner. You need to give it a Camera object and a Geometry object as a minimum.
**Documentation**: [Full Details](./Render.md)
**Related**: _To be added_

#### Render Pass

**Category**: General
**Description**: Is used along with a Render TOP to achieve multipass rendering. It can build upon its inputs render by using the existing depth/color information in the framebuffers, or it can optionally clear one or both of the depth/color buffers before it does its render.
**Documentation**: [Full Details](./Render_Pass.md)
**Related**: _To be added_

#### Render Select

**Category**: General
**Description**: Allows you to select one of the color buffers from any Render TOP .
**Documentation**: [Full Details](./Render_Select.md)
**Related**: _To be added_

#### Reorder

**Category**: General
**Description**: Is a multi-input TOP which lets you choose any of the input channels for the R, G, B, and A output. It also gives the option of outputting one, zero or the input luminance to any of the output channels.
**Documentation**: [Full Details](./Reorder.md)
**Related**: _To be added_

#### Resolution

**Category**: General
**Description**: Changes the resolution of the TOP image. This can also be done on the Common page of most other TOPs.
**Documentation**: [Full Details](./Resolution.md)
**Related**: _To be added_

#### SDI In

**Category**: General
**Description**: Is a TouchDesigner Pro only operator. The SDI In TOP uses NVIDIA's SDI Capture Card to capture video frames directly into GPU memory.
**Documentation**: [Full Details](./SDI_In.md)
**Related**: _To be added_

#### SDI Out

**Category**: General
**Description**: Is a TouchDesigner Pro only operator. The SDI Out TOP uses Nvidia's SDI Output card to output video frames directly to the output card, avoid any issues involved with Windows such as vsync, desktop tearing etc.
**Documentation**: [Full Details](./SDI_Out.md)
**Related**: _To be added_

#### SDI Select

**Category**: General
**Description**: The SDI In TOP is a TouchDesigner Pro only operator. The SDI Select TOP is used to select video from the 2-4 inputs in the SDI In TOP on the Nvidia SDI Capture card.
**Documentation**: [Full Details](./SDI_Select.md)
**Related**: _To be added_

#### SSAO

**Category**: General
**Description**: Performs Screen Space Ambient Occlusion on the output of a Render TOP or Render Pass TOP . Because this technique requires access to the Depth Buffer, no other TOP can be in between the Render/RenderPass TOP and the SSAO TOP.
**Documentation**: [Full Details](./SSAO.md)
**Related**: _To be added_

#### Scalable Display

**Category**: General
**Description**: Lets you load calibration data retrieved from running the Scalable Display Calibration Software . Please refer to How-to calibrate your projector with Scalable Displays for a complete guide on TouchDesigners integration of the Scalable Displays SDK.
**Documentation**: [Full Details](./Scalable_Display.md)
**Related**: _To be added_

#### Screen

**Category**: General
**Description**: Brightens the underlying layers depending on how bright the screened layer's pixels are. If the screened pixel is black, it will look completely transparent.
**Documentation**: [Full Details](./Screen.md)
**Related**: _To be added_

#### Screen Grab

**Category**: General
**Description**: Turns the main screen output into a TOP image. It can be captured in real-time while you work.
**Documentation**: [Full Details](./Screen_Grab.md)
**Related**: _To be added_

#### Select

**Category**: General
**Description**: Allows you to reference a TOP from any other location in TouchDesigner. To save graphics memory, the Select TOP creates an instance of the TOP references.
**Documentation**: [Full Details](./Select.md)
**Related**: _To be added_

#### Shared Mem In

**Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem In TOP will read image data from a shared memory block.
**Documentation**: [Full Details](./Shared_Mem_In.md)
**Related**: _To be added_

#### Shared Mem Out

**Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem Out TOP will write image data out to a shared memory block for use by other TouchDesigner processes or other 3rd party applications.
**Documentation**: [Full Details](./Shared_Mem_Out.md)
**Related**: _To be added_

#### Slope

**Category**: General
**Description**: Generates pixels that represent the difference between its value and its neighbouring pixels' values.
**Documentation**: [Full Details](./Slope.md)
**Related**: _To be added_

#### Spout In

**Category**: General
**Description**: Will obtain its texture image via shared memory from other applications that support the Spout framework .
**Documentation**: [Full Details](./Spout_In.md)
**Related**: _To be added_

#### Spout Out

**Category**: General
**Description**: Will share its input texture with other applications that support the Spout framework . You can download a Spout setup package at <http://spout>.
**Documentation**: [Full Details](./Spout_Out.md)
**Related**: _To be added_

#### Subtract

**Category**: General
**Description**: Composites the input images together by subtracting the pixel values. Output = Input1 - Input2. The pixel values below 0 are clammped to 0.
**Documentation**: [Full Details](./Subtract.md)
**Related**: _To be added_

#### Switch

**Category**: General
**Description**: Is a multi-input operator which lets you switch which input is passed through using the Input parameter.
**Documentation**: [Full Details](./Switch.md)
**Related**: _To be added_

#### Text

**Category**: General
**Description**: Displays text strings in an image. It allows for multiple fonts, sizes, colors, borders, character separation and line separation.
**Documentation**: [Full Details](./Text.md)
**Related**: _To be added_

#### Texture 3D

**Category**: General
**Description**: Creates a 3D texture map. It saves a series of images in one array of pixels. This TOP can be used with Time Machine TOP, as well as materials.
**Documentation**: [Full Details](./Texture_3D.md)
**Related**: _To be added_

#### Threshold

**Category**: General
**Description**: Creates a matte with pixel values set to 0 for pixels below the threshold value, and 1 for pixels greater than or equal to the threshold value.
**Documentation**: [Full Details](./Threshold.md)
**Related**: _To be added_

#### Tile

**Category**: General
**Description**: Tiles images in a repeating pattern. It also has a Crop option which crops an image by defining the position of the left, right, bottom, and top edges of the image.
**Documentation**: [Full Details](./Tile.md)
**Related**: _To be added_

#### Time Machine

**Category**: General
**Description**: Combines pixels in a sequence of images stored in a Texture 3D TOP . Whereas "morphing" warps an image "spatially" (in xy), Time Machine warps images only in time.
**Documentation**: [Full Details](./Time_Machine.md)
**Related**: _To be added_

#### Touch In

**Category**: General
**Description**: Will read in image data send over a TCP/IP network connection from a Touch Out TOP . The other TouchDesigner process can be on the same computer or from another computer anywhere on the connected network.
**Documentation**: [Full Details](./Touch_In.md)
**Related**: _To be added_

#### Touch Out

**Category**: General
**Description**: Sends a TOP image stream over TCP/IP to a Touch In TOP. The Touch In TOP can be in another TouchDesigner session on the same computer or on a computer anywhere on the connected network.
**Documentation**: [Full Details](./Touch_Out.md)
**Related**: _To be added_

#### Transform

**Category**: General
**Description**: Applies 2D transformations to a TOP image like translate, scale, rotate, and multi-repeat tiling. The background can be filled with solid color and alpha.
**Documentation**: [Full Details](./Transform.md)
**Related**: _To be added_

#### Under

**Category**: General
**Description**: Places Input1 'under' Input2. The alpha of Input2 is used to determine what parts of the Input1 image are visible in the result.
**Documentation**: [Full Details](./Under.md)
**Related**: _To be added_

#### Video Device In

**Category**: General
**Description**: Can be used to capture video from an external camera, capture card, or DV decoder connected to the system.
**Documentation**: [Full Details](./Video_Device_In.md)
**Related**: _To be added_

#### Video Device Out

**Category**: General
**Description**: Routes video to output devices using their native driver libraries. Devices currently supported: Blackmagic Design devices The Video Device Out TOP is only available in Commercial and Pro .
**Documentation**: [Full Details](./Video_Device_Out.md)
**Related**: _To be added_

#### Video Stream In

**Category**: General
**Description**: Creates an RTSP client to receive video and audio across the network.  The URL to connect to the RTSP server is in the form: rtsp://<ipaddress>:<port>/<streamName> e.
**Documentation**: [Full Details](./Video_Stream_In.md)
**Related**: _To be added_

#### Video Stream Out

**Category**: General
**Description**: Creates an RTSP server to send H.264 video and MP3 audio across the network. It uses Nvidia's hardware H264 encoder to achieve low-latency encoding.
**Documentation**: [Full Details](./Video_Stream_Out.md)
**Related**: _To be added_

---

## Quick Stats

- **Total TOP Operators**: 101
- **Family Type**: TOP
- **Documentation**: Each operator has detailed parameter reference

## Navigation

- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation-by-family)

---
_Generated from TouchDesigner summaries.txt_
