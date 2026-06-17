from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_NAME


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    entry_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PetcubeFirmwareSensor(entry_data["coordinator"], entry)])


class PetcubeFirmwareSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._device_id = entry.data[CONF_DEVICE_ID]
        device_name = entry.data.get(CONF_DEVICE_NAME, "Petcube")
        self._attr_name = f"{device_name} Firmware"
        self._attr_unique_id = f"petcube_{self._device_id}_firmware"

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get("soft_ver")
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        attrs = {}
        for key in ("device_type", "prod_rev", "firmware_update_status", "serial"):
            if key in data:
                attrs[key] = data[key]
        return attrs

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
