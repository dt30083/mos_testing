# VoIP Probe — Network Quality Testing for Voice Communications

Active UDP probe tool for measuring VoIP network quality with real-time MOS estimation.

## Features

✅ **Round-trip latency (RTT)** - End-to-end delay measurement  
✅ **One-way delay estimation** - OWD ≈ RTT/2 (no clock sync required)  
✅ **RFC 3550 jitter calculation** - Industry-standard jitter measurement  
✅ **Packet loss tracking** - Sliding window loss detection  
✅ **ITU-T E-model MOS scoring** - Voice quality estimation (1.0-4.5 scale)  
✅ **Multiple codec support** - G.711, G.729, Opus profiles  
✅ **CSV export** - Time-series data for analysis  

## Requirements

- Python 3.6+
- No external dependencies (uses standard library only)
- UDP port access between test endpoints

## Quick Start

### 1. Start Server (Destination/Core Site)
```bash
python voip_probe.py server --port 5005
```

### 2. Run Client Test (Source/Branch Site)
```bash
python voip_probe.py client --host 192.168.1.100 --duration 60 --csv results.csv
```

## Understanding Results

### MOS Score Interpretation
| MOS Range | Quality | Description |
|-----------|---------|-------------|
| 4.3 - 4.5 | Excellent | Toll quality, no impairment |
| 4.0 - 4.3 | Good | Slight impairment, acceptable |
| 3.6 - 4.0 | Fair | Some impairment, still acceptable |
| 3.1 - 3.6 | Poor | Significant impairment |
| 1.0 - 3.1 | Bad | Severe impairment, unusable |

### Typical Thresholds for VoIP
- **Latency**: < 150ms (< 100ms preferred)
- **Jitter**: < 30ms (< 20ms preferred)  
- **Packet Loss**: < 1% (< 0.1% preferred)
- **MOS**: > 4.0 for good quality

## Complete Usage Guide

### Server Options
```bash
python voip_probe.py server [options]

Options:
  --bind IP        Bind to specific IP (default: 0.0.0.0)
  --port PORT      Listen port (default: 5005)
```

### Client Options
```bash
python voip_probe.py client --host HOST [options]

Required:
  --host HOST      Server IP address

Optional:
  --port PORT      Server port (default: 5005)
  --pps RATE       Packets per second (default: 50)
  --duration SEC   Test duration in seconds (default: unlimited)
  --codec CODEC    Codec profile: g711, g729, opus (default: g711)
  --csv FILE       Export results to CSV file
  --burstR FLOAT   Burst ratio for loss calculation (default: 1.0)
  --warmup SEC     Warmup period before MOS calculation (default: 3)
  --report-every SEC  Status report interval (default: 5)
  --timeout-ms MS  Socket timeout in milliseconds (default: 200)
```

## Testing Scenarios

### Basic Network Test
```bash
# 30-second test with default settings
python voip_probe.py client --host 10.1.1.1 --duration 30
```

### High-Rate Stress Test  
```bash
# 100 pps for 2 minutes with G.729 profile
python voip_probe.py client --host 10.1.1.1 --pps 100 --codec g729 --duration 120
```

### Long-Term Monitoring
```bash
# Continuous monitoring with CSV logging
python voip_probe.py client --host 10.1.1.1 --csv voip_quality.csv
```

### WAN/VPN Testing
```bash
# Lower rate for WAN links with Opus codec
python voip_probe.py client --host vpn.company.com --pps 20 --codec opus --duration 300
```

## Sample Output

### Console Output
```
[client] sending to 192.168.1.100:5005 @ 50 pps (codec=g711)
[stats] sent=250 recv=248 loss_total=0.80% loss_win=1.20% RTT_avg=45.23ms OWD_avg~=22.61ms jitter=3.45ms MOS≈4.12
```

### CSV Output Format
```csv
ts_utc,seq,rtt_ms,oneway_ms_est,jitter_ms,loss_pct_window,mos,r_factor,Id,Ie_eff
2024-10-28T15:30:45.123Z,1001,42.5,21.25,2.1,0.5,4.15,85.2,1.2,0.0
```

## Codec Profiles

| Codec | Typical Use | Bandwidth | Quality |
|-------|-------------|-----------|---------|
| **g711** | PSTN, high-quality | 64 kbps | Highest |
| **g729** | WAN, bandwidth-limited | 8 kbps | Good |
| **opus** | Modern VoIP, adaptive | 6-510 kbps | Excellent |

## Network Requirements

### Firewall Rules
- **Outbound**: UDP to destination port (default 5005)
- **Server**: UDP inbound on listening port

### Bandwidth Usage
- 50 pps ≈ 2.4 kbps overhead (24 bytes per packet)
- 100 pps ≈ 4.8 kbps overhead

## Troubleshooting

### Common Issues

**"Connection timeout" errors**
- Check firewall rules on both ends
- Verify server is running and reachable
- Test with `ping` or `telnet` first

**High jitter readings**
- Network congestion or QoS issues
- Try lower packet rates (--pps 20)
- Check for competing traffic

**Inconsistent MOS scores**
- Increase warmup period (--warmup 10)
- Run longer tests (--duration 300)
- Check network stability

**No packets received**
- Verify server IP address
- Check NAT/firewall configuration
- Ensure UDP port is not blocked

### Performance Tips

- Use 50 pps for typical VoIP simulation
- Run tests for at least 60 seconds for stable results
- Test during peak and off-peak hours
- Compare results across different network paths

## Advanced Usage

### Automated Testing Script
```bash
#!/bin/bash
# Test multiple destinations
for host in 10.1.1.1 10.2.1.1 10.3.1.1; do
    echo "Testing $host..."
    python voip_probe.py client --host $host --duration 60 --csv "results_${host}.csv"
done
```

### Docker Deployment

**Quick Start:**
```bash
# Start server only
docker-compose up server

# Full testing setup (server + client)
docker-compose --profile testing up
```

**External client testing:**
```bash
docker run --rm \
  -e VOIP_HOST=192.168.1.100 \
  -e VOIP_DURATION=60 \
  -v $(pwd)/results:/app/results \
  voip-probe-client --csv /app/results/test.csv
```

See `docker-README.md` for complete Docker deployment guide.

## How It Works

The tool uses active UDP probes between two endpoints:

| Role | Function | Deployment |
|------|----------|------------|
| **Server** | Echoes packets back | Central site / core network |
| **Client** | Sends probes, calculates metrics | Branch / remote / test location |

The client sends timestamped UDP packets at a configurable rate. The server simply echoes them back. The client then calculates:

- **RTT**: Time difference between send and receive
- **Jitter**: RFC 3550 smoothed variance in packet timing
- **Loss**: Percentage of packets not returned within timeout
- **MOS**: ITU-T E-model estimation based on delay, loss, and codec

This approach simulates real VoIP traffic patterns while providing comprehensive quality metrics for network assessment.