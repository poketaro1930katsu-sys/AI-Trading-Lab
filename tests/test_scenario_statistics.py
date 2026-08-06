"""
Tests for scenario_statistics.py
"""
import pytest
import sys
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, "/mnt/agents/output/AI_Trading_Lab_v1_2")

from scenario_statistics import (
    ScenarioStatistics, wilson_ci, sample_size_status,
    StatisticsResult, WilsonCI, SampleSizeStatus, QualityMetrics
)
from scenario_models import (
    ScenarioRecord, Direction, ResultClassification, MarketSession
)


def make_record(i, **kwargs):
    defaults = dict(
        record_id=f"REC-{i:03d}",
        source_id=f"SRC-{i:03d}",
        scenario_date=date(2024, 1, 15),
        published_at=datetime(2024, 1, 15, 8, 0, 0),
        symbol="EURUSD",
        direction=Direction.LONG,
        data_quality_score=80,
        result_classification=ResultClassification.NOT_EVALUATED,
        entry_triggered=None,
    )
    defaults.update(kwargs)
    return ScenarioRecord(**defaults)


class TestWilsonCI:
    def test_wilson_basic(self):
        ci = wilson_ci(5, 10)
        assert 0 <= ci.lower <= ci.point_estimate <= ci.upper <= 1.0
        assert ci.n == 10
        assert ci.k == 5

    def test_wilson_zero(self):
        ci = wilson_ci(0, 0)
        assert ci.lower == 0.0
        assert ci.upper == 0.0

    def test_wilson_all_success(self):
        ci = wilson_ci(10, 10)
        assert ci.lower < ci.upper
        assert ci.point_estimate == 1.0


class TestSampleSizeStatus:
    def test_forbidden(self):
        s = sample_size_status(15)
        assert s.status == "forbidden"
        assert s.display_allowed is False
        assert s.comparison_allowed is False
        assert "条件比較禁止" in s.warning

    def test_reference(self):
        s = sample_size_status(25)
        assert s.status == "reference"
        assert s.display_allowed is True
        assert s.comparison_allowed is False
        assert "参考値" in s.warning

    def test_caution(self):
        s = sample_size_status(50)
        assert s.status == "caution"
        assert s.display_allowed is True
        assert s.comparison_allowed is True
        assert "高信頼" in s.warning

    def test_normal(self):
        s = sample_size_status(150)
        assert s.status == "normal"
        assert s.display_allowed is True
        assert s.comparison_allowed is True
        assert s.warning == ""


class TestEmptyData:
    def test_empty(self):
        stats = ScenarioStatistics([])
        result = stats.summarize()
        assert result.total == 0
        assert result.win_rate is None
        assert len(result.warnings) > 0


class TestOneRecord:
    def test_one(self):
        stats = ScenarioStatistics([make_record(1, result_classification=ResultClassification.WIN, entry_triggered=True)])
        result = stats.summarize()
        assert result.total == 1
        assert result.evaluated == 1
        assert result.win_rate == 1.0


class TestTenRecords:
    def test_ten(self):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 5 else ResultClassification.LOSS,
                       entry_triggered=True, data_quality_score=70 + i)
            for i in range(10)
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.total == 10
        assert result.win_rate == 0.5
        assert result.win_rate_eligible_n == 10
        assert result.win_rate_sample_status.status == "forbidden"
        assert result.entry_rate == 1.0
        assert result.quality_metrics.count == 10


class TestThirtyRecords:
    def test_thirty(self):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 15 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(30)
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.total == 30
        assert result.win_rate == 0.5
        assert result.win_rate_sample_status.status == "caution"
        assert result.win_rate_ci is not None
        assert result.win_rate_ci.lower < result.win_rate_ci.upper


class TestHundredRecords:
    def test_hundred(self):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 55 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(100)
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.total == 100
        assert result.win_rate == 0.55
        assert result.win_rate_sample_status.status == "normal"
        assert result.win_rate_sample_status.display_allowed is True


