# COMP - Component Operators - Container and UI components

[← Back to All Operators](../OPERATORS_INDEX.md)

## Overview

Component Operators - Container and UI components in TouchDesigner. This family contains 25 operators.

## All COMP Operators

#### Ambient Light

**Category**: General
**Description**: The Ambient Light Component controls the color and intensity of the environmental light in a given scene.
**Documentation**: [Full Details](./Ambient_Light.md)
**Related**: _To be added_

#### Animation

**Category**: General
**Description**: The Animation Component is a special component used for creating keyframe animation channels. The component contains a pre-defined network utilizing a Keyframe CHOP and a number of Table DATs to define the animated CHOP channels.
**Documentation**: [Full Details](./Animation.md)
**Related**: _To be added_

#### Base

**Category**: General
**Description**: The Base Component has no panel parameters and no 3D object parameters. You would use it for a component that has no panel associated with it, nor any 3D, such as component that converted RGB channels to HSV channels.
**Documentation**: [Full Details](./Base.md)
**Related**: _To be added_

#### Blend

**Category**: General
**Description**: The Blend Component allows various effects such as blended inputs, animating the parents of Components, sequencing, partial transformation inheritance, three-point orientation, and other effects.
**Documentation**: [Full Details](./Blend.md)
**Related**: _To be added_

#### Bone

**Category**: General
**Description**: The Bone Component is the foundation of all of the Character Tools . It is a Component with most of the properties of a Geometry Component .
**Documentation**: [Full Details](./Bone.md)
**Related**: _To be added_

#### Button

**Category**: General
**Description**: The Button Component is used in panels to provide interactive on/off buttons, including toggle buttons, momentary buttons, and sets of radio buttons or exclusive buttons.
**Documentation**: [Full Details](./Button.md)
**Related**: _To be added_

#### Camera

**Category**: General
**Description**: The Camera Component is a 3D object that acts like real-world cameras. You view your scene through it and render from their point of view.
**Documentation**: [Full Details](./Camera.md)
**Related**: _To be added_

#### Camera Blend

**Category**: General
**Description**: The Camera Blend Component allows various effects by blending multiple Components together. It gives you some extra flexibility in setting up parent-child relationships.
**Documentation**: [Full Details](./Camera_Blend.md)
**Related**: _To be added_

#### Container

**Category**: General
**Description**: The Container Component groups together any number of button, slider, field, container and other Panel Components to build an interface.
**Documentation**: [Full Details](./Container.md)
**Related**: _To be added_

#### Engine

**Category**: General
**Description**: The Engine Component runs a .tox file (component) in a separate process.
**Documentation**: [Full Details](./Engine.md)
**Related**: _To be added_

#### Field

**Category**: General
**Description**: The Field Component lets you enter text strings and renders text generated with the Text TOP . Internally it contains a Text TOP which points to one cell of a DAT that contains the text to render.
**Documentation**: [Full Details](./Field.md)
**Related**: _To be added_

#### Geometry

**Category**: General
**Description**: The Geometry Component is a 3D surface that you see and render in TouchDesigner with a Render TOP . Lights, cameras and other Components affect the scene, but are not visible surfaces.
**Documentation**: [Full Details](./Geometry.md)
**Related**: _To be added_

#### Handle

**Category**: General
**Description**: The Handle Component is a new IK tool designed for manipulating groups of bones. Whereas the previous IK tools only allowed for a single end-affector per bone chain, this new method allows for several end-affectors per bone.
**Documentation**: [Full Details](./Handle.md)
**Related**: _To be added_

#### Light

**Category**: General
**Description**: The Light Components are objects which cast light into a 3D scene. With the light parameters you can control the color, brightness, and atmosphere of geometry lit by the light.
**Documentation**: [Full Details](./Light.md)
**Related**: _To be added_

#### List

**Category**: General
**Description**: The List Component lets you create large lists that are highly customizable via the List COMPs initialization and callback functions.
**Documentation**: [Full Details](./List.md)
**Related**: _To be added_

#### Null

**Category**: General
**Description**: The Null Component serves as a place-holder in a scene. It can be used to transform (translate, rotate, scale) Components attached to it.
**Documentation**: [Full Details](./Null.md)
**Related**: _To be added_

#### OP Viewer

**Category**: General
**Description**: The OP Viewer Component allows any operator viewer (CHOP Viewer, SOP Viewer etc) to be part of a panel with full interactivity.
**Documentation**: [Full Details](./OP_Viewer.md)
**Related**: _To be added_

#### Replicator

**Category**: General
**Description**: The Replicator Component creates a node for every row of a table, creating nodes (" replicants ") and deleting them as the table changes.
**Documentation**: [Full Details](./Replicator.md)
**Related**: _To be added_

#### Select

**Category**: General
**Description**: The Select Component selects a Panel Component from any other location. This allows a panel to appear in multiple other panels.
**Documentation**: [Full Details](./Select.md)
**Related**: _To be added_

#### Shared Mem In

**Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem In COMP will read transform data from a shared memory block.
**Documentation**: [Full Details](./Shared_Mem_In.md)
**Related**: _To be added_

#### Shared Mem Out

**Category**: General
**Description**: The Shared Mem In TOP is only available in TouchDesigner Commercial and Pro. The Shared Mem Out COMP will write transform data to a shared memory block.
**Documentation**: [Full Details](./Shared_Mem_Out.md)
**Related**: _To be added_

#### Slider

**Category**: General
**Description**: The Slider Component lets you build sliders in X, Y and XY, and outputs 1 or 2 channels from a Panel CHOP placed in the Slider component.
**Documentation**: [Full Details](./Slider.md)
**Related**: _To be added_

#### Table

**Category**: General
**Description**: The Table Component creates a grid of user interface gadgets.  These panels are laid out in a grid format where the contents of each cell are defined by DAT tables.
**Documentation**: [Full Details](./Table.md)
**Related**: _To be added_

#### Time

**Category**: General
**Description**: The Time Component allows each component to have its own timeline (clock). The Time Component contains a network of operators that can drive a Timeline, drive animations in Animation COMPs, or be used to drive any custom time-based system.
**Documentation**: [Full Details](./Time.md)
**Related**: _To be added_

#### Window

**Category**: General
**Description**: The Window Component allows you to create and maintain a separate floating window displaying the contents of any Panel or any other Node Viewer .
**Documentation**: [Full Details](./Window.md)
**Related**: _To be added_

---

## Quick Stats

- **Total COMP Operators**: 25
- **Family Type**: COMP
- **Documentation**: Each operator has detailed parameter reference

## Navigation

- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation-by-family)

---
_Generated from TouchDesigner summaries.txt_
