# VoIP Probe — Latency, Jitter & MOS Testing Tool

This tool actively evaluates VoIP quality across networks by measuring:

✅ Round-trip latency (RTT)  
✅ Estimated one-way delay (OWD ≈ RTT / 2 — no clock sync required)  
✅ RFC 3550 network jitter  
✅ Packet loss (sliding-window measurement)  
✅ ITU-T E-model MOS estimation  
 • Supports: `g711`, `g729`, `opus`

🎯 Purpose:  
Validate VoIP readiness, troubleshoot call quality issues, and benchmark WAN / VPN / SD-WAN performance.

---

## 🧠 How It Works

Active UDP probes between two endpoints:

| Role | Command Mode | Where to run |
|------|--------------|--------------|
| **Server** | `server` | Central site / SBC / router / Raspberry Pi |
| **Client** | `client` | Branch / remote user / VPN endpoint |

Server simply echoes packets.  
Client calculates all QoS metrics.

---

## 🚀 Run Instructions — Steps 1 & 2

### ✅ Step 1️⃣ — Start the Server (Central / Core Site)

Run this anywhere near VoIP infrastructure:

```bash
python voip_probe.py server --port 5005
or
python voip_probe.py server --bind 0.0.0.0 --port 5005

```

### `✅ Step 2️⃣ — Start the Client (Remote / Branch / VPN Site)`
```bash
python voip_probe.py client \
  --host <server-ip> \
  --port 5005 \
  --pps 50 \
  --codec g711 \
  --duration 60 \
  --csv results.csv
or
python voip_probe.py client --host 192.168.50.1 --codec g729 --duration 120
