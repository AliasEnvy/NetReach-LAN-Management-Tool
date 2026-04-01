#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║            NEXUS  ·  LAN Commander Pro  v1.0                     ║
║   SSH Auto-Discovery · Wake · Shutdown · Messages · AnyDesk      ║
║   Fedora · Ubuntu · Arch · Windows  —  Zero external deps        ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
except ImportError:
    print("\n[ERROR] tkinter missing.\n  Fedora: sudo dnf install python3-tkinter -y\n  Ubuntu: sudo apt install python3-tk -y\n")
    sys.exit(1)

import subprocess, threading, json, socket, re, time
import platform, ipaddress, shutil, struct, wave, math, io, tempfile
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  PLATFORM
# ─────────────────────────────────────────────────────────────────────────────
_OS    = platform.system()
IS_WIN = _OS == "Windows"
IS_LIN = _OS == "Linux"
IS_MAC = _OS == "Darwin"

try:    import winsound as _winsound; HAS_WS = True
except: HAS_WS = False

FF = "Tahoma" if IS_WIN else "Liberation Sans"
FM = "Courier New" if IS_WIN else "DejaVu Sans Mono"
def F(s=9, b=False): return (FF, s, "bold" if b else "normal")
def FX(s=9):         return (FM, s, "normal")

# ─────────────────────────────────────────────────────────────────────────────
#  COLOURS  —  XP Luna + NEXUS dark-blue accent
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":     "#ECE9D8", "bg2": "#D4D0C8", "bg3": "#F5F4EA",
    # Title gradient anchors (deep navy → bright blue)
    "ta":     "#071642", "tb":  "#1A4EA0", "tc":  "#4080C8",
    # Button face / states
    "bf":     "#ECE9D8", "bhi": "#DDEEFF", "bact":"#C0D8F8",
    "blo":    "#ACA899", "bsh": "#716F64",
    # Accent blues
    "sel":    "#2455A4", "sel2":"#1A3F8A", "sel3":"#D0E4FF",
    # Status colours
    "on":     "#1E7A1E", "on2": "#D0EED0",
    "off":    "#808080", "off2":"#F0F0F0",
    "wak":    "#C05800", "wak2":"#FFE8C0",
    "shut":   "#A80000", "sh2": "#FFE0E0",
    "disc":   "#4040B0", "di2": "#E0E0FF",
    # Misc
    "sep":    "#ACA899", "gray": "#888888", "gray2":"#CCCCCC",
    "card_a": "#FFFFFF", "card_b":"#F0F5FC",
    "card_s": "#E0ECFF", "card_bd":"#C4D2E8",
    "log_bg": "#080E18", "log_fg":"#7AAAC8",
    "chat_me":"#D4F0C4", "chat_th":"#FFFFFF",
    "btblue": "#1AABF0", "white":"#FFFFFF",
    # Button type colours
    "btn_n":  "#ECE9D8", "btn_w":  "#FFF0D0",
    "btn_d":  "#F0D8D8", "btn_g":  "#D0EED0",
    "btn_b":  "#D0E4FF",
}

APP_NAME    = "NEXUS  ·  LAN Commander Pro"
APP_VER     = "v1.0"
MSG_PORT    = 47779
DB_FILE     = Path.home() / ".nexus_lancommander.json"

# ─────────────────────────────────────────────────────────────────────────────
#  AUDIO  —  synthesised XP-authentic sounds, zero deps
# ─────────────────────────────────────────────────────────────────────────────
def _synth(notes, rate=22050):
    """Multi-note WAV with ADSR + harmonics."""
    out = bytearray()
    for entry in notes:
        freq, ms = entry[0], entry[1]
        vol      = entry[2] if len(entry) > 2 else 0.50
        shape    = entry[3] if len(entry) > 3 else "sine"
        n   = int(rate * ms / 1000)
        att = max(1, int(rate * 0.010))
        dec = max(1, int(rate * 0.055))
        rel = max(1, int(rate * 0.120))
        for i in range(n):
            t = i / rate
            # Envelope
            if   i < att:         env = i / att
            elif i < att + dec:   env = 1.0 - 0.28 * (i - att) / dec
            elif i >= n - rel:    env = max(0.0, (n - i) / rel) * 0.72
            else:                 env = 0.72
            # Waveform
            w = 2 * math.pi * freq * t
            if shape == "bell":
                s = (math.sin(w) + math.sin(2*w)*0.45*math.exp(-4*t)
                                 + math.sin(3*w)*0.18*math.exp(-7*t))
                s /= 1.63
            elif shape == "soft":
                s = math.sin(w) + math.sin(2*w)*0.15; s /= 1.15
            else:   # sine
                s = math.sin(w) + math.sin(2*w)*0.08; s /= 1.08
            val = max(-32767, min(32767, int(32767 * vol * env * s)))
            out += struct.pack("<h", val)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(bytes(out))
    return buf.getvalue()

def _play_wav(data):
    if IS_WIN and HAS_WS:
        _winsound.PlaySound(data, _winsound.SND_MEMORY | _winsound.SND_ASYNC); return
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.write(data); tmp.flush(); tmp.close()
    for cmd in (["aplay","-q",tmp.name], ["paplay",tmp.name],
                ["afplay",tmp.name],
                ["ffplay","-nodisp","-autoexit","-loglevel","quiet",tmp.name]):
        if shutil.which(cmd[0]):
            try: subprocess.Popen(cmd, stderr=subprocess.DEVNULL); return
            except: pass

# 22 XP-authentic sounds
_SFX = {
    "logon":       [(523,130,.50,"bell"),(659,130,.52,"bell"),(784,130,.54,"bell"),(1047,130,.56,"bell"),(1319,400,.60,"bell")],
    "startup":     [(392,100,.46,"bell"),(523,100,.48,"bell"),(659,100,.50,"bell"),(784,100,.52,"bell"),(1047,360,.58,"bell")],
    "error":       [(440,190,.56,"sine"),(349,190,.56,"sine"),(294,320,.52,"sine")],
    "exclaim":     [(659,140,.54,"sine"),(523,210,.50,"sine")],
    "notify":      [(1047,75,.44,"bell"),(1319,165,.50,"bell")],
    "ding":        [(1047,310,.55,"bell")],
    "chord":       [(523,85,.44,"soft"),(659,85,.46,"soft"),(784,85,.47,"soft"),(1047,210,.52,"bell")],
    "tada":        [(523,62,.44,"soft"),(659,62,.46,"soft"),(784,62,.47,"soft"),(1047,62,.49,"soft"),(1319,62,.51,"soft"),(1047,62,.49,"soft"),(1319,350,.60,"bell")],
    "shutdown_snd":[(784,140,.50,"soft"),(659,140,.50,"soft"),(523,140,.50,"soft"),(392,370,.55,"bell")],
    "connect":     [(880,65,.40,"soft"),(1047,65,.43,"soft"),(1319,155,.48,"bell")],
    "disconnect":  [(1319,65,.40,"soft"),(1047,65,.38,"soft"),(880,155,.36,"bell")],
    "msg_in":      [(1047,58,.38,"bell"),(1319,118,.44,"bell")],
    "sound_ping":  [(880,58,.40,"soft"),(1047,58,.42,"soft"),(880,58,.40,"soft"),(1047,58,.42,"soft"),(1319,210,.50,"bell")],
    "boot":        [(130,720,.32,"soft"),(196,720,.36,"soft"),(261,720,.38,"soft"),(392,940,.44,"bell")],
    "wol_sent":    [(659,82,.38,"soft"),(784,82,.40,"soft"),(1047,210,.48,"bell")],
    "click":       [(1100,22,.26,"sine")],
    "online":      [(784,72,.38,"soft"),(1047,185,.46,"bell")],
    "offline":     [(523,72,.36,"soft"),(392,185,.40,"bell")],
    "question":    [(523,82,.38,"soft"),(659,82,.40,"soft"),(784,82,.42,"soft"),(659,260,.40,"bell")],
    "scan_done":   [(523,72,.38,"soft"),(784,72,.40,"soft"),(1047,72,.42,"soft"),(1319,290,.52,"bell")],
    "critical":    [(349,200,.58,"sine"),(294,200,.58,"sine"),(247,320,.55,"sine")],
    "mail":        [(1047,82,.40,"bell"),(1175,82,.42,"bell"),(1319,82,.44,"bell"),(1047,290,.50,"bell")],
}

_cache: dict = {}
def _get_wav(n):
    if n not in _cache: _cache[n] = _synth(_SFX.get(n, [(880,120,.44,"soft")]))
    return _cache[n]
def play(n):
    threading.Thread(target=lambda: _play_wav(_get_wav(n)), daemon=True).start()
def precache():
    for k in _SFX: _get_wav(k)

# ─────────────────────────────────────────────────────────────────────────────
#  NETWORK HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def local_network():
    best = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1); s.connect(("8.8.8.8", 80))
        best = s.getsockname()[0]; s.close()
        if best.startswith("127."): best = None
    except: pass
    if not best and IS_LIN and shutil.which("ip"):
        try:
            o = subprocess.check_output(["ip","route","get","8.8.8.8"],
                stderr=subprocess.DEVNULL,timeout=3).decode(errors="ignore")
            m = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", o)
            if m and not m.group(1).startswith("127."): best = m.group(1)
        except: pass
    if not best and IS_LIN:
        try:
            for ip in subprocess.check_output(["hostname","-I"],
                    stderr=subprocess.DEVNULL,timeout=2).decode().split():
                if re.match(r"\d+\.\d+\.\d+\.\d+$",ip) and not ip.startswith("127."):
                    best = ip; break
        except: pass
    if best:
        p = best.split(".")
        return f"{p[0]}.{p[1]}.{p[2]}.0/24", best, f"{p[0]}.{p[1]}.{p[2]}.255"
    return "192.168.0.0/24","192.168.0.1","192.168.0.255"

def bcast_for(ip):
    try: p=ip.split("."); return f"{p[0]}.{p[1]}.{p[2]}.255"
    except: return "255.255.255.255"

def ping_host(ip, timeout=1):
    try:
        cmd = ["ping","-n","1","-w",str(timeout*1000),ip] if IS_WIN \
              else ["ping","-c","1","-W",str(timeout),ip]
        return subprocess.run(cmd,capture_output=True,timeout=timeout+2).returncode==0
    except: return False

def tcp_check(ip, port, timeout=1.5):
    try:
        with socket.create_connection((ip,port),timeout=timeout): return True
    except: return False

def mac_norm(mac):
    raw = re.sub(r"[^0-9a-fA-F]","",str(mac))
    if len(raw)==12:
        return ":".join(raw[i:i+2].lower() for i in range(0,12,2))
    return None

def hostname_of(ip):
    try: return socket.gethostbyaddr(ip)[0].split(".")[0]
    except: return ""

def arp_table():
    t = {}
    if IS_LIN and shutil.which("ip"):
        try:
            for line in subprocess.check_output(["ip","neigh","show"],
                    stderr=subprocess.DEVNULL,timeout=5).decode(errors="ignore").splitlines():
                p=line.split()
                if "lladdr" in p:
                    m=mac_norm(p[p.index("lladdr")+1])
                    if m and m!="ff:ff:ff:ff:ff:ff":
                        try: socket.inet_aton(p[0]); t[p[0]]=m
                        except: pass
        except: pass
    if IS_LIN:
        try:
            with open("/proc/net/arp") as f:
                for line in f.readlines()[1:]:
                    p=line.split()
                    if len(p)>=4 and p[3] not in ("00:00:00:00:00:00",""):
                        m=mac_norm(p[3])
                        if m: t.setdefault(p[0],m)
        except: pass
    try:
        cmd=["arp","-a"] if IS_WIN else ["arp","-n"]
        for line in subprocess.check_output(cmd,stderr=subprocess.DEVNULL,
                timeout=5).decode(errors="ignore").splitlines():
            p=line.split(); ic=p[0].strip("()")
            mc=next((x for x in p if re.match(r"([0-9a-fA-F]{1,2}[:\-]){5}[0-9a-fA-F]{1,2}",x)),"")
            try:
                socket.inet_aton(ic); m=mac_norm(mc)
                if m and m!="ff:ff:ff:ff:ff:ff": t.setdefault(ic,m)
            except: pass
    except: pass
    return t

def send_wol(mac, bcast="255.255.255.255"):
    try:
        raw=re.sub(r"[^0-9a-fA-F]","",mac)
        if len(raw)!=12: return False
        pkt=b"\xff"*6+bytes.fromhex(raw)*16
        for bc in [bcast,"255.255.255.255"]:
            for port in (7,9):
                try:
                    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                        s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
                        s.settimeout(2); s.sendto(pkt,(bc,port))
                except: pass
        return True
    except: return False

OUI = {
    "00:50:56":"VMware","00:0c:29":"VMware","00:15:5d":"Hyper-V",
    "b8:27:eb":"Raspberry Pi","dc:a6:32":"Raspberry Pi",
    "e4:5f:01":"Raspberry Pi","d8:3a:dd":"Raspberry Pi",
    "3c:22:fb":"Apple","a4:c3:f0":"Apple","f0:18:98":"Apple","78:4f:43":"Apple",
    "00:1d:09":"Dell","14:18:77":"Dell","b8:ac:6f":"Dell","f8:db:88":"Dell",
    "18:db:f2":"Dell","d4:ae:52":"Dell","a4:bb:6d":"Dell",
    "00:1b:21":"Intel","8c:8d:28":"Intel","e4:b9:7a":"Intel",
    "00:1f:16":"Lenovo","54:ee:75":"Lenovo","28:d2:44":"Lenovo",
    "00:24:be":"HP","3c:d9:2b":"HP","1c:98:ec":"HP",
    "18:a9:05":"Cisco","00:1e:13":"Cisco",
    "00:11:32":"Synology","00:08:9b":"QNAP",
    "d8:cb:8a":"ASUS","10:bf:48":"ASUS","cc:2d:e0":"ASUS",
    "c8:5b:76":"TP-Link","54:a7:03":"TP-Link",
    "30:de:4b":"Netgear","20:4e:7f":"Ubiquiti",
    "74:83:c2":"Xiaomi","50:8f:4c":"Realtek","00:e0:4c":"Realtek",
}
def oui(mac): return OUI.get(mac[:8].lower(),"Unknown")

COMMON_PORTS = {
    22:"SSH",80:"HTTP",443:"HTTPS",3389:"RDP",5900:"VNC",
    8080:"HTTP-alt",445:"SMB",21:"FTP",139:"NetBIOS",
    3306:"MySQL",5432:"PostgreSQL",6379:"Redis",9090:"WebUI",
}

# ─────────────────────────────────────────────────────────────────────────────
#  SSH ENGINE  —  key-auth + password fallback, parallel probing
# ─────────────────────────────────────────────────────────────────────────────
SSH_USERS = [
    "pi","ubuntu","debian","fedora","centos","rocky","alma","arch",
    "admin","administrator","root","user","kali","alarm",
    "vagrant","git","ec2-user","ansible","devops","deploy",
    "linuxuser","homeuser","server","nas","media","plex",
]

# Options for KEY-BASED (no-password) probes — fast, non-interactive
_SSH_KEY_OPTS = [
    "-o","StrictHostKeyChecking=no",
    "-o","ConnectTimeout=3",
    "-o","BatchMode=yes",
    "-o","LogLevel=ERROR",
    "-o","PasswordAuthentication=no",
    "-o","KbdInteractiveAuthentication=no",
    "-o","ChallengeResponseAuthentication=no",
    "-o","PubkeyAuthentication=yes",
]

# Options for PASSWORD-BASED connections (via sshpass or expect)
_SSH_PASS_OPTS = [
    "-o","StrictHostKeyChecking=no",
    "-o","ConnectTimeout=5",
    "-o","BatchMode=no",
    "-o","LogLevel=ERROR",
    "-o","PubkeyAuthentication=no",
    "-o","PreferredAuthentications=password,keyboard-interactive",
]

# In-memory password store — never written to disk
_ssh_passwords: dict = {}   # ip -> password

def has_sshpass():
    return shutil.which("sshpass") is not None

def ssh_run(ip, user, cmd, timeout=8, password=None):
    """
    Run cmd via SSH. Returns (stdout, stderr, returncode).
    Uses sshpass for password auth if password given or stored.
    Falls back to key auth if no password.
    """
    if not shutil.which("ssh"):
        return "", "ssh not found", 127

    pwd = password or _ssh_passwords.get(ip)

    if pwd and has_sshpass():
        # Password auth via sshpass
        args = (["sshpass", "-p", pwd, "ssh"] + _SSH_PASS_OPTS +
                [f"{user}@{ip}", cmd])
    elif pwd:
        # sshpass not installed — try with SSH_ASKPASS trick
        env = dict(os.environ)
        askpass = shutil.which("ssh-askpass")
        if askpass:
            env["SSH_ASKPASS"] = askpass
            env["SSH_ASKPASS_REQUIRE"] = "force"
            env["DISPLAY"] = ":0"
        args = (["ssh"] + _SSH_PASS_OPTS + [f"{user}@{ip}", cmd])
        try:
            r = subprocess.run(args, capture_output=True, timeout=timeout,
                               text=True, env=env)
            return r.stdout.strip(), r.stderr.strip(), r.returncode
        except subprocess.TimeoutExpired:
            return "", "SSH timeout", 1
        except Exception as e:
            return "", str(e), 1
    else:
        # Key auth
        args = ["ssh"] + _SSH_KEY_OPTS + [f"{user}@{ip}", cmd]

    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout, text=True)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "SSH timeout", 1
    except Exception as e:
        return "", str(e), 1

def ssh_check_key(ip, user, timeout=3):
    """Quick key-based check — no password, fast."""
    if not shutil.which("ssh"):
        return False
    args = ["ssh"] + _SSH_KEY_OPTS + [f"{user}@{ip}", "echo NEXUS_OK"]
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout, text=True)
        return r.returncode == 0 and "NEXUS_OK" in r.stdout
    except:
        return False

