# SOP - Surface Operators - Process and manipulate 3D geometry

[← Back to All Operators](../OPERATORS_INDEX.md)

## Overview

Surface Operators - Process and manipulate 3D geometry in TouchDesigner. This family contains 102 operators.

## All SOP Operators

#### Add

**Category**: General
**Description**: Can both create new Points and Polygons on its own, or it can be used to add Points and Polygons to an existing input.
**Documentation**: [Full Details](./Add.md)
**Related**: _To be added_

#### Align

**Category**: General
**Description**: Aligns a group of primitives to each other or to an auxiliary input, by translating or rotating each primitive along any pivot point.
**Documentation**: [Full Details](./Align.md)
**Related**: _To be added_

#### Arm

**Category**: General
**Description**: Creates all the necessary geometry for an arm, and provides a smooth, untwisted skin that connects the arm to the body.
**Documentation**: [Full Details](./Arm.md)
**Related**: _To be added_

#### Attribute

**Category**: General
**Description**: Allows you to manually rename and delete point and primitive attributes.
**Documentation**: [Full Details](./Attribute.md)
**Related**: _To be added_

#### Attribute Create

**Category**: General
**Description**: Allows you to add normals or tangents to geometry.
**Documentation**: [Full Details](./Attribute_Create.md)
**Related**: _To be added_

#### Basis

**Category**: General
**Description**: Provides a set of operations applicable to the parametric space of spline curves and surfaces. The parametric space, also known as the "domain" of a NURBS or Bzier primitive, is defined by one basis in the U direction and, if the primitive is a surface, another basis in the V direction.
**Documentation**: [Full Details](./Basis.md)
**Related**: _To be added_

#### Blend

**Category**: General
**Description**: Provides 3D metamorphosis between shapes with the same topology. It can blend between sixteen input SOPs using the average weight of each input's respective channel.
**Documentation**: [Full Details](./Blend.md)
**Related**: _To be added_

#### Bone Group

**Category**: General
**Description**: Groups primitives by common bones (shared bones). For more information regarding using Bone Groups for deforming geometry, see this article: Deforming_Geometry_(Skinning) .
**Documentation**: [Full Details](./Bone_Group.md)
**Related**: _To be added_

#### Boolean

**Category**: General
**Description**: Takes two closed polygonal sets, A and B. Set these Sources to the SOPs with the 3D shapes that you wish to operate on.
**Documentation**: [Full Details](./Boolean.md)
**Related**: _To be added_

#### Box

**Category**: General
**Description**: Creates cuboids. These can be used as geometries by themselves, or they can be sub-divided for use with the Lattice SOP.
**Documentation**: [Full Details](./Box.md)
**Related**: _To be added_

#### Bridge

**Category**: General
**Description**: Is useful for skinning trimmed surfaces, holes, creating highly controllable joins between arms and body, branches or tube intersections.
**Documentation**: [Full Details](./Bridge.md)
**Related**: _To be added_

#### CHOP to

**Category**: General
**Description**: Takes CHOP channels and generates 3D polygons in a SOP. It reads sample data from a CHOP and converts it into point positions and point attributes.
**Documentation**: [Full Details](./CHOP_to.md)
**Related**: _To be added_

#### Cache

**Category**: General
**Description**: Collects its input geometry in a cache for faster random-access playback of multiple SOPs. It should be used when cook times for a chain of SOP s is long and a quicker playback is needed.
**Documentation**: [Full Details](./Cache.md)
**Related**: _To be added_

#### Cap

