# whl-copy

Universal copy tool with wizard + profile mode only.

## CLI Modes

- `whl-copy`: interactive wizard (`Source -> Destination -> Filter -> Preview -> Execute`)
- `whl-copy --fast`: use last `.whl_copy_state.json` plan and run without prompts
- `whl-copy --profile <name>`: run a named saved profile directly

## Proposed Python Structure

```text
whl_copy/
	main.py                     # wizard-only CLI entry
  wizard.py                   # Wizard orchestration pipeline
	presets.yml                 # Preset/custom profile templates (YAML)
  config.yml                  # Runtime configuration
  core/
	 models.py                 # Profile / State models
	 profile_store.py          # Preset/profile YAML store
	 state_store.py            # Local persistent state read/write
  modules/
	 address_discovery.py      # Pluggable storage detectors (disk/usb/ssh/bos/custom)
	 filters.py                # Path and rule filters
	 scanner.py                # Data scan helpers
	 local_transfer.py         # Local copy executor
	 rsync_transfer.py         # Remote copy executor
	 checksum.py               # Verification helpers
  utils/
	 logger.py
	 time_utils.py
tests/
```

## Wizard Workflow

1. Source Selection
	- source is local working directory only
	- default to last source or current working directory
2. Destination Selection
	- scan mounted disks / USB / remote SSH / BOS / custom endpoints
	- choose destination device and save directory
3. Filter Pipeline
	- choose preset (`当天数据`, `近1小时抓包`, `全量配置`) or `自定义过滤`
	- custom filter type/pattern comes from YAML templates
	- time range (`近1小时`, `今天`, `不限`) and size (`1K`, `1M`, `1G`, `不限`)
	- preview matched files and estimated total size
4. Execution
	- ask `是否保存配置? (Y/n)` and save as named profile
	- confirm with `Proceed with copy? (Y/n)`
	- execute copy, print size and estimated time, then progress bar
	- remote destination uses scp-like address `user@host:/path` (only destination address needed)

## Template vs State (分离)

- Template config: [whl_copy/presets.yml](whl_copy/presets.yml)
  - `filter_types`, `presets`, `named_profiles`
- History state: `~/.whl_copy_state.json`
  - `last_source`, `last_dest`, `last_filter_type`, `last_plan`

## Interaction Library

- Preferred: `questionary` (better menu/confirm/text UX)
- Fallback: built-in `input/print` if `questionary` is not installed

## Install & Verify

```bash
pip install -e .
whl-copy --help
whl-copy
```

## Quick Start

```bash
python -m whl_copy.main
python -m whl_copy.main --fast
python -m whl_copy.main --profile 当天日志方案
```
