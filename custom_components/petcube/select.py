from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_NAME

STRENGTH_OPTIONS = ["Faible", "Moyen", "Fort"]
STRENGTH_MAP = {"Faible": 1, "Moyen": 2, "Fort": 3}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([PetcubeStrengthSelect(hass, entry)])


class PetcubeStrengthSelect(SelectEntity):
    def __init__(self, hass, entry: ConfigEntry):
        self.hass = hass
        self._entry_id = entry.entry_id
        self._device_id = entry.data[CONF_DEVICE_ID]
        device_name = entry.data.get(CONF_DEVICE_NAME, "Petcube")
        self._attr_name = f"{device_name} Force friandise"
        self._attr_unique_id = f"petcube_{self._device_id}_strength"
        self._attr_icon = "mdi:speedometer"
        self._attr_options = STRENGTH_OPTIONS
        self._attr_current_option = "Moyen"

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.hass.data[DOMAIN][self._entry_id]["strength"] = STRENGTH_MAP[option]
        self.async_write_ha_state()
