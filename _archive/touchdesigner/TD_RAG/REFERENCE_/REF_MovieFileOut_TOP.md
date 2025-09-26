---
category: REF
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- Movie_File_Out_TOP
- Info_CHOP
- Point_File_In_TOP
- Movie_File_In_TOP
- PreFilterMap_TOP
concepts:
- video_encoding
- image_sequence_export
- file_output
- media_export
- audio_video_muxing
- non-realtime_rendering
- gpu_accelerated_encoding
- point_cloud_export
- codec_selection
prerequisites:
- TOP_basics
- CHOP_basics
- file_path_management
- video_concepts
workflows:
- rendering_final_output
- archiving_generative_content
- creating_video_for_playback
- non-realtime_high_quality_render
- baking_textures
- exporting_data_as_images
- stop_frame_animation
keywords:
- record
- save
- export
- render
- movie
- video
- image sequence
- H.264
- H.265
- HEVC
- Hap
- NotchLC
- ProRes
- Animation
- non-realtime
- audio
- EXR
- point cloud
- NVENC
- codec
- compression
tags:
- gpu
- nvidia
- nvenc
- video
- audio
- export
- file
- codec
- h264
- h265
- hap
- prores
- exr
- png
- jpeg
- non-realtime
- commercial_license
relationships:
  REF_RecordingMoviesWithAudio: strong
  CLASS_ExportMovieDialog: strong
  REF_Hap: strong
  CLASS_MovieFileInTOP: medium
  REF_PixelFormats: medium
  REF_Rendering_Image_Sequences_Tutorial: strong
related_docs:
- CLASS_MovieFileInTOP
- REF_RecordingMoviesWithAudio
- CLASS_ExportMovieDialog
- REF_Hap
- REF_PixelFormats
- REF_Rendering_Image_Sequences_Tutorial
hierarchy:
  secondary: file_io
  tertiary: movie_file_out
question_patterns: []
common_use_cases:
- rendering_final_output
- archiving_generative_content
- creating_video_for_playback
- non-realtime_high_quality_render
---

# Movie File Out TOP

<!-- TD-META
category: REF
document_type: reference
operators: [Movie_File_Out_TOP, Info_CHOP, Point_File_In_TOP, Movie_File_In_TOP, PreFilterMap_TOP]
concepts: [video_encoding, image_sequence_export, file_output, media_export, audio_video_muxing, non-realtime_rendering, gpu_accelerated_encoding, point_cloud_export, codec_selection]
prerequisites: [TOP_basics, CHOP_basics, file_path_management, video_concepts]
workflows: [rendering_final_output, archiving_generative_content, creating_video_for_playback, non-realtime_high_quality_render, baking_textures, exporting_data_as_images, stop_frame_animation]
related: [CLASS_MovieFileInTOP, REF_RecordingMoviesWithAudio, CLASS_ExportMovieDialog, REF_Hap, REF_PixelFormats, REF_Rendering_Image_Sequences_Tutorial]
relationships: {
  "REF_RecordingMoviesWithAudio": "strong",
  "CLASS_ExportMovieDialog": "strong",
  "REF_Hap": "strong",
  "CLASS_MovieFileInTOP": "medium",
  "REF_PixelFormats": "medium",
  "REF_Rendering_Image_Sequences_Tutorial": "strong"
}
hierarchy:
  primary: "tops"
  secondary: "file_io"
  tertiary: "movie_file_out"
keywords: [record, save, export, render, movie, video, image sequence, H.264, H.265, HEVC, Hap, NotchLC, ProRes, Animation, non-realtime, audio, EXR, point cloud, NVENC, codec, compression]
tags: [gpu, nvidia, nvenc, video, audio, export, file, codec, h264, h265, hap, prores, exr, png, jpeg, non-realtime, commercial_license]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical reference for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: rendering_final_output, archiving_generative_content, creating_video_for_playback

