# BANcode Framework

A complete diagnostic code framework for bare-metal OS kernels. Defines four categories of diagnostic codes — fatal errors (BANcode), warnings (WARNcode), communication events (COMcode), and soft recovery (SOFTcode) — and generates language bindings for C99 freestanding, Rust `no_std`, and Python environments.

## Directory Structure

```
BANcode/
├── bancode.txt, warncode.txt, comcode.txt, softcode.txt, codenames.txt  ← source registries
├── data/
│   └── master_registry.json, .csv                                      ← generated machine-readable registry
├── kernel_inc/bancode/
│   └── bancode_all.h, bancode.h, warncode.h, comcode.h, softcode.h     ← generated C99 freestanding headers
├── kernel_src/bancode/
│   └── bancode.c                                                        ← generated C99 implementation
├── rust_bindings/
│   └── src/lib.rs, Cargo.toml                                           ← generated Rust no_std crate
├── python/bancode/
│   └── __init__.py, registry.py, bancode.py, warncode.py, comcode.py, softcode.py  ← Python IntEnum package
├── scripts/
│   ├── parse_sources.py                                                 ← parse .txt → registry
│   └── generate_bindings.py                                             ← registry → C/Rust/Python
├── tools/
│   └── bancode_cli.py                                                   ← CLI management tool
├── tests/
│   └── test_parser.py                                                   ← 14 unit tests
└── CMakeLists.txt                                                       ← build system
```

## Building

### Prerequisites
- CMake 3.20+
- C99 compiler (MSVC, GCC, or Clang)
- Python 3.13+

### Compile the static library

```bash
cmake -S . -B build -G "Visual Studio 17 2022"   # or Ninja, MinGW, etc.
cmake --build build --config Debug
```

Output: `build/lib/Debug/bancode.lib` (MSVC) or `build/lib/libbancode.a` (GCC/Clang)

### Regenerate from source .txt files

```bash
cmake --build build --target generate
```

Or manually:

```bash
py -3.13 scripts/parse_sources.py
py -3.13 scripts/generate_bindings.py
```

### Full pipeline (regenerate + build)

```bash
cmake --build build --target full
```

## Integration into a Bare-Metal Kernel (CMake)

Add the BANcode project as a subdirectory or `FetchContent` in your kernel's `CMakeLists.txt`:

```cmake
# Option A: add_subdirectory (source tree is local)
add_subdirectory(path/to/BANcode)

target_link_libraries(your_kernel PRIVATE bancode)
target_include_directories(your_kernel PRIVATE
    path/to/BANcode/kernel_inc
)
```

```cmake
# Option B: FetchContent (remote or versioned)
include(FetchContent)
FetchContent_Declare(
    bancode
    GIT_REPOSITORY https://github.com/your-org/BANcode.git
    GIT_TAG v1.0.0
)
FetchContent_MakeAvailable(bancode)

target_link_libraries(your_kernel PRIVATE bancode)
```

Then in your kernel code:

```c
#include <bancode/bancode.h>
#include <bancode/warncode.h>
#include <bancode/comcode.h>
#include <bancode/softcode.h>
// or: #include <bancode/bancode_all.h> for everything
```

### Trap Range Dispatch

The trap vector table maps `0x7FFFFFF0 + N` → BANcode codepoint at offset `N`:

```c
#include <bancode/bancode_all.h>

// In your IDT/exception handler:
void handle_trap(uint32_t trap_num) {
    uint32_t base = 0x7FFFFFF0;
    uint32_t code = base + trap_num;
    bancode_info_t info;
    if (bancode_lookup(code, &info) == 0) {
        // info.name, info.description available
        kernel_panic(info.name);
    }
}
```

## CLI Usage

```bash
py -3.13 tools/bancode_cli.py build              # full pipeline
py -3.13 tools/bancode_cli.py lookup 0x0011A01A   # look up a code by hex
py -3.13 tools/bancode_cli.py lookup MBW_FS_SYNC_PROGRESS  # by name
py -3.13 tools/bancode_cli.py validate            # validate source files
py -3.13 tools/bancode_cli.py stats               # allocation statistics
```

## Rust Bindings

```bash
cd rust_bindings
cargo build --no-default-features
cargo test  # (if std is enabled for tests)
```

## Python Package

```python
from bancode.bancode import BANcode
from bancode.comcode import COMcode
from bancode.softcode import SOFTcode
from bancode.warncode import WARNcode

# Lookup by value
err = BANcode(0x0011A01A)
print(err.name, err.value)
```

## Running Tests

```bash
py -3.13 -m unittest tests.test_parser -v
```

All 14 tests verify: registry validity, code ranges, unique names per category, no duplicate hex within categories, C99 freestanding compliance, Rust `no_std` compliance, Python IntEnum usage, and no dynamic allocation in generated C code.

## Code Categories

| Category  | Prefix | Hex Range           | Slots  | Purpose |
|-----------|--------|---------------------|--------|---------|
| BANcode   | `B+`   | `0011A000-0011A7FF` | 2048   | Fatal unrecoverable panics |
| WARNcode  | `W+`   | `0011A800-0011ABFF` | 1024   | Non-fatal telemetry and alerts |
| COMcode   | `C+`   | `0011AC00-0011ADFF` | 512    | IPC, bus orchestration, success |
| SOFTcode  | `S+`   | `0011AE00-0011AEFF` | 256    | Soft recovery and self-healing |
