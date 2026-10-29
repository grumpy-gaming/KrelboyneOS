"""What Stevie can do on the computer.

Each tool is a plain function plus a description the AI reads. Tools with
changes=True alter the system, so Stevie shows what it will do and waits for
a yes before running them.
"""

import glob
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field

MAX_OUTPUT = 6000  # characters of tool output sent back to the AI


@dataclass
class Tool:
    name: str
    description: str
    run: callable
    params: dict = field(default_factory=dict)  # name -> (JSON type, description)
    required: tuple = ()
    changes: bool = False
    summary: callable = None  # args -> one line saying what will happen, for the confirmation

    def schema(self):
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {k: {"type": t, "description": d} for k, (t, d) in self.params.items()},
                "required": list(self.required),
            },
        }}

    def describe(self, args):
        return self.summary(args) if self.summary else f"{self.name} {args}"


def clip(text):
    text = text.strip()
    if len(text) > MAX_OUTPUT:
        return text[:MAX_OUTPUT] + f"\n[... {len(text) - MAX_OUTPUT} more characters cut]"
    return text or "(no output)"


def run(args, timeout=60, shell=False):
    """Run a command; return its output and exit status as text for the AI."""
    try:
        # stdin is inherited, so sudo can still ask for the password in the terminal
        result = subprocess.run(args, shell=shell, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return f"Not available: {args[0] if isinstance(args, list) else args} is not installed."
    except subprocess.TimeoutExpired:
        return f"Stopped after {timeout} seconds without finishing."
    out = result.stdout + (("\n" + result.stderr) if result.stderr.strip() else "")
    status = "" if result.returncode == 0 else f"\n[exit status {result.returncode}]"
    return clip(out + status)


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


# ---- Read-only tools ----

def system_overview():
    lines = []
    for label, path in (("System disk", "/"), ("Home folder", os.path.expanduser("~"))):
        u = shutil.disk_usage(path)
        lines.append(f"{label} ({path}): {u.used * 100 // u.total}% used, {u.free / 1e9:.1f} GB free of {u.total / 1e9:.1f} GB")

    mem = {}
    for line in (read("/proc/meminfo") or "").splitlines():
        key, _, value = line.partition(":")
        mem[key] = int(value.split()[0]) if value.split() else 0
    if mem.get("MemTotal"):
        used = mem["MemTotal"] - mem.get("MemAvailable", 0)
        lines.append(f"Memory: {used / 1048576:.1f} of {mem['MemTotal'] / 1048576:.1f} GiB in use")

    uptime = read("/proc/uptime")
    if uptime:
        hours = float(uptime.split()[0]) / 3600
        load = " ".join((read("/proc/loadavg") or "").split()[:3])
        lines.append(f"Up for {hours:.1f} hours; load average {load}")

    for bat in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        cap, status = read(f"{bat}/capacity"), read(f"{bat}/status")
        full, design = read(f"{bat}/energy_full") or read(f"{bat}/charge_full"), \
            read(f"{bat}/energy_full_design") or read(f"{bat}/charge_full_design")
        health = ""
        if full and design and int(design):
            pct = int(full) * 100 // int(design)
            # Batteries count as worn below 80% of their design capacity
            health = f", holds {pct}% of its original charge ({'worn, consider replacing' if pct < 80 else 'healthy'})"
        lines.append(f"Battery {os.path.basename(bat)}: {cap}% ({status}){health}")

    temps = []
    for hwmon in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = read(f"{hwmon}/name") or os.path.basename(hwmon)
        for t in sorted(glob.glob(f"{hwmon}/temp*_input")):
            value = read(t)
            if value and value.lstrip("-").isdigit():
                label = read(t.replace("_input", "_label")) or os.path.basename(t)
                temps.append(f"{name} {label} {int(value) / 1000:.0f}°C")
    if temps:
        lines.append("Temperatures: " + "; ".join(temps[:12]))

    clock = run(["timedatectl", "show", "-p", "NTP", "-p", "NTPSynchronized", "-p", "Timezone"]).replace("\n", ", ")
    lines.append(f"Clock: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}; {clock}")

    lines.append("Network:\n" + run(["ip", "-brief", "address"]))
    return "\n".join(lines)


def disk_usage(path="~"):
    path = os.path.expanduser(path or "~")
    return run(f"du -xh --max-depth=1 {shlex.quote(path)} 2>/dev/null | sort -rh | head -n 15", timeout=90, shell=True)


def failed_services():
    system = run(["systemctl", "--failed", "--no-legend", "--plain"])
    user = run(["systemctl", "--user", "--failed", "--no-legend", "--plain"])
    return f"System services:\n{system}\n\nUser services:\n{user}"


def recent_errors(unit=None, lines=40):
    args = ["journalctl", "-b", "-p", "err", "-n", str(min(int(lines or 40), 200)), "--no-pager", "-o", "short-iso"]
    if unit:
        args += ["-u", unit]
    return run(args)


def kos_doctor_check():
    return run(["kos-doctor", "--check"], timeout=120)


def kos_doctor_explain(check_id):
    return run(["kos-doctor", "--explain", check_id])


def package_info(name):
    return run(f"dpkg-query -W -f='${{Package}} ${{Version}} ${{db:Status-Abbrev}}\\n' {shlex.quote(name)} 2>&1; "
               f"apt-cache policy {shlex.quote(name)}", shell=True)


def list_updates():
    return run(["apt", "list", "--upgradable"])


# ---- Tools that change things (Stevie asks first) ----

def kos_doctor_fix(check_id):
    return run(["kos-doctor", "--fix", check_id, "--yes"], timeout=900)


def install_package(name):
    return run(["kos-install-tools", "apt", name], timeout=1800)


def install_kos_tool(name):
    return run(["kos-install-tools", "install", name], timeout=1800)


def find_desktop_entries(name):
    dirs = [os.path.expanduser("~/.local/share/applications"), "/usr/share/applications",
            "/var/lib/flatpak/exports/share/applications"]
    needle = name.lower()
    hits = []
    for d in dirs:
        for path in sorted(glob.glob(f"{d}/*.desktop")):
            app_id = os.path.basename(path)[:-len(".desktop")]
            title = next((line[5:] for line in (read(path) or "").splitlines() if line.startswith("Name=")), app_id)
            if needle in app_id.lower() or needle in title.lower():
                hits.append((app_id, title))
    return hits


def open_app(name):
    hits = find_desktop_entries(name)
    if not hits:
        return f"No installed app matches '{name}'."
    exact = [h for h in hits if name.lower() in (h[0].lower(), h[1].lower())]
    if len(exact) != 1 and len(hits) > 1:
        return "Several apps match; ask which one: " + ", ".join(f"{t} ({i})" for i, t in hits[:10])
    app_id, title = (exact or hits)[0]
    subprocess.Popen(["gtk-launch", app_id], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return f"Started {title}."


def open_url(url):
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    if not url.startswith(("https://", "http://")):
        return "Only web addresses (http or https) can be opened."
    subprocess.Popen(["xdg-open", url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return f"Opened {url} in the default browser."


def run_command(command):
    return run(command, timeout=300, shell=True)


TOOLS = [
    Tool("system_overview", "Disk space, memory, uptime, battery health, temperatures and network addresses of this computer.",
         system_overview),
    Tool("disk_usage", "The biggest folders inside a folder, largest first. Use to find what is filling the disk.",
         disk_usage, {"path": ("string", "Folder to look in; defaults to the home folder")}),
    Tool("failed_services", "System and user background services that failed to start.", failed_services),
    Tool("recent_errors", "Error messages from the system log since the last boot, optionally for one service.",
         recent_errors,
         {"unit": ("string", "systemd unit name, e.g. postgresql.service; leave out for all"),
          "lines": ("integer", "How many lines, up to 200 (default 40)")}),
    Tool("kos_doctor_check", "Run KOS Doctor's full checkup: drive health, disk, memory and known KrelboyneOS problems with their check ids.",
         kos_doctor_check),
    Tool("kos_doctor_explain", "Explain one KOS Doctor check: what is wrong and how it is fixed.",
         kos_doctor_explain, {"check_id": ("string", "Check id from kos_doctor_check")}, ("check_id",)),
    Tool("package_info", "Whether a Debian package is installed, its version, and versions available.",
         package_info, {"name": ("string", "Debian package name")}, ("name",)),
    Tool("list_updates", "Packages with updates waiting.", list_updates),

    Tool("kos_doctor_fix", "Apply KOS Doctor's fix for one check. May ask the user for their password.",
         kos_doctor_fix, {"check_id": ("string", "Check id from kos_doctor_check")}, ("check_id",),
         changes=True, summary=lambda a: f"run KOS Doctor's fix for '{a.get('check_id')}'"),
    Tool("install_package", "Install a Debian package with apt. Asks the user for their password.",
         install_package, {"name": ("string", "Debian package name")}, ("name",),
         changes=True, summary=lambda a: f"install the Debian package '{a.get('name')}'"),
    Tool("install_kos_tool", "Install an optional tool from KOS Software (tools not in Debian, e.g. burp, metasploit, playwright_mcp).",
         install_kos_tool, {"name": ("string", "KOS Software tool id")}, ("name",),
         changes=True, summary=lambda a: f"install '{a.get('name')}' from KOS Software"),
    Tool("open_app", "Open an installed desktop app by name.",
         open_app, {"name": ("string", "App name, e.g. Firefox or Steam")}, ("name",),
         changes=True, summary=lambda a: f"open the app '{a.get('name')}'"),
    Tool("open_url", "Open a web address in the user's default browser.",
         open_url, {"url": ("string", "Web address, e.g. krelboyneos.org")}, ("url",),
         changes=True, summary=lambda a: f"open {a.get('url')} in your browser"),
    Tool("run_command", "Run a shell command as the user and return its output. Use only when no other tool fits.",
         run_command, {"command": ("string", "The exact shell command")}, ("command",),
         changes=True, summary=lambda a: f"run this command:\n    {a.get('command')}"),
]

BY_NAME = {t.name: t for t in TOOLS}
