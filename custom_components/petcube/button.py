from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_NAME


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([PetcubeTreatButton(hass, entry)])


class PetcubeTreatButton(ButtonEntity):
    def __init__(self, hass, entry: ConfigEntry):
        self.hass = hass
        self._entry_id = entry.entry_id
        self._device_id = entry.data[CONF_DEVICE_ID]
        device_name = entry.data.get(CONF_DEVICE_NAME, "Petcube")
        self._attr_name = f"{device_name} Lancer friandise"
        self._attr_unique_id = f"petcube_{self._device_id}_treat"
        self._attr_icon = "mdi:dog"

    async def async_press(self) -> None:
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        api = entry_data["api"]
        strength = entry_data["strength"]
        await self.hass.async_add_executor_job(api.launch_treat, self._device_id, strength)
