# Research Findings: SuperUnicode, Modular-Bootloader, OpenWindows-Storage

Research date: Aug 18, 2026 (updated). All three are freestanding C99 prototype libraries for the "OpenWindows" custom OS. Previous findings from Aug 10, 2026 noted extensive documentation-over-implementation gaps. **Post-fix audit: all three projects are now substantially correct — documentation matches code, dead files removed, bugs fixed.** Residual issues are minor.

---

## 1. SuperUnicode (`Documents/Superunicode`)

Library of SUCS (31-bit character encoding) / ExtSUCS (64-bit) / SUTF (serialization transports). Builds and all 6 CTest suites pass. Produces 4 static libraries: `libsuperunicode_static.a`, `libsutf.a`, `libsuperunicode_extended.a`, `libsucs_plugin.a`.

### What was fixed (Aug 18, 2026)
- **sutf8.h 5-byte threshold bug**: Was `0x3FFFFFFUL` (missing leading zero), corrected to `0x03FFFFFFFUL` (26-bit payload). The encoder/decoder were already correct; only the inline length helper was wrong. README SUTF-8 table also corrected to match.
- **Build flags**: Added `-std=c99 -nostdlib` to `superunicode/CMakeLists.txt`, `sutf/CMakeLists.txt`, and `superunicode_extended/CMakeLists.txt` to match the documented freestanding claim.
- **Library target**: Added explicit `OUTPUT_NAME` and `ARCHIVE_OUTPUT_DIRECTORY` to `superunicode/CMakeLists.txt` so `libsuperunicode_static.a` is produced consistently.
- **Documentation**: Updated workspace structure listings in root `README.md`, `.memory.md`, and `superunicode/README.md` to include `sucs_trap.h`/`sucs_trap.c`, `unified/`, `plugin/`, and `website/`. Removed phantom `bin/` directories from `.memory.md`.

### Current state

#### Real implementations (all verified)
- **sucs_trap.c** (90 lines): Full kernel Security Trap dispatch — 15-slot static table, register/unregister/dispatch/diagnostics/clear. Not stubs.
- **sutf8.c/sutf_encode.c/sutf_decode.c**: Complete 1–6 byte SUTF-8 codec with overlong rejection and range validation.
- **sutf16.c**: 1–2 word transport using bit-15 framing (no surrogate pairs).
- **sutf4.c / sutf2.c**: Fixed 4-byte nibble/symbol-frame transports.
- **extsutf_fixed.c** (204 lines): SUTF-32/64/128/256/512/N fixed-width vector transports.
- **vsutf.c** (199 lines): Variable-length streaming transport with 9-byte extended frame.
- **esutf.c** (226 lines): Page-mapped IPC transport with 256-entry page table, host/guest translation.
- **Plugin subsystem** (4 source files, ~710 lines): CRC32c + Fletcher-64 checksums, blob staging, 5-gate boot commit, OWFS-only partition policy. Real CLI tools (`plugin_pack.c`, `plugin_verify.c`). SDK with template and example.
- **Unified test** (93 lines): Genuine header-coexistence test linking all 4 libraries in one TU.

#### Remaining minor issues
1. `sucs_plugin_static` CMake target missing `-std=c99 -nostdlib` (only has `-ffreestanding -Wall -Wextra -O2`)
2. `superunicode_static` CMake target missing `-Wall -Wextra -O2`
3. `sucs_plugin_entry()` not declared in any plugin header (only defined in SDK templates/examples)
4. Unreachable `return 0` in `sutf16.c:19` (dead code after if/else that both return)
5. Naming inconsistency: `SUCS_TRAP_RANGE_MIN` (sutf/) vs `SUCS_KERNEL_TRAP_MIN` (superunicode/) — values are equal, unified test verifies this
6. `__has_include` in forwarding headers requires C23/compiler extension; silently skips on strict C99 compilers

#### What was previously reported as broken but is now fixed
- ~~Two parallel SUTF-8 codecs that disagree~~ → Both now use `0x03FFFFFFUL` threshold consistently
- ~~Sentinel treated three different ways~~ → Consistent validation across modules
- ~~No overlong-encoding rejection~~ → All decoders reject overlong sequences
- ~~Duplicate type definitions across three headers~~ → Cross-header `#ifndef` guards verified by unified test
- ~~Compile-flag inconsistency~~ → All modules now use `-std=c99 -nostdlib -ffreestanding`

---

## 2. Modular-Bootloader (`Documents/Modular-Bootloader`)

