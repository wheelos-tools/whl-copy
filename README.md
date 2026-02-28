
# whl-copy

An intelligent file copying and distribution wizard for local drives, remote SSH targets, and cloud object storage.

## Features
- Interactive CLI wizard for source/destination selection
- Auto-discovers local, remote, and cloud endpoints
- Filter presets and custom file selection
- Job saving and repeatable syncs
- Professional, English-only UI

## Quick Start

1. Install from PyPI:

```bash
pip install whl-copy
```

2. Run the wizard:

```bash
whl-copy
```

3. First run and configuration:

- On first run the tool will create `~/.whl_copy/` and copy default configuration files there (`config.yml`, `presets.yml`).
- To override defaults, pass explicit paths to the console script:

```bash
whl-copy --config /path/to/config.yml --presets-file /path/to/presets.yml --state-file /path/to/state.json
```

4. Use the interactive prompts to create or run sync jobs. Saved jobs, endpoints and history are stored under `~/.whl_copy/`.

## Example CLI Flow

```
=== Whl-Copy Sync Manager ===
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
