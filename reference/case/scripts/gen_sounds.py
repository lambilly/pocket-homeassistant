#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 MAX98357A 内置提示音（WAV，48kHz / mono / 16bit）

ESPHome 的 media_player speaker 平台要求内置文件：
  "Encode on-device files with the configured sample rate, 1 or 2 channels,
   and 16 bits per sample."
所以这里一律 48000Hz / 单声道 / 16bit PCM。

用法：python case/scripts/gen_sounds.py
输出：sounds/*.wav（相对工程根目录，与 yaml 里 file: 路径对应）
"""
from __future__ import annotations

import math
import os
import struct
import wave

SAMPLE_RATE = 48000
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sounds")


def tone(freq: float, dur: float, amp: float = 0.45, decay: float = 6.0) -> list[float]:
    """单个音：正弦 + 指数衰减包络 + 首尾 8ms 淡入淡出（防爆音）。"""
    n = int(SAMPLE_RATE * dur)
    fade = int(SAMPLE_RATE * 0.008)
    out: list[float] = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.exp(-decay * t / dur)
        if i < fade:
            env *= i / fade
        elif i > n - fade:
            env *= (n - i) / fade
        out.append(amp * env * math.sin(2 * math.pi * freq * t))
    return out


def silence(dur: float) -> list[float]:
    return [0.0] * int(SAMPLE_RATE * dur)


def write_wav(name: str, samples: list[float]) -> None:
    path = os.path.join(OUT_DIR, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for s in samples:
            v = max(-1.0, min(1.0, s))
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(bytes(frames))
    size = os.path.getsize(path)
    print(f"  {name:14} {len(samples) / SAMPLE_RATE:5.2f}s  {size / 1024:6.1f}KB")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"输出目录：{os.path.abspath(OUT_DIR)}")

    # 1) ding：轻提示（两声上行，像门铃）
    ding = tone(1046.5, 0.11) + tone(1318.5, 0.16, decay=8.0)
    write_wav("ding.wav", ding)

    # 2) notify：新消息（三声快速上行）
    notify = tone(1318.5, 0.08) + tone(1568.0, 0.08) + tone(2093.0, 0.14, decay=7.0)
    write_wav("notify.wav", notify)

    # 3) alarm：告警（高低交替三次，急促）
    alarm: list[float] = []
    for _ in range(3):
        alarm += tone(880.0, 0.09, amp=0.5, decay=3.0) + silence(0.03)
        alarm += tone(440.0, 0.09, amp=0.5, decay=3.0) + silence(0.03)
    write_wav("alarm.wav", alarm)

    total = sum(os.path.getsize(os.path.join(OUT_DIR, f))
                for f in os.listdir(OUT_DIR) if f.endswith(".wav"))
    print(f"合计 {total / 1024:.1f}KB（全部嵌入固件 flash）")


if __name__ == "__main__":
    main()
