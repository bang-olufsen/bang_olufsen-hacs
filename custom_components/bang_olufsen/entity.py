"""Entity representing a Bang & Olufsen device."""

from __future__ import annotations

from typing import cast

from mozart_api.mozart_client import MozartClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .beoremote_halo.halo import Halo
from .const import BEO_MODEL_PLATFORM_MAP, DOMAIN, BeoPlatform


class BeoBase:
    """Base class for Bang & Olufsen Home Assistant objects."""

    def __init__(
        self, config_entry: ConfigEntry, client: MozartClient | Halo | None = None
    ) -> None:
        """Initialize the object."""

        # Get the input from the config entry.
        self.entry = config_entry

        # Set the configuration variables.
        self._host: str = self.entry.data[CONF_HOST]
        self._unique_id: str = cast(str, self.entry.unique_id)

        # Set the client.
        # Allowing the client to be set directly allows the coordinator to be initialized before being added to runtime_data.
        if client:
            self._client = client
        else:
            self._client = config_entry.runtime_data.client

    @staticmethod
    def get_device(hass: HomeAssistant, unique_id: str) -> dr.DeviceEntry:
        """Get the device."""
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device({(DOMAIN, unique_id)})
        assert device

        return device


class BeoEntity(Entity, BeoBase):
    """Base Entity for Bang & Olufsen entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the object."""
        super().__init__(config_entry)

        match BEO_MODEL_PLATFORM_MAP[config_entry.data[CONF_MODEL]]:
            case BeoPlatform.MOZART.value:
                self._attr_device_info = DeviceInfo(
                    identifiers={(DOMAIN, self._unique_id)}
                )
            case BeoPlatform.BEOREMOTE_HALO.value:
                self._attr_device_info = DeviceInfo(
                    configuration_url=f"http://{self._host}:8080",
                    identifiers={(DOMAIN, self._unique_id)},
                )

    @callback
    def _async_update_connection_state(self, connection_state: bool) -> None:
        """Update entity connection state."""
        self._attr_available = connection_state

        self.async_write_ha_state()
