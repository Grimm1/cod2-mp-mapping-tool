# CoD2 MP Mapping Tool

A modern PyQt6 GUI tool that simplifies creating, editing, compiling, and packaging **Call of Duty 2** multiplayer custom maps.

You can use the launcher.bat file to install python, dependencies and run the code, but microsoft "smart" app control  may block it

### Main Features

- **Script Tools**
  - `maps/mp/<mapname>.gsc` — main script (factions, ambient, fog/glow, killtriggers, HQ radios, extra script calls)
  - `maps/mp/<mapname>_fx.gsc` — FX script (precache/loadfx, scr_sound, ambient FX)
  - `sun/<mapname>.sun` — sun/flare/blind/glare settings with presets
  - `soundaliases/<mapname>.csv` — full sound alias editor
  - `maps/mp/<mapname>.csv` + `mp/<mapname>.arena` — loadscreen + longname/gametypes

- **Compile Tools** (new)
  - BSP / VIS / Lighting pipeline (`cod2map.exe` + `cod2rad.exe`)
  - Grid capture (make new / edit existing)
  - Connect Paths + Run Map
  - Full option panels, custom command-line args, per-map settings, live console

- **IWD Packer**
  - Choose a map and select **Analyze custom files** to scan its `.map` and referenced prefabs for non-stock xmodels, materials, textures, and FX references.
  - Also checks `loadfx` calls in the map's `_fx.gsc`, custom EFX shader/material/texture dependencies, and available map files such as scripts, the BSP, arena, sun, sound aliases, and loadscreen assets.
  - Review the discovered file list, then select **Pack to IWD**. The default name is `zzz_<mapname>.iwd`; the archive uses paths relative to `main/` or `raw/` so assets land in the expected IWD locations.
  - The scan can miss assets loaded dynamically or referenced outside the files it examines, so verify the list and include any such dependencies separately.

- **Model Viewer**  
  Browse stock xmodel thumbnails + large previews (image pack downloadable from inside the tool).

- **Tools Setup**  
  One-click helpers: set CoD2 path, extract xmodels/FX from IWDs, install Asset Manager DLLs, fix grid batch file.

### What’s New / Changed from the original version

- Complete rewrite from **Tkinter → PyQt6** (cleaner UI, better layout, native feel).
- Brand-new **Compile Tools** tab with full map compile pipeline and grid tools.
- Much more robust CoD2 path handling (supports both root and `main/` layouts; always prefers writing under `main/`).
- Expanded IWD Packer analysis (recursive prefab scanning, FX detection from `.map` + `_fx.gsc`, custom EFX shader/material/texture dependencies, and map/loadscreen files) with a reviewable file list and correctly rooted IWD paths.
- Per-map compile settings persistence.
- Better status indicators, color pickers for fog, ambient alias auto-loading, and overall polish.
- Cleaner helpers and configuration system.

### Requirements

1. **Working Call of Duty 2 installation**  
   The tool reads from / writes primarily under the `main/` folder.

2. **Call of Duty 2 Mod Tools**  
   https://www.moddb.com/games/call-of-duty-2/downloads/call-of-duty-2-mod-tools

3. **Python 3.10+** (3.11–3.12 recommended)  
   - Download from https://www.python.org/downloads/  or microsoft store.
   - Make sure “Add python.exe to PATH” is checked during install.

### Installation

# Clone or download the repository
git clone https://github.com/Grimm1/cod2-mp-mapping-tool.git
cd cod2-mp-mapping-tool

# Install dependencies
pip install PyQt6 psutil
```

### How to Run

```bash
python main.py
```

1. Set your CoD2 installation path (Browse button).
2. Select or type a map name (e.g. `mp_mymap`).
3. Use the tabs:
   - **Script Tools** — edit GSC / SUN / sound / basic files
   - **Compile Tools** — compile BSP/VIS/Lighting, capture grid, run map
   - **Model Viewer** — browse stock models
   - **IWD Packer** — analyze + pack custom assets
   - **Tools Setup** — extract folders, fix common issues

### Important Notes

- Always back up your map files before generating or compiling.
- The IWD Packer is thorough but may still miss a few edge-case assets (manually add them if needed).
- Compile Tools require the official CoD2 bin tools (`cod2map.exe`, `cod2rad.exe`, etc.).

Happy mapping!
