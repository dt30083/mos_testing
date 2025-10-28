#!/usr/bin/env python3
"""
voip_probe.py
Active UDP probe for latency/jitter/loss with VoIP MOS estimation using the ITU-T E-model.
- Server: echoes back incoming timestamps (stateless).
- Client: sends timestamped probes, computes RTT, jitter (RFC 3550),
  sliding-window packet loss, and MOS estimation.
CSV export supported for time-series analysis.

Usage examples:
  Server:
    python voip_probe.py server --port 5005
  Client:
    python voip_probe.py client --host 1.2.3.4 --port 5005 --pps 50 --codec g711 --duration 60 --csv results.csv
"""

import argparse
import csv
import socket
import struct
import sys
import time
from datetime import datetime, timezone
from collections import deque

PKT_STRUCT = struct.Struct("!I Q I")  # seq, timestamp_ns, magic
MAGIC = 0xABCD1357

CODEC_PARAMS = {
    "g711": (0.0, 25.0),  # (Ie, Bpl)
    "g729": (11.0, 19.0),
    "opus": (5.0, 14.0),
}

def now_ns():
    return time.time_ns()

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def hstep(x):
    return 1.0 if x > 0 else 0.0

def emodel_mos(delay_ms, loss_percent, codec="g711", burstR=1.0):
    Ie, Bpl = CODEC_PARAMS.get(codec.lower(), CODEC_PARAMS["g711"])
    d = max(0.0, float(delay_ms))
    Ppl = max(0.0, float(loss_percent))

    Id = 0.024*d + 0.11*(d - 177.3)*hstep(d - 177.3)

    if Ppl > 0:
        Ie_eff = Ie + (95.0 - Ie) * Ppl / (Ppl/Bpl + burstR)
    else:
        Ie_eff = Ie

    R = 94.2 - Id - Ie_eff

    if R <= 0:
        mos = 1.0
    elif R >= 100:
        mos = 4.5
    else:
        mos = 1 + 0.035*R + (R*(R-60)*(100-R))*7e-6
        mos = max(1.0, min(4.5, mos))

    return mos, R, Id, Ie_eff

def rfc3550_jitter_update(J_prev, diff_ms):
    return J_prev + (abs(diff_ms) - J_prev) / 16.0

def run_server(bind, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind, port))
    print(f"[server] listening on {bind}:{port}")
    try:
        while True:
            data, addr = sock.recvfrom(2048)
            sock.sendto(data, addr)
    except KeyboardInterrupt:
        pass
    finally:
        print("[server] shutting down")
        sock.close()

