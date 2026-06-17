import urllib.request
import json
import logging
from datetime import timedelta
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    async_add_entities([PetcubeCamera(api, entry)])


class PetcubeCamera(Camera):
    def __init__(self, api, entry: ConfigEntry):
        super().__init__()
        self._api = api
        self._device_id = str(entry.data["device_id"])
        device_name = entry.data.get(CONF_DEVICE_NAME, "Petcube")
        self._attr_name = f"{device_name} Caméra"
        self._attr_unique_id = f"petcube_{self._device_id}_camera"
        self._attr_icon = "mdi:cctv"
        self._image = None

    async def async_camera_image(self, width=None, height=None):
        return await self.hass.async_add_executor_job(self._fetch_snapshot)

    def _fetch_snapshot(self):
        try:
            url = f"https://api.petcube.com/api/v1/care/thumbs?limit=1&device_ids={self._device_id}"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Token {self._api.token}",
                "Accept": "application/json",
                "User-Agent": "Petcube/8.3.0 Android",
                "X-App-Platform": "android",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
                resp = json.loads(raw)
                image = self._extract_image(resp)
                if image:
                    return image
        except Exception as e:
            _LOGGER.debug("care/thumbs error: %s", e)

        return self._image

    def _extract_image(self, resp):
        # resp may be a list or {"data": [...]}
        items = resp if isinstance(resp, list) else resp.get("data", [])
        if not items:
            return None

        # find thumbnail for our device first, then fallback to any
        for match_device in (True, False):
            for item in items:
                if not isinstance(item, dict):
                    continue
                cube_id = str(item.get("cubeId", item.get("cube_id", "")))
                if match_device and cube_id != self._device_id:
                    continue
                # item is a CubeCareThumbnails: {"cubeId": ..., "thumbnails": [...]}
                thumbs = item.get("thumbnails", [])
                if thumbs and isinstance(thumbs[0], dict):
                    snapshot_url = thumbs[0].get("url")
                    if snapshot_url:
                        return self._download_image(snapshot_url)
                # fallback: maybe flat structure {"url": "..."}
                snapshot_url = item.get("url")
                if snapshot_url:
                    return self._download_image(snapshot_url)

        return None

    _IMAGE_MAGIC = (
        b"\xff\xd8",          # JPEG
        b"\x89PNG",           # PNG
        b"RIFF",              # WebP
        b"GIF8",              # GIF
    )

    def _download_image(self, url):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = r.read()
            if len(data) < 4:
                _LOGGER.debug("Response too small (%d bytes): %s", len(data), data)
                return None
            if not any(data.startswith(magic) for magic in self._IMAGE_MAGIC):
                _LOGGER.warning(
                    "Not a valid image (%d bytes, starts with %s): %s",
                    len(data),
                    data[:4].hex(),
                    data[:40],
                )
                return None
            self._image = data
            return data
        except Exception as e:
            _LOGGER.debug("Image download error: %s", e)
            return None
