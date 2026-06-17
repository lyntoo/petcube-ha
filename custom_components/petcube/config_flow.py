import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_DEVICE_ID, CONF_DEVICE_NAME
from .petcube_api import PetcubeAPI


class PetcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._api = None
        self._devices = []
        self._email = None
        self._password = None

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            self._api = PetcubeAPI(self._email, self._password)
            try:
                ok = await self.hass.async_add_executor_job(self._api.login)
                if ok:
                    self._devices = await self.hass.async_add_executor_job(self._api.get_devices)
                    if self._devices:
                        return await self.async_step_device()
                    errors["base"] = "no_devices"
                else:
                    errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_device(self, user_input=None):
        errors = {}
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            device_name = next(
                (d.get("name") or d.get("serial_number") for d in self._devices if str(d.get("id")) == str(device_id)),
                device_id
            )
            return self.async_create_entry(
                title=f"Petcube {device_name}",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_NAME: device_name,
                }
            )

        device_options = {
            str(d.get("id")): d.get("name") or d.get("serial_number") or str(d.get("id"))
            for d in self._devices
        }

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(device_options),
            }),
            errors=errors,
        )
