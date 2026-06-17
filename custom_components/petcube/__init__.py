import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_DEVICE_ID
from .petcube_api import PetcubeAPI

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["binary_sensor", "button", "camera", "select", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = PetcubeAPI(entry.data["email"], entry.data["password"])
    await hass.async_add_executor_job(api.login)

    device_id = entry.data[CONF_DEVICE_ID]

    async def _async_update_data():
        try:
            return await hass.async_add_executor_job(api.get_device, device_id)
        except Exception as e:
            raise UpdateFailed(f"Petcube API error: {e}") from e

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"petcube_{device_id}",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=60),
    )
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "strength": 2,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