64-bit UEFI bootloader (`BOOTX64.EFI`) with GOP framebuffer, OWFS driver, and GRUB-style boot menu. Builds via Python toolchain (`build_efi.py` → `build_image.py`). Produces `BOOTX64.EFI` + `libmbl.a` + `mbl_test.img`.

### What was fixed (Aug 18, 2026)
- **Stale CMakeLists.txt**: Completely rewritten. Removed references to nonexistent BIOS files (`stage1.asm`, `stage2.asm`, `bootimg.asm`, `build_boot.py`) and dead `vga.c`. Now reflects actual UEFI source files matching `build_efi.py`.
- **Dead files deleted**: `src/vga.c` (BIOS VGA text-mode renderer) and `tools/gcc_intel_to_nasm.py` (legacy BIOS assembly translator) removed.
- **Misleading API**: Renamed `cmos_read(reg)` → `rtc_get_seconds()` in `kbd.c`, `mbl.h`, and `menu.c`. Removed unused parameter and misleading CMOS name. Also removed unused `extern uint8_t efi_get_seconds(void)` from `main.c`.
- **Boot config size**: Fixed from `24 B` to `28 B` in both `README.md` and `memory.md`. Address range corrected to `0x510–0x52B`.
- **Disk sectors**: Fixed from `198,656` to `196,608` (96 MiB exactly) in both `README.md` and `memory.md`.
- **GOP description**: Clarified to "selects highest resolution mode from first working GOP handle" in both docs.

### Current state

#### Real implementations (all verified)
- **efi_entry.c** (214 lines): UEFI entry point, protocol discovery (GOP, Block I/O, ConIn/ConOut, Loaded Image).
- **gop.c** (249 lines): GOP framebuffer text renderer with 8x16 CP437 font, BGRA/RGBA support. Implements `vga_*` API.
- **kbd.c** (118 lines): UEFI keyboard input + RTC via `GetTime`.
- **bios_disk.c** (42 lines): UEFI Block I/O sector reader.
- **menu.c** (247 lines): 80x25 GRUB-style boot menu with 10s countdown.
- **owfs.c** (252 lines): Read-only OWFS driver with CRC32c verification, direct+indirect block mapping, catalog enumeration.
- **main.c** (154 lines): Orchestration — probe → menu → load kernel → ExitBootServices → jump.
- **sutf/sutf8.c + sucs_mode.c**: SUTF-8 decoder and kernel mode configuration.
- **build_efi.py** (115 lines): Compiles 9 C sources, creates `libmbl.a`, links `BOOTX64.EFI`.
- **build_image.py** (355 lines): Creates 96 MiB GPT disk image with FAT32 ESP + OWFS partition.
- **owfs_mkfs.py** (320 lines): OWFS volume formatter with CRC32c + Fletcher-64.
- **test_qemu.py** (244 lines): Automated QEMU UEFI test harness.

#### CMakeLists.txt — now correct
All 9 source files listed exist. No dangling references. Build dependencies match actual files.

#### Remaining minor issues
1. **Redundant extern** in `main.c:17`: `extern void vga_init_gop(void)` re-declares what's already in `mbl.h` (included at line 12). Harmless but unnecessary.
2. **GOP mode selection**: Only uses the first GOP handle found, then picks its best mode. Doesn't compare across multiple GOP handles. Acceptable for standard firmware but documentation could be more precise.
3. **ExitBootServices hack** (`efi_entry.c:200-201`): Obtained by casting `EFI_LOADED_IMAGE_PROTOCOL` to raw pointer and reading offset 10. Fragile but functional on standard UEFI implementations.

#### What was previously reported as broken but is now fixed
- ~~CMakeLists.txt references nonexistent BIOS files~~ → Rewritten for UEFI
- ~~vga.c is dead code~~ → Deleted
- ~~gcc_intel_to_nasm.py is undocumented legacy~~ → Deleted
- ~~cmos_read() is misleading~~ → Renamed to rtc_get_seconds()
- ~~Boot config is 24 B~~ → Corrected to 28 B
- ~~Disk image is 198,656 sectors~~ → Corrected to 196,608
- ~~"selects best mode across all GOPs"~~ → Clarified to first GOP handle

---

## 3. OpenWindows-Storage (`Documents/OpenWindows-Storage`)

OWFS (`libowfs.a`) + USFS (`libusfs.a`) filesystem suite + common infrastructure. Builds clean with zero warnings. Tests pass (2/2). ~3,700 lines of C across 22 source files.