def ssh_check_pass(ip, user, password, timeout=5):
    """Password-based check via sshpass."""
    if not shutil.which("ssh"):
        return False
    if has_sshpass():
        args = (["sshpass", "-p", password, "ssh"] + _SSH_PASS_OPTS +
                [f"{user}@{ip}", "echo NEXUS_OK"])
    else:
        # No sshpass — cannot do non-interactive password auth
        return False
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout, text=True)
        return r.returncode == 0 and "NEXUS_OK" in r.stdout
    except:
        return False

def detect_ssh_user_keys(ip, on_progress=None):
    """
    PARALLEL key-based probe. Tries all SSH_USERS simultaneously.
    Returns username string or None. Typically completes in 3-4 seconds.
    """
    if not shutil.which("ssh") or not tcp_check(ip, 22, timeout=1.5):
        return None

    result = [None]
    found_evt = threading.Event()
    lock = threading.Lock()

    def _try(user):
        if found_evt.is_set():
            return
        ok = ssh_check_key(ip, user, timeout=3)
        if ok:
            with lock:
                if result[0] is None:
                    result[0] = user
                    found_evt.set()

    threads = [threading.Thread(target=_try, args=(u,), daemon=True)
               for u in SSH_USERS]
    for t in threads: t.start()

    # Wait up to 6 seconds for any key-auth success
    found_evt.wait(timeout=6)
    return result[0]

def detect_ssh_user_password(ip, password, on_progress=None):
    """
    PARALLEL password-based probe. Tries all SSH_USERS with the given password.
    Requires sshpass. Returns username or None.
    """
    if not has_sshpass() or not shutil.which("ssh"):
        return None
    if not tcp_check(ip, 22, timeout=1.5):
        return None

    result = [None]
    found_evt = threading.Event()
    lock = threading.Lock()

    def _try(user):
        if found_evt.is_set():
            return
        ok = ssh_check_pass(ip, user, password, timeout=5)
        if ok:
            with lock:
                if result[0] is None:
                    result[0] = user
                    found_evt.set()

    threads = [threading.Thread(target=_try, args=(u,), daemon=True)
               for u in SSH_USERS]
    for t in threads: t.start()

    # Wait up to 10 seconds for any password-auth success
    found_evt.wait(timeout=10)
    return result[0]

def detect_ssh_user(ip, password=None):
    """
    Full SSH user detection:
    1. Try key auth in parallel (fast, ~3-6s)
    2. If password given, try password auth in parallel
    Returns username or None.
    """
    # Phase 1: key auth (always try, no extra deps)
    user = detect_ssh_user_keys(ip)
    if user:
        return user

    # Phase 2: password auth (needs sshpass)
    if password:
        user = detect_ssh_user_password(ip, password)
        if user:
            _ssh_passwords[ip] = password   # cache for future ssh_run calls
        return user

    return None

# ─────────────────────────────────────────────────────────────────────────────
#  REMOTE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

# --- OS Detection (no SSH needed) ---------------------------------------------

def detect_remote_os(ip, open_ports=None):
    """
    Guess remote OS from open ports — no auth needed.
    Returns 'windows', 'linux', or 'unknown'.
    Port fingerprints:
      Windows: 135 (RPC), 139/445 (SMB), 3389 (RDP)  usually present
      Linux:   22 (SSH) present, 135/139/445 usually absent
    """
    if open_ports is None:
        open_ports = {}
        for p in (22, 135, 139, 445, 3389):
            if tcp_check(ip, p, timeout=0.8):
                open_ports[p] = True

    win_ports = {135, 139, 445}
    has_win   = bool(win_ports & set(open_ports))
    has_ssh   = 22 in open_ports
    has_rdp   = 3389 in open_ports

    if has_win and not has_ssh:   return "windows"
    if has_win and has_rdp:       return "windows"
    if has_ssh and not has_win:   return "linux"
    if has_win:                   return "windows"   # both open — likely Windows with SSH
    return "unknown"

# --- Shutdown / Reboot --------------------------------------------------------

# Linux — tried in order; first exit-0 wins
_LINUX_SHUTDOWN = [
    "systemctl poweroff",
    "sudo -n systemctl poweroff",
    "sudo -n poweroff",
    "sudo -n /sbin/poweroff",
    "sudo -n shutdown -h now",
    "shutdown -h now",
]
_LINUX_REBOOT = [
    "systemctl reboot",
    "sudo -n systemctl reboot",
    "sudo -n reboot",
    "sudo -n /sbin/reboot",
    "sudo -n shutdown -r now",
    "shutdown -r now",
]

# Windows via SSH (OpenSSH server built-in since Win10 1809)
# No sudo on Windows — user just needs to be admin
_WIN_SHUTDOWN_CMDS = [
    "shutdown /s /f /t 0",                              # force-close apps, immediate
    "shutdown.exe /s /f /t 0",                          # explicit path
    r"C:\Windows\System32\shutdown.exe /s /f /t 0",     # full path
    "powershell -Command Stop-Computer -Force",          # PowerShell fallback
]
_WIN_REBOOT_CMDS = [
    "shutdown /r /f /t 0",
    "shutdown.exe /r /f /t 0",
    r"C:\Windows\System32\shutdown.exe /r /f /t 0",
    "powershell -Command Restart-Computer -Force",
]

def _ssh_is_windows(ip, user, pwd):
    """Quick check: run 'ver' — Windows returns 'Microsoft Windows Version X'."""
    o, _, rc = ssh_run(ip, user, "ver", timeout=5, password=pwd)
    if "Windows" in o or "Microsoft" in o:
        return True
    # Also try echo %OS% (Windows) vs echo $OSTYPE (Linux)
    o2, _, _ = ssh_run(ip, user, "echo %OS%", timeout=4, password=pwd)
    return "Windows_NT" in o2

