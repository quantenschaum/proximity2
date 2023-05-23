The `proximity2` integration is a fork of the [core `proximity` integration](https://www.home-assistant.io/integrations/proximity/). The goal of this fork is to make the integration work correctly.

It calculates the distance of the tracked entities (devices) to a monitored zone, and it also calculates the direction of motion. This allows to trigger automations on an entity approaching the zone.

## Use cases

This integration is useful to reduce the number of automation rules required when wanting to perform automations based on locations outside a particular zone. The [triggers](https://www.home-assistant.io/docs/automation/trigger/) needed when factors such as direction of travel need to be taken into account are much simpler with this integration.

- turn on heating as you approach home
- turn off heating when more than 5km away from home

## Installation

Copy all files into the `custom_components/proximity2/` dir of your HA installation.

## Configuration

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
  home: # name of the proximity entity 
    zone: home # name of monitored zone
    ignored: # list of zone names, tracked entities are ignored if they are in any if these zones
      - work
    devices: # list of ids of entities to track
      - person.bob
      - person.alice
    tolerance: 50 # tolerance (m) used in calculation of direction
    unit_of_measurement: km
    precision: 1 # digits after decimal separator
    radius: 0 # radius of zone used in distance calculation
  work:
    zone: work
    devices:
      - person.bob
      - person.judith
```

## Distance

The state of a `proximity2` entity contains the distance of the closest tracked entity to the tracked zone (excluding ignored entities).

### Algorithm

For each tracked entity get its state. If the there is no state, ignore the entity. If the state value is in the list of ignored zones, ignore the entity. If any of the remaining entities' state value is equal to the name of the monitored zone, the distance is set to 0 (entity is in tracked zone). Otherwise, get the position (lat,lon) of the entity and calculate the distance to the center of the monitored zone and subtract its radius, but limit the result to 0 (distance is always >0).

`d = max(0, distance(entitiy, zone) - radius)`

The final state value of the proximity entity is the _smallest_ of the calculated distance values `d`.

If there is no smallest distance, the state is undefined.

### Ignored zones

Entities that are in any of the ignored zones do not participate in the distance calculation. It is possible to ignore the monitored zone itself. This allows to get the distance of the closest entity, except the ones that are in the zone.

### Zone radius

The radius is taken from monitored zone. This means, the distance of an entity is 0, if the entity is inside the zone. The distance is the distance of the entity to the border of the zone. 

If you want to get the distance to center of the zone, you may the radius to 0 in configuration. You may also set a radius >0.

### Positions

The position of an entity is extracted from its lat/lon attributes. If it does not have these attributes, the position is taken from the zone the entity is in. If it is not in a zone, the position cannot be determined, the distance of this entity is undefined, and it is ignored in the distance calculation.

## Direction

The direction of motion is derived from the distance (state value of the proximity entity) and stored in the `direction` attribute. Let `d0` be the current distance and `d1` the newly calculated distance value after a tracked entity has changed it state. 
Then there are 4 possibilities.

- `d0` and `d1` are undefined: `direction = undefined`
- `abs(d1-d0) <= tolerance`: `direction = stationary`
- `d0 > d1`: `direction = towards`
- `d0 < d1`: `direction = away`

To ignore small movements of entities, the distance (state value) will _only_ be updated, if `direction != stationary or distance == 0`.

## State

The Proximity entity which is created has the following state values:

- `state`: distance of closest tracked entity to monitored zone 
- `nearest`: id of entity with smallest distance
- `direction`: direction of motion (`undefined,towards,away,stationary`)
- `unit_of_measurement`: unit of the distance (`km,m,mi,yd,ft`)

