import json
import urllib.request
import urllib.error

BASE_URL = "https://api.petcube.com"

class PetcubeAPI:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.token = None
        self.user_id = None

    def login(self):
        data = json.dumps({"email": self.email, "password": self.password}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/login",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Petcube/8.3.0 Android",
                "X-App-Platform": "android"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            d = resp.get("data", resp)
            self.token = d.get("token")
            user = d.get("user", {})
            self.user_id = user.get("id") if isinstance(user, dict) else None
            return self.token is not None

    def _headers(self):
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Petcube/8.3.0 Android",
            "X-App-Platform": "android"
        }

    def get_devices(self):
        endpoints = []
        if self.user_id:
            endpoints.append(f"{BASE_URL}/api/v1/users/{self.user_id}/petcubes")
        endpoints.append(f"{BASE_URL}/api/v1/petcubes")

        for url in endpoints:
            try:
                req = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(req, timeout=10) as r:
                    raw = r.read()
                    if not raw:
                        continue
                    resp = json.loads(raw)
                    devices = resp.get("data", resp)
                    if isinstance(devices, list) and len(devices) > 0:
                        return devices
            except urllib.error.HTTPError:
                continue
        return []

    def launch_treat(self, device_id, strength=1):
        if not self.token:
            self.login()
        url = f"{BASE_URL}/api/v1/deviceActivity/treats/launch/{device_id}"
        data = json.dumps({"strength": strength}).encode()
        try:
            req = urllib.request.Request(url, data=data, headers=self._headers())
            with urllib.request.urlopen(req, timeout=15) as r:
                return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Token expiré — re-login et réessayer
                self.login()
                req = urllib.request.Request(url, data=data, headers=self._headers())
                with urllib.request.urlopen(req, timeout=15) as r:
                    return True
            raise