def remote_power(ip, user, reboot=False, password=None, target_os="auto"):
    """
    Shutdown or reboot a remote machine.
    Works on:
      • Windows 10/11  — via SSH (OpenSSH server must be enabled)
                         or via net rpc (samba-client, no SSH needed)
      • Linux           — via SSH with systemctl / sudo / shutdown

    Returns (success, method_used, error_message).
    """
    pwd  = password or _ssh_passwords.get(ip, "")
    ssh_ok = bool(shutil.which("ssh"))

    # ── Detect OS ─────────────────────────────────────────────────────────────
    if target_os == "auto":
        # Try to detect without SSH first (port-based)
        open_p = {}
        for p in (22, 135, 139, 445, 3389):
            if tcp_check(ip, p, timeout=0.8): open_p[p] = True
        target_os = detect_remote_os(ip, open_p)

    # ── WINDOWS ───────────────────────────────────────────────────────────────
    if target_os in ("windows", "unknown"):

        # Method W1: SSH → shutdown.exe (OpenSSH server on Windows)
        if ssh_ok and user:
            # Confirm it's really Windows via SSH
            win_confirmed = _ssh_is_windows(ip, user, pwd)
            if win_confirmed or target_os == "windows":
                cmds = _WIN_REBOOT_CMDS if reboot else _WIN_SHUTDOWN_CMDS
                for cmd in cmds:
                    o, err, rc = ssh_run(ip, user, cmd, timeout=12, password=pwd)
                    # Windows shutdown via SSH always returns exit code 0 or
                    # sometimes disconnects mid-run (rc=1 with empty err) — treat
                    # disconnection as success.
                    if rc == 0 or (rc != 0 and not err.strip()):
                        return True, f"SSH: {cmd}", ""
                    # If "Access is denied" — user not admin
                    if "denied" in err.lower() or "denied" in o.lower():
                        return False, cmd, (
                            "Access denied on Windows.\n\n"
                            "The SSH user must be a local Administrator.\n"
                            "Fix on the Windows target:\n"
                            "  1. Open Computer Management → Local Users and Groups\n"
                            "  2. Add your SSH user to the Administrators group.\n"
                            "  OR run in elevated cmd:\n"
                            f"    net localgroup Administrators {user} /add"
                        )

        # Method W2: net rpc shutdown (samba-client, no SSH or OpenSSH needed)
        # Works over SMB port 445 — native Windows networking
        if shutil.which("net") and pwd:
            action = "--reboot" if reboot else "--shutdown"
            cmd_rpc = [
                "net", "rpc", "shutdown", "-I", ip,
                "-U", f"{user}%{pwd}",
                "--force", "--timeout=1", action
            ]
            try:
                r = subprocess.run(cmd_rpc, capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    return True, "net rpc shutdown (SMB/RPC)", ""
                err_rpc = (r.stderr or r.stdout or "").strip()
                if "NT_STATUS_LOGON_FAILURE" in err_rpc:
                    return False, "net rpc", f"Wrong username or password.\n{err_rpc}"
                if "NT_STATUS_ACCESS_DENIED" in err_rpc:
                    return False, "net rpc", (
                        "Access denied via RPC.\n"
                        "The user needs the 'Force shutdown from a remote system' privilege.\n\n"
                        "Fix on the Windows target (run as admin):\n"
                        "  secpol.msc → Local Policies → User Rights Assignment\n"
                        "  → 'Force shutdown from a remote system' → add your user"
                    )
            except Exception as e:
                pass   # net rpc not available or failed, continue

        # Method W3: PowerShell remoting via WinRM (port 5985)
        if tcp_check(ip, 5985, timeout=1) and shutil.which("pwsh"):
            action_ps = "Restart-Computer" if reboot else "Stop-Computer"
            ps_cmd = (
                f"$pw = ConvertTo-SecureString '{pwd}' -AsPlainText -Force; "
                f"$cred = New-Object System.Management.Automation.PSCredential('{user}', $pw); "
                f"{action_ps} -ComputerName {ip} -Credential $cred -Force"
            )
            try:
                r = subprocess.run(["pwsh","-Command",ps_cmd],
                                   capture_output=True,text=True,timeout=20)
                if r.returncode == 0:
                    return True, "PowerShell WinRM", ""
            except Exception:
                pass

        if target_os == "windows":
            return False, "", (
                "Could not shut down the Windows PC.\n\n"
                "REQUIREMENTS — at least one of:\n\n"
                "Option A — Enable OpenSSH Server (easiest):\n"
                "  Settings → Apps → Optional Features → Add: OpenSSH Server\n"
                "  Then in admin PowerShell:\n"
                "    Start-Service sshd\n"
                "    Set-Service -Name sshd -StartupType Automatic\n"
                "  SSH user must be in Administrators group.\n\n"
                "Option B — Enable WinRM (PowerShell remoting):\n"
                "  Run in admin PowerShell on target:\n"
                "    Enable-PSRemoting -Force\n\n"
                "Option C — Install samba-client on this machine:\n"
                "  sudo dnf install samba-client -y\n"
                "  (uses SMB/RPC — no changes on the Windows target needed,\n"
                "   just needs admin credentials)"
            )

    # ── LINUX ─────────────────────────────────────────────────────────────────
    if not ssh_ok:
        return False, "", "SSH not found on this machine.\n  sudo dnf install openssh-clients -y"
    if not user:
        return False, "", "No SSH username configured for this device."

    cmds = _LINUX_REBOOT if reboot else _LINUX_SHUTDOWN
    last_err = ""
    for cmd in cmds:
        o, err, rc = ssh_run(ip, user, cmd, timeout=12, password=pwd)
        # Some shutdown commands disconnect the SSH session before returning 0
        # — treat a clean disconnect (empty error) as success
        if rc == 0 or (rc != 0 and not err.strip() and not o.strip()):
            return True, f"SSH: {cmd}", ""
        if err: last_err = err

    return False, "", (
        f"All shutdown commands failed on {ip}.\n"
        f"Last error: {last_err}\n\n"
        "Fix (run on the Linux target):\n"
        f"  echo '{user} ALL=(ALL) NOPASSWD: "
        "/sbin/poweroff,/sbin/reboot,/usr/bin/systemctl' "
        "| sudo tee /etc/sudoers.d/nexus-lan && sudo chmod 440 /etc/sudoers.d/nexus-lan"
    )

# --- Message Delivery ---------------------------------------------------------

def remote_message(ip, user, title, body, target_os="auto", password=None):
    """
    Send a visible message/popup to a remote machine.
    Windows: SSH → msg * | PowerShell MessageBox | net send (if available)
    Linux:   SSH → notify-send + zenity + wall
    Returns (bool, method_string).
    """
    pwd     = password or _ssh_passwords.get(ip, "")
    ssh_ok  = bool(shutil.which("ssh")) and bool(user)
    methods = []

    # ── Detect OS ─────────────────────────────────────────────────────────────
    if target_os == "auto":
        open_p = {}
        for p in (22, 135, 139, 445, 3389):
            if tcp_check(ip, p, timeout=0.8): open_p[p] = True
        target_os = detect_remote_os(ip, open_p)

    # ══════════════════════════════════════════════════════════════════════════
    # WINDOWS message delivery
    # ══════════════════════════════════════════════════════════════════════════
    if target_os in ("windows", "unknown"):
        if ssh_ok:
            # Method W1: msg * "text"  — sends popup to all logged-in sessions
            # Works on Pro/Enterprise (not Home — Home has msg.exe but it's often blocked)
            safe_body  = body.replace('"', "'").replace("'", "`'")
            safe_title = title.replace('"', "'")

            msg_cmd = f'msg * /TIME:30 "{safe_title}: {safe_body}"'
            o, err, rc = ssh_run(ip, user, msg_cmd, timeout=8, password=pwd)
            if rc == 0:
                methods.append("msg ✓")

            # Method W2: PowerShell MessageBox popup (works on all editions)
            # Runs hidden PowerShell that shows a GUI dialog
            ps_popup = (
                f"powershell -WindowStyle Hidden -Command \""
                f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;"
                f"[System.Windows.Forms.MessageBox]::Show("
                f"'{safe_body}', '{safe_title} [NEXUS]', "
                f"[System.Windows.Forms.MessageBoxButtons]::OK, "
                f"[System.Windows.Forms.MessageBoxIcon]::Information)\" &"
            )
            o, err, rc = ssh_run(ip, user, ps_popup, timeout=8, password=pwd)
            if rc == 0 or not err.strip():
                methods.append("PowerShell popup ✓")

            # Method W3: mshta VBScript popup (no PS needed, pure Windows)
            mshta_cmd = (
                f'mshta "javascript:var sh=new ActiveXObject(\'WScript.Shell\');"'
                f'"sh.Popup(\'{safe_body}\',10,\'{safe_title}\',64);close();" &'
            )
            o, err, rc = ssh_run(ip, user, mshta_cmd, timeout=8, password=pwd)
            if rc == 0 or not err.strip():
                methods.append("mshta ✓")

            # Method W4: PowerShell toast notification (Win10+)
            ps_toast = (
                f"powershell -WindowStyle Hidden -Command \""
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                f"ContentType = WindowsRuntime] | Out-Null;"
                f"$t = [Windows.UI.Notifications.ToastTemplateType]::ToastText02;"
                f"$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($t);"
                f"$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('{safe_title}')) | Out-Null;"
                f"$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('{safe_body}')) | Out-Null;"
                f"$n = [Windows.UI.Notifications.ToastNotification]::new($x);"
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('NEXUS').Show($n)"
                f"\" &"
            )
            o, err, rc = ssh_run(ip, user, ps_toast, timeout=8, password=pwd)
            if rc == 0 or not err.strip():
                methods.append("WinToast ✓")

        if methods:
            return True, " | ".join(methods)
        # No SSH — can't deliver message to Windows without it
        return False, "No SSH access to Windows target (enable OpenSSH Server)"

    # ══════════════════════════════════════════════════════════════════════════
    # LINUX message delivery
    # ══════════════════════════════════════════════════════════════════════════
    if not ssh_ok:
        return False, "No SSH user configured"

    safe_title = title.replace("'", "\\'")
    safe_body  = body.replace("'", "\\'")

    # Method L1: notify-send with proper DBUS session detection
    notify_py = (
        "python3 -c \""
        "import subprocess,os,glob;"
        "sessions=glob.glob('/run/user/*/bus');"
        "[subprocess.run(['notify-send','--urgency=critical','--expire-time=15000',"
        f"'{safe_title}','{safe_body}'],"
        "env={{**os.environ,'DBUS_SESSION_BUS_ADDRESS':'unix:path='+b,'DISPLAY':':0'}},"
        "capture_output=True,timeout=5)"
        " for b in sessions]"
        "\" 2>/dev/null"
    )
    _, _, rc = ssh_run(ip, user, notify_py, timeout=10, password=pwd)
    if rc == 0: methods.append("notify-send ✓")

    # Method L2: zenity dialog
    zenity_cmd = (
        "DISPLAY=:0 "
        "DBUS_SESSION_BUS_ADDRESS=$(cat /proc/$(ls /tmp/.ICE-unix/ 2>/dev/null | head -1)/environ 2>/dev/null"
        " | tr '\\0' '\\n' | grep DBUS | cut -d= -f2- || ls /run/user/*/bus 2>/dev/null | head -1 | xargs -I{} echo unix:path={}) "
        f"zenity --info --title='{safe_title}' --text='{safe_body}' --width=400 2>/dev/null &"
    )
    _, _, rc = ssh_run(ip, user, zenity_cmd, timeout=6, password=pwd)
    if rc == 0: methods.append("zenity ✓")

    # Method L3: xmessage
    xmsg = f"DISPLAY=:0 xmessage -center '{safe_title}: {safe_body}' &>/dev/null &"
    _, _, rc = ssh_run(ip, user, xmsg, timeout=5, password=pwd)
    if rc == 0: methods.append("xmessage ✓")

    # Method L4: wall (always works, appears in terminal)
    wall = f"echo '[NEXUS] {safe_title}: {safe_body}' | wall 2>/dev/null"
    _, _, rc = ssh_run(ip, user, wall, timeout=5, password=pwd)
    if rc == 0: methods.append("wall ✓")

    return len(methods) > 0, " | ".join(methods) if methods else "no delivery method succeeded"

def get_local_anydesk():
    if shutil.which("anydesk"):
        try:
            r = subprocess.run(["anydesk","--get-id"],capture_output=True,text=True,timeout=5)
            if r.stdout.strip(): return re.sub(r"[^0-9]","",r.stdout.strip())
        except: pass
    for p in [Path.home()/".anydesk"/"user.conf",Path("/etc/anydesk/system.conf")]:
        try:
            txt=p.read_text()
            m=re.search(r"(?:raw_id|id)\s*=\s*(\d+)",txt)
            if m: return m.group(1)
        except: pass
    return None

# ─────────────────────────────────────────────────────────────────────────────
#  AUTO-DISCOVERY ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def gather_info(ip, user, on_progress=None):
    """
    SSH to remote. Auto-detects Windows vs Linux and runs correct commands.
    Calls on_progress(key, value) for each field found.
    """
    info = {}
    pwd  = _ssh_passwords.get(ip, "")

    def _r(label, cmd, timeout=7):
        o, e, rc = ssh_run(ip, user, cmd, timeout=timeout, password=pwd)
        val = o.strip() if o.strip() else ""
        if val and not label.startswith("_"):
            info[label] = val
            if on_progress: on_progress(label, val)
        return val, rc

    # ── Detect Windows vs Linux via 'ver' ────────────────────────────────────
    ver_out, _ = _r("_probe", "ver", timeout=5)
    is_win = "Microsoft" in ver_out or "Windows" in ver_out
    if not is_win:
        uname_out, uname_rc = _r("_probe2", "uname -s", timeout=4)
        is_win = (uname_rc != 0 and not uname_out)

    # ── Windows commands (no bash, no sudo, no grep) ─────────────────────────
    if is_win:
        # Use single-quoted PS commands so no inner " escaping needed
        _r("os",
            "powershell -Command (Get-WmiObject Win32_OperatingSystem).Caption 2>nul")
        if not info.get("os"):
            v, _ = _r("_ver2", "ver", timeout=4)
            if v: info["os"] = v; on_progress and on_progress("os", v)
        _r("hostname",  "hostname")
        _r("arch",      "powershell -Command $env:PROCESSOR_ARCHITECTURE 2>nul")
        _r("cpu",
            "powershell -Command (Get-WmiObject Win32_Processor | Select -First 1 | "
            "Select-Object -ExpandProperty Name) 2>nul")
        _r("cpu_cores",
            "powershell -Command (Get-WmiObject Win32_Processor).NumberOfLogicalProcessors 2>nul")
        _r("ram",
            "powershell -Command "
            "\"$o=(Get-WmiObject Win32_OperatingSystem);"
            "($o.TotalVisibleMemorySize/1MB).ToString('N1')+' GB total, '+"
            "($o.FreePhysicalMemory/1MB).ToString('N1')+' GB free'\" 2>nul")
        _r("disk",
            "powershell -Command "
            "\"$d=Get-PSDrive C;"
            "($d.Used/1GB).ToString('N1')+'/'+(($d.Used+$d.Free)/1GB).ToString('N1')+' GB'\" 2>nul")
        _r("uptime",
            "powershell -Command "
            "\"$b=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime;"
            "$u=[DateTime]::Now-$b;"
            "'up '+$u.Days+'d '+$u.Hours+'h '+$u.Minutes+'m'\" 2>nul")
        _r("users",
            "powershell -Command (Get-WmiObject Win32_ComputerSystem).UserName 2>nul")
        _r("kernel",
            "powershell -Command [System.Environment]::OSVersion.Version 2>nul")
        _r("timezone",
            "powershell -Command [System.TimeZone]::CurrentTimeZone.StandardName 2>nul")
        _r("anydesk_id",
            "powershell -Command "
            "\"try{(Get-ItemProperty 'HKLM:\\SOFTWARE\\AnyDesk' -EA Stop).AnyDeskId}catch{}\" 2>nul")
        return info

    # ── Linux / macOS commands ────────────────────────────────────────────────
    _r("os",
       "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME"
       " | sed s/PRETTY_NAME=// | sed s/[\"]//g"
       " || sw_vers -productName 2>/dev/null"
       " || lsb_release -ds 2>/dev/null"
       " || uname -s -r")
    _r("hostname", "hostname -f 2>/dev/null || hostname")
    _r("kernel",   "uname -r")
    _r("arch",     "uname -m")
    _r("cpu",      "grep -m1 'model name' /proc/cpuinfo 2>/dev/null | sed 's/.*: //' | xargs"
                   " || sysctl -n machdep.cpu.brand_string 2>/dev/null")
    _r("cpu_cores","nproc 2>/dev/null || grep -c '^processor' /proc/cpuinfo 2>/dev/null")
    _r("ram",     "free -m 2>/dev/null | awk '/^Mem:/{printf \"%d MB total, %d MB used\", $2, $3}'")
    _r("disk",    "df -h / 2>/dev/null | awk 'NR==2{print $3\"/ \"$2\" (\"$5\")\"}'")
    _r("uptime",   "uptime -p 2>/dev/null || uptime | sed 's/.*up/up/'")
    _r("users",    "who 2>/dev/null | awk '{print $1}' | sort -u | tr '\\n' ' ' | xargs")
    _r("ip_addrs", "hostname -I 2>/dev/null || ip addr 2>/dev/null | grep 'inet ' | awk '{print $2}' | tr '\\n' ' '")
    _r("anydesk_id",
        "anydesk --get-id 2>/dev/null"
        " || grep -oP '(?<=raw_id=)\\d+' /etc/anydesk/system.conf 2>/dev/null"
        " || grep -oP '(?<=id=)\\d+' ~/.anydesk/user.conf 2>/dev/null")
    _r("load",     "cat /proc/loadavg 2>/dev/null | awk '{print $1\", \"$2\", \"$3}'")
    _r("shell",    "echo $SHELL")
    _r("timezone", "timedatectl show --property=Timezone --value 2>/dev/null || date +%Z")
    _r("services", "ss -tlnp 2>/dev/null | awk 'NR>1{print $4}' | grep -oP ':\\d+'"
                   " | tr -d ':' | sort -un | tr '\\n' ' '")
    return info



def auto_discover(ip, user, on_update):
    """Full auto-discovery: ports → hostname → SSH info."""
    result = {"ip": ip, "ssh_user": user}

    # Port scan
    open_ports = {}
    for port, svc in COMMON_PORTS.items():
        if tcp_check(ip, port, timeout=0.9): open_ports[port] = svc
    if open_ports:
        result["services"] = ", ".join(f"{p}/{s}" for p,s in sorted(open_ports.items()))
        result["open_ports"] = open_ports
        on_update(dict(result))

    # Hostname via DNS
    h = hostname_of(ip)
    if h: result["hostname"] = h; on_update(dict(result))

    # SSH info
    if 22 in open_ports or tcp_check(ip, 22, timeout=1):
        def _prog(key, val):
            result[key] = val
            on_update(dict(result))
        info = gather_info(ip, user, on_progress=_prog)

        # Map gathered fields
        if info.get("anydesk_id"):
            d = re.sub(r"[^0-9]","",info["anydesk_id"])
            if len(d) >= 6: result["anydesk_id"] = d; on_update(dict(result))

    return result

# ─────────────────────────────────────────────────────────────────────────────
#  UDP MESSAGE SERVER
# ─────────────────────────────────────────────────────────────────────────────
class NetServer:
    def __init__(self, on_recv):
        self.on_recv = on_recv; self._sock = None; self._run = False
    def start(self, port=MSG_PORT):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(("", port)); self._sock.settimeout(1.0)
            self._run = True
            threading.Thread(target=self._loop, daemon=True).start()
            return True
        except Exception as e: print(f"[NetServer] {e}"); return False
    def stop(self):
        self._run = False
        if self._sock:
            try: self._sock.close()
            except: pass
    def _loop(self):
        while self._run:
            try:
                data, addr = self._sock.recvfrom(4096)
                pkt = json.loads(data.decode("utf-8",errors="ignore"))
                pkt["_addr"] = addr[0]; self.on_recv(pkt)
            except (socket.timeout, json.JSONDecodeError): pass
            except: pass
    @staticmethod
    def send(ip, pkt, port=MSG_PORT):
        try:
            data = json.dumps(pkt).encode("utf-8")
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(2); s.sendto(data, (ip, port))
            return True
        except: return False

# ─────────────────────────────────────────────────────────────────────────────
#  DEVICE DATABASE
# ─────────────────────────────────────────────────────────────────────────────
_EXTRA = ["cpu","cpu_cores","ram","disk","uptime","kernel","arch",
          "services","users","load","shell","timezone","open_ports",
          "ip_addrs","last_discover"]

class DeviceDB:
    def __init__(self): self.data = {}; self._load()
    def _load(self):
        if DB_FILE.exists():
            try:
                with open(DB_FILE,encoding="utf-8") as f: self.data = json.load(f)
            except: self.data = {}
    def save(self):
        try:
            with open(DB_FILE,"w",encoding="utf-8") as f:
                json.dump(self.data,f,indent=2,ensure_ascii=False)
        except: pass
    def upsert(self, mac, **kw):
        if mac not in self.data:
            self.data[mac] = {
                "mac":mac,"name":"","ip":"","hostname":"","anydesk_id":"",
                "rdp_address":"","ssh_user":"","os":"","vendor":"",
                "group":"Default","icon":"💻","notes":"",
                "status":"offline","last_seen":"","wol_count":0,
                "added":datetime.now().isoformat(),
                **{k:"" for k in _EXTRA},
            }
        self.data[mac].update(kw); self.save()
    def get(self, mac): return dict(self.data.get(mac, {}))
    def remove(self, mac): self.data.pop(mac, None); self.save()
    def macs(self): return list(self.data.keys())

# ─────────────────────────────────────────────────────────────────────────────
#  WIDGETS  — authentic XP Luna look
# ─────────────────────────────────────────────────────────────────────────────
class XBtn(tk.Button):
    """XP Luna button with proper 3-tone border, hover tint, press sunken."""
    def __init__(self, parent, kind="n", snd=True, **kw):
        self._snd = snd
        bg_map = {"n":C["bf"],"w":C["btn_w"],"d":C["btn_d"],"g":C["btn_g"],"b":C["btn_b"]}
        hi_map = {"n":C["bhi"],"w":"#FFE0A0","d":"#FFAAAA","g":"#A8E4A8","b":"#B8D8FF"}
        kw.setdefault("bg",           bg_map.get(kind, C["bf"]))
        kw.setdefault("activebackground", hi_map.get(kind, C["bhi"]))
        kw.setdefault("activeforeground", "black")
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", C["blo"])
        kw.setdefault("relief",   "raised"); kw.setdefault("bd", 2)
        kw.setdefault("font",     F(9));     kw.setdefault("cursor","hand2")
        kw.setdefault("padx",     8);        kw.setdefault("pady", 3)
        self._bg0 = kw["bg"]; self._hi = hi_map.get(kind, C["bhi"])
        super().__init__(parent, **kw)
        self.bind("<Enter>",          self._enter)
        self.bind("<Leave>",          self._leave)
        self.bind("<ButtonPress-1>",  self._press)
        self.bind("<ButtonRelease-1>",self._release)
    def _enter(self,_=None):
        if str(self["state"]) != "disabled":
            self.config(relief="groove", bg=self._hi)
    def _leave(self,_=None):
        self.config(relief="raised", bg=self._bg0)
    def _press(self,_=None):
        if str(self["state"]) != "disabled":
            self.config(relief="sunken", bg=self._hi)
            if self._snd: play("click")
    def _release(self,_=None):
        if str(self["state"]) != "disabled":
            self.config(relief="raised", bg=self._bg0)

def Btn(parent, kind="n", **kw): return XBtn(parent, kind=kind, **kw)

class TitleBar(tk.Canvas):
    def __init__(self, parent, title="", icon="", h=30, **kw):
        super().__init__(parent, height=h, bd=0, highlightthickness=0, **kw)
        self._title=title; self._icon=icon
        self.bind("<Configure>", self._draw)
    def _draw(self, _=None):
        self.delete("all")
        w = self.winfo_width() or 1000; h = self.winfo_height() or 30
        for i in range(h):
            t = i / max(h-1,1)
            r = int(7  + t*(26 - 7))
            g = int(22 + t*(78 - 22))
            b = int(66 + t*(160- 66))
            self.create_line(0,i,w,i, fill=f"#{r:02x}{g:02x}{b:02x}")
        # highlight
        self.create_line(0,0,w,0,fill="#4878C0")
        self.create_line(0,1,w,1,fill="#2858A8")
        txt = f"  {self._icon}  {self._title}" if self._icon else f"  {self._title}"
        self.create_text(12, h//2, anchor="w", text=txt, fill="white", font=F(9,True))

class SBar(tk.Frame):
    def __init__(self, p, **kw):
        super().__init__(p, bg=C["bg2"], bd=1, relief="sunken", **kw)
    def add(self, width=0, anchor="w"):
        v = tk.StringVar()
        kw = dict(textvariable=v, bg=C["bg2"], font=F(8), anchor=anchor, relief="sunken", bd=1)
        if width: kw["width"] = width
        tk.Label(self,**kw).pack(side="left",fill="x",expand=(width==0),padx=1,pady=1)
        return v

class Tip:
    def __init__(self, w, t):
        self._w=w; self._t=t; self._tip=None
        w.bind("<Enter>",self._s,"+"); w.bind("<Leave>",self._h,"+")
    def _s(self,_=None):
        x=self._w.winfo_rootx()+16; y=self._w.winfo_rooty()+26
        self._tip=tk.Toplevel(self._w); self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self._tip,text=self._t,bg="#FFFFCC",fg="black",relief="solid",
                 bd=1,font=F(8),padx=6,pady=3).pack()
    def _h(self,_=None):
        if self._tip: self._tip.destroy(); self._tip=None

# ─────────────────────────────────────────────────────────────────────────────
#  EVENT LOG
# ─────────────────────────────────────────────────────────────────────────────
class EventLog(tk.Frame):
    ICONS = {"online":"🟢","offline":"⚫","wol":"⚡","shutdown":"🔴","reboot":"🔁",
             "msg":"💬","sound":"🔔","error":"⚠️","info":"ℹ️","scan":"🔍",
             "anydesk":"🖥️","ssh":"🔑","disc":"🔭","connect":"🔌","warn":"⚠️"}
    def __init__(self, p, **kw):
        super().__init__(p, bg=C["log_bg"], **kw)
        hdr=tk.Frame(self,bg="#050A12"); hdr.pack(fill="x")
        tk.Label(hdr,text="  ▶  Event Console",bg="#050A12",fg="#5A8AAA",
                 font=F(8,True),pady=3).pack(side="left",padx=4)
        XBtn(hdr,text="Clear",bg="#050A12",fg=C["gray2"],relief="flat",
             bd=0,font=F(7),pady=1,padx=6,snd=False,
             command=self._clear).pack(side="right",padx=4)
        self._txt=tk.Text(self,bg=C["log_bg"],fg=C["log_fg"],font=FX(8),
                          state="disabled",relief="flat",height=6,wrap="word",padx=8,pady=4)
        vsb=ttk.Scrollbar(self,orient="vertical",command=self._txt.yview)
        self._txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right",fill="y"); self._txt.pack(fill="both",expand=True)
        for tag,col in [("green","#4AE04A"),("red","#FF6060"),("yellow","#FFCC44"),
                        ("cyan","#44DDFF"),("gray","#8899AA"),("white","#CCDDE8"),
                        ("orange","#FFA040"),("blue","#88AAFF")]:
            self._txt.tag_configure(tag,foreground=col)
        self._txt.tag_configure("ts", foreground="#3A5A7A")
    def log(self, kind, msg, col="white"):
        ts=datetime.now().strftime("%H:%M:%S")
        ico=self.ICONS.get(kind,"•")
        self._txt.config(state="normal")
        self._txt.insert("end",f"[{ts}] ","ts")
        self._txt.insert("end",f"{ico} ",col)
        self._txt.insert("end",msg+"\n",col)
        self._txt.see("end"); self._txt.config(state="disabled")
    def _clear(self):
        self._txt.config(state="normal"); self._txt.delete("1.0","end")
        self._txt.config(state="disabled")

# ─────────────────────────────────────────────────────────────────────────────
#  TOAST
# ─────────────────────────────────────────────────────────────────────────────
class Toast(tk.Toplevel):
    def __init__(self, parent, title, msg, icon="💬", ms=5000):
        super().__init__(parent)
        self.overrideredirect(True); self.attributes("-topmost",True)
        self.configure(bg=C["ta"])
        w,h=340,74
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{sw-w-14}+{sh-h-56}")
        f=tk.Frame(self,bg=C["ta"],bd=2,relief="raised"); f.pack(fill="both",expand=True)
        tk.Label(f,text=f" {icon}  {title}",bg=C["ta"],fg="white",
                 font=F(9,True),anchor="w").pack(fill="x",padx=6,pady=(4,0))
        tk.Label(f,text=msg,bg=C["ta"],fg="#AACCFF",font=F(8),
                 anchor="w",wraplength=300).pack(fill="x",padx=12)
        tk.Button(f,text="✕",bg=C["ta"],fg="white",relief="flat",bd=0,
                  font=F(7),cursor="hand2",command=self.destroy
                  ).place(relx=1,x=-2,y=2,anchor="ne")
        self.after(ms,self.destroy)

# ─────────────────────────────────────────────────────────────────────────────
#  WOL BOOT SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class WOLScreen(tk.Toplevel):
    def __init__(self, parent, device, bcast, on_done):
        super().__init__(parent)
        self.device=device; self.bcast=bcast; self.on_done=on_done
        self._alive=True; self._pos=0
        self.title("Waking…"); self.configure(bg="black"); self.resizable(False,False)
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        w,h=660,510; self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        try: self.overrideredirect(True)
        except: pass
        self.lift(); self.focus_force()
        self._build(); play("boot"); self.after(300,self._tick)

    def _build(self):
        f=tk.Frame(self,bg="black"); f.place(relx=.5,rely=.43,anchor="center")
        tk.Label(f,text="Windows",font=("Times New Roman",52,"italic"),fg="white",bg="black").pack()
        tk.Label(f,text="XP",font=("Times New Roman",52,"italic"),fg=C["btblue"],bg="black").pack()
        tk.Label(f,text="Professional",font=("Times New Roman",14),fg="white",bg="black").pack(pady=(0,4))
        tk.Frame(f,bg="#2A2A2A",height=1,width=500).pack(pady=16)
        self._sv=tk.StringVar(value="Sending Wake-on-LAN magic packet…")
        tk.Label(f,textvariable=self._sv,fg="#999999",bg="black",font=F(10)).pack(pady=4)
        bar=tk.Frame(f,bg="black"); bar.pack(pady=14)
        self._blks=[]
        for _ in range(12):
            b=tk.Frame(bar,width=26,height=14,bg="#2A2A2A"); b.pack(side="left",padx=2)
            self._blks.append(b)
        name=self.device.get("name") or self.device.get("hostname") or self.device.get("mac","?")
        mac=self.device.get("mac","—"); ip=self.device.get("ip","—")
        tk.Label(f,text=f"Target: {name}   MAC: {mac}   IP: {ip}",
                 fg="#333333",bg="black",font=F(8)).pack(pady=4)
        tk.Label(f,text=f"Broadcast: {self.bcast}",fg="#222222",bg="black",font=F(7)).pack()
        tk.Label(f,text="Copyright © 2001 Microsoft Corporation. All rights reserved.",
                 fg="#161616",bg="black",font=F(7)).pack(pady=(14,4))
        XBtn(f,text=" Cancel ",command=self._cancel,bg="#0E0E0E",fg="white",
             activebackground="#280000",bd=1,snd=False).pack(pady=6)

    def _tick(self):
        if not self._alive: return
        n=len(self._blks)
        for i,b in enumerate(self._blks):
            d=(i-self._pos)%n
            b.config(bg=(C["btblue"] if d==0 else "#0D6FA0" if d==1 else "#063A5A" if d==2 else "#2A2A2A"))
        self._pos=(self._pos+1)%n; self.after(110,self._tick)

    def start(self):
        threading.Thread(target=self._thread, daemon=True).start()

    def _thread(self):
        mac=self.device.get("mac","")
        self.after(0,lambda: self._sv.set(f"Sending WOL to {self.bcast} …"))
        for _ in range(6): send_wol(mac,self.bcast); time.sleep(0.15)
        self.after(0,lambda: self._sv.set("Packet sent!  Waiting for PC to boot…"))
        play("wol_sent")
        ip=self.device.get("ip",""); deadline=time.time()+120
        while time.time()<deadline and self._alive:
            if ip and ping_host(ip,timeout=2):
                play("tada")
                self.after(0,lambda: self._sv.set("✓  PC is online!"))
                self.after(0,lambda: [b.config(bg="#00AA00") for b in self._blks])
                time.sleep(2.5); self._finish(True); return
            time.sleep(3)
        if self._alive:
            self.after(0,lambda: self._sv.set("Timeout — check BIOS Wake-on-LAN setting."))
            time.sleep(3); self._finish(False)

    def _finish(self,ok):
        self._alive=False
        self.after(0,lambda: (self.destroy(),self.on_done(ok)))

    def _cancel(self):
        self._alive=False; self.destroy(); self.on_done(False)

# ─────────────────────────────────────────────────────────────────────────────
#  TERMINAL OUTPUT WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class TermWin(tk.Toplevel):
    def __init__(self, parent, title, icon="📋", w=640, h=420):
        super().__init__(parent)
        self.title(title); self.configure(bg=C["bg"])
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        TitleBar(self,title=title,icon=icon,h=28).pack(fill="x")
        self._txt=tk.Text(self,font=FX(9),bg="#0A0F1A",fg="#00FF88",
                          state="disabled",padx=10,pady=8,relief="flat")
        self._txt.tag_configure("head",foreground="#44CCFF",font=FX(8))
        self._txt.tag_configure("val", foreground="#CCFFCC")
        self._txt.tag_configure("warn",foreground="#FFCC44")
        self._txt.tag_configure("err", foreground="#FF6060")
        vsb=ttk.Scrollbar(self,orient="vertical",command=self._txt.yview)
        self._txt.configure(yscrollcommand=vsb.set); vsb.pack(side="right",fill="y")
        self._txt.pack(fill="both",expand=True)
        self._bf=tk.Frame(self,bg=C["bg"]); self._bf.pack(fill="x",padx=8,pady=6)
        Btn(self._bf,text="Close",command=self.destroy).pack(side="right",padx=4)
    def w(self, txt, tag=None):
        self._txt.config(state="normal")
        if tag: self._txt.insert("end",txt,tag)
        else:   self._txt.insert("end",txt)
        self._txt.see("end"); self._txt.config(state="disabled")
    def add_btn(self, lbl, cmd):
        Btn(self._bf,text=lbl,command=cmd).pack(side="left",padx=4)

# ─────────────────────────────────────────────────────────────────────────────
#  CHAT WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class ChatWin(tk.Toplevel):
    _wins = {}
    @classmethod
    def get(cls, parent, device, my_name, send_fn):
        ip=device.get("ip","")
        if ip in cls._wins and cls._wins[ip].winfo_exists():
            cls._wins[ip].lift(); return cls._wins[ip]
        cw=cls(parent,device,my_name,send_fn); cls._wins[ip]=cw; return cw

    def __init__(self, parent, device, my_name, send_fn):
        super().__init__(parent)
        self.device=device; self.my_name=my_name; self.send_fn=send_fn
        name=device.get("name") or device.get("hostname") or device.get("ip","?")
        self.title(f"Messages — {name}"); self.configure(bg=C["bg"])
        w,h=460,540; self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self.protocol("WM_DELETE_WINDOW",self._close)
        TitleBar(self,title=f"💬  {name}  ·  {device.get('ip','?')}",h=28).pack(fill="x")

        # Delivery method info
        user=device.get("ssh_user","")
        info_txt=("SSH + notify-send + wall + UDP" if user else "UDP only (no SSH user)")
        tk.Label(self,text=f"  Delivery: {info_txt}  ·  UDP {MSG_PORT}",
                 bg=C["bg2"],font=F(8),fg=C["gray"],pady=2).pack(fill="x")

        self._txt=tk.Text(self,font=F(9),bg="#FFFFFF",relief="sunken",bd=1,
                          state="disabled",wrap="word",padx=8,pady=6)
        self._txt.tag_configure("me_h",  foreground=C["sel"],  font=F(8,True))
        self._txt.tag_configure("you_h", foreground=C["on"],   font=F(8,True))
        self._txt.tag_configure("me_t",  background=C["chat_me"],  lmargin1=16,lmargin2=16)
        self._txt.tag_configure("you_t", background=C["chat_th"],  lmargin1=16,lmargin2=16)
        self._txt.tag_configure("sys",   foreground=C["gray"],  font=F(8), justify="center")
        vsb=ttk.Scrollbar(self,orient="vertical",command=self._txt.yview)
        self._txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right",fill="y"); self._txt.pack(fill="both",expand=True,padx=2,pady=2)

        bf=tk.Frame(self,bg=C["bg"],bd=1,relief="sunken"); bf.pack(fill="x",padx=4,pady=4)
        self._inp=tk.Entry(bf,font=F(10),relief="flat",bd=0)
        self._inp.pack(side="left",fill="both",expand=True,padx=6,pady=6)
        self._inp.bind("<Return>",lambda _: self._send())
        Btn(bf,kind="g",text="📤 Send",command=self._send).pack(side="right",padx=4,pady=4)
        Btn(bf,kind="w",text="🔔 Sound",
            command=lambda: self.send_fn("sound",self.device)).pack(side="right",padx=2,pady=4)
        self._sys(f"Conversation with {name} opened")

    def _sys(self, t):
        self._txt.config(state="normal")
        self._txt.insert("end",f"\n── {t} ──\n","sys")
        self._txt.see("end"); self._txt.config(state="disabled")

    def add_msg(self, sender, text, me=True):
        self._txt.config(state="normal")
        ts=datetime.now().strftime("%H:%M")
        self._txt.insert("end",f"\n{sender}  {ts}\n","me_h" if me else "you_h")
        self._txt.insert("end",f" {text} \n","me_t" if me else "you_t")
        self._txt.see("end"); self._txt.config(state="disabled")

    def receive(self, sender, text):
        self.add_msg(sender,text,me=False); self.lift()

    def _send(self):
        t=self._inp.get().strip()
        if not t: return
        self._inp.delete(0,"end")
        self.send_fn("message",self.device,t)
        self.add_msg(f"Me ({self.my_name})",t,me=True)

    def _close(self):
        ip=self.device.get("ip","")
        if ip in self.__class__._wins: del self.__class__._wins[ip]
        self.destroy()

# ─────────────────────────────────────────────────────────────────────────────
#  SHUTDOWN DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class ShutDlg(tk.Toplevel):
    def __init__(self, parent, device, on_confirm, default_reboot=False):
        super().__init__(parent)
        self.device=device; self.on_confirm=on_confirm
        self.title("Remote Power Control"); self.configure(bg=C["bg"])
        self.resizable(False,False); self.grab_set()
        w,h=440,340; self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        name=device.get("name") or device.get("hostname") or device.get("ip","?")
        TitleBar(self,title="Remote Power Control",icon="⚡",h=28).pack(fill="x")
        f=tk.Frame(self,bg=C["bg"]); f.pack(fill="both",expand=True,padx=16,pady=10)
        tk.Label(f,text=f"Target:  {name}  ({device.get('ip','?')})",
                 bg=C["bg"],font=F(9,True),fg=C["sel"]).pack(anchor="w",pady=(0,8))
        # SSH user
        uf=tk.Frame(f,bg=C["bg"]); uf.pack(fill="x",pady=4)
        tk.Label(uf,text="SSH Username:",bg=C["bg"],font=F(9),width=14,anchor="e").pack(side="left")
        self._user=tk.StringVar(value=device.get("ssh_user",""))
        tk.Entry(uf,textvariable=self._user,font=F(9),relief="sunken",bd=2,width=22
                 ).pack(side="left",padx=4)
        if device.get("ssh_user"):
            tk.Label(uf,text="✓",fg=C["on"],bg=C["bg"],font=F(9)).pack(side="left")
        pf=tk.Frame(f,bg=C["bg"]); pf.pack(fill="x",pady=4)
        tk.Label(pf,text="SSH Password:",bg=C["bg"],font=F(9),width=14,anchor="e").pack(side="left")
        self._pass=tk.StringVar(value=_ssh_passwords.get(device.get("ip",""),""))
        tk.Entry(pf,textvariable=self._pass,font=F(9),relief="sunken",bd=2,width=22,show="•"
                 ).pack(side="left",padx=4)
        tk.Label(pf,text="(blank = key auth)",fg=C["gray"],bg=C["bg"],font=F(8)).pack(side="left",padx=4)
        # Action
        self._act=tk.StringVar(value="reboot" if default_reboot else "shutdown")
        ar=tk.Frame(f,bg=C["bg"]); ar.pack(anchor="w",pady=8)
        for v,t in [("shutdown","🔴  Shutdown"),("reboot","🔁  Reboot")]:
            tk.Radiobutton(ar,text=t,variable=self._act,value=v,
                           bg=C["bg"],font=F(10),cursor="hand2").pack(side="left",padx=16)
        # Warning
        tk.Label(f,text=(
            "⚠  The app tries multiple methods automatically:\n"
            "  systemctl poweroff  →  sudo -n poweroff  →  shutdown -h now\n\n"
            "For sudo to work without password, run on target machine:\n"
            f"  echo '{self._user.get() or 'USER'} ALL=(ALL) NOPASSWD: "
            "/sbin/poweroff,/sbin/reboot,/usr/bin/systemctl' "
            "| sudo tee /etc/sudoers.d/nexus-lan"
        ),bg=C["sh2"],fg="#600000",font=F(8),relief="solid",bd=1,
            justify="left",padx=10,pady=6,wraplength=380).pack(fill="x",pady=6)
        bf=tk.Frame(self,bg=C["bg"]); bf.pack(fill="x",padx=16,pady=8)
        Btn(bf,kind="d",text="  Execute  ",command=self._go).pack(side="right",padx=4)
        Btn(bf,text="Cancel",command=self.destroy).pack(side="right")

    def _go(self):
        u=self._user.get().strip()
        if not u:
            messagebox.showerror("Error","SSH username required.",parent=self); return
        self.device["ssh_user"]=u
        pwd=self._pass.get().strip()
        if pwd:
            _ssh_passwords[self.device.get("ip","")] = pwd
        self.on_confirm(self.device,self._act.get()); self.destroy()

# ─────────────────────────────────────────────────────────────────────────────
#  DEVICE EDIT DIALOG
# ─────────────────────────────────────────────────────────────────────────────
ICONS = ["💻","🖥️","🖨️","📱","📡","🔌","🛡️","🌐","🎮","📷","🔧","💾",
         "📺","🔬","🖱️","🧰","⌨️","🖲️","📶","🔒","⚙️","🔩","🗄️","📦"]

class DevDlg(tk.Toplevel):
    def __init__(self, parent, device=None, on_save=None):
        super().__init__(parent)
        self.on_save=on_save; self.dev=dict(device) if device else {}
        self.title("Device Properties"); self.configure(bg=C["bg"])
        self.resizable(False,False); self.grab_set()
        w,h=530,640; self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        TitleBar(self,title="Device Properties",icon="⚙️",h=28).pack(fill="x")
        nb=ttk.Notebook(self); nb.pack(fill="both",expand=True,padx=8,pady=8)

        # General
        g=tk.Frame(nb,bg=C["bg"]); nb.add(g,text="  General  ")
        self._v={}
        for row,(lbl,key) in enumerate([
            ("Display Name","name"),("IP Address","ip"),("MAC Address","mac"),
            ("Hostname","hostname"),("OS","os"),("Group","group"),
        ]):
            tk.Label(g,text=lbl+":",bg=C["bg"],font=F(9),anchor="e",width=14
                     ).grid(row=row,column=0,padx=8,pady=5,sticky="e")
            v=tk.StringVar(value=self.dev.get(key,""))
            tk.Entry(g,textvariable=v,font=F(9),relief="sunken",bd=2,width=34
                     ).grid(row=row,column=1,padx=4,pady=5,sticky="w")
            self._v[key]=v
        r=6
        tk.Label(g,text="Icon:",bg=C["bg"],font=F(9),anchor="ne",width=14
                 ).grid(row=r,column=0,padx=8,pady=5,sticky="ne")
        icf=tk.Frame(g,bg=C["bg"]); icf.grid(row=r,column=1,sticky="w")
        self._icon_v=tk.StringVar(value=self.dev.get("icon","💻"))
        for i,ic in enumerate(ICONS):
            tk.Radiobutton(icf,text=ic,variable=self._icon_v,value=ic,
                           bg=C["bg"],font=F(13),indicatoron=False,
                           padx=1,pady=0,selectcolor=C["sel"],relief="flat"
                           ).grid(row=i//12,column=i%12,padx=1,pady=1)
        tk.Label(g,text="Notes:",bg=C["bg"],font=F(9),anchor="ne",width=14
                 ).grid(row=r+2,column=0,padx=8,pady=5,sticky="ne")
        self._notes=tk.Text(g,font=F(9),relief="sunken",bd=2,width=34,height=3)
        self._notes.insert("1.0",self.dev.get("notes",""))
        self._notes.grid(row=r+2,column=1,padx=4,pady=5,sticky="w")

        # Remote
        rem=tk.Frame(nb,bg=C["bg"]); nb.add(rem,text="  Remote Access  ")
        for row,(lbl,key,hint) in enumerate([
            ("AnyDesk ID","anydesk_id","Auto-discovered via SSH · or enter manually"),
            ("RDP Address","rdp_address","IP or hostname for Remote Desktop"),
            ("SSH Username","ssh_user","Auto-detected on scan · or set manually"),
        ]):
            tk.Label(rem,text=lbl+":",bg=C["bg"],font=F(9),anchor="e",width=16
                     ).grid(row=row*2,column=0,padx=8,pady=(10,0),sticky="e")
            v=tk.StringVar(value=self.dev.get(key,""))
            tk.Entry(rem,textvariable=v,font=F(9),relief="sunken",bd=2,width=32
                     ).grid(row=row*2,column=1,padx=4,pady=(10,0),sticky="w")
            tk.Label(rem,text=hint,bg=C["bg"],font=F(8),fg=C["gray"]
                     ).grid(row=row*2+1,column=1,sticky="w",padx=5)
            self._v[key]=v

        # Auto-Info (read-only)
        inf=tk.Frame(nb,bg=C["bg"]); nb.add(inf,text="  Auto-Info  ")
        for row,(lbl,key) in enumerate([
            ("CPU","cpu"),("CPU Cores","cpu_cores"),("RAM","ram"),
            ("Disk","disk"),("Uptime","uptime"),("Kernel","kernel"),
            ("Architecture","arch"),("Load Avg","load"),
            ("Logged Users","users"),("Services","services"),
            ("Timezone","timezone"),("Shell","shell"),
        ]):
            tk.Label(inf,text=lbl+":",bg=C["bg"],font=F(9,True),anchor="e",width=14,
                     fg=C["sel2"]).grid(row=row,column=0,padx=8,pady=3,sticky="e")
            v=tk.StringVar(value=self.dev.get(key,"—"))
            tk.Label(inf,textvariable=v,bg=C["bg"],font=F(9),anchor="w",
                     wraplength=310,justify="left"
                     ).grid(row=row,column=1,padx=4,pady=3,sticky="w")

        bf=tk.Frame(self,bg=C["bg"]); bf.pack(fill="x",padx=8,pady=8)
        Btn(bf,kind="g",text="  OK  ",command=self._save).pack(side="right",padx=4)
        Btn(bf,text="Cancel",command=self.destroy).pack(side="right")

    def _save(self):
        for k,v in self._v.items(): self.dev[k]=v.get().strip()
        self.dev["icon"]=self._icon_v.get()
        self.dev["notes"]=self._notes.get("1.0","end").strip()
        if not self.dev.get("mac"):
            messagebox.showerror("Error","MAC address is required.",parent=self); return
        m=mac_norm(self.dev["mac"])
        if not m:
            messagebox.showerror("Error","Invalid MAC — expected AA:BB:CC:DD:EE:FF",parent=self); return
        self.dev["mac"]=m
        if self.on_save: self.on_save(self.dev)
        self.destroy()

# ─────────────────────────────────────────────────────────────────────────────
#  SCANNER
# ─────────────────────────────────────────────────────────────────────────────
class Scanner:
    def __init__(self, on_found, on_prog=None, on_done=None):
        self.on_found=on_found; self.on_prog=on_prog; self.on_done=on_done
        self._stop=threading.Event()
    def stop(self): self._stop.set()
    def run(self, subnet):
        self._stop.clear()
        try: net=ipaddress.ip_network(subnet,strict=False)
        except: net=ipaddress.ip_network("192.168.0.0/24")
        hosts=[str(h) for h in net.hosts()]; total=len(hosts)
        done=[0]; lock=threading.Lock(); all_done=threading.Event()
        sem=threading.Semaphore(64)
        def _p(h):
            with sem:
                if not self._stop.is_set(): ping_host(h,timeout=1)
            with lock:
                done[0]+=1
                if self.on_prog:
                    try: self.on_prog(done[0]/total)
                    except: pass
                if done[0]>=total: all_done.set()
        for h in hosts:
            if self._stop.is_set(): break
            threading.Thread(target=_p,args=(h,),daemon=True).start()
        all_done.wait(timeout=12)
        if self._stop.is_set():
            if self.on_done: self.on_done(); return
        found={}
        if IS_LIN and shutil.which("ip"):
            try:
                for line in subprocess.check_output(["ip","neigh","show"],
                        stderr=subprocess.DEVNULL,timeout=5).decode(errors="ignore").splitlines():
                    p=line.split()
                    if "lladdr" in p:
                        m=mac_norm(p[p.index("lladdr")+1])
                        if m and m!="ff:ff:ff:ff:ff:ff":
                            try: socket.inet_aton(p[0]); found[p[0]]=m
                            except: pass
            except: pass
        if IS_LIN:
            try:
                with open("/proc/net/arp") as f:
                    for line in f.readlines()[1:]:
                        p=line.split()
                        if len(p)>=4 and p[3] not in ("00:00:00:00:00:00",""):
                            m=mac_norm(p[3])
                            if m: found.setdefault(p[0],m)
            except: pass
        try:
            cmd=["arp","-a"] if IS_WIN else ["arp","-n"]
            for line in subprocess.check_output(cmd,stderr=subprocess.DEVNULL,
                    timeout=5).decode(errors="ignore").splitlines():
                p=line.split(); ic=p[0].strip("()")
                mc=next((x for x in p if re.match(r"([0-9a-fA-F]{1,2}[:\-]){5}[0-9a-fA-F]{1,2}",x)),"")
                try:
                    socket.inet_aton(ic); m=mac_norm(mc)
                    if m and m!="ff:ff:ff:ff:ff:ff": found.setdefault(ic,m)
                except: pass
        except: pass
        if shutil.which("nmap") and not self._stop.is_set():
            try:
                out=subprocess.check_output(["nmap","-sn","--min-rate=200",subnet],
                    stderr=subprocess.DEVNULL,timeout=45).decode(errors="ignore")
                last_ip=None
                for line in out.splitlines():
                    mm=re.search(r"(\d+\.\d+\.\d+\.\d+)",line)
                    if mm: last_ip=mm.group(1)
                    mm=re.search(r"MAC Address: ([0-9A-Fa-f:]{17})",line)
                    if mm and last_ip:
                        mn=mac_norm(mm.group(1))
                        if mn: found.setdefault(last_ip,mn)
            except: pass
        for ip_a,mac_a in list(found.items()):
            if self._stop.is_set(): break
            try:
                if ipaddress.ip_address(ip_a) not in net: continue
            except: continue
            alive=ping_host(ip_a,timeout=1); hname=hostname_of(ip_a)
            try: self.on_found(ip_a,mac_a,hname,"online" if alive else "offline")
            except Exception as e: print(f"[Scanner] {ip_a}: {e}")
        if self.on_done: self.on_done()

# ─────────────────────────────────────────────────────────────────────────────
#  DEVICE CARD
# ─────────────────────────────────────────────────────────────────────────────
def dlabel(d): return d.get("name") or d.get("hostname") or d.get("mac","?")

class DevCard(tk.Frame):
    _ST={"online":(C["on"],"🟢","Online"),"offline":(C["off"],"⚫","Offline"),
         "waking":(C["wak"],"🟡","Waking…"),"shutting":(C["shut"],"🔴","Shutting…"),
         "disc":(C["disc"],"🔵","Discovering…")}

    def __init__(self, parent, dev, on_act, even=False, **kw):
        bg=C["card_b"] if even else C["card_a"]
        super().__init__(parent,bg=bg,highlightthickness=1,
                         highlightbackground=C["card_bd"],**kw)
        self.dev=dev; self.on_act=on_act; self._bg=bg
        self._build()

    def _build(self):
        d=self.dev; status=d.get("status","offline")
        sc,sd,st=self._ST.get(status,(C["off"],"⚫","?"))

        # Colour strip
        tk.Frame(self,bg=sc,width=6).pack(side="left",fill="y")

        # Icon
        ic=tk.Label(self,text=d.get("icon","💻"),font=F(22),bg=self._bg,cursor="hand2")
        ic.pack(side="left",padx=(10,6),pady=8)
        ic.bind("<Button-1>",     lambda _: self.on_act("select",d.get("mac","")))
        ic.bind("<Double-Button-1>",lambda _: self.on_act("double",d.get("mac","")))

        # Info
        mf=tk.Frame(self,bg=self._bg); mf.pack(side="left",fill="both",expand=True,pady=5)

        # Row 1: name + badges
        r1=tk.Frame(mf,bg=self._bg); r1.pack(fill="x")
        tk.Label(r1,text=dlabel(d),font=F(11,True),fg=C["ta"],
                 bg=self._bg,anchor="w").pack(side="left")
        tk.Label(r1,text=f"  {sd} {st}",font=F(8),fg=sc,bg=self._bg).pack(side="left",padx=4)
        if d.get("ssh_user"):
            tk.Label(r1,text=f" 🔑{d['ssh_user']}",font=F(7),fg=C["on"],bg=self._bg).pack(side="left")
        if d.get("anydesk_id"):
            tk.Label(r1,text=f" 🖥️{d['anydesk_id']}",font=F(7),fg=C["sel"],bg=self._bg).pack(side="left")
        if (g:=d.get("group","")) and g!="Default":
            tk.Label(r1,text=f" [{g}]",font=F(7),fg=C["gray"],bg=self._bg).pack(side="left",padx=2)

        # Row 2: IP · MAC · vendor · OS
        r2=tk.Frame(mf,bg=self._bg); r2.pack(fill="x")
        for txt,col in [(d.get("ip",""),C["sel2"]),(d.get("mac",""),"#566678"),
                        ("["+oui(d.get("mac","000000000000"))+"]",C["gray"]),
                        (d.get("os",""),"#445566")]:
            if txt and txt not in ("","[]","[Unknown]"):
                tk.Label(r2,text=txt+"  ",font=F(8),fg=col,bg=self._bg).pack(side="left")

        # Row 3: last seen · wol · anydesk · services
        r3=tk.Frame(mf,bg=self._bg); r3.pack(fill="x")
        for txt,col in [
            (f"🕐 {d['last_seen']}"   if d.get("last_seen")  else "", C["gray"]),
            (f"⚡×{d['wol_count']}"   if d.get("wol_count")  else "", C["wak"]),
            (f"🔌 {d['services']}"    if d.get("services")   else "", "#448844"),
        ]:
            if txt: tk.Label(r3,text=txt+"  ",font=F(8),fg=col,bg=self._bg).pack(side="left")

        # Row 4: hardware info
        r4=tk.Frame(mf,bg=self._bg); r4.pack(fill="x")
        for txt,col in [
            (f"💾 {d['ram']}"   if d.get("ram")    else "", "#446644"),
            (f"📀 {d['disk']}"  if d.get("disk")   else "", "#664444"),
            (f"⏱ {d['uptime']}" if d.get("uptime") else "", "#444466"),
            (f"⚙ {d['cpu']}"   if d.get("cpu")    else "", "#444444"),
        ]:
            if txt: tk.Label(r4,text=txt+"  ",font=FX(7),fg=col,bg=self._bg).pack(side="left")

        # Buttons
        rf=tk.Frame(self,bg=self._bg); rf.pack(side="right",padx=6,pady=6)
        mac=d.get("mac","")
        def B(parent, ico, tip, act, kind="n"):
            b=XBtn(parent,kind=kind,text=ico,
                   command=lambda a=act,m=mac: self.on_act(a,m),
                   font=F(11),padx=7,pady=2,snd=True,bd=2)
            b.pack(side="left",padx=1,pady=1); Tip(b,tip); return b

        r_a=tk.Frame(rf,bg=self._bg); r_a.pack()
        B(r_a,"⚡","Wake on LAN",         "wake",     "w")
        B(r_a,"🖥️","AnyDesk Connect",      "anydesk",  "b")
        B(r_a,"🎮","Get AnyDesk ID",       "get_ad",   "b")
        B(r_a,"💻","Remote Desktop (RDP)", "rdp",      "g")
        B(r_a,"🔑","SSH Terminal",         "ssh",      "n")

        r_b=tk.Frame(rf,bg=self._bg); r_b.pack()
        B(r_b,"🔴","Shutdown",             "shutdown", "d")
        B(r_b,"🔁","Reboot",               "reboot",   "w")
        B(r_b,"💬","Send Message",         "message",  "n")
        B(r_b,"🔔","Sound Ping",           "sndping",  "n")
        B(r_b,"📋","Ping",                 "ping",     "n")

        r_c=tk.Frame(rf,bg=self._bg); r_c.pack()
        B(r_c,"🔍","Port Scan",            "portscan", "n")
        B(r_c,"🔭","Auto-Discover",        "disc",     "b")
        B(r_c,"📊","SSH System Info",      "sshinfo",  "n")
        B(r_c,"✏️","Edit Properties",      "edit",     "n")
        B(r_c,"🗑️","Remove Device",        "remove",   "d")

    def highlight(self, on):
        self.config(bg=C["card_s"] if on else self._bg,
                    highlightbackground=C["sel"] if on else C["card_bd"],
                    highlightthickness=2 if on else 1)

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=C["bg"])
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        w,h=min(1300,sw-50),min(800,sh-50)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(980,640)
        self.protocol("WM_DELETE_WINDOW",self._quit)

        self.db=DeviceDB()
        self._scanner=None; self._scanning=False
        self._sel_mac=None; self._cards={}
        self._filter=tk.StringVar(); self._subnet_v=tk.StringVar()
        self._spin=0
        self._subnet,self._my_ip,self._my_bc=local_network()
        self._my_name=socket.gethostname()
        self._subnet_v.set(self._subnet)
        try:   self._filter.trace_add("write",lambda *_: self._render())
        except: self._filter.trace("w",lambda *_: self._render())

        self._server=NetServer(on_recv=self._on_pkt)
        self._srv_ok=self._server.start()

        self._build_ui(); self._styles()
        self._render(); self._update_status()
        threading.Thread(target=precache,daemon=True).start()
        self.after(200,lambda: play("logon"))
        self._clock()
        self.after(700,self._fetch_my_ad)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Title bar
        self._tb=TitleBar(self,title=f"{APP_NAME}  {APP_VER}",icon="⬡",h=30)
        self._tb.pack(fill="x"); self._tb.bind("<Configure>",self._tb._draw)
        tk.Button(self,text="✕",bg="#AA1818",fg="white",relief="flat",bd=0,
                  font=F(8,True),activebackground="#EE3333",activeforeground="white",
                  cursor="hand2",padx=8,pady=5,command=self._quit
                  ).place(relx=1.0,x=-2,y=2,anchor="ne")

        # Menu
        mb=tk.Menu(self,font=F(9),bg=C["bg"],fg="black",relief="flat",tearoff=0)
        self.config(menu=mb)
        def M(lbl,items):
            m=tk.Menu(mb,tearoff=0,font=F(9))
            for it in items:
                if it=="---": m.add_separator()
                else: m.add_command(label=it[0],command=it[1])
            mb.add_cascade(label=lbl,menu=m)
        M("File",[
            ("➕  Add Device",          self._add),
            ("📂  Import JSON…",        self._import),
            ("💾  Export JSON…",        self._export),
            ("📊  Export CSV…",         self._export_csv),
            "---",("❌  Exit",           self._quit),
        ])
        M("Scan",[
            ("🔍  Scan Network",        self._scan_start),
            ("⏹  Stop Scan",           self._scan_stop),
            "---",
            ("🔄  Refresh All",         self._refresh_all),
            ("🔭  Auto-Discover All",   self._disc_all),
        ])
        M("Network",[
            ("📢  Broadcast Message…",  self._bc_msg),
            ("🔔  Broadcast Sound",     self._bc_sound),
            "---",
            ("🗺️  Network Map",         self._netmap),
            ("📡  Live Monitor",        self._live_monitor),
        ])
        M("View",[
            ("⬇ Sort: Name",  lambda: self._sort("name")),
            ("⬇ Sort: IP",    lambda: self._sort("ip")),
            ("⬇ Sort: Status",lambda: self._sort("status")),
            ("⬇ Sort: Vendor",lambda: self._sort("vendor")),
            "---",
            ("📊 Statistics",  self._stats),
            ("🔧 System Info", self._sysinfo),
        ])
        M("Help",[("ℹ️  About",self._about)])

        # Toolbar
        tbar=tk.Frame(self,bg=C["bg2"],bd=1,relief="raised"); tbar.pack(fill="x")
        def TB(ico,lbl,cmd,tip="",kind="n"):
            b=XBtn(tbar,kind=kind,text=f"{ico}\n{lbl}",command=cmd,
                   font=F(7),padx=6,pady=2,snd=False,bd=1)
            b.pack(side="left",padx=1,pady=1); Tip(b,tip or lbl); return b
        def SEP():
            tk.Frame(tbar,bg=C["sep"],width=2).pack(side="left",fill="y",padx=4,pady=2)

        TB("🔍","Scan",       self._scan_start, "Scan entire subnet","b")
        TB("⏹","Stop",       self._scan_stop,  "Stop scanning")
        SEP()
        TB("➕","Add",        self._add,         "Add device manually")
        TB("🔄","Refresh",    self._refresh_all, "Ping all devices")
        TB("🔭","Discover",   self._disc_all,    "Auto-discover all online","b")
        SEP()
        TB("📢","Broadcast",  self._bc_msg,      "Message all online devices")
        TB("🔔","Sound All",  self._bc_sound,    "Sound ping all","w")
        SEP()
        TB("🗺️","Net Map",    self._netmap,      "Network topology map")
        TB("📡","Monitor",    self._live_monitor,"Live status monitor")
        TB("📊","Stats",      self._stats,       "Network statistics")
        TB("🔧","Info",       self._sysinfo,     "System & tool info")
        SEP()
        self._spin_lbl=tk.Label(tbar,text="",bg=C["bg2"],font=F(12),fg=C["sel"],width=3)
        self._spin_lbl.pack(side="left",padx=4)
        self._ad_lbl=tk.Label(tbar,text="",bg=C["bg2"],font=F(8),fg=C["sel2"])
        self._ad_lbl.pack(side="right",padx=10)

        # Filter bar
        sf=tk.Frame(self,bg=C["bg2"],bd=1,relief="raised"); sf.pack(fill="x")
        tk.Label(sf,text=" Subnet:",bg=C["bg2"],font=F(9)).pack(side="left",padx=4)
        tk.Entry(sf,textvariable=self._subnet_v,font=F(9),relief="sunken",bd=2,width=18
                 ).pack(side="left",padx=4,pady=3)
        XBtn(sf,text="Go",command=self._scan_start,padx=10).pack(side="left",padx=2)
        tk.Frame(sf,bg=C["sep"],width=2).pack(side="left",fill="y",padx=6,pady=2)
        tk.Label(sf,text="🔍 Filter:",bg=C["bg2"],font=F(9)).pack(side="left",padx=4)
        tk.Entry(sf,textvariable=self._filter,font=F(9),relief="sunken",bd=2,width=28
                 ).pack(side="left",padx=4,pady=3)
        XBtn(sf,text="✕",command=lambda: self._filter.set(""),padx=4,snd=False).pack(side="left")
        self._cnt_lbl=tk.Label(sf,text="",bg=C["bg2"],font=F(9),fg=C["ta"])
        self._cnt_lbl.pack(side="right",padx=12)

        # Main paned workspace
        pane=tk.PanedWindow(self,orient="horizontal",bg=C["bg2"],sashwidth=5,sashrelief="flat")
        pane.pack(fill="both",expand=True)

        # Left — card list
        left=tk.Frame(pane,bg=C["bg"]); pane.add(left,minsize=640)
        hdr=tk.Frame(left,bg=C["ta"]); hdr.pack(fill="x")
        tk.Label(hdr,text="  ⬡  Network Devices",bg=C["ta"],fg="white",
                 font=F(10,True),anchor="w",pady=6).pack(side="left",fill="x",expand=True)
        self._onl_lbl=tk.Label(hdr,text="",bg=C["ta"],fg="#88FF88",font=F(9),padx=10)
        self._onl_lbl.pack(side="right")

        outer=tk.Frame(left,bg=C["bg"]); outer.pack(fill="both",expand=True)
        self._canvas=tk.Canvas(outer,bg=C["bg"],bd=0,highlightthickness=0)
        vsb=ttk.Scrollbar(outer,orient="vertical",command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right",fill="y"); self._canvas.pack(side="left",fill="both",expand=True)
        self._cf=tk.Frame(self._canvas,bg=C["bg"])
        self._cw=self._canvas.create_window((0,0),window=self._cf,anchor="nw")
        self._cf.bind("<Configure>",lambda _: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",lambda e: self._canvas.itemconfig(self._cw,width=e.width))
        for ev,d in [("<MouseWheel>",lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)),"units")),
                     ("<Button-4>",  lambda _: self._canvas.yview_scroll(-1,"units")),
                     ("<Button-5>",  lambda _: self._canvas.yview_scroll( 1,"units"))]:
            self._canvas.bind(ev,d)
        self._prog=ttk.Progressbar(left,mode="determinate",style="XP.Horizontal.TProgressbar")

        # Right — detail panel
        right=tk.Frame(pane,bg=C["bg3"],bd=1,relief="sunken"); pane.add(right,minsize=240)
        hdr2=tk.Frame(right,bg=C["tb"],height=28); hdr2.pack(fill="x")
        hdr2.pack_propagate(False)
        tk.Label(hdr2,text="  ⬡  Device Details",bg=C["tb"],fg="white",
                 font=F(9,True),anchor="w").pack(fill="both",expand=True,padx=8)
        df=tk.Frame(right,bg=C["bg3"]); df.pack(fill="x",padx=10,pady=6)
        self._dv={}
        for row,(ico,lbl,key) in enumerate([
            ("🏷️","Name","name"),      ("🌐","IP","ip"),
            ("🔌","MAC","mac"),        ("🏭","Vendor","vendor"),
            ("💻","Hostname","hostname"),("🖥️","OS","os"),
            ("⚡","WOL×","wol_count"), ("🕐","Last Seen","last_seen"),
            ("🎮","AnyDesk","anydesk_id"),("🔑","SSH User","ssh_user"),
            ("💾","RAM","ram"),         ("📀","Disk","disk"),
            ("⏱","Uptime","uptime"),   ("⚙","CPU","cpu"),
            ("🔌","Services","services"),("📝","Notes","notes"),
        ]):
            tk.Label(df,text=f"{ico} {lbl}",bg=C["bg3"],font=F(8,True),
                     fg=C["ta"],anchor="w").grid(row=row,column=0,sticky="w",pady=1)
            v=tk.StringVar(value="—")
            tk.Label(df,textvariable=v,bg=C["bg3"],font=F(8),anchor="w",
                     wraplength=195,justify="left").grid(row=row,column=1,sticky="w",padx=4,pady=1)
            self._dv[key]=v
        sep=tk.Frame(right,bg=C["sep"],height=1); sep.pack(fill="x",pady=4)
        qf=tk.Frame(right,bg=C["bg3"]); qf.pack(fill="x",padx=8,pady=2)
        tk.Label(qf,text="Quick Actions",bg=C["bg3"],font=F(8,True),fg=C["gray"]).pack(anchor="w",pady=(0,3))
        for txt,act,kind in [
            ("⚡ Wake on LAN",     "wake",    "w"),("🖥️ AnyDesk Connect",  "anydesk","b"),
            ("🎮 Get AnyDesk ID",  "get_ad",  "b"),("💻 Remote Desktop",   "rdp",   "g"),
            ("🔑 SSH Terminal",    "ssh",     "n"),("📋 Ping Device",       "ping",  "n"),
            ("🔍 Port Scan",       "portscan","n"),("🔭 Auto-Discover",     "disc",  "b"),
            ("🔴 Shutdown",        "shutdown","d"),("🔁 Reboot",            "reboot","w"),
            ("💬 Send Message",    "message", "n"),("🔔 Sound Ping",        "sndping","n"),
            ("✏️ Edit Properties","edit",    "n"),("🗑️ Remove Device",     "remove","d"),
        ]:
            XBtn(qf,kind=kind,text=txt,anchor="w",padx=6,
                 command=lambda a=act: self._action(a,self._sel_mac)
                 ).pack(fill="x",pady=1)

        # Event log
        self._elog=EventLog(self,height=115); self._elog.pack(fill="x",side="bottom")
        # Status bar
        sb=SBar(self); sb.pack(fill="x",side="bottom")
        self._sb=sb.add(); self._sb_cnt=sb.add(width=16)
        self._sb_net=sb.add(width=30); self._sb_os=sb.add(width=22)
        self._sb_t=sb.add(width=16,anchor="e")

    def _styles(self):
        s=ttk.Style(); s.theme_use("clam")
        s.configure("XP.Horizontal.TProgressbar",
            troughcolor=C["bg2"],background="#3D9B3D",
            darkcolor="#2A7A2A",lightcolor="#70D070",bordercolor=C["sep"])

    # ─── Render ───────────────────────────────────────────────────────────────
    def _render(self):
        q=self._filter.get().strip().lower()
        for w in self._cf.winfo_children(): w.destroy()
        self._cards.clear()
        visible=[self.db.get(m) for m in self.db.macs()
                 if q in " ".join(str(v) for v in self.db.get(m).values()).lower()]
        if not visible:
            msg=("No devices match the filter." if q else
                 "No devices found.\n\nClick 🔍 Scan to discover your network\n"
                 "or ➕ Add to add a device manually.")
            tk.Label(self._cf,text=msg,bg=C["bg"],font=F(11),fg=C["gray"],
                     justify="center",pady=70).pack(expand=True)
            self._cnt_lbl.config(text=""); self._upd_onl([])
            return
        for i,dev in enumerate(visible):
            mac=dev.get("mac","")
            card=DevCard(self._cf,dev,on_act=self._card_act,even=(i%2==1))
            card.pack(fill="x",padx=4,pady=2)
            self._cards[mac]=card
        n=len(visible)
        self._cnt_lbl.config(text=f"  {n} device{'s' if n!=1 else ''}  ")
        self._upd_onl(visible)
        if self._sel_mac and self._sel_mac in self._cards:
            self._cards[self._sel_mac].highlight(True)

    def _upd_onl(self, vis):
        on=sum(1 for d in vis if d.get("status")=="online"); t=len(vis)
        self._onl_lbl.config(text=f"🟢 {on}  ⚫ {t-on}  " if vis else "")

    def _elog_l(self, kind, msg, col="white"):
        try: self._elog.log(kind,msg,col)
        except: pass

    # ─── Card / Action dispatch ───────────────────────────────────────────────
    def _card_act(self, act, mac):
        if self._sel_mac and self._sel_mac in self._cards:
            self._cards[self._sel_mac].highlight(False)
        self._sel_mac=mac
        if mac in self._cards: self._cards[mac].highlight(True)
        self._upd_detail(self.db.get(mac))
        if act not in ("select",): self._action(act,mac)

    def _action(self, act, mac):
        if not mac:
            if act!="select":
                messagebox.showinfo("No Device","Please select a device first.",parent=self)
            return
        dev=self.db.get(mac)
        if not dev: return
        if act=="double":
            act="anydesk" if (dev.get("status")=="online" and dev.get("anydesk_id")) else "wake"
        {
            "wake":     self._do_wake,     "anydesk":  self._do_anydesk,
            "get_ad":   self._do_get_ad,   "rdp":      self._do_rdp,
            "ssh":      self._do_ssh,      "ping":     self._do_ping,
            "portscan": self._do_portscan, "shutdown": self._do_shutdown,
            "reboot":   self._do_reboot,   "message":  self._do_message,
            "sndping":  self._do_sndping,  "disc":     self._do_disc,
            "sshinfo":  self._do_sshinfo,  "edit":     self._do_edit,
            "remove":   self._do_remove,
        }.get(act, lambda d: None)(dev)

    def _upd_detail(self, dev):
        for k,v in self._dv.items():
            val=(dev or {}).get(k,""); v.set(str(val) if val else "—")

    def _sort(self, key):
        def k(m):
            d=self.db.get(m); v=d.get(key,"") or ""
            if key=="ip":
                try: return tuple(int(x) for x in str(v).split("."))
                except: return (0,)
            return str(v).lower()
        self.db.data={m:self.db.data[m] for m in sorted(self.db.macs(),key=k) if m in self.db.data}
        self._render()

    # ─── WAKE ─────────────────────────────────────────────────────────────────
    def _do_wake(self, dev):
        mac=dev.get("mac","")
        if not mac: messagebox.showerror("Error","No MAC address.",parent=self); return
        self.db.upsert(mac,wol_count=dev.get("wol_count",0)+1,status="waking")
        bc=bcast_for(dev.get("ip","")) if dev.get("ip") else self._my_bc
        play("exclaim")
        self._elog_l("wol",f"WOL → {dlabel(dev)}  ({bc})","yellow")
        WOLScreen(self,self.db.get(mac),bcast=bc,
                  on_done=lambda ok,m=mac: self._wol_done(m,ok)).start()

    def _wol_done(self, mac, ok):
        dev=self.db.get(mac)
        if ok:
            self.db.upsert(mac,status="online",last_seen=datetime.now().strftime("%Y-%m-%d %H:%M"))
            play("tada"); name=dlabel(dev)
            self._elog_l("online",f"{name} is ONLINE","green")
            Toast(self,"PC Online! 🟢",f"{name} woke up.","⚡")
            if dev.get("anydesk_id"):
                if messagebox.askyesno("🟢 Online!",f"'{name}' is online!\n\nOpen AnyDesk?",parent=self):
                    self._do_anydesk(self.db.get(mac))
            else:
                messagebox.showinfo("🟢 Online!",f"'{name}' is now online!",parent=self)
        else:
            self.db.upsert(mac,status="offline")
            self._elog_l("error",f"WOL timeout — {dlabel(dev)} — check BIOS WOL setting","yellow")
        self._render(); self._update_status()

    # ─── ANYDESK ──────────────────────────────────────────────────────────────
    def _do_anydesk(self, dev):
        mac=dev.get("mac",""); ad=dev.get("anydesk_id","").strip()
        if not ad:
            ad=simpledialog.askstring("AnyDesk ID",f"AnyDesk ID for '{dlabel(dev)}':",parent=self)
            if not ad: return
            self.db.upsert(mac,anydesk_id=ad.strip()); self._render()
        paths=([r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe",
                r"C:\Program Files\AnyDesk\AnyDesk.exe"] if IS_WIN
               else ["/usr/bin/anydesk","/usr/local/bin/anydesk","/opt/anydesk/anydesk"])
        cmd=None
        for p in paths:
            if os.path.isfile(p): cmd=[p]; break
        if not cmd and shutil.which("anydesk"): cmd=["anydesk"]
        if not cmd and IS_LIN and shutil.which("flatpak"):
            try:
                r=subprocess.run(["flatpak","list","--app","--columns=application"],
                    capture_output=True,text=True,timeout=4)
                if "com.anydesk.Anydesk" in r.stdout: cmd=["flatpak","run","com.anydesk.Anydesk"]
            except: pass
        if cmd:
            try:
                subprocess.Popen(cmd+[ad]); play("notify")
                self._elog_l("anydesk",f"AnyDesk → {dlabel(dev)} ({ad})","cyan"); return
            except: pass
        messagebox.showerror("AnyDesk Not Found",
            f"AnyDesk not installed.\nID: {ad}\n\n"
            "Fedora: sudo dnf install anydesk\n"
            "or: flatpak install flathub com.anydesk.Anydesk",parent=self)

    def _do_get_ad(self, dev):
        mac=dev.get("mac",""); ip=dev.get("ip",""); user=dev.get("ssh_user","")
        if not ip: messagebox.showerror("Error","No IP.",parent=self); return
        if not user:
            user=simpledialog.askstring("SSH User","SSH username:",parent=self)
            if not user: return
            self.db.upsert(mac,ssh_user=user)
        self._elog_l("disc",f"Fetching AnyDesk ID from {ip}…","cyan")
        def run():
            cmd=("anydesk --get-id 2>/dev/null"
                 " || grep -oP '(?<=raw_id=)\\d+' /etc/anydesk/system.conf 2>/dev/null"
                 " || grep -oP '(?<=id=)\\d+' ~/.anydesk/user.conf 2>/dev/null")
            o,_,rc=ssh_run(ip,user,cmd,timeout=7)
            digits=re.sub(r"[^0-9]","",o.strip()) if o else ""
            if len(digits)>=6:
                self.db.upsert(mac,anydesk_id=digits)
                self.after(0,lambda d=digits: [
                    self._render(), self._upd_detail(self.db.get(mac)),
                    self._elog_l("anydesk",f"AnyDesk ID: {d} on {dlabel(self.db.get(mac))}","cyan"),
                    Toast(self,"AnyDesk ID Found 🎮",f"{dlabel(self.db.get(mac))}: {d}","🎮"),
                ])
            else:
                self.after(0,lambda: messagebox.showerror("Not Found",
                    f"Could not get AnyDesk ID from {ip}.\n"
                    "Ensure AnyDesk is installed and running.",parent=self))
        threading.Thread(target=run,daemon=True).start()

    # ─── RDP / SSH ────────────────────────────────────────────────────────────
    def _do_rdp(self, dev):
        addr=dev.get("rdp_address") or dev.get("ip","")
        if not addr:
            addr=simpledialog.askstring("RDP","IP or hostname:",parent=self)
            if not addr: return
        if IS_WIN:
            try: subprocess.Popen(["mstsc",f"/v:{addr}"]); play("notify"); return
            except: pass
        for cl,fl in [("xfreerdp",f"/v:{addr}"),("remmina",f"rdp://{addr}"),("rdesktop",addr)]:
            if shutil.which(cl):
                try: subprocess.Popen([cl,fl]); play("notify"); return
                except: pass
        messagebox.showerror("RDP","No RDP client.\n  sudo dnf install freerdp -y",parent=self)

    def _do_ssh(self, dev):
        ip=dev.get("ip",""); user=dev.get("ssh_user","")
        if not ip: messagebox.showerror("SSH","No IP.",parent=self); return
        target=f"{user}@{ip}" if user else ip
        if IS_WIN:
            try: subprocess.Popen(f'start cmd /k "ssh {target}"',shell=True); play("notify"); return
            except: pass
        for b,fl in [("gnome-terminal","--"),("xfce4-terminal","-x"),
                     ("konsole","-e"),("xterm","-e"),("alacritty","-e"),("kitty","")]:
            if shutil.which(b):
                args=[b,fl,"ssh",target] if fl else [b,"ssh",target]
                try: subprocess.Popen([a for a in args if a]); play("notify"); return
                except: pass
        messagebox.showerror("SSH","No terminal.\n  sudo dnf install xterm -y",parent=self)

    # ─── PING ─────────────────────────────────────────────────────────────────
    def _do_ping(self, dev):
        ip=dev.get("ip","")
        if not ip: messagebox.showerror("Ping","No IP.",parent=self); return
        tw=TermWin(self,title=f"Ping: {dlabel(dev)}  [{ip}]",icon="📋",w=620,h=360)
        tw.add_btn("Ping Again",lambda: self._run_ping(tw,ip))
        self._run_ping(tw,ip)

    def _run_ping(self, tw, ip):
        tw._txt.config(state="normal"); tw._txt.delete("1.0","end"); tw._txt.config(state="disabled")
        tw.w(f"Pinging {ip}  [{datetime.now().strftime('%H:%M:%S')}]\n\n")
        def run():
            cmd=["ping","-n","4",ip] if IS_WIN else ["ping","-c","4",ip]
            try:
                proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                for line in proc.stdout:
                    tw.after(0,lambda l=line: tw.w(l.decode(errors="ignore")))
                proc.wait(); tw.after(0,lambda: tw.w("\n── Done ──\n"))
            except Exception as e:
                tw.after(0,lambda: tw.w(f"\nError: {e}\n","err"))
        threading.Thread(target=run,daemon=True).start()

    # ─── PORT SCAN ────────────────────────────────────────────────────────────
    def _do_portscan(self, dev):
        ip=dev.get("ip","")
        if not ip: messagebox.showerror("Port Scan","No IP.",parent=self); return
        tw=TermWin(self,title=f"Port Scan: {dlabel(dev)}  [{ip}]",icon="🔍",w=500,h=400)
        tw.w(f"Scanning {ip} — {len(COMMON_PORTS)} common ports…\n\n")
        prog=ttk.Progressbar(tw,mode="indeterminate"); prog.pack(fill="x"); prog.start(10)
        mac=dev.get("mac","")
        def run():
            open_p={}
            for port,svc in COMMON_PORTS.items():
                if tcp_check(ip,port,timeout=1.2): open_p[port]=svc
            tw.after(0,prog.stop); tw.after(0,prog.pack_forget)
            if open_p:
                tw.after(0,lambda: tw.w(f"Open ports on {ip}:\n\n"))
                for p,s in sorted(open_p.items()):
                    tw.after(0,lambda pp=p,ss=s: tw.w(f"  ✓  {pp:5d}/tcp   {ss}\n","val"))
                svc_str=", ".join(f"{p}/{s}" for p,s in sorted(open_p.items()))
                if mac: self.db.upsert(mac,services=svc_str); self.after(0,self._render)
            else:
                tw.after(0,lambda: tw.w("  No common ports open.\n","warn"))
            tw.after(0,lambda: tw.w("\n── Complete ──\n"))
        threading.Thread(target=run,daemon=True).start()

    # ─── SHUTDOWN / REBOOT ────────────────────────────────────────────────────
    def _do_shutdown(self, dev):
        def go(d, act):
            ip=d.get("ip",""); user=d.get("ssh_user","")
            self.db.upsert(d["mac"],ssh_user=user,status="shutting"); self._render()
            name=dlabel(d)
            def run():
                ok,method,err=remote_power(ip,user,reboot=(act=="reboot"),password=_ssh_passwords.get(ip))
                self.db.upsert(d["mac"],status="offline")
                if ok:
                    snd_name="shutdown_snd" if act=="shutdown" else "exclaim"
                    self.after(0,lambda m=method: [
                        play(snd_name),
                        self._elog_l("shutdown",f"{'Shutdown' if act=='shutdown' else 'Reboot'} sent → {name}  (via {m})","red"),
                        Toast(self,f"{'Shutdown' if act=='shutdown' else 'Reboot'} Sent",f"{name}…","🔴",5000),
                    ])
                else:
                    self.after(0,lambda e=err: messagebox.showerror(
                        "Power Command Failed",e,parent=self))
                self.after(0,self._render)
            threading.Thread(target=run,daemon=True).start()
        ShutDlg(self,dev,on_confirm=go)

    def _do_reboot(self, dev):
        def go(d, act):
            ip=d.get("ip",""); user=d.get("ssh_user","")
            self.db.upsert(d["mac"],ssh_user=user); name=dlabel(d)
            def run():
                ok,method,err=remote_power(ip,user,reboot=True,password=_ssh_passwords.get(ip))
                if ok:
                    self.after(0,lambda m=method: [
                        play("exclaim"),
                        self._elog_l("reboot",f"Reboot sent → {name}  (via {m})","yellow"),
                        Toast(self,"Reboot Sent 🔁",f"{name} is rebooting…","🔁",5000),
                    ])
                else:
                    self.after(0,lambda e=err: messagebox.showerror("Reboot Failed",e,parent=self))
                self.after(0,self._render)
            threading.Thread(target=run,daemon=True).start()
        ShutDlg(self,dev,on_confirm=go,default_reboot=True)

    # ─── MESSAGES ─────────────────────────────────────────────────────────────
    def _do_message(self, dev):
        if not dev.get("ip"): messagebox.showerror("Message","No IP.",parent=self); return
        ChatWin.get(self,dev,self._my_name,send_fn=self._send_msg).lift()

    def _send_msg(self, cmd, dev, data=""):
        ip=dev.get("ip",""); user=dev.get("ssh_user","")
        if not ip: return

        if cmd == "message":
            # 1. UDP (if target also runs this app)
            NetServer.send(ip,{"cmd":"message","from_name":self._my_name,
                               "from_ip":self._my_ip,"data":data})
            # 2. SSH: notify-send + wall + zenity (actually appears on screen)
            if user:
                def _ssh_deliver():
                    pwd=_ssh_passwords.get(ip,"")
                    ok,methods=remote_message(ip,user,
                        title=f"Message from {self._my_name}",body=data,
                        password=pwd)
                    self.after(0,lambda m=methods: self._elog_l("msg",
                        f"\u2192 {dlabel(dev)}: {data}  [{m}]","cyan"))
                threading.Thread(target=_ssh_deliver,daemon=True).start()
            else:
                self._elog_l("msg",f"→ {dlabel(dev)}: {data}  [UDP only — no SSH user set]","cyan")

        elif cmd == "sound":
            NetServer.send(ip,{"cmd":"sound","from_name":self._my_name,"from_ip":self._my_ip})
            # Also via SSH paplay / aplay
            if user:
                def _ssh_sound():
                    snd_cmd=("DISPLAY=:0 paplay /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null"
                             " || aplay /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null"
                             " || speaker-test -t sine -f 1000 -l 1 -p 1 2>/dev/null &")
                    ssh_run(ip,user,snd_cmd,timeout=5)
                threading.Thread(target=_ssh_sound,daemon=True).start()
            play("sound_ping")
            self._elog_l("sound",f"Sound ping → {dlabel(dev)}","yellow")

    def _do_sndping(self, dev):
        self._send_msg("sound",dev)

    # ─── AUTO-DISCOVER ────────────────────────────────────────────────────────
    def _do_disc(self, dev):
        """
        Auto-discovery pipeline:
        1. Port scan (always, no auth needed)
        2. DNS hostname lookup
        3. Try SSH key auth in parallel across all common usernames
        4. If key auth fails AND SSH port is open → ask for password once
        5. Retry SSH with password via sshpass
        6. Gather full system info via SSH
        """
        mac=dev.get("mac",""); ip=dev.get("ip","")
        if not ip: messagebox.showerror("Discover","No IP.",parent=self); return

        known_user = dev.get("ssh_user","")
        known_pass = _ssh_passwords.get(ip,"")   # from in-memory store

        self.db.upsert(mac,status="disc"); self._render()
        self._elog_l("disc",f"Starting discovery on {ip}…","cyan"); play("connect")

        # Mutable container so worker thread can set it and main thread reads it
        _pass_box = [known_pass]   # [0] = password (may be filled by dialog)

        def _ask_password_on_main(evt):
            """Called on main thread to show password dialog."""
            pwd = simpledialog.askstring(
                "SSH Password",
                f"No SSH key access found for {ip}.\n\n"
                f"Enter the SSH password to connect\n"
                "(or leave blank to skip SSH):\n\n"
                "Tip: install sshpass for password auth:\n"
                "  sudo dnf install sshpass -y",
                show="*", parent=self)
            _pass_box[0] = pwd or ""
            evt.set()

        def run():
            name = dlabel(self.db.get(mac))

            # ── Step 1: Port scan ─────────────────────────────────────────────
            self.after(0, lambda: self._elog_l("scan", f"{ip}  scanning ports…","gray"))
            open_p = {}
            for port, svc in COMMON_PORTS.items():
                if tcp_check(ip, port, timeout=0.9):
                    open_p[port] = svc
            if open_p:
                svc_str = ", ".join(f"{p}/{s}" for p,s in sorted(open_p.items()))
                self.db.upsert(mac, services=svc_str)
                self.after(0, self._render)
                self.after(0, lambda s=svc_str: self._elog_l("connect",
                    f"{ip}  open: {s}","green"))

            # ── Step 2: Hostname ──────────────────────────────────────────────
            hname = hostname_of(ip)
            if hname:
                self.db.upsert(mac, hostname=hname)
                self.after(0, self._render)

            # ── Step 3: SSH detection ─────────────────────────────────────────
            ssh_open = (22 in open_p) or tcp_check(ip, 22, timeout=1.5)
            active_user = known_user   # start with whatever we know

            if not active_user:
                if not ssh_open:
                    self.after(0, lambda: self._elog_l("ssh",
                        f"{ip}  SSH port 22 not open — skipping SSH discovery","gray"))
                elif not shutil.which("ssh"):
                    self.after(0, lambda: self._elog_l("error",
                        "ssh command not found — install openssh-clients","red"))
                else:
                    # Phase 3a: parallel key auth (fast, ~4s)
                    self.after(0, lambda: self._elog_l("ssh",
                        f"{ip}  trying {len(SSH_USERS)} usernames with key auth…","gray"))
                    found = detect_ssh_user_keys(ip)
                    if found:
                        active_user = found
                        self.db.upsert(mac, ssh_user=found)
                        self.after(0, lambda u=found: [
                            self._elog_l("ssh", f"✓ Key auth: {u}@{ip}","green"),
                            Toast(self,"SSH Keys Work! 🔑",
                                  f"{name}: key login as {u}","🔑"),
                        ])
                    else:
                        # Phase 3b: key auth failed → ask for password
                        self.after(0, lambda: self._elog_l("ssh",
                            f"{ip}  no key auth — will ask for password","yellow"))

                        if not has_sshpass():
                            self.after(0, lambda: self._elog_l("warn",
                                "sshpass not installed — password auth disabled.\n  Install: sudo dnf install sshpass -y","yellow"))
                        else:
                            # Ask on main thread (tkinter requirement)
                            pwd_evt = threading.Event()
                            self.after(0, lambda: _ask_password_on_main(pwd_evt))
                            pwd_evt.wait(timeout=120)   # wait for user input

                            pwd = _pass_box[0]
                            if pwd:
                                self.after(0, lambda: self._elog_l("ssh",
                                    f"{ip}  trying {len(SSH_USERS)} usernames with password…","gray"))
                                found = detect_ssh_user_password(ip, pwd)
                                if found:
                                    active_user = found
                                    _ssh_passwords[ip] = pwd   # cache
                                    self.db.upsert(mac, ssh_user=found)
                                    self.after(0, lambda u=found: [
                                        self._elog_l("ssh",
                                            f"✓ Password auth: {u}@{ip}","green"),
                                        Toast(self,"SSH Connected! 🔑",
                                              f"{name}: logged in as {u}","🔑"),
                                    ])
                                else:
                                    self.after(0, lambda: self._elog_l("error",
                                        f"{ip}  wrong password or user — check credentials","red"))
                            else:
                                self.after(0, lambda: self._elog_l("ssh",
                                    f"{ip}  password skipped — SSH info unavailable","gray"))

            elif active_user:
                # Already have user — verify still works
                ok = ssh_check_key(ip, active_user, timeout=3)
                if not ok and has_sshpass() and _pass_box[0]:
                    ok = ssh_check_pass(ip, active_user, _pass_box[0], timeout=5)
                if not ok:
                    self.after(0, lambda u=active_user: self._elog_l("ssh",
                        f"{ip}  {u}: SSH no longer accessible (key/pass changed?)","yellow"))

            # ── Step 4: gather info via SSH ───────────────────────────────────
            def on_upd(info):
                kw = {k:v for k,v in info.items() if k not in ("open_ports",)}
                self.db.upsert(mac, **kw)
                self.after(0, self._render)
                self.after(0, lambda: self._upd_detail(self.db.get(mac)))

            if active_user:
                self.after(0, lambda u=active_user: self._elog_l("disc",
                    f"{ip}  gathering system info as {u}…","cyan"))
                auto_discover(ip, active_user, on_update=on_upd)

            # ── Step 5: finalise ──────────────────────────────────────────────
            alive = ping_host(ip, timeout=2)
            self.db.upsert(mac,
                status="online" if alive else "offline",
                last_discover=datetime.now().strftime("%Y-%m-%d %H:%M"))

            d = self.db.get(mac)
            ok_ssh = bool(d.get("ssh_user"))
            self.after(0, lambda: [
                self._render(),
                self._update_status(),
                play("scan_done") if ok_ssh else play("notify"),
                self._elog_l("disc",
                    f"✓ Discovery done: {dlabel(d)}"
                    f"  SSH={'✓ '+str(d.get('ssh_user')) if d.get('ssh_user') else '✗'}"
                    f"  AnyDesk={'✓ '+str(d.get('anydesk_id')) if d.get('anydesk_id') else '✗'}"
                    f"  OS={str(d.get('os','?'))[:30]}",
                    "green" if ok_ssh else "yellow"),
                Toast(self,"Discovery Done 🔭",
                    f"{dlabel(d)}\n"
                    f"SSH: {d.get('ssh_user') or '✗ no access'}  "
                    f"AnyDesk: {d.get('anydesk_id') or '—'}","🔭",7000),
            ])
        threading.Thread(target=run, daemon=True).start()

    def _disc_all(self):
        online=[self.db.get(m) for m in self.db.macs()
                if self.db.get(m).get("status")=="online"]
        if not online:
            messagebox.showinfo("Discover All","No online devices.\nScan the network first.",parent=self)
            return
        play("ding"); self._elog_l("disc",f"Auto-discovering {len(online)} online devices…","cyan")
        for i,dev in enumerate(online):
            self.after(i*400,lambda d=dev: self._do_disc(d))

    # ─── SSH INFO ─────────────────────────────────────────────────────────────
    def _do_sshinfo(self, dev):
        mac=dev.get("mac",""); ip=dev.get("ip",""); user=dev.get("ssh_user","")
        if not ip: messagebox.showerror("SSH Info","No IP.",parent=self); return
        if not user:
            user=simpledialog.askstring("SSH User","SSH username:",parent=self)
            if not user: return
            self.db.upsert(mac,ssh_user=user)
        tw=TermWin(self,title=f"System Info: {dlabel(dev)}  [{ip}]",icon="📊",w=600,h=480)
        tw.w(f"Connecting to {user}@{ip}…\n\n")
        def run():
            def _prog(key, val):
                tw.after(0,lambda k=key,v=val: [
                    tw.w(f"  {(k+':'):<18s}","head"),
                    tw.w(f"{v}\n","val"),
                ])
                # Save to DB
                self.db.upsert(mac,**{key:val})
                if key=="anydesk_id":
                    digits=re.sub(r"[^0-9]","",val)
                    if len(digits)>=6:
                        self.db.upsert(mac,anydesk_id=digits)
                        self.after(0,lambda d=digits: [self._render(),
                            self._elog_l("anydesk",f"AnyDesk ID saved: {d}","cyan")])
                self.after(0,self._render)
                self.after(0,lambda: self._upd_detail(self.db.get(mac)))
            # Ensure password is available for this session
            if not _ssh_passwords.get(ip) and not ssh_check_key(ip, user, timeout=3):
                # Need password — but we're in a thread, use stored or skip
                pass
            gather_info(ip, user, on_progress=_prog)
            tw.after(0,lambda: tw.w("\n── Complete ──\n"))
        threading.Thread(target=run,daemon=True).start()

    # ─── CRUD ─────────────────────────────────────────────────────────────────
    def _do_edit(self, dev): DevDlg(self,device=dict(dev),on_save=self._saved)
    def _add(self): DevDlg(self,device={},on_save=self._saved)
    def _saved(self, dev):
        mac=dev.get("mac",""); self.db.upsert(mac,**dev)
        self._sel_mac=mac; self._render(); self._update_status()
        play("notify"); self._elog_l("info",f"Saved: {dlabel(dev)}","white")
    def _do_remove(self, dev):
        if messagebox.askyesno("Remove",f"Remove '{dlabel(dev)}'?",parent=self):
            self.db.remove(dev.get("mac",""))
            if self._sel_mac==dev.get("mac",""): self._sel_mac=None; self._upd_detail(None)
            self._render(); self._update_status(); play("error")

    # ─── SCAN ─────────────────────────────────────────────────────────────────
    def _scan_start(self):
        if self._scanning: return
        self._scanning=True; self._sb.set("🔍 Scanning…")
        self._prog.config(value=0,mode="determinate"); self._prog.pack(fill="x")
        play("ding"); self._spin_anim()
        self._elog_l("scan",f"Scan started on {self._subnet_v.get()}","cyan")
        subnet=self._subnet_v.get().strip() or self._subnet
        self._scanner=Scanner(
            on_found=self._on_found,
            on_prog=lambda p: self.after(0,lambda: self._prog.config(value=int(p*100))),
            on_done=self._scan_done)
        threading.Thread(target=self._scanner.run,args=(subnet,),daemon=True).start()

    def _scan_stop(self):
        if self._scanner: self._scanner.stop()
        self._scanning=False; self._spin_lbl.config(text="")
        self._prog.stop()
        try: self._prog.pack_forget()
        except: pass
        self._sb.set("Scan stopped.")

    def _spin_anim(self):
        if not self._scanning: return
        self._spin_lbl.config(text=["◐","◓","◑","◒"][self._spin%4])
        self._spin+=1; self.after(150,self._spin_anim)

    def _on_found(self, ip, mac, hname, status):
        mac=mac_norm(mac) or mac; ex=self.db.get(mac)
        ls=datetime.now().strftime("%Y-%m-%d %H:%M") if status=="online" else ex.get("last_seen","")
        was=ex.get("status","offline")
        self.db.upsert(mac,ip=ip,hostname=hname,vendor=oui(mac),status=status,
                       name=ex.get("name","") or hname or "",last_seen=ls)
        if status=="online" and was!="online":
            self.after(0,lambda h=hname or ip: self._elog_l("online",f"Online: {h} ({ip})","green"))
            play("connect")
        self.after(0,self._render); self.after(0,self._update_status)

    def _scan_done(self):
        self.after(0,self._scan_stop)
        n=len(self.db.data)
        self.after(0,lambda: self._sb.set(f"Scan complete — {n} device(s)"))
        self.after(0,lambda: self._elog_l("scan",f"Scan complete — {n} devices","green"))
        self.after(0,lambda: play("scan_done"))

    def _refresh_all(self):
        self._sb.set("🔄 Refreshing…")
        def run():
            for mac in self.db.macs():
                d=self.db.get(mac); ip=d.get("ip","")
                if ip:
                    alive=ping_host(ip,timeout=1); st="online" if alive else "offline"
                    ls=datetime.now().strftime("%Y-%m-%d %H:%M") if alive else d.get("last_seen","")
                    was=d.get("status","offline"); self.db.upsert(mac,status=st,last_seen=ls)
                    if st!=was:
                        kind="online" if alive else "offline"
                        self.after(0,lambda m=mac,k=kind: [
                            self._elog_l(k,f"{dlabel(self.db.get(m))} is {k.upper()}",
                                        "green" if k=="online" else "yellow"),
                            play("online" if k=="online" else "offline")])
            self.after(0,self._render); self.after(0,self._update_status)
            self.after(0,lambda: self._sb.set("Refresh complete."))
        threading.Thread(target=run,daemon=True).start()

    # ─── NETWORK MSG RECEIVE ──────────────────────────────────────────────────
    def _on_pkt(self, pkt):
        cmd=pkt.get("cmd",""); frm=pkt.get("from_name","?"); fip=pkt.get("_addr",""); data=pkt.get("data","")
        if cmd=="message":
            play("msg_in")
            self.after(0,lambda: Toast(self,f"Message from {frm}",data,"💬",8000))
            self.after(0,lambda: self._elog_l("msg",f"Received from {frm} ({fip}): {data}","cyan"))
            self.after(0,lambda: self._route_msg(fip,frm,data))
        elif cmd=="sound":
            play("sound_ping")
            self.after(0,lambda: Toast(self,f"Sound Ping from {frm}","🔔","🔔",3000))
            self.after(0,lambda: self._elog_l("sound",f"Sound ping from {frm} ({fip})","yellow"))

    def _route_msg(self, fip, frm, text):
        if fip in ChatWin._wins and ChatWin._wins[fip].winfo_exists():
            ChatWin._wins[fip].receive(frm,text)

    # ─── BROADCAST ────────────────────────────────────────────────────────────
    def _bc_msg(self):
        msg=simpledialog.askstring("Broadcast Message","Message for ALL online devices:",parent=self)
        if not msg: return
        cnt=0
        for mac in self.db.macs():
            d=self.db.get(mac)
            if d.get("status")=="online" and d.get("ip"):
                NetServer.send(d["ip"],{"cmd":"message","from_name":self._my_name,
                               "from_ip":self._my_ip,"data":msg})
                if d.get("ssh_user"):
                    ip=d["ip"]; u=d["ssh_user"]
                    threading.Thread(target=lambda i=ip,usr=u:
                        remote_message(i,usr,f"[{self._my_name}] Broadcast",msg,password=_ssh_passwords.get(i,"")),daemon=True).start()
                cnt+=1
        play("notify"); self._elog_l("msg",f"Broadcast to {cnt} devices: {msg}","cyan")
        messagebox.showinfo("Broadcast",f"Sent to {cnt} online device(s).",parent=self)

    def _bc_sound(self):
        cnt=0
        for mac in self.db.macs():
            d=self.db.get(mac)
            if d.get("status")=="online" and d.get("ip"):
                NetServer.send(d["ip"],{"cmd":"sound","from_name":self._my_name,"from_ip":self._my_ip})
                cnt+=1
        play("sound_ping"); self._elog_l("sound",f"Sound ping broadcast → {cnt} devices","yellow")

    # ─── NETWORK MAP ──────────────────────────────────────────────────────────
    def _netmap(self):
        tw=TermWin(self,title="Network Map",icon="🗺️",w=820,h=540)
        tw.add_btn("Refresh",lambda: self._draw_map(tw))
        self._draw_map(tw)

    def _draw_map(self, tw):
        tw._txt.config(state="normal"); tw._txt.delete("1.0","end"); tw._txt.config(state="disabled")
        tw.w(f"  {APP_NAME}  —  Network Map\n","head")
        tw.w(f"  Subnet: {self._subnet_v.get()}   My IP: {self._my_ip}   Broadcast: {self._my_bc}\n\n")
        tw.w("="*90+"\n\n")
        online  =[(m,self.db.get(m)) for m in self.db.macs() if self.db.get(m).get("status")=="online"]
        offline_ =[(m,self.db.get(m)) for m in self.db.macs() if self.db.get(m).get("status")!="online"]
        tw.w(f"🟢  ONLINE  ({len(online)} devices)\n\n","val")
        for _,d in sorted(online,key=lambda x:x[1].get("ip","")):
            ad  = f"  🖥️{d['anydesk_id']}" if d.get("anydesk_id") else ""
            ssh = f"  🔑{d['ssh_user']}"   if d.get("ssh_user")   else ""
            os_ = f"  [{d['os'][:20]}]"    if d.get("os")          else ""
            tw.w(f"  🟢  {d.get('ip','?'):17s}  {d.get('mac','?'):19s}  "
                 f"{(d.get('name') or d.get('hostname') or '?'):24s}{os_}{ad}{ssh}\n")
        tw.w(f"\n⚫  OFFLINE  ({len(offline_)} devices)\n\n")
        for _,d in sorted(offline_,key=lambda x:x[1].get("ip","")):
            tw.w(f"  ⚫  {d.get('ip','?'):17s}  {d.get('mac','?'):19s}  "
                 f"{(d.get('name') or d.get('hostname') or '?'):24s}  "
                 f"last: {d.get('last_seen','never')}\n")

    # ─── LIVE MONITOR ─────────────────────────────────────────────────────────
    def _live_monitor(self):
        win=tk.Toplevel(self); win.title("Live Monitor"); win.configure(bg=C["bg"])
        w,h=680,460; win.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        TitleBar(win,title="⬡  Live Network Monitor",icon="📡",h=28).pack(fill="x")
        cols=("icon","name","ip","status","last_seen","wol","anydesk","ssh","services")
        tree=ttk.Treeview(win,columns=cols,show="headings",style="XP.Treeview")
        cfg=[("",22,"center"),("Name",120,"w"),("IP",90,"w"),("Status",65,"center"),
             ("Last Seen",105,"w"),("WOL",30,"center"),("AnyDesk",80,"w"),("SSH",55,"center"),("Services",140,"w")]
        for col,(hd,w2,anc) in zip(cols,cfg):
            tree.heading(col,text=hd); tree.column(col,width=w2,anchor=anc)
        vsb=ttk.Scrollbar(win,orient="vertical",command=tree.yview)
        tree.configure(yscrollcommand=vsb.set); vsb.pack(side="right",fill="y")
        tree.pack(fill="both",expand=True)
        self._live_styles(tree)
        active=[True]
        def refresh():
            if not active[0]: return
            for iid in tree.get_children(): tree.delete(iid)
            for mac in self.db.macs():
                d=self.db.get(mac)
                st=d.get("status","offline")
                ss="🟢 Online" if st=="online" else ("🟡 Waking" if st=="waking" else "⚫ Offline")
                tree.insert("","end",values=(
                    d.get("icon","💻"),d.get("name") or d.get("hostname") or mac,
                    d.get("ip",""),ss,d.get("last_seen",""),
                    str(d.get("wol_count",0)),d.get("anydesk_id",""),
                    "✓" if d.get("ssh_user") else "—",d.get("services","")[:40],
                ))
            if active[0]: win.after(3000,refresh)
        refresh()
        bf=tk.Frame(win,bg=C["bg"]); bf.pack(fill="x",padx=8,pady=6)
        Btn(bf,text="Refresh Now",command=refresh).pack(side="left",padx=4)
        def _close():
            active[0]=False; win.destroy()
        win.protocol("WM_DELETE_WINDOW",_close)
        Btn(bf,text="Close",command=_close).pack(side="right",padx=4)

    def _live_styles(self, tree):
        s=ttk.Style()
        s.configure("XP.Treeview",background=C["card_a"],fieldbackground=C["card_a"],
                    foreground="black",font=F(9),rowheight=20)
        s.configure("XP.Treeview.Heading",background=C["bg2"],foreground="black",
                    font=F(9,True),relief="raised")
        s.map("XP.Treeview",background=[("selected",C["sel"])],foreground=[("selected","white")])
        tree.configure(style="XP.Treeview")

    # ─── IMPORT / EXPORT ──────────────────────────────────────────────────────
    def _import(self):
        from tkinter import filedialog
        p=filedialog.askopenfilename(filetypes=[("JSON","*.json"),("All","*.*")])
        if not p: return
        try:
            with open(p,encoding="utf-8") as f: data=json.load(f)
            for mac,dev in data.items(): self.db.upsert(mac,**dev)
            self._render(); self._update_status()
            messagebox.showinfo("Import",f"Imported {len(data)} devices.",parent=self)
        except Exception as e: messagebox.showerror("Import Error",str(e),parent=self)

    def _export(self):
        from tkinter import filedialog
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")])
        if not p: return
        try:
            with open(p,"w",encoding="utf-8") as f:
                json.dump(self.db.data,f,indent=2,ensure_ascii=False)
            messagebox.showinfo("Export",f"Exported {len(self.db.data)} devices.",parent=self)
        except Exception as e: messagebox.showerror("Export Error",str(e),parent=self)

    def _export_csv(self):
        from tkinter import filedialog
        p=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")])
        if not p: return
        try:
            import csv
            fields=["name","ip","mac","vendor","hostname","os","group","status",
                    "last_seen","wol_count","anydesk_id","ssh_user","services",
                    "ram","cpu","disk","uptime","notes"]
            with open(p,"w",newline="",encoding="utf-8") as f:
                wr=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
                wr.writeheader()
                for mac in self.db.macs(): wr.writerow(self.db.get(mac))
            messagebox.showinfo("Export CSV",f"Exported {len(self.db.data)} devices.",parent=self)
        except Exception as e: messagebox.showerror("Export Error",str(e),parent=self)

    # ─── STATUS / CLOCK ───────────────────────────────────────────────────────
    def _update_status(self):
        total=len(self.db.data)
        on=sum(1 for d in self.db.data.values() if d.get("status")=="online")
        self._sb_cnt.set(f"  {total} dev")
        self._sb_net.set(f"  🟢{on}  {self._my_ip}")
        self._sb_os.set(f"  {_OS} {platform.release()[:8]}")

    def _clock(self):
        self._sb_t.set(datetime.now().strftime(" %H:%M:%S"))
        self.after(1000,self._clock)

    def _fetch_my_ad(self):
        def run():
            ad=get_local_anydesk()
            if ad:
                self.after(0,lambda: self._ad_lbl.config(text=f"  🎮 My AnyDesk: {ad}  "))
                self.after(0,lambda: self._elog_l("anydesk",f"Local AnyDesk ID: {ad}","cyan"))
        threading.Thread(target=run,daemon=True).start()

    # ─── STATS ────────────────────────────────────────────────────────────────
    def _stats(self):
        devs=list(self.db.data.values()); total=len(devs)
        on=sum(1 for d in devs if d.get("status")=="online")
        wols=sum(d.get("wol_count",0) for d in devs)
        ssh_n=sum(1 for d in devs if d.get("ssh_user"))
        ad_n =sum(1 for d in devs if d.get("anydesk_id"))
        vendors={}
        for d in devs: v=d.get("vendor","?") or "?"; vendors[v]=vendors.get(v,0)+1
        win=tk.Toplevel(self); win.title("Statistics"); win.configure(bg=C["bg"])
        win.resizable(False,False)
        w2,h2=500,560; win.geometry(f"{w2}x{h2}+{(self.winfo_screenwidth()-w2)//2}+{(self.winfo_screenheight()-h2)//2}")
        TitleBar(win,title="Network Statistics",icon="📊",h=28).pack(fill="x")
        f=tk.Frame(win,bg=C["bg"]); f.pack(fill="both",expand=True,padx=16,pady=12)
        rows=[
            ("🌐 Subnet",           self._subnet_v.get()),
            ("💻 My IP",            self._my_ip),
            ("📡 Broadcast",        self._my_bc),
            ("🏷️ My Hostname",       self._my_name),
            ("📦 Total Devices",    total),
            ("🟢 Online",           on), ("⚫ Offline", total-on),
            ("⚡ WOL Sent",         wols),
            ("🔑 SSH Auto-Detected",ssh_n),
            ("🎮 AnyDesk Known",    ad_n),
            ("── Tools ──",""),
            ("ip neigh",            "✓" if (IS_LIN and shutil.which("ip")) else "✗"),
            ("nmap",                "✓" if shutil.which("nmap") else "✗ sudo dnf install nmap -y"),
            ("SSH",                 "✓" if shutil.which("ssh")  else "✗"),
            ("AnyDesk",             "✓" if shutil.which("anydesk") else "✗"),
            ("xfreerdp",            "✓" if shutil.which("xfreerdp") else "✗ sudo dnf install freerdp -y"),
            ("UDP server",          f"✓ port {MSG_PORT}" if self._srv_ok else "✗ failed"),
            ("── Audio ──",""),
            ("aplay",               "✓" if shutil.which("aplay")  else "✗"),
            ("paplay",              "✓" if shutil.which("paplay") else "—"),
            ("Database",            str(DB_FILE)),
        ]
        for i,(lbl,val) in enumerate(rows):
            if str(lbl).startswith("──"):
                tk.Label(f,text=lbl,bg=C["bg"],font=F(8,True),fg=C["gray"],anchor="w"
                         ).grid(row=i,column=0,columnspan=2,sticky="w",pady=(8,2)); continue
            tk.Label(f,text=lbl+":",bg=C["bg"],font=F(9,True),anchor="w",width=22
                     ).grid(row=i,column=0,sticky="w",pady=2)
            col=(C["on"] if str(val).startswith("✓") else
                 C["shut"] if str(val).startswith("✗") else C["ta"])
            tk.Label(f,text=str(val),bg=C["bg"],font=F(9),fg=col,anchor="w"
                     ).grid(row=i,column=1,sticky="w",padx=8,pady=2)
        if vendors:
            r=len(rows)
            tk.Label(f,text="Vendors:",bg=C["bg"],font=F(9,True),anchor="w"
                     ).grid(row=r,column=0,sticky="w",pady=(10,2))
            top=" · ".join(f"{v}({c})" for v,c in sorted(vendors.items(),key=lambda x:-x[1])[:6])
            tk.Label(f,text=top,bg=C["bg"],font=F(8),fg=C["gray"],anchor="w"
                     ).grid(row=r,column=1,sticky="w",padx=8,pady=(10,2))
        Btn(win,text="Close",command=win.destroy).pack(pady=10)

    def _sysinfo(self):
        win=tk.Toplevel(self); win.title("System Info"); win.configure(bg=C["bg"])
        win.resizable(False,False)
        w2,h2=540,600; win.geometry(f"{w2}x{h2}+{(self.winfo_screenwidth()-w2)//2}+{(self.winfo_screenheight()-h2)//2}")
        TitleBar(win,title="System Information",icon="🔧",h=28).pack(fill="x")
        f=tk.Frame(win,bg=C["bg"]); f.pack(fill="both",expand=True,padx=16,pady=12)
        rows=[
            ("── System ──",""),
            ("OS",            f"{_OS} {platform.release()}"),
            ("Python",        sys.version.split()[0]),
            ("Architecture",  platform.machine()),
            ("Hostname",      socket.gethostname()),
            ("My IP",         self._my_ip), ("Broadcast", self._my_bc),
            ("── SSH Discovery ──",""),
            ("SSH binary",    "✓ "+str(shutil.which("ssh")) if shutil.which("ssh") else "✗ not found"),
            ("Tries usernames", " · ".join(SSH_USERS[:8])+"…"),
            ("Auth method",   ("Key + Password (sshpass)" if has_sshpass() else "Key only (install sshpass for password auth)")),
            ("sshpass",       "✓ " + str(shutil.which("sshpass")) if has_sshpass() else "✗  sudo dnf install sshpass -y"),
            ("── Scan ──",""),
            ("ip neigh",      "✓" if (IS_LIN and shutil.which("ip")) else "✗"),
            ("nmap",          "✓" if shutil.which("nmap")  else "✗  sudo dnf install nmap -y"),
            ("arp",           "✓" if shutil.which("arp")   else "✗  sudo dnf install net-tools -y"),
            ("── Remote ──",""),
            ("AnyDesk",       "✓ "+str(shutil.which("anydesk")) if shutil.which("anydesk") else "✗"),
            ("My AnyDesk",    get_local_anydesk() or "(not found)"),
            ("xfreerdp",      "✓" if shutil.which("xfreerdp") else "✗  sudo dnf install freerdp -y"),
            ("── Messaging ──",""),
            ("notify-send",   "✓" if shutil.which("notify-send") else "✗ (messages use wall+zenity)"),
            ("zenity",        "✓" if shutil.which("zenity") else "—"),
            ("xmessage",      "✓" if shutil.which("xmessage") else "—"),
            ("UDP server",    f"✓ port {MSG_PORT}" if self._srv_ok else "✗ failed"),
            ("── Audio ──",""),
            ("aplay",         "✓" if shutil.which("aplay")  else "✗"),
            ("paplay",        "✓" if shutil.which("paplay") else "—"),
            ("Database",      str(DB_FILE)),
        ]
        for i,(lbl,val) in enumerate(rows):
            if str(lbl).startswith("──"):
                tk.Label(f,text=lbl,bg=C["bg"],font=F(8,True),fg=C["gray"],anchor="w"
                         ).grid(row=i,column=0,columnspan=2,sticky="w",pady=(8,2)); continue
            tk.Label(f,text=lbl+":",bg=C["bg"],font=F(9,True),anchor="w",width=18
                     ).grid(row=i,column=0,sticky="w",pady=2)
            col=(C["on"] if str(val).startswith("✓") else
                 C["shut"] if str(val).startswith("✗") else C["ta"])
            tk.Label(f,text=str(val),bg=C["bg"],font=F(9),fg=col,anchor="w"
                     ).grid(row=i,column=1,sticky="w",padx=8,pady=2)
        Btn(win,text="Close",command=win.destroy).pack(pady=10)

    def _about(self):
        win=tk.Toplevel(self); win.title("About"); win.configure(bg=C["bg"])
        win.resizable(False,False); win.grab_set()
        TitleBar(win,title=f"About  {APP_NAME}",icon="⬡",h=28).pack(fill="x")
        tk.Label(win,text="⬡",font=F(52),bg=C["bg"],fg=C["sel"]).pack(pady=10)
        tk.Label(win,text=APP_NAME,font=F(16,True),bg=C["bg"],fg=C["ta"]).pack()
        tk.Label(win,text=f"{APP_VER}  ·  The Ultimate LAN Management Tool  ·  Cross-Platform",
                 font=F(9),bg=C["bg"],fg=C["gray"]).pack()
        tk.Frame(win,bg=C["sep"],height=1,width=420).pack(pady=12)
        tk.Label(win,justify="center",font=F(9),bg=C["bg"],text=(
            "🔭 Auto-discovers SSH users, OS, CPU, RAM, disk, AnyDesk IDs\n"
            "⚡ Wake-on-LAN with directed broadcast\n"
            "🔴 Remote Shutdown & Reboot (multi-fallback: systemctl/sudo/shutdown)\n"
            "💬 Messages appear on remote screen (notify-send / zenity / wall)\n"
            "🔔 Sound pings via SSH + UDP\n"
            "🖥️ AnyDesk auto-discovery · 💻 RDP · 🔑 SSH Terminal\n"
            "🔍 Port Scanner · 📋 Ping · 🗺️ Network Map · 📡 Live Monitor\n"
            "🔊 22 authentic Windows XP synthesised sounds\n\n"
            f"Platform:  {_OS} {platform.release()}\n"
            f"Database:  {DB_FILE}\n"
            f"UDP Port:  {MSG_PORT}"
        )).pack(padx=24)
        Btn(win,kind="g",text="  OK  ",command=win.destroy).pack(pady=14)

    def _quit(self):
        self._server.stop()
        if self._scanner: self._scanner.stop()
        self.db.save(); self.destroy()

# ─────────────────────────────────────────────────────────────────────────────
#  LINUX DESKTOP ENTRY
# ─────────────────────────────────────────────────────────────────────────────
def desktop_entry():
    script=Path(__file__).resolve()
    entry=f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
GenericName=LAN Management Tool
Comment=SSH Auto-Discovery · Wake · Shutdown · AnyDesk · Messages
Exec=python3 {script}
Icon=network-workgroup
Terminal=false
Categories=Network;System;
Keywords=wol;wake;lan;anydesk;rdp;ssh;shutdown;network;nexus;
"""
    for p in [Path.home()/"Desktop"/"NEXUS_LAN_Commander.desktop",
               Path.home()/".local"/"share"/"applications"/"nexus-lancommander.desktop"]:
        try:
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(entry,encoding="utf-8"); p.chmod(0o755)
        except: pass
    d=Path.home()/"Desktop"/"NEXUS_LAN_Commander.desktop"
    if d.exists() and shutil.which("gio"):
        try: subprocess.run(["gio","set",str(d),"metadata::trusted","true"],capture_output=True)
        except: pass

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if IS_LIN:
        try: desktop_entry()
        except: pass
    App().mainloop()
