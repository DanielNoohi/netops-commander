# AGENTS.md — NetOps Commander

Guidance for AI agents improving or fixing this codebase. Read this before making changes.

## Project reality (read first)

This is an early **MVP** (~2.2k LOC Python), **not** a finished NetOps suite.

| Claimed in README | Actual state |
|-------------------|--------------|
| Full tools suite (traceroute, DNS, TLS, WOL, Wi‑Fi, subnet calc, launchers, …) | **Missing.** Only `gui/tools/ping_tool.py` exists — and it is a **stub** (appends text, no ping) |
| Continuous ping with live graph | Not implemented |
| Dark/light themes | Colors defined in `gui/themes.py` but **never applied** |
| Monitoring & alerts | Models + `MonitorController` exist; **not wired to the GUI** |
| Alerts feed on dashboard | Table UI exists; **never populated** from DB |
| Inventory stats (online/offline) | Labels exist; `update_stats()` rarely/never called from scan flow |
| Nmap / SNMP / scapy integration | Dependency *detection* only; no real integration in scan path |
| `PROJECT_STRUCTURE.md` | **Outdated / aspirational** — lists widgets & tools that do not exist |

**Rule:** Prefer fixing and wiring what exists over inventing the whole README feature list. If you add a feature, implement it end-to-end (core + GUI + tests) or do not claim it in the README.

**Version:** `1.1.1` — keep `__version__` in `netops_commander/__init__.py` and `APP_VERSION` in `constants.py` in sync (CI checks this).

---

## Priority order

Work in this order unless the user specifies otherwise:

1. **Correctness bugs** (crashes, wrong data, broken scan/export)
2. **Wire incomplete features** that already have partial code (monitor, alerts, themes, ping, progress)
3. **Align docs** with reality (README + `PROJECT_STRUCTURE.md`)
4. **New tools** one at a time (only if asked)
5. Polish / extras

---

## Known bugs & gaps to fix

### Critical / high

1. **`open_ports` type mismatch**
   - DB model stores JSON **string** (`models.Device.open_ports: Text`).
   - `persist_device()` correctly does `json.dumps(...)`.
   - `device_table.py` treats ORM `d.open_ports` as a **list** (`", ".join(map(str, d.open_ports))`). That joins characters of the JSON string, or breaks oddly.
   - **Fix:** helper `parse_open_ports(value) -> list[int]` used everywhere UI/export reads ports; never assume list on the ORM object.

2. **Scan progress never updates**
   - `ScanThread` defines `progress` signal but `background_scan` / `scan_cidr` are called **without** `progress_callback`.
   - Progress bar stays at 0 until done.
   - **Fix:** pass a thread-safe callback from `ScanThread.run` into `scan_cidr` / `background_scan` that emits `self.progress`.

3. **Monitoring is fake**
   - Context menu “Toggle Monitoring” only flips `Device.is_monitored` in SQLite.
   - `MonitorController` (`core/monitoring.py`) is never started from the GUI; no alert generation for offline/recovery/latency.
   - New devices get `is_monitored=True` by default in `persist_device` — may be too aggressive.
   - **Fix:** own a single `MonitorController` (or QThread wrapper) in `MainWindow`; load monitored devices on startup; react to toggle; write `Alert` rows; refresh dashboard alerts.

4. **Ping / Port Scan menu actions are placeholders**
   - `_ping_selected` / `_portscan_selected` only show `QMessageBox`.
   - `PingToolWidget` does not run ping.
   - **Fix:** implement real ping (reuse `discovery.async_ping` or subprocess) on a worker thread; either open a tool dock/dialog or stream into a log panel. Port scan: rate-limited TCP connect using config ports — do not shell out unsafely.

5. **`QAction` import**
   - `main_window.py` imports `QAction` from `QtWidgets`.
   - PySide6 6.5+ moved `QAction` to `QtGui`; newer versions may warn/break.
   - README changelog claims this was fixed — **it was not** in `main_window.py`.
   - **Fix:** `from PySide6.QtGui import QAction`.

6. **`psutil` gateway / MAC bugs in `utils/network.py`**
   - Uses `psutil.net_if_gateways()` — may not exist on all psutil versions (already try/except’d for gateways).
   - MAC assignment is wrong: compares `addr.family == psutil.AF_LINK` on an AF_INET addr in the same loop; MAC rarely set correctly.
   - **Fix:** separate pass for `AF_LINK` / `psutil.AF_LINK` addresses; use a portable gateways API (or parse OS routes).

### Medium

7. **Themes unused** — apply `DARK`/`LIGHT` via stylesheet or `QPalette` from config `app.theme`; add View → Theme toggle.

8. **`DeviceDialog` unused** — `_edit_device` uses `QInputDialog`; prefer opening `DeviceDialog(device_id)`.

9. **Dashboard disconnected** — after scan / monitor / alert writes, call `dashboard.update_stats(...)` and reload alerts from `Alert` table.

10. **`export_devices_csv` in `scanner.py`** — assumes `DiscoveredDevice` has `.notes` / `.tags` / `.first_seen` attributes that the dataclass may not have; GUI export path uses `utils.export` instead. Clean up dead/duplicate export APIs.

11. **`vacuum_database`** — `session.execute("VACUUM")` is invalid on SQLAlchemy 2.x; needs `text("VACUUM")` on the connection/engine.

12. **`constants.py`** — `DEFAULT_THEME = "dark"` duplicated twice.

