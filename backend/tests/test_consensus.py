"""pytest tests — M5 Consensus Engine"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.consensus_engine import _compare_field, _normalize_string
from app.models import MatchStatus


class TestFieldComparison:
    def test_identical_string_match(self):
        status, score = _compare_field("applicant_name", "Priya Kapoor", "Priya Kapoor", 2.0)
        assert status == MatchStatus.match
        assert score == 1.0

    def test_normalized_string_match(self):
        # Case and punctuation differences
        status, score = _compare_field("employer_name", "Tech Solutions Pvt Ltd", "TECH SOLUTIONS PVT. LTD.", 2.0)
        assert status in (MatchStatus.match, MatchStatus.soft_match)
        assert score >= 0.7

    def test_string_mismatch(self):
        status, score = _compare_field("employer_name", "Acme Corp", "Totally Different Company", 2.0)
        assert status == MatchStatus.mismatch
        assert score == 0.0

    def test_numeric_within_tolerance(self):
        status, score = _compare_field("net_salary", "60000", "60500", 2.0)  # 0.83% diff
        assert status == MatchStatus.match
        assert score == 1.0

    def test_numeric_outside_tolerance(self):
        status, score = _compare_field("net_salary", "60000", "45000", 2.0)  # 25% diff
        assert status == MatchStatus.mismatch
        assert score == 0.0

    def test_both_null_skipped(self):
        status, score = _compare_field("pan_number", None, None, 2.0)
        assert status == MatchStatus.skipped
        assert score == 1.0

    def test_one_null_partial(self):
        status, score = _compare_field("pan_number", "ABCPK1234P", None, 2.0)
        assert status == MatchStatus.partial
        assert score == 0.5

    def test_exact_field_pan_match(self):
        status, score = _compare_field("pan_number", "ABCPK1234P", "ABCPK1234P", 2.0)
        assert status == MatchStatus.match

    def test_exact_field_pan_mismatch(self):
        status, score = _compare_field("pan_number", "ABCPK1234P", "XYZPK5678Q", 2.0)
        assert status == MatchStatus.mismatch
        assert score == 0.0

    def test_numeric_zero_both(self):
        status, score = _compare_field("deductions_total", "0", "0", 2.0)
        assert status == MatchStatus.match
        assert score == 1.0

    def test_salary_month_mismatch(self):
        status, score = _compare_field("salary_month", "2026-07", "2026-06", 2.0)
        assert status == MatchStatus.mismatch


class TestNormalizeString:
    def test_removes_punctuation(self):
        assert _normalize_string("Tech. Solutions Pvt. Ltd.") == "techsolutionspvtltd"

    def test_lowercase(self):
        assert _normalize_string("PRIYA KAPOOR") == "priyakapoor"

    def test_empty(self):
        assert _normalize_string("") == ""
