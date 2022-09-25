from datetime import datetime, timedelta
import json
import logging
import re
from typing import Any, Dict

from bs4 import BeautifulSoup
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import requests
import voluptuous as vol

from . import const

CONF_CONTAINERS = "containers"
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_CONTAINERS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)

CONTAINER_INFO_RE = r"var oContainerModel =(\[{.*?}\]);"
DATE_RE = r"Date\((.*?)\)"

log = logging.getLogger(__name__)


class SpaarnelandenCoordinator(DataUpdateCoordinator):
    def __init__(self, hass):
        super().__init__(
            hass,
            log,
            name="spaarnelanden",
            update_interval=timedelta(hours=1)
        )
        self.hass = hass

    def _fetch_data(self):
        resp = requests.get("https://inzameling.spaarnelanden.nl/")
        soup = BeautifulSoup(resp.text, "html.parser")
        script_ele = soup.find(id="MapPartial").findChild(type="text/javascript")
        if script_ele is None:
            log.error("Failed to find script container")
            raise ValueError("Failed to find script container")
        data_search = re.search(CONTAINER_INFO_RE, script_ele.get_text())
        if data_search is None:
            log.error("Failed to find data in script")
            raise ValueError("failed to extract container data from script")

        return json.loads(data_search.group(1))

    async def _async_update_data(self):
        log.info("Fetching container state from saarnelanden")
        data = await self.hass.async_add_executor_job(self._fetch_data)
        return {c['sRegistrationNumber']: c for c in data}


class ContainerSensor(CoordinatorEntity):
    def __init__(self, coordinator, container_id: str):
        super().__init__(coordinator)
        self.container_id = container_id
        self.attrs = {const.ATTR_CAPACITY: 0, const.ATTR_ID: container_id}
        self._state = None
        self._available = False

    @property
    def name(self):
        return f"spaarnelanden {self.container_id}"

    @property
    def unique_id(self):
        return self.container_id

    @property
    def available(self):
        return self._available

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        container = self.coordinator.data[self.container_id]
        last_emptied_match = re.search(DATE_RE, container["dtDateLastEmptied"])
        last_emptied = int(last_emptied_match.group(1)) / 1000
        self.attrs = {
            const.ATTR_OUT_OF_USE: container["bIsOutOfUse"],
            const.ATTR_CAPACITY: container["dFillingDegree"],
            const.ATTR_ID: container["sRegistrationNumber"],
            const.ATTR_LAST_EMPTIED: datetime.fromtimestamp(last_emptied),
            const.ATTR_CONTAINER_TYPE: container["sProductName"],
        }
        self._available = True
        self._state = container["dFillingDegree"]
        self.async_write_ha_state()


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    log.debug("Setting up spaarnelanden container sensor")
    containers = set(config.get(CONF_CONTAINERS))
    coordinator = SpaarnelandenCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [ContainerSensor(coordinator, container_id) for container_id in containers],
        update_before_add=True,
    )
