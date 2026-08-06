"""
Tests for scenario_validator.py
"""
import pytest
import sys
from datetime import datetime, date, timezone
from decimal import Decimal

sys.path.insert(0, "/mnt/agents/output/AI_Trading_Lab_v1_2")

from scenario_validator import ScenarioValidator, BatchValidator, ValidationIssue
from scenario_models import ScenarioRecord, Direction, HumanReviewStatus


def make_record(**kwargs):
    defaults = dict(
        record_id="REC-001",
        source_id="SRC-001",
        scenario_date=date(2024, 1, 15),
        published_at=datetime(2024, 1, 15, 8, 0, 0),
        symbol="EURUSD",
        direction=Direction.LONG,
        original_text="Test scenario text",
        data_quality_score=80,
    )
    defaults.update(kwargs)
    return ScenarioRecord(**defaults)


class TestValidLong:
    def test_normal_long(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.LONG,
            entry_price_low=Decimal("1.0850"),
            entry_price_high=Decimal("1.0860"),
            stop_loss=Decimal("1.0800"),
            take_profit_1=Decimal("1.0900"),
        )
        valid, issues, score = v.validate(r)
        assert valid is True
        assert score > 70
        assert r.missing_required_fields is None


class TestValidShort:
    def test_normal_short(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.SHORT,
            entry_price_low=Decimal("1.0850"),
            entry_price_high=Decimal("1.0860"),
            stop_loss=Decimal("1.0900"),
            take_profit_1=Decimal("1.0800"),
        )
        valid, issues, score = v.validate(r)
        assert valid is True
        assert score > 70


class TestRequiredMissing:
    def test_missing_symbol(self):
        v = ScenarioValidator()
        r = make_record(symbol="")
        valid, issues, score = v.validate(r)
        assert valid is False
        assert any("symbol" in i.field and "必須" in i.message for i in issues)
        assert r.missing_required_fields is not None
        assert "symbol" in r.missing_required_fields

    def test_missing_source_id(self):
        v = ScenarioValidator()
        r = make_record(source_id='')
        valid, issues, score = v.validate(r)
        assert valid is False
        assert any(i.severity == "critical" for i in issues)


class TestPriceInversion:
    def test_entry_zone_inverted(self):
        v = ScenarioValidator()
        r = make_record(
            entry_price_low=Decimal("1.0900"),
            entry_price_high=Decimal("1.0800"),
        )
        valid, issues, score = v.validate(r)
        assert any("逆転" in i.message for i in issues)


class TestLongSL:
    def test_long_sl_above_entry(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.LONG,
            entry_price_low=Decimal("1.0850"),
            stop_loss=Decimal("1.0860"),
        )
        valid, issues, score = v.validate(r)
        assert any("SLがエントリー" in i.message for i in issues)


class TestLongTP:
    def test_long_tp_below_entry(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.LONG,
            entry_price_low=Decimal("1.0850"),
            entry_price_high=Decimal("1.0860"),
            take_profit_1=Decimal("1.0850"),
        )
        valid, issues, score = v.validate(r)
        assert any("TP1がエントリー" in i.message for i in issues)


class TestShortSL:
    def test_short_sl_below_entry(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.SHORT,
            entry_price_high=Decimal("1.0860"),
            stop_loss=Decimal("1.0850"),
        )
        valid, issues, score = v.validate(r)
        assert any("SLがエントリー" in i.message for i in issues)


class TestShortTP:
    def test_short_tp_above_entry(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.SHORT,
            entry_price_low=Decimal("1.0850"),
            entry_price_high=Decimal("1.0860"),
            take_profit_1=Decimal("1.0860"),
        )
        valid, issues, score = v.validate(r)
        assert any("TP1がエントリー" in i.message for i in issues)


class TestTimeInversion:
    def test_valid_until_before_from(self):
        v = ScenarioValidator()
        r = make_record(
            scenario_valid_from=datetime(2024, 1, 16, 8, 0, 0),
            scenario_valid_until=datetime(2024, 1, 15, 8, 0, 0),
        )
        valid, issues, score = v.validate(r)
        assert any("期限逆転" in i.message for i in issues)