**Category**: General
**Description**: Is used to close open areas with flat or rounded coverings. Meshes are capped by extending the mesh in either the U or V direction (e.
**Documentation**: [Full Details](./Cap.md)
**Related**: _To be added_

#### Capture

**Category**: General
**Description**: Is used to weight points in a geometry to capture regions. The weighting scheme is described in the next section, Capture Region SOP .
**Documentation**: [Full Details](./Capture.md)
**Related**: _To be added_

#### Capture Region

**Category**: General
**Description**: Defines capture region (cregion), which is a type of primitive which can be thought of as a modified tube primitive (a tube with half a sphere on either end).
**Documentation**: [Full Details](./Capture_Region.md)
**Related**: _To be added_

#### Carve

**Category**: General
**Description**: Works with any face or surface type, be that polygon, Bzier, or NURBS. It can be used to slice a primitive, cut it into multiple sections, or extract points or cross-sections from it.
**Documentation**: [Full Details](./Carve.md)
**Related**: _To be added_

#### Circle

**Category**: General
**Description**: Creates open or closed arcs, circles and ellipses. If two NURBS circles that are non-rational (i.e. their X and Y radii are unequal) are skinned, more isoparms may be generated than expected.
**Documentation**: [Full Details](./Circle.md)
**Related**: _To be added_

#### Clay

**Category**: General
**Description**: Deforms faces and surfaces by pulling points that lie directly on them. As opposed to the Point SOP or other SOPs that manipulate control points (CVs), the Clay SOP operates on the primitive contours themselves, providing a direct, intuitive, and unconstrained way of reshaping geometry.
**Documentation**: [Full Details](./Clay.md)
**Related**: _To be added_

#### Clip

**Category**: General
**Description**: Cuts and creases source geometry with a plane.
**Documentation**: [Full Details](./Clip.md)
**Related**: _To be added_

#### Convert

**Category**: General
**Description**: Converts geometry from one geometry type to another type. Types include polygon, mesh, Bezier patche, particle and sphere primitive.
**Documentation**: [Full Details](./Convert.md)
**Related**: _To be added_

#### Copy

**Category**: General
**Description**: Lets you make copies of the geometry of other SOPs and apply a transformation to each copy. It also allows you to copy geometry to points on an input template.
**Documentation**: [Full Details](./Copy.md)
**Related**: _To be added_

#### Creep

**Category**: General
**Description**: Lets you deform and animate Source Input geometry along the surface of the PathInput geometry.
**Documentation**: [Full Details](./Creep.md)
**Related**: _To be added_

#### Curveclay

**Category**: General
**Description**: Is similar to the Clay SOP in that you deform a spline surface not by modifying the CVs but by directly manipulating the surface.
**Documentation**: [Full Details](./Curveclay.md)
**Related**: _To be added_

#### Curvesect

**Category**: General
**Description**: Finds the intersections or the points of minimum distance between two or more faces (polygons, Bziers, and NURBS curves) or between faces and a polygonal or spline surface.
**Documentation**: [Full Details](./Curvesect.md)
**Related**: _To be added_

#### DAT to

**Category**: General
**Description**: Can be used to create geometry from DAT tables, or if a SOP input is specified, to modify attributes on existing geometry.
**Documentation**: [Full Details](./DAT_to.md)
**Related**: _To be added_

#### Deform

**Category**: General
**Description**: Takes geometry along with point weights (assigned by the Capture SOP ) and deforms geometry as Capture Regions are moved.
**Documentation**: [Full Details](./Deform.md)
**Related**: _To be added_

#### Delete

**Category**: General
**Description**: Deletes input geometry as selected by a group specification or a geometry selection by using either of the three selection options: by entity number, by a bounding volume, and by entity (primitive/point) normals.
**Documentation**: [Full Details](./Delete.md)
**Related**: _To be added_

#### Divide

**Category**: General
**Description**: Divides incoming polygonal geometry. It will smooth input polygons, dividing polygons, as well as sub-divide input polygons using the Bricker option.
**Documentation**: [Full Details](./Divide.md)
**Related**: _To be added_

#### Extrude

**Category**: General
**Description**: Can be used for: Extruding and bevelling Text and other geometry Cusping the bevelled edges to get sharp edges Making primitives thicker or thinner In order to do so, it uses the normal of the surface to determine the direction of extrusion.
**Documentation**: [Full Details](./Extrude.md)
**Related**: _To be added_

#### Facet

**Category**: General
**Description**: Lets you control the smoothness of faceting of a given object. It also lets you consolidate points or surface normals.
**Documentation**: [Full Details](./Facet.md)
**Related**: _To be added_

#### File In

**Category**: General
**Description**: Allows you to read a geometry file that may have been previously created in the Model Editor, output geometry from a SOP, or generated from other software such as Houdini .
**Documentation**: [Full Details](./File_In.md)
**Related**: _To be added_

#### Fillet

**Category**: General
**Description**: Is used to create smooth bridging geometry between two curves / polygons or two surfaces / meshes. Filleting creates a new primitive between each input pair and never affects the original shapes.
**Documentation**: [Full Details](./Fillet.md)
**Related**: _To be added_

#### Fit

**Category**: General
**Description**: Fits a Spline curve to a sequence of points or a Spline surface to an m X n mesh of points. Any type of face or surface represents a valid input.
**Documentation**: [Full Details](./Fit.md)
**Related**: _To be added_

#### Font

**Category**: General
**Description**: Allows you to create text in your model from Adobe Type 1 Postscript Fonts. To install fonts, copy the font files to the $TFS/touch/fonts directory of your installation path.
**Documentation**: [Full Details](./Font.md)
**Related**: _To be added_

#### Force

**Category**: General
**Description**: Adds force attributes to the input metaball field that is used by either Particle SOP or Spring SOP as attractor or repulsion force fields.
**Documentation**: [Full Details](./Force.md)
**Related**: _To be added_

#### Fractal

**Category**: General
**Description**: Allows you created jagged mountain-like divisions of the input geometry. It will create random-looking deviations and sub-divisions along either a specified normal vector (the Direction xyz fields) or the vertex normals of the input geometry.
**Documentation**: [Full Details](./Fractal.md)
**Related**: _To be added_

#### Grid

**Category**: General
**Description**: Allows you to create grids and rectangles using polygons, a mesh, Bzier and NURBS surfaces, or multiple lines using open polygons.
**Documentation**: [Full Details](./Grid.md)
**Related**: _To be added_

#### Group

**Category**: General
**Description**: Generates groups of points or primitives according to various criteria and allows you to act upon these groups.
**Documentation**: [Full Details](./Group.md)
**Related**: _To be added_

#### Hole

**Category**: General
**Description**: Is for making holes where faces are enclosed, even if they are not in the same plane. It can also remove existing holes from the input geometry.
**Documentation**: [Full Details](./Hole.md)
**Related**: _To be added_

#### In

**Category**: General
**Description**: Creates a SOP input in a Component. Component inputs are positioned alphanumerically on the left side of the node.
**Documentation**: [Full Details](./In.md)
**Related**: _To be added_

#### Inverse Curve

**Category**: General
**Description**: Takes data from an Inverse Curve CHOP and builds a curve from it.
**Documentation**: [Full Details](./Inverse_Curve.md)
**Related**: _To be added_

#### Iso Surface

**Category**: General
**Description**: Uses implicit functions to create 3D visualizations of isometric surfaces found in Grade 12 Functions and Relations textbooks.
**Documentation**: [Full Details](./Iso_Surface.md)
**Related**: _To be added_

#### Join

**Category**: General
**Description**: Connects a sequence of faces or surfaces into a single primitive that inherits their attributes. Faces of different types can be joined together, and so can surfaces.
**Documentation**: [Full Details](./Join.md)
**Related**: _To be added_

#### Joint

**Category**: General
**Description**: Will aid in the creation of circle-based skeletons by creating a series of circles between each pair of input circles.
**Documentation**: [Full Details](./Joint.md)
**Related**: _To be added_

#### LOD

**Category**: General
**Description**: Is unusual in so far as it does not actually alter any geometry. Instead it builds a level of detail cache for the input object.
**Documentation**: [Full Details](./LOD.md)
**Related**: _To be added_

#### LSystem

**Category**: General
**Description**: The Lsystem SOP implements L-systems (Lindenmayer-systems, named after Aristid Lindenmayer (1925-1989)), allow definition of complex shapes through the use of iteration.
**Documentation**: [Full Details](./LSystem.md)
**Related**: _To be added_

#### Lattice

**Category**: General
**Description**: Allows you to create animated deformations of its input geometry by manipulating grids or a subdivided box that encloses the input source's geometry.
**Documentation**: [Full Details](./Lattice.md)
**Related**: _To be added_

#### Limit

**Category**: General
**Description**: Creates geometry from samples fed to it by CHOPs . It creates geometry at every point in the sample.
**Documentation**: [Full Details](./Limit.md)
**Related**: _To be added_

#### Line

**Category**: General
**Description**: Creates straight lines.
**Documentation**: [Full Details](./Line.md)
**Related**: _To be added_

#### Line Thick

**Category**: General
**Description**: Extrudes a surface from a curved line. The line can be of polygon, NURBS, or Bezier geometry type.
**Documentation**: [Full Details](./Line_Thick.md)
**Related**: _To be added_

#### Magnet

**Category**: General
**Description**: Allows you to affect deformations of the input geometry with another object using a "magnetic field" of influence, defined by a metaball field.
**Documentation**: [Full Details](./Magnet.md)
**Related**: _To be added_

#### Material

**Category**: General
**Description**: Allows the assignment of materials (MATs) to geometry at the SOP level. Note: The Material parameter in Object Components will override material attributes assigned to geometry using the Material SOP.
**Documentation**: [Full Details](./Material.md)
**Related**: _To be added_

#### Merge

**Category**: General
**Description**: Merges geometry from multiple SOPs.
**Documentation**: [Full Details](./Merge.md)
**Related**: _To be added_

#### Metaball

**Category**: General
**Description**: Creates metaballs and meta-superquadric surfaces. Metaballs can be thought of as spherical force fields whose surface is an implicit function defined at any point where the density of the force field equals a certain threshold.
**Documentation**: [Full Details](./Metaball.md)
**Related**: _To be added_

#### Model

**Category**: General
**Description**: Holds the surface modeler in TouchDesigner. It is designed to hold raw model geometry constructed using the SOP Editor (aka Modeler).
**Documentation**: [Full Details](./Model.md)
**Related**: _To be added_

#### Noise

**Category**: General
**Description**: Displaces geometry points using noise patterns. It uses the same math as the Noise CHOP .
**Documentation**: [Full Details](./Noise.md)
**Related**: _To be added_

#### Null

**Category**: General
**Description**: Has no effect on the geometry. It is an instance of the SOP connected to its input. The Null SOP is often used when making reference to a SOP network, allowing new SOPs to be added to the network (upstream) without the need to update the reference.
**Documentation**: [Full Details](./Null.md)
**Related**: _To be added_

#### Object Merge

**Category**: General
**Description**: Allows you to merge the geometry of several SOPs spanning different components.
**Documentation**: [Full Details](./Object_Merge.md)
**Related**: _To be added_

#### Out

**Category**: General
**Description**: Is used to create a SOP output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.
**Documentation**: [Full Details](./Out.md)
**Related**: _To be added_

#### Particle

**Category**: General
**Description**: Is used for creating and controlling motion of "particles" for particle systems simulations. Particle systems are often used to create simulations of natural events such as rain and snow, or effects such as fireworks and sparks.
**Documentation**: [Full Details](./Particle.md)
**Related**: _To be added_

#### Point

**Category**: General
**Description**: Allows you to get right down into the geometry and manipulate the position, color, texture coordinates, and normals of the points in the Source, and other attributes.
**Documentation**: [Full Details](./Point.md)
**Related**: _To be added_

#### Polyloft

**Category**: General
**Description**: Generates meshes of triangles by connecting (i.e. lofting/stitching) the points of open or closed faces without adding any new points.
**Documentation**: [Full Details](./Polyloft.md)
**Related**: _To be added_

#### Polypatch

**Category**: General
**Description**: Creates a smooth polygonal patch from a mesh primitive or a set of faces (polygons, NURBS or Bezier curves).
**Documentation**: [Full Details](./Polypatch.md)
**Related**: _To be added_

#### Polyreduce

**Category**: General
**Description**: Reduces a high detail polygonal model into one consisting of fewer polygons. The second input's polygons represent feature edges.
**Documentation**: [Full Details](./Polyreduce.md)
**Related**: _To be added_

#### Polyspline

**Category**: General
**Description**: Fits a spline curve to a polygon or hull and outputs a polygonal approximation of that spline. You can choose either to create divisions between the original points, or to ignore the position of the original points and divide the shape into segments of equal lengths.
**Documentation**: [Full Details](./Polyspline.md)
**Related**: _To be added_

#### Polystitch

**Category**: General
**Description**: Attempts to stitch polygonal surfaces together, thereby eliminating cracks that result from evaluating the surfaces at differing levels of detail.
**Documentation**: [Full Details](./Polystitch.md)
**Related**: _To be added_

#### Primitive

**Category**: General
**Description**: Is like the Point SOP but manipulates a primitive 's position, size, orientation, color, alpha, in addition to primitive-specific attributes, such as reversing primitive normals.
**Documentation**: [Full Details](./Primitive.md)
**Related**: _To be added_

#### Profile

**Category**: General
**Description**: Enables the extraction and manipulation of profiles. You will usually need a Trim SOP, Bridge SOP, or Profile SOP after a Project SOP .
**Documentation**: [Full Details](./Profile.md)
**Related**: _To be added_

#### Project

**Category**: General
**Description**: Creates curves on surface (also known as trim or profile curves) by projecting a 3D face onto a spline surface, much like a light casts a 2D shadow onto a 3D surface.
**Documentation**: [Full Details](./Project.md)
**Related**: _To be added_

#### Rails

**Category**: General
**Description**: Generates surfaces by stretching cross-sections between two rails. This is similar to the Sweep SOP, but it gives more control over the orientation and scaling of the cross-sections.
**Documentation**: [Full Details](./Rails.md)
**Related**: _To be added_

#### Ray

**Category**: General
**Description**: Is used to project one surface onto another. Rays are projected from each point of the input geometry in the direction of its normal.
**Documentation**: [Full Details](./Ray.md)
**Related**: _To be added_

#### Rectangle

**Category**: General
**Description**: Creates a 4-sided polygon. It is a planar surface.
**Documentation**: [Full Details](./Rectangle.md)
**Related**: _To be added_

#### Refine

**Category**: General
**Description**: Allows you to increase the number of CVs in any NURBS, Bzier, or polygonal surface or face without changing its shape.
**Documentation**: [Full Details](./Refine.md)
**Related**: _To be added_

#### Resample

**Category**: General
**Description**: Will resample one or more primitives into even length segments. It only applies to polygons so when presented with a NURBS or Bzier curve input, it first converts it to polygons using the Level of Detail parameter.
**Documentation**: [Full Details](./Resample.md)
**Related**: _To be added_

#### Revolve

**Category**: General
**Description**: Revolves faces to create a surface of revolution. The revolution's direction and origin are represented by guide geometry that resembles a thick line with a cross hair at the centre.
**Documentation**: [Full Details](./Revolve.md)
**Related**: _To be added_

#### Script

**Category**: General
**Description**: Runs a script each time the Script SOP cooks. By default, the Script SOP is created with a docked DAT that contains three Python methods: cook, onPulse, and setupParameters .
**Documentation**: [Full Details](./Script.md)
**Related**: _To be added_

#### Select

**Category**: General
**Description**: Allows you to reference a SOP from any other location in TouchDesigner. To save memory, the Select SOP creates an instance of the SOP references.
**Documentation**: [Full Details](./Select.md)
**Related**: _To be added_

#### Sequence Blend

**Category**: General
**Description**: Allows you do 3D Metamorphosis between shapes and Interpolate point position, colors, point normals, and texture coordinates between shapes.
**Documentation**: [Full Details](./Sequence_Blend.md)
**Related**: _To be added_

#### Skin

**Category**: General
**Description**: Takes any number of faces and builds a skin surface over them. If given two or more surfaces, however, the SOP builds four skins, one for each set of boundary curves.
**Documentation**: [Full Details](./Skin.md)
**Related**: _To be added_

#### Sort

**Category**: General
**Description**: Allows you to sort points and primitives in different ways. Sometimes the primitives are arranged in the desired order, but the point order is not.
**Documentation**: [Full Details](./Sort.md)
**Related**: _To be added_

#### Sphere

**Category**: General
**Description**: Generates spherical objects of different geometry types. It is capable of creating non-uniform scalable spheres of all geometry types.
**Documentation**: [Full Details](./Sphere.md)
**Related**: _To be added_

#### Spring

**Category**: General
**Description**: Deforms and moves the input geometry using spring "forces" on the edges of polygons and on masses attached to each point.
**Documentation**: [Full Details](./Spring.md)
**Related**: _To be added_

#### Sprite

**Category**: General
**Description**: Creates geometry (quad sprites) at point positions defined by the CHOP referenced in the XYZ CHOP parameter.
**Documentation**: [Full Details](./Sprite.md)
**Related**: _To be added_

#### Stitch

**Category**: General
**Description**: Is used to stretch two curves or surfaces to cover a smooth area. It can also be used to create certain types of upholstered fabrics such as cushions and parachutes.
**Documentation**: [Full Details](./Stitch.md)
**Related**: _To be added_

#### Subdivide

**Category**: General
**Description**: Takes an input polygon surface (which can be piped into one or both inputs), and divides each face to create a smoothed polygon surface using a Catmull-Clark subdivision algorithm.
**Documentation**: [Full Details](./Subdivide.md)
**Related**: _To be added_

#### Superquad

**Category**: General
**Description**: Generates an isoquadric surface. This produces a spherical shape that is similar to a metaball, with the difference that it doesn't change it's shape in response to what surrounds it.
**Documentation**: [Full Details](./Superquad.md)
**Related**: _To be added_

#### Surfsect

**Category**: General
**Description**: Performs boolean operations with NURBS and Bezier surfaces, or only generates profiles where the surfaces intersect.
**Documentation**: [Full Details](./Surfsect.md)
**Related**: _To be added_

#### Sweep

**Category**: General
**Description**: Sweeps primitives in the Cross-section input along Backbone Source primitive(s), creating ribbon and tube-like shapes.
**Documentation**: [Full Details](./Sweep.md)
**Related**: _To be added_

#### Switch

**Category**: General
**Description**: Switches between up to 9999 possible inputs. The output of this SOP is specified by the Select Input field.
**Documentation**: [Full Details](./Switch.md)
**Related**: _To be added_

#### Text

**Category**: General
**Description**: Creates text geometry from any TrueType font that is installed on the system, or any TrueType font file on disk.
**Documentation**: [Full Details](./Text.md)
**Related**: _To be added_

#### Texture

**Category**: General
**Description**: Assigns texture UV and W coordinates to the Source geometry for use in texture and bump mapping. It generates multi-layers of texture coordinates.
**Documentation**: [Full Details](./Texture.md)
**Related**: _To be added_

#### Torus

**Category**: General
**Description**: Generates complete or specific sections of torus shapes (like a doughnut).
**Documentation**: [Full Details](./Torus.md)
**Related**: _To be added_

#### Trace

**Category**: General
**Description**: Reads an image file and automatically traces it, generating a set of faces around areas exceeding a certain brightness threshold.
**Documentation**: [Full Details](./Trace.md)
**Related**: _To be added_

#### Trail

**Category**: General
**Description**: Takes an input SOP and makes a trail of each point of the input SOP over the past several frames, and connects the trails in different ways.
**Documentation**: [Full Details](./Trail.md)
**Related**: _To be added_

#### Transform

**Category**: General
**Description**: Translates, rotates and scales the input geometry in "object space" or local to the SOP. The Model Editor and the Transform SOP both work in "object space", and change the X Y Z positions of the points.
**Documentation**: [Full Details](./Transform.md)
**Related**: _To be added_

#### Trim

**Category**: General
**Description**: Cuts out parts of a spline surface, or uncuts previously cut pieces. When a portion of the surface is trimmed, it is not actually removed from the surface; instead, that part is made invisible.
**Documentation**: [Full Details](./Trim.md)
**Related**: _To be added_

#### Tristrip

**Category**: General
**Description**: Convert geometry into triangle strips. Triangle strips are faster to render than regular triangles or quads.
**Documentation**: [Full Details](./Tristrip.md)
**Related**: _To be added_

#### Tube

**Category**: General
**Description**: Generates open or closed tubes, cones, or pyramids along the X, Y or Z axes. It outputs as meshes, polygons or simply a tube primitive .
**Documentation**: [Full Details](./Tube.md)
**Related**: _To be added_

#### Twist

**Category**: General
**Description**: Performs non-linear deformations such as bend, linear taper, shear, squash and stretch, taper and twist.
**Documentation**: [Full Details](./Twist.md)
**Related**: _To be added_

#### Vertex

**Category**: General
**Description**: Allows you to edit/create attributes on a per-vertex (rather than per-point) basis. It is similar to the Point SOP in this respect.
**Documentation**: [Full Details](./Vertex.md)
**Related**: _To be added_

#### Wireframe

**Category**: General
**Description**: Converts edges to tubes and points to spheres, creating the look of a wire frame structure in renderings.
**Documentation**: [Full Details](./Wireframe.md)
**Related**: _To be added_

---

## Quick Stats

- **Total SOP Operators**: 102
- **Family Type**: SOP
- **Documentation**: Each operator has detailed parameter reference

## Navigation

- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation-by-family)

---
_Generated from TouchDesigner summaries.txt_