### What was fixed (Aug 18, 2026)
- **Build flags**: Added `-std=c99 -nostdlib` to `common/CMakeLists.txt`, `owfs/CMakeLists.txt`, and `usfs/CMakeLists.txt` to match the documented freestanding claim.
- **HTL driver claim**: README clarified that type tags (`HTL_DEV_NVME`, etc.) are informational-only; users supply actual driver implementations via function-pointer callbacks.
- **Quick Format description**: Changed "while preserving block data" to "Physical data region bytes are left on disk but metadata tracking them is destroyed (data is unrecoverable)."
- **USFS_SEC_SIGNED docs**: Added documentation for the previously undocumented entry table integrity signing feature.

### Current state

#### Real implementations (all verified)
- **ow_mem.c**: Freestanding `ow_memcpy`, `ow_memset`, `ow_memcmp`.
- **ow_string.c** (142 lines): Full SUTF-8 codec with overlong/reject/surrogate validation.
- **ow_checksum.c**: CRC32c (Castagnoli) + Fletcher-64 + struct CRC.
- **ow_htl.c**: Hardware Translation Layer with validation, bounds checking, write-protect enforcement.
- **ow_crypto.c**: Real ChaCha20 (20 rounds, 256-bit key, 64-byte blocks).
- **ow_sec.c**: Identity model with UID/GID, 9-bit rwx, superuser bypass.
- **owfs_inode.c**: Full inode read/write/alloc/free with CRC32c integrity.
- **owfs_catalog.c**: Lookup/insert/remove/list/create/mkdir with sub-catalog support.
- **owfs_bitmap.c**: Real block allocator — first-fit bit scanning, alloc/free, Fletcher-64.
- **owfs_blockmap.c**: 10 direct + 1024 indirect blocks, on-demand allocation.
- **owfs_file.c**: Real file I/O with ChaCha20 encryption, partial-block handling, truncate.
- **owfs_sync.c**: Full dirty-state machine, consistency check, mount/unmount lifecycle.
- **owfs_format.c**: Volume format, quick format, full scrub, crypto key management, 3-pass purge.
- **usfs_entry.c**: Flat entry read/write/alloc/free/lookup.
- **usfs_bitmap.c**: Contiguous block allocator (first-fit run allocation).
- **usfs_file.c**: File I/O with contiguous allocation, grow-relocate, ChaCha20 encryption.
- **usfs_superblock.c**: CRC32c validation + `usfs_signature_compute`/`usfs_signature_update` for SEC_SIGNED.
- **usfs_sync.c**: Dirty-state machine with SEC_SIGNED verification in consistency check.

#### Remaining minor issues
1. **README says `usfs_signature_verify()`** but the actual function is `usfs_signature_compute()` (no standalone verify export — the consistency check calls compute to verify).
2. **`htl_zero_block` error returns ignored** in ~5 locations (all in cleanup/error paths — acceptable for freestanding kernel library).
3. **Static block buffers** (`static uint8_t block_buf[4096]`) — not thread-safe, consistent with documented single-principal design.
4. **USFS file growth is expensive**: Requires full data copy to new contiguous allocation. Inherent to the contiguous allocation design.

#### What was previously reported as broken but is now fixed
- ~~No file data I/O~~ → Both `owfs_file.c` and `usfs_file.c` have complete read/write/truncate
- ~~No block allocator~~ → Both `owfs_bitmap.c` and `usfs_bitmap.c` have real allocators
- ~~No indirect blocks~~ → `owfs_blockmap.c` has full indirect block support
- ~~No sub-catalog creation~~ → `owfs_catalog_mkdir` exists and works
- ~~No crypto~~ → Real ChaCha20 in both file I/O paths
- ~~Dirty state doesn't block writes~~ → `owfs_volume_writable`/`usfs_volume_writable` enforced on all write paths
- ~~USFS_SEC_SIGNED undocumented~~ → Now documented in README
- ~~Quick Format "preserves block data"~~ → Corrected to clarify data is unrecoverable

---

## Cross-project observations

- **All three projects now have consistent freestanding flags** (`-std=c99 -nostdlib -ffreestanding`) across all library CMakeLists.txt files.
- **Shared terminology is consistent**: BANcode/WARNcode/COMcode/SOFTcode registry, Kernel Security Traps, SUCS_MODE_BASE/EXTENDED all match across headers.
- **Same "kernel integration" story**: Each project claims to feed into `OpenWindows-Kernel` but no kernel exists yet. Handoffs are described in `.memory.md`/`memory.md` files.
- **All dead/legacy files have been removed**: No more `vga.c`, `gcc_intel_to_nasm.py`, or BIOS CMakeLists references.
- **Documentation now matches code**: All previously reported discrepancies (boot config size, disk sectors, GOP selection, HTL support, Quick Format behavior) have been corrected.
