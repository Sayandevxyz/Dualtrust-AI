"""pytest tests — M4 Deterministic Rule Engine"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.rule_engine import (
    _pan_validate, _verhoeff_validate, _gstin_validate, _ifsc_validate
)


# ─── PAN Format ────────────────────────────────────────────────────

class TestPANFormat:
    def test_valid_pan_individual(self):
        ok, msg = _pan_validate("ABCPK1234P")
        assert ok, msg

    def test_valid_pan_company(self):
        ok, msg = _pan_validate("AABCA1234C")
        assert ok, msg

    def test_invalid_pan_too_short(self):
        ok, msg = _pan_validate("ABCP1234")
        assert not ok

    def test_invalid_pan_digit_in_name(self):
        ok, msg = _pan_validate("A1CPK1234P")
        assert not ok

    def test_invalid_pan_bad_category(self):
        # 4th letter must be in PCHABFTLJG — 'X' is invalid
        ok, msg = _pan_validate("ABCXK1234P")
        assert not ok
        assert "category" in msg.lower()

    def test_pan_lowercase_normalized(self):
        ok, msg = _pan_validate("abcpk1234p")
        assert ok

    def test_pan_empty(self):
        ok, msg = _pan_validate("")
        assert not ok


# ─── Aadhaar Verhoeff Checksum ─────────────────────────────────────

class TestAadhaarChecksum:
    def test_valid_aadhaar(self):
        # Verhoeff-valid test number
        assert _verhoeff_validate("499118665246") is True

    def test_invalid_aadhaar_from_scenario_3(self):
        assert _verhoeff_validate("123456789013") is False

    def test_invalid_aadhaar_all_zeros(self):
        assert _verhoeff_validate("000000000000") is False

    def test_wrong_length(self):
        # Should not pass (caller should check length before calling)
        # 11 digits — verhoeff will still run but give wrong result
        result = _verhoeff_validate("12345678901")
        assert isinstance(result, bool)  # doesn't crash


# ─── GSTIN Checksum ────────────────────────────────────────────────

class TestGSTIN:
    def test_valid_gstin(self):
        # Known valid GSTIN format (synthetic)
        assert _gstin_validate("29AADCB2230M1ZP") is True

    def test_invalid_gstin_wrong_length(self):
        assert _gstin_validate("29AADCB2230M1Z") is False

    def test_invalid_gstin_bad_checksum(self):
        assert _gstin_validate("29AADCB2230M1ZX") is False

    def test_gstin_lowercase(self):
        assert _gstin_validate("29aadcb2230m1zp") is True


# ─── IFSC Format ───────────────────────────────────────────────────

class TestIFSC:
    def test_valid_sbi(self):
        assert _ifsc_validate("SBIN0001234") is True

    def test_valid_hdfc(self):
        assert _ifsc_validate("HDFC0001234") is True

    def test_invalid_wrong_5th_char(self):
        # 5th character must be 0
        assert _ifsc_validate("SBIN1001234") is False

    def test_invalid_too_short(self):
        assert _ifsc_validate("SBIN001234") is False

    def test_invalid_digits_in_bank_code(self):
        assert _ifsc_validate("1234001234A") is False
