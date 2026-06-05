# NePTA Core

**Network Performance Test Automatization** — the core framework for automated network performance testing on RHEL systems.

NePTA orchestrates test tools (iperf3, netperf, sockperf, ubench) across pairs of machines, collects results into structured [`nepta-dataformat`](https://github.com/rh-nepta/nepta-dataformat) packages, and optionally submits them to a result server. It handles the full lifecycle: interface setup, system tuning, test execution, result collection, and reporting.

## Features

- **Multi-tool support** — iperf3 (TCP/UDP/SCTP, zero-copy, parallel streams, congestion), netperf (stream, request-response), sockperf (ping-pong latency), ubench (microbenchmarks), perun (perf/BPF profiling)
- **Phase-based execution** — run any combination of setup, prepare, execute, store, and submit phases independently
- **Declarative configuration** — define hosts, interfaces, IP addresses, test paths, and scenarios in Python
- **Multi-host synchronization** — coordinate test phases across machines via Beaker, PerfSync, or standalone mode
- **Structured results** — output as `nepta-dataformat` packages with metadata, logs, and attachments
- **Flexible networking** — supports Ethernet, VLAN, IPsec, WireGuard, OVS, bond, and team interfaces

## Quick Start

```bash
git clone https://github.com/rh-nepta/nepta-core
cd nepta-core
hatch shell
nepta --help
```

## Installation

### From source (development)

```bash
pip install -e .
```

### Dependencies

| Required | Optional |
|---|---|
| [nepta-dataformat](https://github.com/rh-nepta/nepta-dataformat) | [nepta-synchronization](https://github.com/rh-nepta/nepta-synchronization) |
| [jinja2](https://pypi.org/project/Jinja2/) | [coloredlogs](https://pypi.org/project/coloredlogs/) |
| [xml-diff](https://pypi.org/project/xmldiff/) | |
| [numpy](https://pypi.org/project/numpy/) | |

All dependencies are managed by Hatch and installed automatically in the development environment.

## Usage

### Print a configuration

```bash
nepta -i example_config . -p -c Default -e fqdn host_1.testlab.org
```

### Run a full test

```bash
nepta -i example_config . -c Default -e fqdn host_1.testlab.org \
    --setup --prepare --execute --store --store-logs
```

### Run individual phases

```bash
# Setup network interfaces and system configuration
nepta -i example_config . -c Default -e fqdn host_1.testlab.org --setup

# Execute tests only (assumes setup is already done)
nepta -i example_config . -c Default -e fqdn host_1.testlab.org --execute

# Submit results to the result server
nepta -i example_config . -c Default -e fqdn host_1.testlab.org --submit
```

### Filter scenarios and paths

```bash
# Run a specific scenario
nepta -i my_config . -c Default -e fqdn host.lab.org --execute -s Iperf3TCPStream

# Filter test paths by tag
nepta -i my_config . -c Default -e fqdn host.lab.org --execute -t IPv4

# Override message sizes
nepta -i my_config . -c Default -e fqdn host.lab.org --execute -m 64 512 1024
```

### Multi-host synchronization

```bash
# Using Beaker synchronization
nepta -i my_config . -c Default -e fqdn host.lab.org --sync beaker --execute

# Using PerfSync server
nepta -i my_config . -c Default -e fqdn host.lab.org --sync perfqe --execute
```

### Environment variable configuration

Arguments can also be set via the `NETWORK_PERFTEST_ARGS` environment variable:

```bash
export NETWORK_PERFTEST_ARGS="-i example_config . -c Default -e fqdn host_1.testlab.org --execute"
nepta
```

## Configuration

Tests are defined in Python configuration modules. See [`example_config/`](example_config/) for a complete example.

```python
from nepta.core import scenarios
from nepta.core.model import bundles, tag
from nepta.core.model.network import EthernetInterface, IPv4Configuration
from nepta.core.model.schedule import Path as P

# Define two test hosts
host_1 = bundles.HostBundle('host_1.testlab.org', 'Default')
host_2 = bundles.HostBundle('host_2.testlab.org', 'Default')

# Configure network interfaces
host_1.interfaces.eth.eth_1 = EthernetInterface('eth_1', 'A2:A0:8B:4B:B5:C7', net4.new_config())
host_2.interfaces.eth.eth_1 = EthernetInterface('eth_1', 'A2:A0:8B:4B:B5:C8', net4.new_config())

# Define test paths between hosts
paths = [
    P(host_1.interfaces.eth.eth_1.v4_conf[0],
      host_2.interfaces.eth.eth_1.v4_conf[0],
      [tag.SoftwareInventoryTag('IPv4')]),
]

# Add test scenarios
host_1.scenarios += scenarios.Iperf3TCPStream(paths, 60, 2, [1024, 8192, 65536], (0, 0), 5201, 2, 2)
host_1.scenarios += scenarios.Iperf3TCPReversed(paths, 60, 2, [1024, 8192, 65536], (0, 0), 5201, 2, 2)
```

## Development

### Running tests

```bash
hatch run test
```

Or directly:

```bash
pip install . && pytest unittests/
```

### Linting and formatting

```bash
hatch run lint:style     # check style (ruff + black)
hatch run lint:fmt       # auto-format
```

### Type checking

```bash
hatch run mypy:typing    # mypy on nepta.core
```

### Container build

```bash
make build-container     # uses docker or podman
```

## Architecture

```
nepta/core/
├── __main__.py          # CLI entry point
├── model/               # Configuration model (Bundle tree, interfaces, paths, system settings)
├── strategies/          # Phase implementations (setup, prepare, run, save, submit, report)
├── scenarios/           # Test scenario definitions (iperf3, netperf, sockperf, ubench, perun)
├── tests/               # Test tool CLI wrappers (CommandTool → CLI flag mapping)
├── distribution/        # OS interaction layer (commands, env detection, config file generation)
└── templates/           # Jinja2 templates for network config files (ifcfg, nmconnection, etc.)
```

The framework uses a **strategy pattern** — each execution phase is a `Strategy` subclass whose methods are auto-discovered via the `@Strategy.schedule` decorator. Strategies compose with `+` into a `CompoundStrategy` that runs them in sequence.

## License

[GPL-3.0-or-later](LICENSE)