13. **Dependency checker thread leak** — `_refresh_status` can spawn a new `DependencyChecker` every 30s without retaining/joining previous threads. Keep one worker or guard with `isRunning()`.

14. **Icon resource** — `QIcon(":/icons/app.png")` is a placeholder; missing Qt resource file → silent empty icon. Either add `.qrc` or load a filesystem icon / skip.

15. **Migrations not run on startup** — `init_database()` only `create_all`; `run_migrations()` never called from `main.py`.

### Docs / hygiene

16. **README honesty** — strip or mark “Planned” for unimplemented tools; match the real tree under `gui/tools/`.

17. **Rewrite `PROJECT_STRUCTURE.md`** to match the filesystem (or delete it and keep README structure only).

18. **License clarity** — repo has GPL-3 `LICENSE`; README says “authorized use only” without naming GPL. Align messaging.

19. **`requirements.txt`** — `asyncio-mqtt` appears unused; optional deps (`scapy`, `python-nmap`, `pysnmp`) are required in the file but treated as optional in docs. Split into `requirements.txt` (core) + `requirements-optional.txt`, or document clearly.

20. **CI** — pyflakes is advisory; after cleanup, make it a hard gate. Expand tests beyond `tests/test_scan_pipeline.py`.

---

## Architecture map (what to touch)

```
main.py                          # entry; init DB + logging + MainWindow
netops_commander/
  config.py / config.yaml        # defaults; SQLite settings intended later
  constants.py                   # version, ports, alert types
  core/
    discovery.py                 # ping / ARP / TCP / hostname / OUI / type guess  ← strongest code
    scanner.py                   # scan_cidr, background_scan, persist_device, cancel
    monitoring.py                # MonitorController (unwired)
    alerts.py                    # severity_for() helper only
  database/
    models.py                    # Device, ScanHistory, MonitorResult, Alert, Setting
    database.py                  # engine, session_scope, init_database
    migrations.py                # lightweight ALTER helpers (not hooked up)
  gui/
    main_window.py               # shell; menus thin
    dashboard.py                 # network card + empty alerts
    device_table.py              # scan UX + table + export + context menu
    device_dialog.py             # edit dialog (unused)
    themes.py                    # color dicts only
    tools/ping_tool.py           # STUB
  utils/
    network.py, validators.py, export.py, logger.py, privileges.py, dependencies.py
tests/test_scan_pipeline.py      # only automated test; mocks discover_host
.github/workflows/ci.yml         # py_compile + pipeline test + version sync
```

**Patterns already in use (follow them):**
- Async network work off the GUI thread via `QThread` + `asyncio.new_event_loop()`.
- DB access via `session_scope()` context manager.
- Logging via `get_logger(__name__)`.
- No `shell=True`; subprocess with argument lists only.
- Validate user CIDR/IP via `utils.validators` before scanning.

---

## Security / product constraints

- Authorized networks only; keep validation and rate limits.
- Do not add exploit payloads, aggressive scanners, or default-on wide internet scans.
- Port scans: respect `PORT_SCAN_MAX_*` in constants and config concurrency/timeouts.
- Prefer stdlib / existing deps over new heavy dependencies unless necessary.

---

## Suggested fix batches (good PR-sized chunks)

### Batch A — Correctness
- Fix `open_ports` parse/display/export
- Wire scan `progress_callback`
- Fix `QAction` import
- Fix MAC/gateway detection
- Fix `vacuum_database` / call migrations from `init_database` or `main`
- Deduplicate `DEFAULT_THEME`

### Batch B — Monitoring & dashboard
- Wire `MonitorController` to MainWindow
- Persist real alerts; fill dashboard table
- Update inventory stats after scan/monitor
- Soften default `is_monitored=True` if product intent is opt-in

### Batch C — First real tool
- Implement functional Ping tool (UI + worker)
- Hook context-menu Ping to it
- Optional: simple TCP port check for selected device

### Batch D — Truth in docs + deps
- Trim README feature list / mark Planned
- Refresh `PROJECT_STRUCTURE.md`
- Split or clarify requirements
- Turn pyflakes into a failing CI step after import cleanup

---

## Testing expectations

- Keep `tests/test_scan_pipeline.py` green.
- For logic changes, add small non-GUI tests (validators, open_ports helper, persist behavior with mocked session if feasible).
- Do not require a display for CI; GUI tests are optional/manual unless you add offscreen Qt setup.
- After edits: `python -m py_compile` on touched modules; run `python tests/test_scan_pipeline.py`.

---

## Do / Don’t

**Do**
- Fix one coherent batch at a time
- Match existing style (type hints, module loggers, relative imports)
- Update README when behavior changes
- Prefer completing half-built features over new folders of stubs

**Don’t**
- Paste README fantasy features as empty files
- Use `shell=True`
- Commit secrets, `.db` files, or venvs
- Expand scope into a full rewrite unless the user asks
- Claim “fixed” in changelog unless the code path is actually fixed (see QAction)

---

## Quick verification checklist

After a fix batch, manually or via tests confirm:

- [ ] `python main.py` launches without import errors
- [ ] Scan a small CIDR (e.g. local `/30` or `/29`); cancel works; progress moves
- [ ] Discovered devices show sane Vendor / Ports / Online columns
- [ ] Export CSV/JSON/HTML opens and contains expected fields
- [ ] Toggle monitor actually pings on an interval (if Batch B done)
- [ ] Version strings still match (`__init__.py` ↔ `constants.py`)
