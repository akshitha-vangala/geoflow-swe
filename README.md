# GeoFlow-SWE

## Overview

GeoFlow-SWE is a declarative, compiled domain-specific language (DSL) implemented in OCaml for modeling and simulating multimodal transportation and logistics networks. It allows users to express routing problems using high-level constraints, which are compiled into an optimized graph-based routing engine along with a structured visualization output.

The system is designed to bridge the gap between human-readable specifications and efficient execution of complex routing and simulation tasks.

## Motivation

Traditional routing systems require low-level programming and manual handling of constraints such as schedules, multimodal transfers, and geographic restrictions. GeoFlow-SWE addresses this by providing a high-level language that abstracts these complexities while still producing efficient execution.

## Operational Modes

The system supports two execution environments:

* 2D Surface Mode
  Models transportation systems on an (x, y) plane. Suitable for logistics, transit networks, and simulation environments. Optimization is performed over time and cost.

* 3D Volumetric Mode
  Extends routing into (x, y, z) space. Designed for drone-based systems and urban air mobility. Incorporates energy constraints and altitude-aware movement.

## Language Design

GeoFlow-SWE provides a structured DSL for defining the components of a transportation network:

* Modes
  Represent vehicles or transport types with attributes such as speed, cost, energy consumption, and payload capacity.

* Nodes
  Represent locations or hubs defined by coordinates, allowed transport modes, and optional schedule constraints.

* Geofences
  Represent restricted or regulated regions using bounding boxes or polygons, with rules affecting traversal.

* Missions
  Define routing queries including source, destination, optimization goals, and constraints.

## Core Features

### Multimodal Routing

The system supports multiple transport modes and automatically handles transitions between them by introducing transfer costs and constraints.

### Time-Dependent Routing

Routing decisions depend on arrival times. Schedules at nodes influence path selection, enabling realistic modeling of delays and waiting times.

### Multi-Objective Optimization

Instead of returning a single solution, the system computes a set of optimal trade-offs (Pareto frontier), such as fastest, cheapest, and balanced routes.

### Geospatial Constraints

Geofences influence routing by restricting movement or applying penalties such as increased cost or energy usage.

### Event-Driven Behavior

The DSL supports monitoring conditions and triggering fallback actions such as rerouting or waiting.

## System Architecture

The system follows a compilation pipeline:

1. DSL Input
   User-defined script describing the network and constraints

2. Parsing and Compilation
   The DSL is parsed and converted into an internal representation

3. Graph Construction
   A multigraph is built with nodes, edges, and constraints

4. Routing Engine
   Optimized graph traversal algorithms (such as A*) compute routes

5. Output Generation
   The system produces executable routing logic and visualization data

## Input Parameters

The DSL allows users to define:

* Vehicle properties: speed, cost, energy, payload
* Network structure: nodes and connectivity
* Constraints: schedules, geofences, limits
* Optimization parameters: time vs cost or energy trade-offs

## Output

The compiler generates two main artifacts:

* Routing Engine
  A highly optimized in-memory graph with a tailored search algorithm capable of handling constraints and multi-objective optimization.

* Visualizer Payload
  Structured JSON or GeoJSON data describing nodes, routes, and constraints, which can be rendered in a web-based interface.

## Project Structure

geoflow-swe/

* src/ : core compiler and routing logic
* examples/ : sample DSL programs
* output/ : generated results and visualizations
* docs/ : supporting documentation

## Applications

* Logistics and supply chain optimization
* Smart transportation systems
* Autonomous vehicle routing
* Simulation and planning tools

## Author

Akshitha Vangala

## License

This project is intended for academic use.
