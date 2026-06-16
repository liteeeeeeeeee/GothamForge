<div align="center">

# 🦇 GothamForge

### A modding tool for *LEGO Batman 2: DC Super Heroes* (PC)

Edit abilities, vehicles, textures, audio, dialogue, unlocks, cheat codes, colours and 3D models.

<br>

![Python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)
![Game](https://img.shields.io/badge/game-LEGO%20Batman%202-FFD700?logo=lego&logoColor=black)
![Version](https://img.shields.io/badge/version-1.3.0-7E57C2)
![License](https://img.shields.io/badge/license-MIT-3DA639)

</div>

---

## ✨ Highlights

- 🖥️ **Two ways to mod** — a point-and-click **Mod Studio** GUI *and* `gf` command line.
- ♻️ **Non-destructive by design** — the first time any file is touched it's copied to `backups/`. `restore-all` reverts your install to vanilla in one step.
- 🔍 **Auto-detects your game** — drop the folder into your install and GothamForge finds it (or point it anywhere with `--game`).
---

## 📑 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [The Mod Studio (GUI)](#-the-mod-studio-gui)
- [Command-Line Reference](#-command-line-reference)
- [How Backups Work](#-how-backups-work)
- [Project Layout](#-project-layout)
- [Troubleshooting](#-troubleshooting)
- [Credits & Disclaimer](#-credits--disclaimer)

---

## 🧰 Features

| Area | What you can do |
|------|-----------------|
| 🦸 **Abilities** | View and edit any character's ability **flags** (`flight`, `super_strength`, `heat_vision`, `x_ray_vision`, `swimmer`, …) and numeric **stats** (`hit_points`, `run_speed`, `jump_speed`, `scale`, …). |
| 🚗 **Vehicles** | Same treatment for vehicles — top speed, acceleration, turn rate, mass, fire rate, weapons, hover/flight and more. |
| 💬 **Dialogue & Text** | Search the game's `TEXT.CSV` across every language and rewrite subtitles, menu strings and character names. |
| 🖼️ **Textures** | Convert `.TEX ⇄ .DDS ⇄ .PNG`, and **import your own PNG** straight into a game texture — auto-encoded to DXT1/DXT5 with mipmaps and resized to match the original. |
| 🔊 **Audio** | Browse OGG music tracks, open `.PAC` sound banks, list/extract individual samples, **decode CBX → WAV**, and flip `SAMPLES.CFG` file types. Built-in playback in the GUI. |
| 🛒 **Roster / Shop** | Edit `COLLECTION.TXT` unlocks — change a character's stud cost, make one free, or **unlock the entire shop** at once. |
| 🎮 **Cheat Codes** | List, add, change or remove the Batcomputer unlock codes for any character. |
| 🎨 **Colours & Parts** | Recolour minifig parts using the game's LEGO colour palette, toggle part visibility **layers** (torso, arms, cape, hair, hat…), and **swap heads** from the game's catalogue. |
| ✈️ **Flight Streaks** | View and tweak the RGBA flight-trail streaks behind flying characters. |
| 🧱 **3D Models** | Inspect `.GHG` models (build info, mesh parts, texture refs), **export embedded textures to PNG**, and extract geometry to a standard **`.obj`** — with a live 3D preview in the GUI. |
| 🛟 **Safety** | List every file you've modified and restore them individually or all at once. |

---

## 📋 Requirements

- **Windows** (recommended) — model extraction, CBX decoding and audio playback use Windows helpers. 
- **Python 3.8 or newer**
- **A copy of LEGO Batman 2: DC Super Heroes (PC)** installed locally.
- Python packages: [`Pillow`](https://pypi.org/project/Pillow/) ≥ 9.4 and [`NumPy`](https://pypi.org/project/numpy/) ≥ 1.20.

<details>
<summary><b>Optional extras</b></summary>

| Extra | Enables |
|-------|---------|
| [`soundfile`](https://pypi.org/project/soundfile/) | In-app OGG playback and decoding |
| **FFmpeg** (`ffplay` on your `PATH`) | Alternative audio playback backend |
| `CBXDecoder.exe` (placed in the game root or a `CBXDecoder/` subfolder) | Decoding `.CBX` voice/SFX samples to WAV |
</details>

---

## ⚙️ Installation

```bash
# 1. Put the GothamForge folder inside your game install, e.g.
#    .../steamapps/common/LEGO Batman 2/GothamForge
#    (GothamForge auto-detects the game by walking up from here)

# 2. Install the Python dependencies
pip install -r requirements.txt
```

That's it. GothamForge locates the game automatically by looking for `GAMEVERSION.TXT` + the `CHARS/` folder. If you keep it somewhere else, pass `--game "C:\path\to\LEGO Batman 2"` on any command, or set the `LB2_PATH` environment variable.

---

## 🚀 Quick Start

### Launch the GUI

```bash
python gothamforge_gui.py
```

…or on Windows just **double-click `run_gui.bat`**.

### Or use the command line

```bash
# Show what GothamForge found
python gf.py info

# Give Batman the power of flight
python gf.py char set-flag batman flight on

# Make Superman tankier
python gf.py char set-value superman hit_points 8

# Unlock the entire shop for free
python gf.py roster free-all

# Drop a custom PNG onto a texture
python gf.py tex import my_logo.png STUFF/ICONS/SOMETHING.TEX

# Changed your mind? Undo absolutely everything:
python gf.py restore-all
```

---

## 🖥️ The Mod Studio (GUI)

Running `gothamforge_gui.py` opens a tabbed studio (1240×740) that wraps every feature in a visual interface:

| Tab | Highlights |
|-----|-----------|
| **Dashboard** | Install info, build version and a summary of what you've modified |
| **Abilities** | Pick a character, tick ability flags, slide numeric stats |
| **Vehicles** | The same, for every drivable/flyable vehicle |
| **Dialogue** | Live search + inline editing of any in-game string |
| **Textures** | Preview `.TEX`/`.DDS`, export to PNG, import replacements |
| **Audio** | Browse banks, **play** samples, extract and decode |
| **Roster** | Spreadsheet-style editing of unlock costs |
| **Model** | Software-rendered **3D preview**, texture export, OBJ export |
| **Cheats** | Manage Batcomputer codes |
| **Colors** | Colour-picker recolouring, part-visibility layers, head swaps |
| **Streaks** | Edit flight-trail colours |
| **Archives** | Open and extract `.PAK` files |
| **Backups** | One-click **Restore ALL** and per-file restore |

> 💡 Use **File → Restore ALL** at any time to wipe every change and return to a clean install.

<!-- Tip: drop a screenshots/ folder next to this README and embed it here, e.g.
![Mod Studio](screenshots/dashboard.png)
-->

---

## ⌨️ Command-Line Reference

General form:

```bash
python gf.py [--game <path>] <command> <action> [arguments]
```

Character/vehicle names are **fuzzy** — `bat` will match `Batman` if it's unambiguous.

<details>
<summary><b>info</b> — install summary</summary>

```bash
python gf.py info
```
Prints the install path, build/version, number of character definitions and how many files are currently backed up.
</details>

<details>
<summary><b>char</b> — character abilities & stats</summary>

```bash
python gf.py char list [filter]                 # list characters (optional name filter)
python gf.py char show  <name>                  # show flags, values and add-ons
python gf.py char set-flag  <name> <flag> on|off
python gf.py char set-value <name> <key> <value>
```
Example: `python gf.py char set-value flash run_speed 14`
</details>

<details>
<summary><b>dialogue</b> — text & subtitles (TEXT.CSV)</summary>

```bash
python gf.py dialogue search <query> [--lang ENGLISH] [--type TYPE] [--limit 50]
python gf.py dialogue set    <LABEL> "<new text>" [--lang ENGLISH]
```
Example: `python gf.py dialogue set FE_PLAY "PLAY GAME" --lang ENGLISH`
</details>

<details>
<summary><b>tex</b> — texture conversion & import</summary>

```bash
python gf.py tex info   <file.TEX>
python gf.py tex topng  <file.TEX> <out.png>
python gf.py tex todds  <file.TEX> [out.dds]
python gf.py tex import <image.png> <target.TEX>   # auto DXT1/DXT5 + mipmaps, matched to target
```
</details>

<details>
<summary><b>pak</b> — texture archives</summary>

```bash
python gf.py pak list    <file.PAK>
python gf.py pak extract <file.PAK> [out_dir]
```
</details>

<details>
<summary><b>audio</b> — OGG / sound banks / CBX / SAMPLES.CFG</summary>

```bash
python gf.py audio ogg-list  [filter]
python gf.py audio banks
python gf.py audio bank-list <bank.PAC> [filter]
python gf.py audio extract   <bank.PAC> <name> [out]
python gf.py audio decode    <bank.PAC> <name> [out_dir]   # CBX -> WAV (needs CBXDecoder.exe)
python gf.py audio set-filetype <sample> [WAV]
```
</details>

<details>
<summary><b>roster</b> — shop unlocks (COLLECTION.TXT)</summary>

```bash
python gf.py roster list
python gf.py roster set-cost <name> <studs>
python gf.py roster free     <name>
python gf.py roster free-all
```
</details>

<details>
<summary><b>cheats</b> — Batcomputer codes</summary>

```bash
python gf.py cheats list [--coded]
python gf.py cheats set-code    <name> <CODE>
python gf.py cheats remove-code <name>
```
</details>

<details>
<summary><b>colors</b> — minifig parts, layers & heads (.CD)</summary>

```bash
python gf.py colors list       <name>
python gf.py colors set        <name> <material#> <COLOUR_NAME>
python gf.py colors layers     <name>
python gf.py colors set-layers <name> <byte1 hex> <byte2 hex> <byte3 hex>
python gf.py colors heads      <name>
python gf.py colors set-head   <name> <HEAD_NAME> [slot#]
```
</details>

<details>
<summary><b>model</b> — .GHG model inspection & export</summary>

```bash
python gf.py model info     <file.GHG>
python gf.py model textures <file.GHG> [out_dir]   # export embedded textures (PNG)
python gf.py model mesh     <file.GHG>             # vertex/face stats
python gf.py model obj      <file.GHG> [out.obj]   # export geometry to OBJ
```
</details>

<details>
<summary><b>streaks</b> — flight trails</summary>

```bash
python gf.py streaks list
python gf.py streaks show <name>
```
</details>

<details>
<summary><b>backup / restore</b> — safety net</summary>

```bash
python gf.py backup                 # list every modified/created file
python gf.py restore <relative/path>
python gf.py restore-all            # revert everything to vanilla
```
</details>

---

## 🛟 How Backups Work

GothamForge never edits a file without protecting it first:

1. The **first** time a file is modified, the original is copied into `GothamForge/backups/`, and its size + SHA-1 are recorded in `backups_manifest.json`.
2. Files that didn't exist before (new files you created) are tracked too — restoring simply deletes them.
3. `restore` puts one file back; `restore-all` (CLI) or **File → Restore ALL** (GUI) returns your whole install to vanilla.

This means you can experiment freely — nothing you do is permanent until you decide it is.

---

## 🗂️ Project Layout


Want to verify everything works against your install? Run the self-test:

```bash
python tests/selftest.py
```


## 🙌 Credits & Disclaimer

- Mesh extraction uses the community **ExtractNxgMESH** tool (bundled as a convenience).
- CBX decoding uses **CBXDecoder** when present.

> **LEGO®** is a trademark of the LEGO Group. *LEGO Batman 2: DC Super Heroes* © TT Games / Warner Bros. Interactive Entertainment, DC characters © DC. **GothamForge is an unofficial, fan-made tool and is not affiliated with, endorsed by, or sponsored by any of these companies.** Use it only with games you own, and respect the rights of the original creators when sharing mods.

---


</div>
