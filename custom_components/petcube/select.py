from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_NAME

STRENGTH_OPTIONS = ["Faible", "Moyen", "Fort"]
STRENGTH_MAP = {"Faible": 33.0, "Moyen": 66.0, "Fort": 99.0}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    entry_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PetcubeStrengthSelect(entry_data["coordinator"], hass, entry)])


class PetcubeStrengthSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, hass, entry: ConfigEntry):
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        self._device_id = entry.data[CONF_DEVICE_ID]
        device_name = entry.data.get(CONF_DEVICE_NAME, "Petcube")
        self._attr_name = f"{device_name} Force friandise"
        self._attr_unique_id = f"petcube_{self._device_id}_strength"
        self._attr_icon = "mdi:speedometer"
        self._attr_options = STRENGTH_OPTIONS
        self._attr_current_option = "Moyen"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=data.get("name", "Petcube"),
            manufacturer="Petcube",
            model=data.get("device_type"),
            sw_version=data.get("soft_ver"),
        )

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.hass.data[DOMAIN][self._entry_id]["strength"] = STRENGTH_MAP[option]
        self.async_write_ha_state()
