#!/usr/bin/env python3
"""Generalized live sanitizer for terminal session logs.

This parser is designed for noisy interactive shells (oh-my-zsh, powerlevel,
terminfo redraws, bracketed paste, cursor movement). It aims to produce clean,
readable, timestamped plain-text logs.
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
import time
from typing import Iterable


PROMPT_ONLY_RE = [
    re.compile(r"^[\s\W]*[#$%❯➜›»]\s*$"),
    re.compile(r"^[\w.-]+@[\w.-]+[: ].*[#$%]\s*$"),
]

BOX_CHARS = set("╭╮╰╯─│┌┐└┘├┤┬┴┼")
PROMPT_MARKERS = (" on ", "Py base", " at ")


class ANSIStreamStripper:
    NORMAL = 0
    ESC = 1
    CSI = 2
    OSC = 3
    DCS = 4
    ST_ESC = 5

    def __init__(self) -> None:
        self.state = self.NORMAL

    def feed(self, data: bytes) -> str:
        out = bytearray()
        i = 0
        n = len(data)
        while i < n:
            b = data[i]

            if self.state == self.NORMAL:
                if b == 0x1B:
                    self.state = self.ESC
                elif 0x80 <= b <= 0x9F:
                    pass
                elif b in (0x00, 0x07, 0x0B, 0x0C):
                    pass
                else:
                    out.append(b)
                i += 1
                continue

            if self.state == self.ESC:
                if b == ord("["):
                    self.state = self.CSI
                elif b == ord("]"):
                    self.state = self.OSC
                elif b in (ord("P"), ord("_"), ord("^"), ord("X")):
                    self.state = self.DCS
                else:
                    self.state = self.NORMAL
                i += 1
                continue

            if self.state == self.CSI:
                if 0x40 <= b <= 0x7E:
                    self.state = self.NORMAL
                i += 1
                continue

            if self.state in (self.OSC, self.DCS):
                if b == 0x07:
                    self.state = self.NORMAL
                    i += 1
                    continue
                if b == 0x1B:
                    self.state = self.ST_ESC
                    i += 1
                    continue
                i += 1
                continue

            if self.state == self.ST_ESC:
                if b == ord("\\"):
                    self.state = self.NORMAL
                else:
                    self.state = self.OSC
                i += 1
                continue

        text = out.decode("utf-8", errors="ignore")
        # caret-encoded escapes sometimes appear in recorded streams
        text = re.sub(r"\^\[[0-?]*[ -/]*[@-~]", "", text)
        text = text.replace("^M", "")
        return text


class LineReconstructor:
    def __init__(self) -> None:
        self.buf: list[str] = []
        self.cursor = 0

    def _line(self) -> str:
        return "".join(self.buf)

    def feed(self, text: str) -> Iterable[str]:
        for ch in text:
            if ch == "\r":
                self.cursor = 0
                continue
            if ch == "\b":
                if self.cursor > 0:
                    self.cursor -= 1
                    del self.buf[self.cursor]
                continue
            if ch == "\n":
                line = self._line()
                self.buf.clear()
                self.cursor = 0
                yield line
                continue

            o = ord(ch)
            if ch != "\t" and (o < 32 or o == 127):
                continue

            if self.cursor >= len(self.buf):
                self.buf.append(ch)
            else:
                self.buf[self.cursor] = ch
            self.cursor += 1


class SessionNormalizer:
    def __init__(self) -> None:
        self.last_cmd: str | None = None

    def normalize(self, line: str) -> str:
        s = line.strip()
        s = re.sub(r"^\^D+", "", s).strip()
        if not s:
            return ""

        # Heuristic: if command got glued to immediate output, split by prior cmd.
        if self.last_cmd and s.startswith(self.last_cmd) and len(s) > len(self.last_cmd):
            tail = s[len(self.last_cmd) :]
            if tail and not tail.startswith((" ", "\t")):
                s = tail.lstrip()

        # Track likely command lines for next-line deglueing.
        if self._looks_like_command(s):
            self.last_cmd = s

        return s

    @staticmethod
    def _looks_like_command(s: str) -> bool:
        if len(s) > 200:
            return False
        if s.startswith(("/", "[")):
            return False
        if "  " in s:
            return False
        # Accept common shell command-like starts.
        return bool(re.match(r"^[A-Za-z0-9_.-]+([ \t].*)?$", s))


def looks_like_prompt_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return True

    for pat in PROMPT_ONLY_RE:
        if pat.match(s):
            return True

    if s.startswith(("╭", "╰")):
        return True

    if any(marker in s for marker in PROMPT_MARKERS):
        return True

    if sum(ch in BOX_CHARS for ch in s) > max(2, len(s) // 8):
        return True

    if len(s) > 80 and (" on " in s or " at " in s):
        return True

    if s.startswith("..") and "/" in s:
        return True
    if s.endswith("%") and "/" in s:
        return True

    return False


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: session_log_sanitizer.py <raw_log> <clean_log>", file=sys.stderr)
        return 2

    raw_path, clean_path = sys.argv[1], sys.argv[2]

    stripper = ANSIStreamStripper()
    recon = LineReconstructor()
    norm = SessionNormalizer()

    with open(raw_path, "rb") as src, open(clean_path, "a", encoding="utf-8") as dst:
        src.seek(0)
        while True:
            chunk = src.read(8192)
            if not chunk:
                time.sleep(0.08)
                continue

            clean_chunk = stripper.feed(chunk)
            for line in recon.feed(clean_chunk):
                line = norm.normalize(line)
                if not line or looks_like_prompt_noise(line):
                    continue
                ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dst.write(f"[{ts}] {line}\n")
                dst.flush()


if __name__ == "__main__":
    raise SystemExit(main())
