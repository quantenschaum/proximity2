"""Support for tracking the proximity of a device."""
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_RADIUS,
    CONF_DEVICES,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_ZONE,
    LENGTH_FEET,
    LENGTH_KILOMETERS,
    LENGTH_METERS,
    LENGTH_MILES,
    LENGTH_YARD,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_state_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.distance import convert
from homeassistant.util.location import distance

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DOMAIN = "proximity2"

CONF_BASE = DOMAIN
CONF_IGNORED = "ignored"
CONF_TOLERANCE = "tolerance"
CONF_PRECISION = "precision"

ATTR_DIRECTION = "direction"
ATTR_CHANGE = "change"
ATTR_NEAREST = "nearest"

UNITS = [LENGTH_METERS, LENGTH_KILOMETERS, LENGTH_FEET, LENGTH_YARD, LENGTH_MILES]

ZONE_SCHEMA = vol.Schema({
    vol.Optional(CONF_ZONE, default="home"): cv.string,
    vol.Required(CONF_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_IGNORED, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_TOLERANCE, default=0): cv.positive_int,
    vol.Optional(CONF_PRECISION, default=0): cv.positive_int,
    vol.Optional(CONF_RADIUS): cv.positive_int,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): vol.All(cv.string, vol.In(UNITS)),
})

CONFIG_SCHEMA = vol.Schema({CONF_BASE: cv.schema_with_slug_keys(ZONE_SCHEMA)}, extra=vol.ALLOW_EXTRA)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Get the zones and offsets from configuration.yaml."""
    for name, conf in config[CONF_BASE].items():
        setup_entity(hass, name, conf)

    return True


def setup_entity(hass, name, conf):
    _LOGGER.debug("setup %s %s", name, conf)
    proximity = Proximity(hass, name, conf)

    def update(*a):
        _LOGGER.debug("UPDATE %s %s", name, a)
        proximity.schedule_update_ha_state(True)

    update()
    track_state_change(hass, conf[CONF_DEVICES], update)


class Proximity(Entity):
    _distance = None
    _nearest = None
    _direction = None
    _attr_icon = "mdi:compass"
    _attr_force_update = True

    def __init__(self, hass, name, config):
        self.hass = hass
        self.entity_id = f"{DOMAIN}.{name}"
        self._name = name
        self._ignored_zones = config[CONF_IGNORED]
        self._devices = config[CONF_DEVICES]
        self._tolerance = config[CONF_TOLERANCE]
        self._zone = config[CONF_ZONE]
        self._zone_id = f"zone.{self._zone}"
        self._precision = config[CONF_PRECISION]
        self._radius = config.get(CONF_RADIUS)
        self._attr_unit_of_measurement = config.get(CONF_UNIT_OF_MEASUREMENT, hass.config.units.length_unit)

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self._distance == 0:
            return 0
        return self.convert(self._distance)

    @property
    def extra_state_attributes(self):
        return {ATTR_NEAREST: self._nearest, ATTR_DIRECTION: self._direction}

    def convert(self, meters):
        if meters is not None:
            return round(convert(meters, LENGTH_METERS, self.unit_of_measurement), self._precision)

    def position(self, entity_id):
        state = self.hass.states.get(entity_id)
        if state:
            pos = state.attributes.get(ATTR_LATITUDE), state.attributes.get(ATTR_LONGITUDE)
            if all(v is not None for v in pos):
                _LOGGER.debug("pos=%s %s %s", pos, entity_id, state.attributes.get("source") or "")
                return pos
            else:
                return self.position(f"zone.{state.state}")

    @property
    def radius(self):
        if self._radius is not None:
            return self._radius
        state = self.hass.states.get(self._zone_id)
        if state:
            radius = state.attributes.get(CONF_RADIUS)
            if radius:
                return radius
        return 0

    def distance(self, pos):
        pos = self.position(pos) if isinstance(pos, str) else pos
        zone_pos = self.position(self._zone_id)
        if pos and zone_pos:
            d0 = distance(*zone_pos, *pos)
            d = max(0, d0 - self.radius)
            _LOGGER.debug("distance=%s-%s->%s", d0, self.radius, d)
            return d

    def update(self):
        _LOGGER.debug("update %s", self.name)
        dist, nearest = None, None
        for dev in self._devices:
            dev_state = self.hass.states.get(dev)
            _LOGGER.debug("dev=%s", dev)
            if dev_state:
                dev_zone = dev_state.state
                dev_name = dev_state.name
                _LOGGER.debug("dev_zone=%s", dev_zone)
                if dev_zone in self._ignored_zones:
                    _LOGGER.debug("ignore")
                    continue
                if dev_zone == self._zone:
                    _LOGGER.debug("in this zone")
                    dist, nearest = 0, dev_name
                    break
                d = self.distance(dev)
                _LOGGER.debug("dist=%s", d)
                if not dist or d and d < dist:
                    dist, nearest = d, dev_name

        change = dist - self._distance if all(v is not None for v in [dist, self._distance]) else None
        _LOGGER.debug("nearest=%s dist=%s change=%s", nearest, dist, change)

        if change is None:
            self._direction = None
        elif abs(change) <= self._tolerance:
            self._direction = "stationary"
        elif change < 0:
            self._direction = "towards"
        elif change > 0:
            self._direction = "away"

        if self._direction != "stationary" or dist == 0:
            self._distance = dist

        self._nearest = nearest

        _LOGGER.debug("state=%s attr=%s", self.state, self.extra_state_attributes)
