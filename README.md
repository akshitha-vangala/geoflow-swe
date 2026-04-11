# GeoFlow-SWE

## Description

GeoFlow-SWE is a declarative, compiled domain-specific language (DSL) written in OCaml for defining multimodal transportation and logistics networks. It allows users to describe routing problems using high-level constraints, which are compiled into an optimized graph-based routing engine and a visual output.

## Operational Modes

The system supports two execution environments:

* 2D Surface Mode: operates on an (x, y) plane and is used for transit systems and logistics. It optimizes for time and cost.

* 3D Volumetric Mode: operates in (x, y, z) space and is designed for drone systems and air mobility. It optimizes for time and energy while handling altitude constraints.

## Input Parameters

Users define the system using the DSL:

* Vehicles (modes): speed, cost, energy usage, payload
* Nodes: coordinates, allowed modes, schedules
* Geofences: restricted regions defined by boundaries
* Query constraints: parameters such as time vs cost or energy limits

## Core Features

* Multimodal routing with support for transfer between transport modes
* Time-dependent routing based on schedules
* Multi-objective optimization producing multiple optimal solutions
* Geofencing with penalties or restrictions

## Output

The compiler generates:

* A routing engine: an optimized graph-based executable for pathfinding
* A visual output: JSON or GeoJSON data for rendering in a web interface

## Project Structure

geoflow-swe/

* src/ : source code
* examples/ : sample DSL scripts
* output/ : generated files

## Author

Akshitha Vangala

## License

For academic use.