class TestWinRateDenominator:
    def test_excludes_not_triggered(self):
        records = [
            make_record(0, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, result_classification=ResultClassification.LOSS, entry_triggered=True),
            make_record(2, result_classification=ResultClassification.NOT_TRIGGERED, entry_triggered=False),
            make_record(3, result_classification=ResultClassification.INVALIDATED_BEFORE_ENTRY, entry_triggered=False),
            make_record(4, result_classification=ResultClassification.EXPIRED, entry_triggered=False),
            make_record(5, result_classification=ResultClassification.AMBIGUOUS, entry_triggered=True),
            make_record(6, result_classification=ResultClassification.NOT_EVALUATED, entry_triggered=None),
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        # WIN + LOSS = 2 が母数。NOT_TRIGGERED等は含めない
        assert result.win_rate_eligible_n == 2
        assert result.win_rate == 0.5

    def test_includes_partial(self):
        records = [
            make_record(0, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, result_classification=ResultClassification.PARTIAL_WIN, entry_triggered=True),
            make_record(2, result_classification=ResultClassification.PARTIAL_LOSS, entry_triggered=True),
            make_record(3, result_classification=ResultClassification.LOSS, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.win_rate_eligible_n == 4
        assert result.win_rate == 0.375  # (1 + 0.5) / 4


class TestEntryRate:
    def test_entry_rate(self):
        records = [
            make_record(0, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, result_classification=ResultClassification.LOSS, entry_triggered=True),
            make_record(2, result_classification=ResultClassification.NOT_TRIGGERED, entry_triggered=False),
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.entry_rate == 2 / 3
        assert result.not_triggered_rate == 1 / 3


class TestAmbiguousRate:
    def test_ambiguous(self):
        records = [
            make_record(0, result_classification=ResultClassification.AMBIGUOUS, entry_triggered=True),
            make_record(1, result_classification=ResultClassification.WIN, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.ambiguous_rate == 0.5


class TestBySymbol:
    def test_by_symbol(self):
        records = [
            make_record(0, symbol="EURUSD", result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, symbol="USDJPY", result_classification=ResultClassification.LOSS, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        eur = stats.by_symbol("EURUSD")
        assert eur.total == 1
        assert eur.win_rate == 1.0


class TestByDirection:
    def test_by_direction(self):
        records = [
            make_record(0, direction=Direction.LONG, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, direction=Direction.SHORT, result_classification=ResultClassification.LOSS, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        long_stats = stats.by_direction(Direction.LONG)
        assert long_stats.total == 1
        assert long_stats.direction_counts.get("LONG") == 1


class TestBySource:
    def test_by_source(self):
        records = [
            make_record(0, source_id="S1", result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, source_id="S2", result_classification=ResultClassification.LOSS, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        s1 = stats.by_source("S1")
        assert s1.total == 1
        assert s1.source_counts.get("S1") == 1


class TestBySession:
    def test_by_session(self):
        records = [
            make_record(0, market_session=MarketSession.TOKYO, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, market_session=MarketSession.LONDON, result_classification=ResultClassification.LOSS, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        tokyo = stats.by_session(MarketSession.TOKYO)
        assert tokyo.total == 1
        assert tokyo.session_counts.get("TOKYO") == 1


class TestByTimeframe:
    def test_by_timeframe(self):
        records = [
            make_record(0, timeframe="1H", result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, timeframe="4H", result_classification=ResultClassification.LOSS, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        h1 = stats.by_timeframe("1H")
        assert h1.total == 1
        assert h1.timeframe_counts.get("1H") == 1


class TestQualityMetrics:
    def test_quality_histogram(self):
        records = [
            make_record(i, data_quality_score=score, result_classification=ResultClassification.WIN, entry_triggered=True)
            for i, score in enumerate([55, 65, 75, 85, 95])
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.quality_metrics.count == 5
        assert result.quality_metrics.mean == 75.0
        assert result.quality_metrics.median == 75
        assert result.quality_metrics.minimum == 55
        assert result.quality_metrics.maximum == 95
        assert "50-59" in result.quality_metrics.histogram
        assert "90-99" in result.quality_metrics.histogram

    def test_quality_std_dev(self):
        records = [
            make_record(i, data_quality_score=score, result_classification=ResultClassification.WIN, entry_triggered=True)
            for i, score in enumerate([80, 80, 80, 90, 90])
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.quality_metrics.std_dev is not None
        assert result.quality_metrics.std_dev >= 0


class TestDisplayAllowed:
    def test_display_false(self):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 3 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(5)
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.win_rate_sample_status.display_allowed is False
        assert result.win_rate_sample_status.comparison_allowed is False

    def test_display_true(self):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 30 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(50)
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.win_rate_sample_status.display_allowed is True


class TestWarning:
    def test_small_sample_warning(self):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 5 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(10)
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert any("母数" in w.message for w in result.warnings)


class TestHumanRates:
    def test_human_review_rate(self):
        records = [
            make_record(0, human_review_status=__import__("scenario_models").HumanReviewStatus.REVIEWED,
                       result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, human_review_status=__import__("scenario_models").HumanReviewStatus.PENDING,
                       result_classification=ResultClassification.WIN, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.human_review_rate == 0.5

    def test_human_corrected_rate(self):
        records = [
            make_record(0, human_corrected=True, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, human_corrected=False, result_classification=ResultClassification.WIN, entry_triggered=True),
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.human_corrected_rate == 0.5


class TestIntegration:
    def test_with_journal_and_validator(self):
        from scenario_journal import ScenarioJournal
        from scenario_validator import ScenarioValidator

        j = ScenarioJournal()
        for i in range(5):
            r = make_record(i, result_classification=ResultClassification.WIN if i < 3 else ResultClassification.LOSS,
                          entry_triggered=True)
            v = ScenarioValidator()
            v.validate(r)
            j.add_record(r)

        stats = ScenarioStatistics(j.batch.records)
        result = stats.summarize()
        assert result.total == 5
        assert result.win_rate is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
