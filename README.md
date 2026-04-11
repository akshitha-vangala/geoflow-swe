# GeoFlow-SWE

## Overview

GeoFlow-SWE is a declarative, compiled domain-specific language (DSL) implemented in Python for modeling and simulating multimodal transportation and logistics networks. It allows users to express routing problems using high-level constraints, which are compiled into an optimized graph-based routing engine along with a structured visualization output.

The system bridges the gap between human-readable specifications and efficient execution of complex routing and simulation tasks.

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

Supports multiple transport modes and automatically handles transitions between them using transfer costs and constraints.

### Time-Dependent Routing

Routing decisions depend on arrival times. Node schedules influence path selection, enabling realistic modeling of delays and waiting times.

### Multi-Objective Optimization

Computes a set of optimal trade-offs (Pareto frontier), such as fastest, cheapest, and balanced routes.

### Geospatial Constraints

Geofences restrict movement or apply penalties such as increased cost or energy usage.

### Event-Driven Behavior

Supports monitoring conditions and triggering fallback actions such as rerouting or waiting.

## System Architecture

The system follows a compilation pipeline:

1. DSL Input
   User-defined script describing the network and constraints

2. Parsing
   The DSL is parsed using the grammar definition

3. Transformation
   Parsed data is converted into an internal representation

4. Execution
   Graph construction and routing algorithms compute optimal paths

5. Output Generation
   The system produces visualization data and results

## Project Structure

geoflow-swe/

* .github/workflows/ : GitHub Actions for linting and automation

* geoflow/           : core implementation of the DSL and routing logic

* semantic/          : semantic analysis and validation components

* tests/             : unit tests for the system

* outputs/           : generated HTML dashboards and results

* grammar.lark       : DSL grammar definition

* parser.py          : parses DSL input into structured form

* transformer.py     : transforms parsed data into internal representation

* interpreter.py     : executes the DSL and routing logic

* main.py            : entry point to run the project

* README.md          : project documentation

## Installation

Clone the repository:

```bash id="b7t3mj"
git clone https://github.com/akshitha-vangala/geoflow-swe.git
cd geoflow-swe
```

Install dependencies:

```bash id="r1l0fc"
pip install -r requirements.txt
```

## Usage

Run the project using:

```bash id="1rc3yx"
python main.py
```

## Applications

* Logistics and supply chain optimization
* Smart transportation systems
* Autonomous vehicle routing
* Simulation and planning tools

## Author

Akshitha Vangala

## License

This project is intended for academic use.
