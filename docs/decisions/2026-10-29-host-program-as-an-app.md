# The host program should install like an app: the options

Date: 2026-10-29. Status: proposal for Cooper. Nothing here is built.

## Why this is first

`docs/PATH.md` ranks it the first obstacle: no independent host can exist until an ordinary
person can run the host program, and without an independent host there is no independent
session and nobody to pay. Rule 9: "The host program installs like an app and works behind a
home router with nothing to configure. It only dials out." The stranger test's number two
complaint was the install.

## What a host needs today (verified in the repository)

- Python 3 and `host/orbit_host.py`, one file.
- The `cryptography` package (`host/requirements.txt`), for the sealed chat. Without it the
  program runs unsealed and the page says so.
- llama.cpp's server reachable as the `llama` command (`ORBIT_LLAMA_CMD`, default
  `llama serve`), listening on `ORBIT_LLAMA_PORT` (default 8081).
- A token file, `host/token.txt`, pasted from the Hosts page.

On Cooper's PC the `llama` command is version 0.7.0-dev, build 11941, a 51 MB executable under
`AppData\Local\Microsoft\WindowsApps`; how it was installed was not verified (winget reports no
`ggml.llamacpp` package and no Appx package matches).

## Facts that shape the choice (checked 2026-10-29)

- llama.cpp is MIT licensed ("Copyright (c) 2023-2026 The ggml authors"), so its binaries may
  be redistributed with the notice.
- llama.cpp publishes a release per build on GitHub (`b11981` on 2026-10-29, 38 assets).
  Windows x64 archives and sizes from that release: `llama-b11981-bin-win-vulkan-x64.zip`
  37.3 MB (the one an RX 580 needs), `llama-b11981-bin-win-cpu-x64.zip` 24.4 MB,
  `llama-b11981-bin-win-rocm-10.0-x64.zip` 264.9 MB, `llama-b11981-bin-win-cuda-13.4-x64.zip`
  165.0 MB plus a 423.5 MB `cudart` archive. There is also a `v0.8.0` tag with three assets
  (not binaries). Release `b11981` publishes no checksum file and its notes mention none
  (checked 2026-10-29), so Orbit must record the SHA-256 of the exact archive it ships or
  downloads, and update it deliberately when llama.cpp moves.
- Windows shows a SmartScreen warning for an unsigned executable downloaded from the web. A
  code-signing certificate removes it and costs money; the price was not researched.

## The options

| Option | What the host does | Size | What it needs from us | Risk |
|---|---|---|---|---|
| A. One folder, unzip and run | Downloads `orbit-host-win.zip`: the host program built into one executable plus llama.cpp's Vulkan build, a `README.txt`, and a `run.cmd` that asks for the token once | about 40 to 60 MB | A build step that freezes `orbit_host.py` with its dependency and copies the pinned llama.cpp archive in; a release on GitHub; the licence notice | Unsigned: SmartScreen warning. Vulkan only, so CUDA cards run through Vulkan (slower than CUDA, still works) |
| B. Tiny installer that fetches llama.cpp | A small executable that downloads the pinned llama.cpp archive on first run and checks its hash | under 10 MB download, then 37 MB | The same freeze, plus download and hash code, plus a choice of backend per GPU | Two things to trust and sign; a hash to keep current |
| C. Package manager | `winget install` of llama.cpp and `pip install` of the host program | 0 shipped | Publishing to winget and PyPI | Not "installs like an app"; still a terminal |

Keystone's recommendation: A first, Windows first (Cooper's host number one is Windows, the
RX 580 needs Vulkan), signed later when there is a reason to pay for it. B when A is in use and
the archive size or GPU choice becomes a complaint. C never as the main path.

## What the host program itself must do before any of this ships

From `docs/NEXT.md`, Later: if a model server is already answering on its port when it starts
(left over from a crash), adopt or stop it instead of failing to bind forever; one file, no
settings; the Hosts page gives the plain steps and the download link.

## Decisions for Cooper

1. Windows first, with the Vulkan build for everyone, yes or no.
2. Where the download lives: a GitHub release on `Diamond9k/orbit` (free, public) or the Hosts
   page of a running Orbit (needs the public address decision first).
3. Whether to pay for code signing now, later, or never.
4. Whether the freeze tool may be a build-time dependency (PyInstaller or Nuitka; their
   licences and the antivirus false-positive rate are to be verified before choosing).

## What this does not claim

No stranger has installed anything. No archive has been built. The sizes above are the
upstream archives, not Orbit's.
