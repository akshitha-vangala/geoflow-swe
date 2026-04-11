# GeoFlow-SWE

## Description

GeoFlow is a domain-specific language (DSL) designed for modeling and simulating transportation networks. It allows users to define nodes, transport modes, geofences, and missions, and generates a visual output of the routing and simulation.

## Features

* Custom DSL for defining routing problems
* Support for multiple transport modes
* Geospatial modeling using nodes and geofences
* Event-driven missions with triggers and fallback actions
* Generates interactive HTML output

## How It Works

1. The user writes a DSL script describing the system
2. The compiler processes the script
3. A graph-based algorithm computes the route
4. The system generates an HTML visualization

## Example

```
mode DeliveryDrone {
  speed: 45.0
  cost: 1.2
}

node A {
  loc: (40.7128, -74.0060)
  allows: [DeliveryDrone]
}
```

## Project Structure

geoflow-swe/

* src/ : source code
* examples/ : sample scripts
* output/ : generated files

## Author

Akshitha Vangala

## License

For academic use.
