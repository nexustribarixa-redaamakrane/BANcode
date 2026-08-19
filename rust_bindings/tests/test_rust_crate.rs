#![cfg(test)]

extern crate bancode;
use bancode::{BANcode, WARNcode, COMcode, SOFTcode, is_valid, name};

#[test]
fn test_bancode_try_from_valid() {
    let code = BANcode::try_from(0x0011A01A).unwrap();
    assert_eq!(code as u32, 0x0011A01A);
}

#[test]
fn test_bancode_try_from_invalid() {
    assert!(BANcode::try_from(0xDEADBEEF).is_err());
}

#[test]
fn test_warncode_try_from_valid() {
    let code = WARNcode::try_from(0x0011A800).unwrap();
    assert_eq!(code as u32, 0x0011A800);
}

#[test]
fn test_warncode_try_from_invalid() {
    assert!(WARNcode::try_from(0x0011A000).is_err());
}

#[test]
fn test_comcode_try_from_valid() {
    let code = COMcode::try_from(0x0011AC00).unwrap();
    assert_eq!(code as u32, 0x0011AC00);
}

#[test]
fn test_softcode_try_from_valid() {
    let code = SOFTcode::try_from(0x0011AE00).unwrap();
    assert_eq!(code as u32, 0x0011AE00);
}

#[test]
fn test_is_valid_true() {
    assert!(is_valid(0x0011A01A));
}

#[test]
fn test_is_valid_false() {
    assert!(!is_valid(0x00000000));
}

#[test]
fn test_name_returns_string() {
    let n = name(0x0011A01A);
    assert!(n.is_some());
    assert!(!n.unwrap().is_empty());
}

#[test]
fn test_name_invalid_returns_none() {
    assert!(name(0xDEADBEEF).is_none());
}

#[test]
fn test_bancode_all_variants_are_distinct() {
    let mut seen = std::collections::HashSet::new();
    let variants = [
        BANcode::SUCS_TRAP_DISPATCH_FAILED as u32,
        BANcode::MBL_OWMKFS_BOOT_BYPASS as u32,
        BANcode::MBW_FS_SYNC_PROGRESS as u32,
    ];
    for v in variants {
        assert!(seen.insert(v), "duplicate variant value: {:#X}", v);
    }
}