def run_client(host, port, pps, duration, csv_path, codec, burstR, warmup, report_every, timeout_ms):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout_ms/1000)
    interval_s = 1.0 / float(pps)

    sent_times = {}
    received = set()
    rtt_samples = []
    oneway_samples = []
    window = deque(maxlen=max(pps*10, 100))
    last_transit_ms = None
    J_ms = 0.0

    total_sent = total_recv = 0
    seq = 0

    csv_writer = None
    csv_file = None
    if csv_path:
        csv_file = open(csv_path, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            "ts_utc","seq","rtt_ms","oneway_ms_est","jitter_ms",
            "loss_pct_window","mos","r_factor","Id","Ie_eff"
        ])

    print(f"[client] sending to {host}:{port} @ {pps} pps (codec={codec})")
    if duration:
        print(f"[client] duration: {duration}s")

    start = time.time()
    next_send = time.time()
    next_report = time.time() + report_every
    server_addr = (host, port)

    try:
        while True:
            now = time.time()

            if duration and (now - start) >= duration:
                break

            if now >= next_send:
                send_ns = now_ns()
                packet = PKT_STRUCT.pack(seq, send_ns, MAGIC)
                try:
                    sock.sendto(packet, server_addr)
                    sent_times[seq] = send_ns
                    window.append(seq)
                    total_sent += 1
                except Exception as err:
                    print("send error:", err)
                seq = (seq + 1) & 0xffffffff
                next_send += interval_s

            try:
                data, _ = sock.recvfrom(2048)
                recv_ns = now_ns()
                if len(data) >= PKT_STRUCT.size:
                    r_seq, s_ns, magic = PKT_STRUCT.unpack(data[:PKT_STRUCT.size])
                    if magic != MAGIC:
                        continue
                    if r_seq in received:
                        continue
                    received.add(r_seq)
                    if r_seq in sent_times:
                        rtt_ms = (recv_ns - sent_times[r_seq]) / 1e6
                        oneway_ms = rtt_ms / 2.0
                        rtt_samples.append(rtt_ms)
                        oneway_samples.append(oneway_ms)
                        total_recv += 1

                        transit_ms = (recv_ns - s_ns) / 1e6
                        if last_transit_ms is not None:
                            J_ms = rfc3550_jitter_update(J_ms, transit_ms - last_transit_ms)
                        last_transit_ms = transit_ms

                        win = list(window)
                        recv_win = sum(1 for w in win if w in received)
                        loss_pct = 100*(len(win)-recv_win)/len(win) if win else 0.0

                        elapsed = time.time() - start
                        if elapsed > warmup and len(oneway_samples) > 2:
                            avg_oneway = sum(oneway_samples[-pps:]) / max(1, min(len(oneway_samples),pps))
                            mos,R,Id,Ie_eff = emodel_mos(avg_oneway, loss_pct, codec, burstR)
                        else:
                            mos = R = Id = Ie_eff = None

                        if csv_writer:
                            csv_writer.writerow([
                                iso_now(), r_seq,
                                round(rtt_ms,3), round(oneway_ms,3),
                                round(J_ms,3), round(loss_pct,3),
                                round(mos,3) if mos else "",
                                round(R,1) if R else "",
                                round(Id,3) if Id else "",
                                round(Ie_eff,3) if Ie_eff else ""
                            ])

            except socket.timeout:
                pass

            if now >= next_report:
                elapsed = max(1e-9, now-start)
                avg_rtt = sum(rtt_samples)/len(rtt_samples) if rtt_samples else 0.0
                avg_oneway = sum(oneway_samples)/len(oneway_samples) if oneway_samples else 0.0
                loss_total = 100*(total_sent-total_recv)/total_sent if total_sent else 0.0
                win = list(window)
                recv_win = sum(1 for w in win if w in received)
                loss_win = 100*(len(win)-recv_win)/len(win) if win else 0.0

                mos,R,Id,Ie_eff = emodel_mos(avg_oneway, loss_win, codec, burstR)
                print(
                    f"[stats] sent={total_sent} recv={total_recv} "
                    f"loss_total={loss_total:.2f}% loss_win={loss_win:.2f}% "
                    f"RTT_avg={avg_rtt:.2f}ms OWD_avg~={avg_oneway:.2f}ms "
                    f"jitter={J_ms:.2f}ms MOS≈{mos:.2f}"
                )
                next_report += report_every

            time.sleep(0.0003)

    except KeyboardInterrupt:
        print("\n[client] interrupted")

    finally:
        if csv_file:
            csv_file.close()
        sock.close()
        print("[client] stopped")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    sp = sub.add_parser("server")
    sp.add_argument("--bind", default="0.0.0.0")
    sp.add_argument("--port", type=int, default=5005)

    cp = sub.add_parser("client")
    cp.add_argument("--host", required=True)
    cp.add_argument("--port", type=int, default=5005)
    cp.add_argument("--pps", type=int, default=50)
    cp.add_argument("--duration", type=int, default=0)
    cp.add_argument("--csv", default=None)
    cp.add_argument("--codec", default="g711", choices=list(CODEC_PARAMS.keys()))
    cp.add_argument("--burstR", type=float, default=1.0)
    cp.add_argument("--warmup", type=int, default=3)
    cp.add_argument("--report-every", type=int, default=5)
    cp.add_argument("--timeout-ms", type=int, default=200)

    args = parser.parse_args()

    if args.mode == "server":
        run_server(args.bind, args.port)
    else:
        run_client(
            args.host, args.port, args.pps,
            args.duration if args.duration>0 else None,
            args.csv, args.codec,
            args.burstR, args.warmup,
            args.report_every, args.timeout_ms
        )

if __name__ == "__main__":
    main()