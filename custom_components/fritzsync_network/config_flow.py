"""Config flow for FritzSync Network."""

from __future__ import annotations

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import FritzAuthorizationError, FritzConnectionException
from fritzconnection.lib.fritzhosts import FritzHosts
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .const import CONF_SCAN_INTERVAL, CONF_USE_TLS, DEFAULT_HOST, DEFAULT_SCAN_INTERVAL, DOMAIN


class FritzSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST].lower())
            self._abort_if_unique_id_configured()

            def validate() -> None:
                connection = FritzConnection(
                    address=user_input[CONF_HOST], username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD], use_tls=user_input[CONF_USE_TLS], timeout=10.0,
                )
                FritzHosts(connection).host_numbers

            try:
                await self.hass.async_add_executor_job(validate)
            except FritzAuthorizationError:
                errors["base"] = "invalid_auth"
            except FritzConnectionException:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_USE_TLS, default=False): bool,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FritzSyncOptionsFlow()


class FritzSyncOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=15, max=3600))
        }))
