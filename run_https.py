"""Run the local Flask app behind Caddy and stop both processes together."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _lan_ip() -> str | None:
    """Find the IPv4 address used by the default network route."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # UDP connect chooses a route without sending a packet.
            sock.connect(("192.0.2.1", 80))
            address = sock.getsockname()[0]
            if not address.startswith(("127.", "169.254.")) and address != "0.0.0.0":
                return address
    except OSError:
        pass
    return None


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main() -> int:
    caddy = shutil.which("caddy")
    if not caddy:
        print("Caddy was not found in PATH. Install Caddy and restart start.bat.", file=sys.stderr)
        return 1

    config = BASE_DIR / "Caddyfile"
    lan_ip = _lan_ip()
    caddy_env = os.environ.copy()
    addresses = ["localhost", "127.0.0.1"]
    if lan_ip:
        addresses.append(lan_ip)
    else:
        print("No LAN IPv4 address found; HTTPS will be available locally only.", file=sys.stderr)
    caddy_env["FILE_CONVERTER_SITE_ADDRESSES"] = ", ".join(addresses)
    try:
        validation = subprocess.run([caddy, "validate", "--config", str(config)], cwd=BASE_DIR, env=caddy_env)
    except OSError as exc:
        print(f"Could not run Caddy at {caddy}: {exc}", file=sys.stderr)
        if getattr(exc, "winerror", None) == 1260:
            print("Windows application control blocked Caddy. Ask your administrator to allow it.", file=sys.stderr)
        return 1
    if validation.returncode:
        return validation.returncode

    flask_env = os.environ.copy()
    flask_env["PORT"] = "5000"
    flask = subprocess.Popen([sys.executable, str(BASE_DIR / "app.py")], cwd=BASE_DIR, env=flask_env)
    try:
        caddy_process = subprocess.Popen([caddy, "run", "--config", str(config)], cwd=BASE_DIR, env=caddy_env)
    except OSError as exc:
        _stop(flask)
        print(f"Could not start Caddy at {caddy}: {exc}", file=sys.stderr)
        if getattr(exc, "winerror", None) == 1260:
            print("Windows application control blocked Caddy. Ask your administrator to allow it.", file=sys.stderr)
        return 1

    print("File Converter: https://localhost/ (or https://127.0.0.1/)", flush=True)
    if lan_ip:
        print(f"LAN access: https://{lan_ip}/", flush=True)
    try:
        while True:
            for process, name in ((flask, "Flask"), (caddy_process, "Caddy")):
                result = process.poll()
                if result is not None:
                    print(f"{name} exited with code {result}.", file=sys.stderr)
                    return result or 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 0
    finally:
        _stop(caddy_process)
        _stop(flask)


if __name__ == "__main__":
    sys.exit(main())
