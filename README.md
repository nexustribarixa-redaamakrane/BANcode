# BANcode

BANcode is a registry compiler for four diagnostic-code ranges used by the
OpenWindows projects. The five top-level `.txt` files are the editable source;
the JSON/CSV registry and C, Rust, and Python bindings are generated outputs.

## Registry ranges

| Registry | Range | Number of slots | Intended use |
| --- | --- | ---: | --- |
| BANcode (`B+`) | `0x0011A000–0x0011A7FF` | 2048 | Fatal conditions |
| WARNcode (`W+`) | `0x0011A800–0x0011ABFF` | 1024 | Warnings and telemetry |
| COMcode (`C+`) | `0x0011AC00–0x0011ADFF` | 512 | Status and communication events |
| SOFTcode (`S+`) | `0x0011AE00–0x0011AEFF` | 256 | Recoverable conditions |

`bancode.txt`, `warncode.txt`, `comcode.txt`, and `softcode.txt` define the
slots and category metadata. `codenames.txt` supplies names used by the
generator. `scripts/parse_sources.py` writes `data/master_registry.json` and
`.csv`; `scripts/generate_bindings.py` emits the C headers and implementation,
the Rust `no_std` crate source, and the Python enums.

The C API is under `kernel_inc/bancode/` and implemented in
`kernel_src/bancode/`. `bancode_trap.c` maps fatal-code clusters to the
15-code kernel trap range; the final 128-code B+ cluster has no trap mapping.
The registry values are code points, not OS error strings or exceptions.

## Build and regenerate

Requirements: CMake 3.20 or newer and a C99 compiler. Python 3 is needed for
generation and the parser tests; Cargo is needed only for Rust bindings.

```powershell
cmake -S . -B build -G "MinGW Makefiles" -DCMAKE_C_COMPILER=gcc
cmake --build build
ctest --test-dir build --output-on-failure
```

On GCC/Clang builds, CTest runs `symbol_audit`, which checks that the static
library does not leave unresolved hosted-runtime symbols. MSVC does not define
that audit target.

To regenerate the checked-in outputs and then compile:

```powershell
cmake --build build --target full
```

Or run the pipeline stages directly:

```powershell
py scripts/parse_sources.py
py scripts/generate_bindings.py
```

Generation rewrites files under `data/`, `kernel_inc/`, `kernel_src/`,
`python/`, and `rust_bindings/`; inspect the resulting diff before accepting it.

## CLI and tests

The repository CLI is a Python script, not an installed console command:

```powershell
py tools/bancode_cli.py validate
py tools/bancode_cli.py stats
py tools/bancode_cli.py lookup 0x0011A01A
py tools/bancode_cli.py lookup MBW_FS_SYNC_PROGRESS
py tools/bancode_cli.py build
```

The `build` command parses the source, regenerates bindings, configures CMake
under `build/`, and compiles `libbancode`. The tests are Python `unittest`
tests; they also regenerate files in their setup:

```powershell
py -m unittest discover -s tests -v
```

The Rust crate is in `rust_bindings/`:

```powershell
cargo test --manifest-path rust_bindings/Cargo.toml
```

## Repository map

- `data/` — generated registry snapshots.
- `kernel_inc/bancode/`, `kernel_src/bancode/` — C API and trap dispatch.
- `rust_bindings/` — Rust `no_std` binding crate.
- `python/bancode/` — generated Python enums and lookup data.
- `scripts/` — parser and binding generator.
- `tools/bancode_cli.py` — validation, lookup, statistics, and build commands.
- `tests/test_parser.py` — parser and generated-output checks.

The text registries are the source of truth. A generated binding is stale until
the parser and generator have been rerun from the same source revision.
