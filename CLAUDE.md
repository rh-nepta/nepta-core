# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

nepta-core is the core of the NePTA (Network Performance Test Automatization) framework. It automates network performance testing on RHEL systems by orchestrating test tools (iperf3, netperf, sockperf, ubench) across pairs of machines, collecting results into `nepta-dataformat` packages, and optionally submitting them to a result server.

## Build & Development Commands

The project uses **Hatch** as its build/environment manager.

```bash
hatch shell                     # enter development environment
hatch run test                  # install package + run pytest (generates JUnit XML)
hatch run print                 # import example config and print it
hatch build                     # build distribution
```

**Linting & formatting:**
```bash
hatch run lint:style            # ruff + black check
hatch run lint:fmt              # auto-format with black + ruff --fix
```

**Type checking:**
```bash
hatch run mypy:typing           # mypy on nepta.core package
hatch run mypy:pytest-mypy      # pytest with mypy plugin
```

**Single test file:**
```bash
pip install . && pytest unittests/model/network_test.py
```

The `pip install .` step is required before running tests due to namespace package import resolution.

**Makefile shortcuts:**
```bash
make test                       # hatch run test
make fmt                        # hatch run lint:fmt
make code-style-check           # hatch run lint:style
make build-container            # build container image (docker or podman)
```

**Pre-commit hook** (`.githooks/pre-commit`): runs `lint:style` then `test`.

## Code Style

- Line length: 120
- Single quotes for strings (ruff `flake8-quotes`)
- Black formatter targeting py37
- Absolute imports only (no relative imports)

## Architecture

### Entry Point

`nepta.core.__main__:main` — the `nepta` CLI. Parses args, loads a `HostBundle` configuration by hostname+config name, builds a `CompoundStrategy` from the selected phases (`--setup`, `--prepare`, `--execute`, `--store`, `--submit`), and executes it. Configurations can also be loaded from the `NETWORK_PERFTEST_ARGS` environment variable.

### Configuration Model (`nepta/core/model/`)

`Bundle` is a tree structure (graph-capable, with cycle detection) that holds configuration components. Nodes are accessed as attributes (`conf.interfaces.eth.eth_0`). `HostBundle` extends `Bundle` with a global registry keyed by `(hostname, conf_name)`, enabling `HostBundle.find(fqdn, conf_name)` lookups.

Key model classes:
- **`network.py`** — `Interface`, `EthernetInterface`, `VlanInterface`, `IPsecTunnel`, `WireGuardTunnel`, `OVSwitch`, bond/team interfaces, routes
- **`schedule.py`** — `Path` (source IP ↔ dest IP + tags + optional CPU pinning), `PathList`, `CongestedPath`, `SockPerfPath`
- **`system.py`** — system-level config objects (packages, services, tuned profiles, sysctl, IRQ settings)
- **`tag.py`** — `HardwareInventoryTag`, `SoftwareInventoryTag` for classifying test paths

### Strategy Pattern (`nepta/core/strategies/`)

`Strategy` is the base class. Methods decorated with `@Strategy.schedule` are auto-discovered and run in order. Strategies compose via `+` into a `CompoundStrategy`.

Phases map to strategy classes:
- `setup/` — install packages, configure network interfaces, system settings, virtualization
- `prepare.py` — non-persistent pre-test setup
- `sync.py` — multi-host synchronization barriers (Beaker, PerfSync, or none)
- `run.py` — `RunScenarios` iterates filtered scenarios and collects results
- `save/` — persist metadata, attachments, logs into a `DataPackage`
- `submit.py` — rsync results to a result server
- `report.py` — report pass/fail to Beaker/restraint

### Test Scenarios (`nepta/core/scenarios/`)

`ScenarioGeneric` → `StreamGeneric` → tool-specific scenarios. `StreamGeneric` iterates over `Path` objects and message sizes, running test instances with retry logic.

Scenario families: `iperf3/` (TCP, UDP, SCTP, zero-copy, parallel, congestion), `netperf/` (stream, request-response), `sockperf/` (ping-pong latency), `ubench/` (microbenchmarks), `perun/` (perf/BPF profiling).

### Test Tool Wrappers (`nepta/core/tests/`)

`CommandTool` base class wraps CLI tools. Subclasses define a `MAPPING` list of `CommandArgument` objects that declaratively map Python attributes to CLI flags. The `_make_cmd()` method generates the command string.

### Distribution Layer (`nepta/core/distribution/`)

- `command.py` — `Command` and `ShellCommand` wrap `subprocess.Popen` with output watching
- `env.py` — `Environment` (hostname, kernel, distro, Beaker/TF vars) and `Hardware` (nproc, memory, interfaces) are metaclass singletons populated at import time from the host system
- `conf_files.py` — generators for network config files (ifcfg, nmconnection, IPsec, WireGuard, udev rules, chrony)
- `utils/` — system utilities (package management, tuna, IRQ balancing, filesystem, virtualization)

### External Dependencies

- **`nepta-dataformat`** — data packaging library (`DataPackage`, `Section`); results are stored as nested `Section` trees
- **`nepta-synchronization`** (optional) — client for multi-host test coordination via a sync server

## Testing

Unit tests live in `unittests/` and mirror the source layout. Tests use pytest directly (no special fixtures or mocking frameworks). The CI matrix runs across multiple Python versions via `hatch run all:test`.
