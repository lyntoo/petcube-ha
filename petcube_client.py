#!/usr/bin/env python3
"""
Petcube local API client.
Cloud auth + device listing + treat dispense via cloud API.
TLS probe on local port 35000 for future protocol reverse-engineering.

Credentials are entered interactively and never stored to disk.
"""

import getpass
import json
import socket
import ssl
import sys
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE    = "https://api.petcube.com/"
DEVICE_IP   = "10.0.0.116"
DEVICE_PORT = 35000
BUILD_NUM   = 80030000
APP_VERSION = "8.3.0"

# Certs extracted from APK assets / libpet.so
CERT_DIR    = Path(__file__).parent
CA_CRT      = CERT_DIR / "ca.crt"
CLI_CRT     = CERT_DIR / "cli_ndk.crt"
CLI_KEY     = CERT_DIR / "cli_ndk.key.pem"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _session(token: str, bearer: bool = False) -> requests.Session:
    s = requests.Session()
    prefix = "Bearer" if bearer else "Token"
    s.headers.update({
        "Authorization": f"{prefix} {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "User-Agent":    f"Petcube/{APP_VERSION} Android",
        "X-App-Platform": "android",
        "X-App-AVer":    APP_VERSION,
    })
    return s


def _data(resp: requests.Response) -> dict:
    resp.raise_for_status()
    body = resp.json()
    return body.get("data", body)


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> tuple[str, dict]:
    """
    POST api/v1/login → legacy token + user object.
    The legacy token is used as "Authorization: Token {token}" for all REST calls.
    Returns (legacy_token, user_dict).
    """
    resp = requests.post(
        f"{API_BASE}api/v1/login",
        json={"email": email, "password": password},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    body = _data(resp)
    legacy_token = body["token"]
    user = body.get("user", {})
    print(f"[auth] Login OK — user id={user.get('id')}")
    return legacy_token, user


def get_profile(session: requests.Session) -> dict:
    return _data(session.get(f"{API_BASE}api/v1/user/profile"))


# ── Devices ───────────────────────────────────────────────────────────────────

def list_devices(session: requests.Session, user_id: int) -> list:
    return _data(session.get(f"{API_BASE}api/v1/users/{user_id}/petcubes"))


def print_devices(devices: list) -> None:
    print(f"\n{'─'*60}")
    print(f"  {'ID':>10}  {'Name':<25}  {'Type':<12}  Treat?")
    print(f"{'─'*60}")
    for d in devices:
        treat = "✓" if d.get("i_can_use_treat_dispenser") else " "
        print(f"  {d['id']:>10}  {d.get('name','?'):<25}  {d.get('device_type','?'):<12}  {treat}")
    print(f"{'─'*60}\n")


def print_device_raw(session: requests.Session, device_id: int) -> None:
    """Dump all fields for a device — useful to find serial, prod_rev, etc."""
    import json
    resp = session.get(f"{API_BASE}api/v1/petcubes/{device_id}")
    try:
        d = _data(resp)
    except Exception:
        d = resp.json()
    # Redact any token-like fields just in case
    redact = {"token", "access_token", "refresh_token", "password", "secret"}
    def _safe(obj, depth=0):
        if isinstance(obj, dict):
            return {k: ("***" if k.lower() in redact else _safe(v, depth+1))
                    for k, v in obj.items()}
        if isinstance(obj, list):
            return [_safe(i, depth+1) for i in obj]
        return obj
    print(json.dumps(_safe(d), indent=2))


# ── Cloud actions ─────────────────────────────────────────────────────────────

def check_firmware_update(session: requests.Session, device_id: int, fake_ver: str = "") -> dict:
    """GET api/v1/pet-tracker/available-update/{id} → firmware downloadLink if available."""
    url = f"{API_BASE}api/v1/pet-tracker/available-update/{device_id}"
    if fake_ver:
        url += f"?softVer={fake_ver}"
    resp = session.get(url)
    try:
        return _data(resp)
    except Exception:
        return resp.json() if resp.content else {}


def get_firmware_direct(session: requests.Session, device_id: int) -> dict:
    """Try alternate firmware endpoints."""
    results = {}
    for path in [
        f"api/v1/petcubes/{device_id}/firmware",
        f"api/v1/petcubes/{device_id}/settings",
        f"api/v1/pet-tracker/mstr/devices/{device_id}",
    ]:
        resp = session.get(f"{API_BASE}{path}")
        if resp.status_code == 200:
            results[path] = resp.json()
    return results


def get_release_notes(session: requests.Session, soft_ver: str) -> dict:
    """GET api/v1/release-notes/{softVer} → release notes for a firmware version."""
    resp = session.get(f"{API_BASE}api/v1/release-notes/{soft_ver}")
    try:
        return _data(resp)
    except Exception:
        return resp.json() if resp.content else {}


def dispense_treat(session: requests.Session, device_id: int, strength: int = 1) -> None:
    """POST api/v1/deviceActivity/treats/launch/{id} with strength payload."""
    resp = session.post(
        f"{API_BASE}api/v1/deviceActivity/treats/launch/{device_id}",
        json={"strength": strength},
    )
    if resp.status_code in (200, 201, 204):
        print(f"[treat] Dispensed (strength={strength}) ✓")
    else:
        print(f"[treat] Failed: {resp.status_code} {resp.text}")


# ── Local probe ──────────────────────────────────────────────────────────────

def _recv_all(sock: socket.socket, timeout: float) -> bytes:
    sock.settimeout(timeout)
    buf = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
    except socket.timeout:
        pass
    return buf


def probe_local(token: str, user_id: int, timeout: float = 5.0) -> None:
    """
    Multi-stage probe on device port 35000:
      1. Raw TCP banner (no TLS)
      2. TLS with old cipher suites (device firmware is old)
      3. UDP banner
    """
    print(f"\n[probe] ── Stage 1: raw TCP on {DEVICE_IP}:{DEVICE_PORT} ──")
    try:
        raw = socket.create_connection((DEVICE_IP, DEVICE_PORT), timeout=timeout)
        banner = _recv_all(raw, timeout=2.0)
        if banner:
            print(f"[probe] TCP banner ({len(banner)} bytes): {banner[:256]}")
            print(f"[probe] hex: {banner[:64].hex()}")
        else:
            print("[probe] TCP connected, no banner — server waits for client")
            # Send a raw hello and see what comes back
            raw.sendall(b"\x00\x01\x00\x00")
            reply = _recv_all(raw, timeout=2.0)
            print(f"[probe] Reply to 4-byte probe: {reply[:256] or b'(empty)'}")
        raw.close()
    except (ConnectionRefusedError, OSError) as e:
        print(f"[probe] TCP failed: {e}")

    print(f"\n[probe] ── Stage 2: TLS (legacy ciphers) on {DEVICE_IP}:{DEVICE_PORT} ──")
    if not (CLI_CRT.exists() and CLI_KEY.exists() and CA_CRT.exists()):
        print("[probe] Cert files missing")
    else:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_verify_locations(cafile=str(CA_CRT))
        ctx.load_cert_chain(certfile=str(CLI_CRT), keyfile=str(CLI_KEY))
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.minimum_version = ssl.TLSVersion.TLSv1      # device firmware may need TLS 1.0/1.1
        ctx.set_ciphers("ALL:@SECLEVEL=0")               # allow old cipher suites
        try:
            raw2 = socket.create_connection((DEVICE_IP, DEVICE_PORT), timeout=timeout)
            tls = ctx.wrap_socket(raw2, server_hostname=DEVICE_IP)
            print(f"[probe] TLS handshake OK — {tls.version()} cipher={tls.cipher()[0]}")
            banner2 = _recv_all(tls, timeout=2.0)
            if banner2:
                print(f"[probe] TLS banner: {banner2[:256]}")
                print(f"[probe] hex: {banner2[:64].hex()}")
            else:
                print("[probe] No TLS banner — sending SIP OPTIONS")
                probe = (
                    f"OPTIONS sip:{user_id}@{DEVICE_IP} SIP/2.0\r\n"
                    f"Via: SIP/2.0/TLS 127.0.0.1:5060;branch=z9hG4bKprobe\r\n"
                    f"From: <sip:{user_id}@petcube.com>;tag=probe\r\n"
                    f"To: <sip:{user_id}@{DEVICE_IP}>\r\n"
                    f"Call-ID: probe@petcube-py\r\n"
                    f"CSeq: 1 OPTIONS\r\nContent-Length: 0\r\n\r\n"
                ).encode()
                tls.sendall(probe)
                reply2 = _recv_all(tls, timeout=2.0)
                print(f"[probe] SIP reply: {reply2[:256] or b'(no response)'}")
            tls.close()
        except ssl.SSLError as e:
            print(f"[probe] TLS error: {e}")
        except (ConnectionRefusedError, OSError) as e:
            print(f"[probe] TLS connect failed: {e}")

    print(f"\n[probe] ── Stage 3: UDP on {DEVICE_IP}:{DEVICE_PORT} ──")
    try:
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.settimeout(timeout)
        udp.sendto(b"\x00\x01\x00\x00", (DEVICE_IP, DEVICE_PORT))
        data, addr = udp.recvfrom(4096)
        print(f"[probe] UDP response from {addr}: {data[:256]}")
        print(f"[probe] hex: {data[:64].hex()}")
        udp.close()
    except socket.timeout:
        print("[probe] UDP: no response (port may be TCP only)")
    except OSError as e:
        print(f"[probe] UDP error: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Petcube client — credentials are not stored\n")

    email    = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    # 1. Cloud auth — legacy Token header
    legacy_token, user = login(email, password)
    session = _session(legacy_token, bearer=False)

    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        user = get_profile(session)
        user_id = user.get("id")
    print(f"[auth] Logged in as {user.get('username', user.get('email', '?'))} (id={user_id})")

    # 3. List devices
    devices = list_devices(session, user_id)
    print_devices(devices)

    if not devices:
        print("No devices found.")
        return

    # 4. Pick device (default: first one with treat dispenser, else first)
    treat_devices = [d for d in devices if d.get("i_can_use_treat_dispenser")]
    target = treat_devices[0] if treat_devices else devices[0]
    print(f"Target: {target['name']} (id={target['id']}, ip={DEVICE_IP})")

    # 5. Menu
    while True:
        print("\n[1] Dispense treat (cloud)  [2] Local TLS probe  [3] Raw device info  [4] Firmware update check  [5] Release notes  [q] Quit")
        choice = input("> ").strip().lower()

        if choice == "1":
            dispense_treat(session, target["id"])

        elif choice == "2":
            probe_local(legacy_token, user_id)

        elif choice == "3":
            print_device_raw(session, target["id"])

        elif choice == "4":
            # Try versions just below current (0.7.82.4007) to get download URL
            versions = [
                "0.7.82.4006", "0.7.82.4000", "0.7.82.0",
                "0.7.81.0", "0.7.80.0", "0.7.75.0",
                "0.7.70.0", "0.7.60.0", "0.7.50.0",
                "0.6.99.0", "0.6.0.0", "0.5.99.0",
            ]
            for ver in versions:
                fw = check_firmware_update(session, target["id"], fake_ver=ver)
                if fw and "errors" not in fw:
                    print(f"\n[fw] *** HIT with ver={ver} ***")
                    print(json.dumps(fw, indent=2))
                    break
                else:
                    err = fw.get("errors", fw) if fw else "empty"
                    print(f"[fw] {ver}: {err}")

            # Also try alternate endpoints
            print("\n[fw] Trying alternate endpoints...")
            alt = get_firmware_direct(session, target["id"])
            for path, data in alt.items():
                print(f"\n  {path}:")
                print(json.dumps(data, indent=2)[:500])

        elif choice == "5":
            soft_ver = target.get("soft_ver", "0.7.82.4007")
            notes = get_release_notes(session, soft_ver)
            print(json.dumps(notes, indent=2))

        elif choice == "q":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye.")
    except requests.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