## 🔗 Learning Path

**Prerequisites**: [Top Basics] → [Chop Basics] → [File Path Management]
**This document**: REF reference/guide
**Next steps**: [CLASS MovieFileInTOP] → [REF RecordingMoviesWithAudio] → [CLASS ExportMovieDialog]

**Related Topics**: rendering final output, archiving generative content, creating video for playback

## Summary

Reference documentation for Movie File Out TOP operator, covering video encoding, image sequence export, and media export workflows.

## Relationship Justification

Forms performance trio with [PERF_Optimize] and [PERF_Performance_Monitor_Dialog]. Strong connection to [PY_Python_in_Touchdesigner] since it uses Python extensions. Links to [performance_fundamentals] for context.

## Content

- [Introduction](#introduction)
- [Parameters - Movie Out Page](#parameters---movie-out-page)
  - [Type](#type)
  - [Video Codec](#video-codec)
  - [Video Codec Type](#video-codec-type)
  - [Image File Type](#image-file-type)
  - [Unique Suffix](#unique-suffix)
  - [N](#n)
  - [File](#file)
  - [Movie Pixel Format](#movie-pixel-format)
  - [Audio CHOP](#audio-chop)
  - [Audio Codec](#audio-codec)
  - [Audio Bit Rate](#audio-bit-rate)
  - [Quality](#quality)
  - [Movie FPS](#movie-fps)
  - [Limit Length](#limit-length)
  - [Length](#length)
  - [Length Unit](#length-unit)
  - [Record](#record)
  - [Pause](#pause)
  - [Add Frame](#add-frame)
  - [Max Threads](#max-threads)
  - [Header Source DAT](#header-source-dat)
- [Parameters - EXR Page](#parameters---exr-page)
  - [Save as Point Cloud](#save-as-point-cloud)
  - [Additional Input TOP](#additional-input-top)
  - [Red](#red)
  - [Green](#green)
  - [Blue](#blue)
  - [Alpha](#alpha)
  - [TOP](#top)
- [Parameters - Settings Page](#parameters---settings-page)
  - [Stall for File Open](#stall-for-file-open)
  - [Profile](#profile)
  - [Preset](#preset)
  - [Bit Rate Mode](#bit-rate-mode)
  - [Average Bitrate (Kb/s)](#average-bitrate-kbs)
  - [Peak Bitrate (Kb/s)](#peak-bitrate-kbs)
  - [Keyframe Interval](#keyframe-interval)
  - [Max B-Frames](#max-b-frames)
  - [Motion Prediction](#motion-prediction)
  - [Frame Slicing](#frame-slicing)
  - [Num Slices](#num-slices)
  - [Entropy Mode](#entropy-mode)
  - [Secondary Compression](#secondary-compression)
  - [Encode Test Mode](#encode-test-mode)
  - [Include Mip Maps](#include-mip-maps)
- [Parameters - Common Page](#parameters---common-page)
  - [Output Resolution](#output-resolution)
  - [Resolution](#resolution)
  - [Resolution Menu](#resolution-menu)
  - [Use Global Res Multiplier](#use-global-res-multiplier)
  - [Output Aspect](#output-aspect)
  - [Aspect](#aspect)
  - [Aspect Menu](#aspect-menu)
  - [Input Smoothness](#input-smoothness)
  - [Fill Viewer](#fill-viewer)
  - [Viewer Smoothness](#viewer-smoothness)
  - [Passes](#passes)
  - [Channel Mask](#channel-mask)
  - [Pixel Format](#pixel-format)
- [Operator Inputs](#operator-inputs)
- [Info CHOP Channels](#info-chop-channels)
  - [Specific Movie File Out TOP Info Channels](#specific-movie-file-out-top-info-channels)
  - [Common TOP Info Channels](#common-top-info-channels)
  - [Common Operator Info Channels](#common-operator-info-channels)
- [Warnings](#warnings)
- [See Also](#see-also)

## Introduction

The Movie File Out TOP saves a TOP stream out to a movie file (.mov/.mp4) using a variety of codecs, including the H.264/H.265, Hap Q, NotchLC, Apple ProRes and Animation video codecs. It can also save single frame images, image sequences, or stop-frame movies.

For codecs that support Alpha, use the `Movie Pixel Format` parameter to select a format that includes alpha.

The [CLASS_ExportMovieDialog] is a user interface built around the Movie File Out TOP.

To record movies with audio using the Movie File Out TOP, a Time Sliced CHOP with mono or stereo channels of audio is required. If TouchDesigner is running at a lower frame rate than the target video frame rate and a CHOP is specified for audio, the Movie File Out TOP will automatically repeat video frames to ensure the video and audio stay in sync.

Recording a movie without frame drops can be done in non-realtime by turning off the Realtime flag at the top of the user interface. The length of the video is not predetermined and depends on the amount of time the Record parameter is on.

You can record a sequence of .tif or .exr files by setting the `Type` parameter to Image Sequence. When `Image File Type` is set to OpenEXR, the EXR page has options to record any number of color channels from multiple TOPs into an EXR image file, and can create it with metadata that would get read by a [CLASS_PointFileInTOP].

**H264/H265 NOTE:** Encoding movies in H.264/H.265 codec is only available with a Commercial or Pro license. Nvidia graphic hardware is also required.

Recording still images and stop-frame animation can be done by changing the `Type` parameter. Then the `Add Frame` pulse button can be pulsed manually or via a script to cause the frames to be written.

## Parameters - Movie Out Page

### Type

`type` - Output either a movie, image, image sequence, or stop-frame movie.

- `Movie` - Records a movie file.
- `Image` - Records a single image.
- `Image Sequence` - Records a sequence of images.
- `Stop-Frame Movie` - Records stop-frame animation.

### Video Codec

`videocodec` - Select the video compression codec used to encode the movie.

- `Animation` - Run-length encoded video, lossless codec and low decode times, but very large file size. Alpha channel can be included when Pixel Format is RGBA.
- `Photo/Motion JPEG` - JPEG encoded video, lossy codec and low decode times with medium file sizes. Good for playback both forwards and backwards or for random access.
- `MPEG 4 (Part 2)` - High quality but can produce large files size and/or have high decode times.
- `H.264 (NVIDIA GPU)` - H.264 GPU encoding, only available when using Nvidia graphics cards. Great compression and quality and small file sizes. However can suffer from high decode times and not the best for random access, scrubbing, or reverse playback.
- `GoPro-Cineform` - A lossy compression similar to Apple ProRes. Alpha channel can be included.
- `Hap` - See [REF_Hap], a fast codec that uses the GPU. Lower quality than Hap Q.
- `Hap Q` - See [REF_Hap], a fast codec that uses the GPU. Higher quality than regular Hap.
- `H.265/HEVC (NVIDIA GPU)` - H.265 GPU encoding, only available when using Nvidia graphics cards. Better compression (and sometimes quality) than H.264 but more resource intensive to encode/decode.
- `GIF` - An animated .gif file. Because there is no way to specific the color palette currently, a default palette will be used.
- `NotchLC` - NotchLC is a high quality, GPU accelerated video format. It offers higher quality results than HapQ, at the cost of higher GPU usage as well as larger file sizes.
- `VP8` - The open standard VP8 format. Somewhat comparable to H264.
- `VP9` - The open standard VP9 format. Somewhat comparable to HEVC/H265.
- `Apple ProRes` - Apple ProRes video format.

### Video Codec Type

`videocodectype` - Some video codecs such as Apple ProRes, Hap and Hap Q have various different types such as ProRes 442 HQ, ProRes 4444 HQ etc.

### Image File Type

`imagefiletype` - Choose what file type to use when Type is set to Image.

- `TIFF` - A lossless, compressed, image format that includes alpha.
- `JPEG` - A lossy image format, very well compressed. No support for alpha.
- `BMP` - A lossless, uncompressed, image format that includes alpha.
- `OpenEXR` - A lossless, compressed, image format that can save files in 16-bit float and 32-bit float formats. Can also include alpha.
- `PNG` - A lossless, compressed, image format that can include alpha. Supports 8-bit and 16-bit fixed data.
- `DDS` - A lossless, uncompressed, image format that can include alpha. Can include mipmap information. Natively support most pixel formats supported by TOPs.

### Unique Suffix

`uniquesuff` - When enabled, `me.fileSuffix` will be a unique suffix when used in the file parameter.

### N

`n` - N is the index used in `me.fileSuffix`. When unique suffix is enabled, N specifies the starting index to increment from when calculating a unique suffix/name.

### File

`file` - Sets the path and filename of the movie file that is saved out. The filename must include the file extension such as .mov/.mp4 etc. For movies, generally the .mov file extension will work with the most codecs.

### Movie Pixel Format

`moviepixelformat` - Options for the pixel format based on the Video Codec selected. Use this parameter to change the color quality of the output (how many bits are used, YUV sampling etc.), as well as selecting formats that include alpha for codecs that support alpha.

- `YUV 4:2:0` - (Photo/Motion JPEG, MPEG 4 (Part 2))
- `YUV 4:2:0 (8-Bit)` - (H.264 (NVIDIA GPU), H.265/HEVC (NVIDIA GPU))
- `YUV 4:2:0 (10-Bit)` - (H.265/HEVC (NVIDIA GPU))
- `YUV 4:2:2` - (Photo/Motion JPEG)
- `YUV 4:4:4 (8-Bit)` - (H.264 (NVIDIA GPU), H.265/HEVC (NVIDIA GPU))
- `YUV 4:4:4 (10-Bit)` - (H.265/HEVC (NVIDIA GPU))
- `RGB` - (Animation, Hap, Hap Q)
- `RGBA` - (Animation, GoPro-Cineform, Hap, Hap Q)
- `RGBA BC7` - (Hap Q) - Slow, Read Help Before Using!
- `RGB Palette 3` - (GIF)

### Audio CHOP

`audiochop` - Specify a CHOP to use as the audio track for the movie. Drag & Drop a CHOP here or manually enter the CHOP's path. The CHOP needs to be time-sliced.

### Audio Codec

`audiocodec` - Select the audio compression codec used to encode the audio.

- `ALAC (Apple Lossless)` - A lossless audio codec that still offers some compression for the data.
- `MP3` - Highly compressed lossy codec. Can only do 2 channels of audio. MP3 compression will not have gapless playback.
- `Uncompressed 16-bit (PCM)` - Uncompressed audio (Pulse Code Modulation).
- `Uncompressed 24-bit (PCM)` - Uncompressed audio (Pulse Code Modulation).
- `Uncompressed 32-bit (PCM)` - Uncompressed audio (Pulse Code Modulation).
- `Vorbis` - Vorbis is a lossy audio compression codec. Vorbis compression will have gapless playback.

### Audio Bit Rate

`audiobitrate` - The bitrate to write the audio out at.

**Note:** A particular behavior on Windows OS AAC encoder; for 1 and 2 channels the selection of bit rate is for both channels ie. it's 192kb/s for either of them, so either 1x192kb/s or 2x96kb/s. However, when using more than 2 channels the bitrate is per channel ie. for 6 channel then it's 6x192kb/s.

- `96 kb/s`
- `128 kb/s`
- `192 kb/s`
- `256 kb/s`
- `320 kb/s`

### Quality

`quality` - Select the quality of the movie compression. **NOTE:** Some codecs can not output lossless compression.

### Movie FPS

`fps` - The frame rate of the movie file created.

### Limit Length

`limitlength` - This can be used to automatically stop recording the file once it reaches a specified length.

### Length

`length` - The length to stop recording the file at.

### Length Unit

`lengthunit` - The unit the length is specified in.

- `I` - indices
- `F` - frames
- `S` - seconds

### Record

`record` - When this parameter is set to 1, the movie will be recording.

### Pause

`pause` - Pauses the recording.

### Add Frame

`addframe` - Adds a single frame to the output for each click of the button. Pause must be On to enable the Add Frame parameter.

### Max Threads

`maxthread` - When outputting sequences of images, this controls the maximum number of threads can be used to output images (one thread per image). If this is set to 1 then the main thread will be used to write the image.

### Header Source DAT

`headerdat` - The path to a Table DAT that stores header metadata that should be written to the output image or movie file. Header data is written as key-value pairs with the first column storing the keys and the second column storing the associated values. **Note:** Currently only supported for EXR files. **Warning:** Files may fail to save if the header data conflicts with system headers.

## Parameters - EXR Page

The Inputs page can be used to add extra channels of image data to the output file and to change the names of the base 4 channels.

Each `Additional Input TOP` is a path to a TOP containing the image data to add to the file. The associated Red, Green, Blue and Alpha parameters are the names assigned to that input's channels in the new file. If the channel parameter is left blank, that channel will not be added to the output file. Channels with duplicate names will be overwritten.

**Note:** Additional inputs are currently only supported in EXR images and sequences. In EXR files, channels are stored in alphabetical order.

### Save as Point Cloud

`pointcloud` - When enabled, an additional header will be added to the file that indicates the contents are point data rather than images. This header is used to automatically load the file into a [CLASS_PointFileInTOP] rather than a [CLASS_MovieFileInTOP] when dragging and dropping.

### Additional Input TOP

`input` - Sequence of TOPs containing image data to add to the file.

### Red

`input0r` - Name assigned to the specified TOP's Red channel.

### Green

`input0g` - Name assigned to the specified TOP's Green channel.

### Blue

`input0b` - Name assigned to the specified TOP's Blue channel.

### Alpha

`input0a` - Name assigned to the specified TOP's Alpha channel.

### TOP

`input1top` - The path to the TOP used to specify addition channels to the EXR file. The first 4 channels specified above come from the input connected to the Movie File Out TOP, this TOPs RGBA data can be assigned unique names in the EXR file using the Red, Green, Blue, Alpha parameters below.

## Parameters - Settings Page

### Stall for File Open

`stallforopen` - When this is on playback will stall until the file is opened and ready to receive frames, to make sure the frame that was inputted when Record was turned on gets recorded. When this is off recording may start on a later frame, after the file has been opened. Turning this off can avoid a stall in playback, if missing recording some frames at the start is acceptable.

### Profile

`profile` - Select the H.264 profile to use.

- `Auto-Select`
- `Baseline`
- `Main`
- `High`

### Preset

`preset` - The H264 preset to use.

- `None` - Select from the available presets.
- `Lossless`

### Bit Rate Mode

`bitratemode` - Select between Constant or Variable bit rate, and regular or high quality bit rate modes.

- `Constant (CBR)`
- `Variable (VBR)`
- `Constant HQ (CBR)`
- `Variable HQ (VBR)`

### Average Bitrate (Kb/s)

`avgbitrate` - Set the average bitrate target for the encoding.

### Peak Bitrate (Kb/s)

`peakbitrate` - Set the peak bitrate allowed for the encoding.

### Keyframe Interval

`keyframeinterval` - Set the number of frames between key-frames (I-frames) while encoding.

### Max B-Frames

`maxbframes` - Controls the maximum number of B-frames (bi-directional frames) that will be created between pairs of key-frames.

### Motion Prediction

`motionpredict` - Controls the quality of the Motion Prediction used when encoding H264/H265.

- `Default`
- `Quarter`
- `Half`
- `Full`

### Frame Slicing

`frameslicing` - Controls if H264/H265 frames are sliced into multiple pieces, allowing them to be decoded using multiple CPUs more easily.

### Num Slices

`numslices` - The number of slices each frame is split into.

### Entropy Mode

`entropymode` - Controls which entropy mode is used for H265 encoding.

- `Auto-Select`
- `CABAC`
- `CAVLC`

### Secondary Compression

`secondarycompression` - Hap uses a secondary CPU compression stage usually. Encoding video without this compression will result in faster playback, but potentially larger file sizes (which would require faster drives to play back).

### Encode Test Mode

`encodetestmode` - This mode disables file writing, and only does the encoding. This is useful to test the GPU/CPU performance of encoding while taking the SSD speed out of the equation.

### Include Mip Maps

`mipmaps` - When saving out .dds file, mipmaps can be included if this is enabled. This is primarily used for the [CLASS_PreFilterMapTOP], which will encode special information into the mipmap levels of the texture which needs to be maintained.

## Parameters - Common Page

### Output Resolution

`outputresolution` - Quickly change the resolution of the TOP's data.

- `Use Input` - Uses the input's resolution.
- `Eighth` - Multiply the input's resolution by that amount.
- `Quarter` - Multiply the input's resolution by that amount.
- `Half` - Multiply the input's resolution by that amount.
- `2X` - Multiply the input's resolution by that amount.
- `4X` - Multiply the input's resolution by that amount.
- `8X` - Multiply the input's resolution by that amount.
- `Fit Resolution` - Fits the width and height to the resolution given below, while maintaining the aspect ratio.
- `Limit Resolution` - The width and height are limited to the resolution given below. If one of the dimensions exceeds the given resolution, the width and height will be reduced to fit inside the given limits while maintaining the aspect ratio.
- `Custom Resolution` - Enables the Resolution parameter below, giving direct control over width and height.

### Resolution

`resolution` - Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size. The drop down menu on the right provides some commonly used resolutions.

- `W` - Width resolution.
- `H` - Height resolution.

### Resolution Menu

`resmenu` - A drop-down menu with some commonly used resolutions.

### Use Global Res Multiplier

`resmult` - Uses the Global Resolution Multiplier found in Edit>Preferences>TOPs. This multiplies all the TOPs resolutions by the set amount. This is handy when working on computers with different hardware specifications. If a project is designed on a desktop workstation with lots of graphics memory, a user on a laptop with only 64MB VRAM can set the Global Resolution Multiplier to a value of half or quarter so it runs at an acceptable speed. By checking this checkbox on, this TOP is affected by the global multiplier.

### Output Aspect

`outputaspect` - Sets the image aspect ratio allowing any textures to be viewed in any size. Watch for unexpected results when compositing TOPs with different aspect ratios.

- `Use Input` - Uses the input's aspect ratio.
- `Resolution` - Uses the aspect of the image's defined resolution (ie 512x256 would be 2:1), whereby each pixel is square.
- `Custom Aspect` - Lets you explicitly define a custom aspect ratio in the Aspect parameter below.

### Aspect

`aspect` - Use when Output Aspect parameter is set to Custom Aspect.

### Aspect Menu

`armenu` - A drop-down menu with some commonly used aspect ratios.

### Input Smoothness

`inputfiltertype` - This controls pixel filtering on the input image of the TOP.

- `Nearest Pixel` - Uses nearest pixel or accurate image representation. Images will look jaggy when viewing at any zoom level other than Native Resolution.
- `Interpolate Pixels` - Uses linear filtering between pixels. This is how you get TOP images in viewers to look good at various zoom levels, especially useful when using any Fill Viewer setting other than Native Resolution.
- `Mipmap Pixels` - Uses mipmap filtering when scaling images. This can be used to reduce artifacts and sparkling in moving/scaling images that have lots of detail.

### Fill Viewer

`fillmode` - Determine how the TOP image is displayed in the viewer.

**NOTE:** To get an understanding of how TOPs work with images, you will want to set this to Native Resolution as you lay down TOPs when starting out. This will let you see what is actually happening without any automatic viewer resizing.

- `Use Input` - Uses the same Fill Viewer settings as it's input.
- `Fill` - Stretches the image to fit the edges of the viewer.
- `Fit Horizontal` - Stretches image to fit viewer horizontally.
- `Fit Vertical` - Stretches image to fit viewer vertically.
- `Fit Best` - Stretches or squashes image so no part of image is cropped.
- `Fit Outside` - Stretches or squashes image so image fills viewer while constraining it's proportions. This often leads to part of image getting cropped by viewer.
- `Native Resolution` - Displays the native resolution of the image in the viewer.

### Viewer Smoothness

`filtertype` - This controls pixel filtering in the viewers.

- `Nearest Pixel` - Uses nearest pixel or accurate image representation. Images will look jaggy when viewing at any zoom level other than Native Resolution.
- `Interpolate Pixels` - Uses linear filtering between pixels. Use this to get TOP images in viewers to look good at various zoom levels, especially useful when using any Fill Viewer setting other than Native Resolution.
- `Mipmap Pixels` - Uses mipmap filtering when scaling images. This can be used to reduce artifacts and sparkling in moving/scaling images that have lots of detail.

### Passes

`npasses` - Duplicates the operation of the TOP the specified number of times. Making this larger than 1 is essentially the same as taking the output from each pass, and passing it into the first input of the node and repeating the process. Other inputs and parameters remain the same for each pass.

### Channel Mask

`chanmask` - Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default.

### Pixel Format

`format` - Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to [REF_PixelFormats] for more information.

- `Use Input` - Uses the input's pixel format.
- `8-bit fixed (RGBA)` - Uses 8-bit integer values for each channel.
- `sRGB 8-bit fixed (RGBA)` - Uses 8-bit integer values for each channel and stores color in sRGB colorspace.
- `16-bit float (RGBA)` - Uses 16-bits per color channel, 64-bits per pixel.
- `32-bit float (RGBA)` - Uses 32-bits per color channel, 128-bits per pixels.
- `10-bit RGB, 2-bit Alpha, fixed (RGBA)` - Uses 10-bits per color channel and 2-bits for alpha, 32-bits total per pixel.
- `16-bit fixed (RGBA)` - Uses 16-bits per color channel, 64-bits total per pixel.
- `11-bit float (RGB), Positive Values Only` - A RGB floating point format that has 11 bits for the Red and Green channels, and 10-bits for the Blue Channel, 32-bits total per pixel (therefore the same memory usage as 8-bit RGBA). The Alpha channel in this format will always be 1. Values can go above one, but can't be negative.
- `16-bit float (RGB)` - 16-bit float RGB format.
- `32-bit float (RGB)` - 32-bit float RGB format.
- `8-bit fixed (Mono)` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 8-bits per pixel.
- `16-bit fixed (Mono)` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 16-bits per pixel.
- `16-bit float (Mono)` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 16-bits per pixel.
- `32-bit float (Mono)` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 32-bits per pixel.
- `8-bit fixed (RG)` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 8-bits per channel, 16-bits total per pixel.
- `16-bit fixed (RG)` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 16-bits per channel, 32-bits total per pixel.
- `16-bit float (RG)` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 16-bits per channel, 32-bits total per pixel.
- `32-bit float (RG)` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 32-bits per channel, 64-bits total per pixel.
- `8-bit fixed (A)` - An Alpha only format that has 8-bits per channel, 8-bits per pixel.
- `16-bit fixed (A)` - An Alpha only format that has 16-bits per channel, 16-bits per pixel.
- `16-bit float (A)` - An Alpha only format that has 16-bits per channel, 16-bits per pixel.
- `32-bit float (A)` - An Alpha only format that has 32-bits per channel, 32-bits per pixel.
- `8-bit fixed (Mono+Alpha)` - A 2 channel format, one value for RGB and one value for Alpha. 8-bits per channel, 16-bits per pixel.
- `16-bit fixed (Mono+Alpha)` - A 2 channel format, one value for RGB and one value for Alpha. 16-bits per channel, 32-bits per pixel.
- `16-bit float (Mono+Alpha)` - A 2 channel format, one value for RGB and one value for Alpha. 16-bits per channel, 32-bits per pixel.
- `32-bit float (Mono+Alpha)` - A 2 channel format, one value for RGB and one value for Alpha. 32-bits per channel, 64-bits per pixel.

## Operator Inputs

**Input 0:** - The TOP input to be recorded.

## Info CHOP Channels

Extra Information for the Movie File Out TOP can be accessed via an Info CHOP.

### Specific Movie File Out TOP Info Channels

- `last_frames_written` - The number of frames written to the file on the last cook. This may be multiple repeats of the same image if TouchDesigner dropped frames, to ensure time stays in sync.
- `total_frames_written` - The total number of frames written to the file so far.
- `last_audio_samples_written` - The number of audio samples written to the file on the last cook.
- `total_audio_samples_written` - The total number of audio samples written to the file.
- `last_audio_frames_written` - The number of audio frames written to the file on the last cook. This is the samples value, converted to frame units.
- `total_audio_frames_written` - The total number of audio frames written to the file. This is the samples value, converted to frame units.
- `total_frames_dropped` - The number frames that TouchDesigner failed to provide unique images for in the output file. This occurs when TouchDesigner drops frames when the file needed new images.
- `active_records` - When recording sequences of images, they may be written using multiple CPUs at the same time. This tells how many images are currently being recorded.
- `cur_seq_index` - When recording sequences of images, this is the current sequence image index.

### Common TOP Info Channels

- `resx` - Horizontal resolution of the TOP in pixels.
- `resy` - Vertical resolution of the TOP in pixels.
- `aspectx` - Horizontal aspect of the TOP.
- `aspecty` - Vertical aspect of the TOP.
- `depth` - Depth of 2D or 3D array if this TOP contains a 2D or 3D texture array.
- `gpu_memory_used` - Total amount of texture memory used by this TOP.

### Common Operator Info Channels

- `total_cooks` - Number of times the operator has cooked since the process started.
- `cook_time` - Duration of the last cook in milliseconds.
- `cook_frame` - Frame number when this operator was last cooked relative to the component timeline.
- `cook_abs_frame` - Frame number when this operator was last cooked relative to the absolute time.
- `cook_start_time` - Time in milliseconds at which the operator started cooking in the frame it was cooked.
- `cook_end_time` - Time in milliseconds at which the operator finished cooking in the frame it was cooked.
- `cooked_this_frame` - 1 if operator was cooked this frame.
- `warnings` - Number of warnings in this operator if any.
- `errors` - Number of errors in this operator if any.

## Warnings

**WARNING - GPU Driver Timeout on long GPU activities:** Encoding some formats at high-resolution may be a slow, GPU-intensive operation. Generally only the RGBA BC7 mode for HapQ can suffer from this though. Consequently it will usually take longer than the default 2 seconds per frame that Windows gives the GPU driver to complete an operation. If you see a message saying that Windows has reset the GPU driver, this is the issue you are running into. To fix the issue, create this registry value: `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers\TdrDelay`. The value should be of type REG_DWORD. The value is the number of seconds an operation can take before the OS resets the GPU driver. Set it to something larger, like 20-40 (seconds), depending on the resolution you intend to encode. You must reboot your machine for this setting to take effect. If you still get driver resets, make it even larger.

## See Also

See also [CLASS_MovieFileInTOP], [REF_RecordingMoviesWithAudio].
