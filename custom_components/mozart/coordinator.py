"""Update coordinator for the Bang & Olufsen Mozart integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import TypedDict

from mozart_api.exceptions import ApiException
from mozart_api.models import PlayQueueSettings, Preset
from mozart_api.mozart_client import MozartClient
from urllib3.exceptions import MaxRetryError, NewConnectionError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CLEANUP, CONNECTION_STATUS

_LOGGER = logging.getLogger(__name__)


class CoordinatorData(TypedDict):
    """TypedDict for coordinator data."""

    favourites: dict[str, Preset]
    queue_settings: PlayQueueSettings


class MozartCoordinator(DataUpdateCoordinator):
    """The Mozart entity coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the Mozart entity coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="coordinator",
            update_interval=timedelta(seconds=30),
        )

        self.entry = entry
        self._mozart_client = MozartClient(host=self.entry.data[CONF_HOST])
        self._dispatchers = []

        self._coordinator_data: CoordinatorData = {
            "favourites": {},
            "queue_settings": PlayQueueSettings(),
        }

        cleanup_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self.entry.unique_id}_{CLEANUP}",
            self._disconnect,
        )

        connection_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{self.entry.unique_id}_{CONNECTION_STATUS}",
            self._update_connection_state,
        )

        self._dispatchers.append(cleanup_dispatcher)
        self._dispatchers.append(connection_dispatcher)

    async def _update_connection_state(self, connection_state: bool) -> None:
        """Update entity connection state."""
        self.last_update_success = connection_state

    async def _disconnect(self) -> None:
        """Remove dispatchers."""
        for dispatcher in self._dispatchers:
            dispatcher()

    async def _async_update_data(self) -> CoordinatorData:
        """Get all information needed by the polling entities."""
        # Wait for the WebSocket listener to regain connection.
        if not self.last_update_success:
            raise UpdateFailed

        # Try to update coordinator_data.
        try:
            await self._update_variables()
            return self._coordinator_data

        except (
            MaxRetryError,
            NewConnectionError,
            ApiException,
            Exception,
            ConnectionResetError,
        ) as error:
            _LOGGER.error(error)
            async_dispatcher_send(
                self.hass,
                f"{self.entry.unique_id}_{CONNECTION_STATUS}",
                False,
            )
            raise UpdateFailed(error) from error

    async def _update_variables(self) -> None:
        """Update the coordinator data."""

        favourites = self._mozart_client.get_presets(
            async_req=True, _request_timeout=5
        ).get()

        queue_settings = self._mozart_client.get_settings_queue(
            async_req=True, _request_timeout=5
        ).get()

        self._coordinator_data = {
            "favourites": favourites,
            "queue_settings": queue_settings,
        }