class TestTimezoneMix:
    def test_aware_and_naive(self):
        v = ScenarioValidator()
        r = make_record(
            published_at=datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc),
            scenario_valid_from=datetime(2024, 1, 15, 9, 0, 0),
        )
        valid, issues, score = v.validate(r)
        assert any("timezone混在" in i.message for i in issues)


class TestUnknownDirection:
    def test_unknown_with_price(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.UNKNOWN,
            entry_price_low=Decimal("1.0850"),
        )
        valid, issues, score = v.validate(r)
        assert any("UNKNOWN" in i.message for i in issues)

    def test_both_no_sl_check(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.BOTH,
            entry_price_low=Decimal("1.0850"),
            stop_loss=Decimal("1.0900"),
        )
        valid, issues, score = v.validate(r)
        # BOTHはSL位置検証をスキップ
        assert not any("SLがエントリー" in i.message for i in issues)

    def test_neutral_no_sl_check(self):
        v = ScenarioValidator()
        r = make_record(
            direction=Direction.NEUTRAL,
            entry_price_low=Decimal("1.0850"),
            stop_loss=Decimal("1.0800"),
        )
        valid, issues, score = v.validate(r)
        # NEUTRALもスキップ
        assert not any("SLがエントリー" in i.message for i in issues)


class TestDuplicates:
    def test_exact_duplicate(self):
        v = ScenarioValidator()
        records = [
            make_record(record_id="R1"),
            make_record(record_id="R1"),
        ]
        exact, _ = v.check_duplicates(records)
        assert len(exact) == 1

    def test_candidate_duplicate(self):
        v = ScenarioValidator()
        records = [
            make_record(record_id="R1", source_id="S1", scenario_date=date(2024,1,15), symbol="EURUSD"),
            make_record(record_id="R2", source_id="S1", scenario_date=date(2024,1,15), symbol="EURUSD"),
        ]
        _, candidates = v.check_duplicates(records)
        assert len(candidates) == 1

    def test_different_source_not_duplicate(self):
        v = ScenarioValidator()
        records = [
            make_record(record_id="R1", source_id="S1", scenario_date=date(2024,1,15), symbol="EURUSD"),
            make_record(record_id="R2", source_id="S2", scenario_date=date(2024,1,15), symbol="EURUSD"),
        ]
        _, candidates = v.check_duplicates(records)
        assert len(candidates) == 0


class TestScoreBounds:
    def test_score_minimum_0(self):
        v = ScenarioValidator()
        r = make_record(
            record_id="",
            source_id="",
            symbol="",
            original_text="",
            entry_price_low=Decimal("1.0900"),
            entry_price_high=Decimal("1.0800"),
            direction=Direction.LONG,
            stop_loss=Decimal("1.0860"),
        )
        valid, issues, score = v.validate(r)
        assert score == 0
        assert score >= 0

    def test_score_maximum_100(self):
        v = ScenarioValidator()
        r = make_record()
        valid, issues, score = v.validate(r)
        assert score <= 100


class TestHumanReviewStatus:
    def test_updated_on_issues(self):
        v = ScenarioValidator()
        r = make_record(direction=Direction.LONG, stop_loss=Decimal("1.0900"), entry_price_low=Decimal("1.0850"))
        valid, issues, score = v.validate(r)
        assert r.human_review_status == HumanReviewStatus.PENDING


class TestMissingFieldsUpdate:
    def test_missing_required_updated(self):
        v = ScenarioValidator()
        r = make_record(symbol="")
        v.validate(r)
        assert r.missing_required_fields is not None
        assert "symbol" in r.missing_required_fields


class TestDuplicateFlag:
    def test_flag_updated(self):
        bv = BatchValidator()
        records = [
            make_record(record_id="R1", source_id="S1", scenario_date=date(2024,1,15), symbol="EURUSD"),
            make_record(record_id="R2", source_id="S1", scenario_date=date(2024,1,15), symbol="EURUSD"),
        ]
        bv.validate_batch(records)
        r2 = [r for r in records if r.record_id == "R2"][0]
        assert r2.duplicate_flag is True


class TestIntegration:
    def test_with_journal(self):
        from scenario_journal import ScenarioJournal
        j = ScenarioJournal()
        r = make_record(record_id="INT-001")
        j.add_record(r)
        v = ScenarioValidator()
        valid, issues, score = v.validate(r)
        assert score >= 0
        assert score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
