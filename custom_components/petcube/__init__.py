from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .petcube_api import PetcubeAPI

PLATFORMS = ["button", "camera", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = PetcubeAPI(entry.data["email"], entry.data["password"])
    await hass.async_add_executor_job(api.login)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": api, "strength": 2}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
