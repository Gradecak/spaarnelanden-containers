from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
import json
import logging
import re
from typing import Any, Dict
from urllib.error import HTTPError

from bs4 import BeautifulSoup
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
import requests
import voluptuous as vol

from . import const

CONF_CONTAINERS = "containers"
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_CONTAINERS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


SCAN_INTERVAL = timedelta(hours=12)

CONTAINER_INFO_RE = r"var oContainerModel =(\[{.*?}\]);"
DATE_RE = r"Date\((.*?)\)"

log = logging.getLogger(__name__)


class ContainerSensor(Entity):
    def __init__(self, container_id: str, session):
        super().__init__()
        self.session = session
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

    async def async_update(self):
        async with self.session.get("https://inzameling.spaarnelanden.nl/") as resp:
            text = await resp.text()

        soup = BeautifulSoup(text, "html.parser")
        script_ele = soup.find(id="MapPartial").findChild(type="text/javascript")
        if script_ele is None:
            log.error("Failed to find script container")
            raise ValueError("Failed to find script container")
        data_search = re.search(CONTAINER_INFO_RE, script_ele.get_text())
        if data_search is None:
            log.error("Failed to find data in script")
            raise ValueError("failed to extract container data from script")

        data = json.loads(data_search.group(1))
        [container, *_] = [
            c for c in data if c["sRegistrationNumber"] == self.container_id
        ]

        last_emptied_match = re.search(DATE_RE, container["dtDateLastEmptied"])
        last_emptied = int(last_emptied_match.group(1)) / 1000
        self.attrs = {
            const.ATTR_OUT_OF_USE: container["bIsOutOfUse"],
            const.ATTR_CAPACITY: container["dFillingDegree"],
            const.ATTR_ID: container["sRegistrationNumber"],
            const.ATTR_LAST_EMPTIED: datetime.fromtimestamp(last_emptied),
            const.ATTR_CONTAINER_TYPE: container["sProductName"]
        }
        self._available = True
        self._state = container["dFillingDegree"]


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    log.debug("Setting up spaarnelanden container sensor")
    session = async_get_clientsession(hass)
    containers = config.get(CONF_CONTAINERS)
    async_add_entities(
        [ContainerSensor(container_id, session) for container_id in containers],
        update_before_add=True,
    )
