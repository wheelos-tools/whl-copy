
# universal-copy-wizard (whl-copy)

An intelligent file copying and distribution wizard for local drives, remote SSH targets, and cloud object storage.

## Features
- Interactive CLI wizard for source/destination selection
- Auto-discovers local, remote, and cloud endpoints
- Filter presets and custom file selection
- Job saving and repeatable syncs
- Professional, English-only UI

## Quick Start

1. **Install dependencies** (Python 3.8+ required):
	 ```bash
	 pip install -r requirements.txt
	 ```

2. **Run the wizard:**
	 ```bash
	 python -m whl_copy.main
	 ```

3. **Follow the prompts:**
	 - Select operation: Run a saved job or create a new one
	 - Choose source and destination endpoints (local, remote, or cloud)
	 - Select a filter preset or define custom file filters
	 - Review the file preview and estimated transfer size/time
	 - Confirm to start the sync

4. **Saved jobs** can be rerun from the main menu for fast repeat operations.

## Example CLI Flow

```
=== Whl-Copy Sync Manager (Bidirectional) ===
Select operation:
	1) [Run] Execute a saved Sync Job (Skip config)
	2) [New] Create new Sync Job (Save for future)
	3) [Quit] Exit manager

--- Storage Endpoint Selection ---
Select Source (From):
	1) [Saved] MyLocal (/home/user)
	2) [Discovered: local] Local Home: /home/user (/home/user)
	3) [Manual] Enter a custom path

Select Destination (To):
	1) [Saved] MyNAS (nas:/data)
	2) [Discovered: remote] NAS: /data (nas:/data)
	3) [Manual] Enter a custom path

[Step] Select Filter Strategy
Select Filter Preset:
	1) [Preset] Documents (*.pdf, *.docx)
	2) [Preset] Media (*.mp4, *.jpg)
	3) [Custom] Create new filter...

Matched files (showing up to 50): 12
	- /home/user/Documents/file1.pdf
	...
Estimated transfer size: 1.2 GB
Estimated transfer time: 2m 30s

Proceed with sync? (Y/n)
```

## Configuration
- Edit `whl_copy/config.yml` and `whl_copy/presets.yml` to customize endpoints and filter presets.

## License
See LICENSE for details.
