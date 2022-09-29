---
title: Proximity
description: Instructions on how to setup Proximity monitoring within Home Assistant.
ha_category:
  - Automation
  - Presence Detection
ha_release: 0.13
ha_quality_scale: internal
ha_domain: proximity
ha_iot_class: calculated
ha_integration_type: integration
---

The `proximity2` integration is a fork of the [core `proximity` integration](https://www.home-assistant.io/integrations/proximity/). The goal of this fork is to make the integration work correctly.

It monitors the distance of the tracked entities (devices) to a zone, and it also calculates their direction of motion. This allows to trigger automations if an entity is approaching to the zone.

## distance

The state of a `proximity2` entity contains the distance of the closest tracked entity to the tracked zone (excluding ignored entities).

### calculation

For each tracked entity get its state. If the there is no state, ignore the entity. If the state value is in the list of ignored zones, ignore the entity. If any of the remaining entities' state value is equal to the name of the monitored zone, the distance is set to 0 (entity is in tracked zone). Otherwise, get the position (lat,lon) of the entity and calculate the distance to the center of the monitored zone and subtract its radius, but limit the result to 0 (distance is always >0).

`d = max(0, distance(entitiy, zone) - radius)`

The final state value of the proximity entity is the _smallest_ of the calculated distance values `d`.

If there is no smallest distance, the state is undefined.

### zone radius

The radius is taken from monitored zone. This means, the distance of an entity is 0, if the entity is inside the zone. The distance is the distance of the entity to the border of the zone. 

If you want to get the distance to center of the zone, you may the radius to 0 in configuration. You may also set a radius >0.

### position

The position of an entity is extracted from its lat/lon attributes. If it does not have these attributes, the position is taken from the zone the entity is in. If it is not in a zone, the position cannot be determined, the distance of this entity is undefined, and it is ignored in the distance calculation.

## direction

The direction of motion is derived from the distance (state value of the proximity entity) and stored in the `direction` attribute. Let `d0` be the current distance and `d1` be the newly calculated distance value after a tracked entity has changed it state. 
Then there are 4 possibilities.

- `d0` and `d1` are undefined: `direction = undefined`
- `abs(d1-d0) <= tolerance`: `direction = stationary`
- `d0 > d1`: `direction = towards`
- `d0 < d1`: `direction = away`

If `direction == stationary`, then the distance will _not_ be updated. This allows to ignore small movements of entities.

## example use cases

This integration is useful to reduce the number of automation rules required when wanting to perform automations based on locations outside a particular zone. The [triggers](/getting-started/automation-trigger/ needed when factors such as direction of travel need to be taken into account are much simple with this integration.

- turn on heating as you approach home
- turn off heating when more than 5km away from home

## state

The Proximity entity which is created has the following state values:

- `state`: distance of closest tracked entity to monitored zone 
- `nearest`: id of entity with smallest distance
- `direction`: direction of motion (`undefined,towards,away,stationary`)
- `unit_of_measurement`: unit of the distance (`km,m,mi,yd,ft`)

## installation

Copy all files into the `custom_components/proximity2/` dir of your HA installation.

## configuration

{% configuration %}
zone:
  description: name of zone to monitor (default = home)
  required: false
  type: string
ignored:
  description: names of zone, ignore entities if they are in one these zones
  required: false
  type: list
devices:
  description: list of ids of entities to track
  required: true
  type: list
tolerance:
  description: tolerance (m) used in calculation of direction of motion
  required: false
  type: integer
radius:
  description: radius (m) of zone used in calculation of distance (default = radius of zone)
  required: false
  type: integer
precision:
  description: number of digits of distance after decimal separator (default = 0)
  required: false
  type: integer
unit_of_measurement:
  description: unit of measurement for displaying distance (km,m,mi,yd,ft)
  required: false
  type: string
  default: km
{% endconfiguration %}

```yaml
# Example configuration.yaml entry
proximity:
  home: 
    zone: home
    ignored:
      - work
    devices:
      - person.bob
      - person.alice
    tolerance: 50
    unit_of_measurement: km
    precision: 1
    radius: 0
  work:
    devices:
      - person.bob
      - person.joe
    
```