# CoD2 MP Map Script Generator

A clean, modern GUI tool designed to simplify creating and editing essential script files for **Call of Duty 2** multiplayer custom maps.

### Main Features
- Generate/edit core map scripts:
  - `maps/mp/mp_mapname.gsc` (main script: factions, ambient, fog, glow, killtriggers, HQ radios…)
  - `maps/mp/mp_mapname_fx.gsc` (FX/effects script: precache/loadfx, scr_sound, ambient calls…)
  - `sun/mp_mapname.sun` (sun/lighting: presets + full flare/blind/glare controls)
  - `soundaliases/mp_mapname.csv` (custom sound aliases — wide table editor with horizontal scroll)
  - `maps/mp/mp_mapname.csv` + `mp/mp_mapname.arena` (basic files: loadscreen + longname/gametypes)
- **Model Viewer**: Browse hundreds of stock xmodel preview images (thumbnails + full-size)
- **IWD Packer**: Automatically detect and pack custom assets (models, textures, sounds, scripts, FX, loadscreen…) into a .iwd file
- **Tools Setup**: Set CoD2 path, extract missing `xmodel/` & `fx/` folders, create admin desktop shortcuts, fix grid batch file

## Requirements

1. **Working Call of Duty 2 installation**  
   - The tool reads from / writes to the `main/` folder, so it must be a valid, working CoD2 install.

2. **Call of Duty 2 Mod Tools** (required even if you only use this script generator)  
   Download and install from the following link:  
   https://www.moddb.com/games/call-of-duty-2/downloads/call-of-duty-2-mod-tools  

3. **Python 3.8 or newer** (3.10–3.12 recommended)  
   - Download from: https://www.python.org/downloads/  
   - During installation, **check the box "Add python.exe to PATH"**  
   - Verify installation by opening Command Prompt and running:
     ```
     python --version
     ```
     You should see something like `Python 3.11.9`

## Installation & Setup

1. **Download the tool**  
   Either:
   - Clone the repository:
     ```
     git clone https://github.com/yourusername/cod2-map-script-gen.git
     cd cod2-map-script-gen
     ```
   - Or download the ZIP from GitHub → extract it to a folder

2. **Install required Python package** (only Pillow is needed — tkinter is usually built-in)  
   Open Command Prompt in the project folder and run:
    ```
      pip install pillow
	```
	If you get a "pip not found" error, run this first:	
	```
	 python -m ensurepip --upgrade
	```
	
	Note: A virtual environment is optional and not required — the tool runs fine in your global Python installation.

## How to Run

	From the project folder (where `main.py` is located), run:
	```
	python main.py
	```
	

- A window titled "CoD2 MP Mapping tools" will open.
- On first launch:
  1. Click Browse next to "CoD2 folder" and select your Call of Duty 2 installation directory  
     (the folder containing `main/`, `bin/`, `mods/`, etc.)
  2. Choose or type a map name in the dropdown (e.g. `mp_mymap`)
  3. Click Refresh if needed
- Use the tabs to work on your map:
  - **Script Tools** — edit main/fx/sun/sound/basic files
  - **Model Viewer** — browse stock xmodel images
  - **Tools Setup** — extract folders, create shortcuts, fix grid batch
  - **IWD Packer** — pack custom assets into .iwd

## Core Functionality Summary

**Script Tools** (main working area)  
- Main GSC: factions, ambient sound, fog/glow, killtriggers, HQ radios, custom script calls  
- FX GSC: loadfx precache, scr_sound, ambient FX placement  
- SUN File: preset loader + full sun/flare/blind/glare editing  
- Sound Aliases: 24-column CSV table editor with horizontal + vertical scroll  
- Basic Files: loadscreen CSV + arena file (longname + gametypes)  

**Generate / Save All Files** button (bottom of Script Tools) writes everything at once.

**Model Viewer** — offline browser of stock xmodel preview images. -requires a seperate download of images, downloader built in

**IWD Packer** — scans map folder and packs only custom/non-stock files into .iwd.

**Tools Setup** — one-click fixes for common setup issues.

## Important Notes

- Always backup your map folder before generating files.
- Although every effor has been made with the iwd packing, it may miss some files (rare) 

Happy mapping!  
Built for the CoD2 community.
