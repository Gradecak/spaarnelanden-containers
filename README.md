# Sparnelanden Containers Sensor for Home Assistant

A sensor for the capacity status of garbage containers serviced by the Spaarnelanden.

The sensor scrapes container data every 2 hours from
https://inzameling.spaarnelanden.nl/.  Rather than exposing the status of all waste
containers in the Haarlem area, you can subscribe and receive container status
information for a particular set of containers, by their registration number.

Sample `configuration.yaml`

```yaml
sensor:
  - platform: spaarnelanden
    containers:
      - "111111"
      - "222222"
```

## Installation


Installation can be done via HACS (recommended) by adding this repository as a custom
repository and proceeding in the usual way.

The alternative is to clone this repository manually and copy the contents of the
`custom_components` directory to the `custom_components` directory of your home
assistant install.

If your home assistant install does not have a `custom_components` directory, create one
at the same level as your `configuration.yaml` file.

## Finding container registration number

The container registration number can be discovered by finding the desired container on
the https://inzameling.spaarnelanden.nl/ map. Open the container information by clicking
on the icon in the map and copy the number at the top.


## Available attributes

Currently the following attributes are made available via the sensor:

```
- id
- capacity
- out_of_use
- last_emptied
- container_type
```
