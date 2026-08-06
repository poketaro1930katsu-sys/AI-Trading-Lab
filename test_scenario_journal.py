"""
Tests for scenario_journal.py
"""
import pytest
import sys
import tempfile
import os
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, "/mnt/agents/output/AI_Trading_Lab_v1_2")

from scenario_journal import ScenarioJournal
from scenario_models import (
    ScenarioRecord, ScenarioEvaluationInput,
    Direction, ResultClassification, HumanReviewStatus
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
    )
    defaults.update(kwargs)
    return ScenarioRecord(**defaults)


class TestAddAndGet:
    def test_add_and_get(self):
        j = ScenarioJournal()
        r = make_record(1)
        j.add_record(r)
        assert j.get_by_id("REC-001") == r

    def test_duplicate_rejected(self):
        j = ScenarioJournal()
        j.add_record(make_record(1))
        with pytest.raises(ValueError, match="重複record_id"):
            j.add_record(make_record(1))


class TestQuery:
    def test_query_symbol(self):
        j = ScenarioJournal()
        j.add_record(make_record(1, symbol="EURUSD"))
        j.add_record(make_record(2, symbol="EURUSD"))
        j.add_record(make_record(3, symbol="USDJPY"))
        assert len(j.query(symbol="EURUSD")) == 2
        assert len(j.query(symbol="USDJPY")) == 1

    def test_query_direction(self):
        j = ScenarioJournal()
        j.add_record(make_record(1, direction=Direction.LONG))
        j.add_record(make_record(2, direction=Direction.SHORT))
        assert len(j.query(direction=Direction.LONG)) == 1
        assert len(j.query(direction=Direction.SHORT)) == 1

    def test_query_result(self):
        j = ScenarioJournal()
        j.add_record(make_record(1, result_classification=ResultClassification.WIN))
        j.add_record(make_record(2, result_classification=ResultClassification.LOSS))
        assert len(j.query(result=ResultClassification.WIN)) == 1

    def test_query_evaluated_only(self):
        j = ScenarioJournal()
        j.add_record(make_record(1, result_classification=ResultClassification.WIN))
        j.add_record(make_record(2, result_classification=ResultClassification.NOT_EVALUATED))
        assert len(j.query(evaluated_only=True)) == 1

    def test_query_date_range(self):
        j = ScenarioJournal()
        j.add_record(make_record(1, scenario_date=date(2024, 1, 10)))
        j.add_record(make_record(2, scenario_date=date(2024, 1, 20)))
        assert len(j.query(date_from=date(2024, 1, 15))) == 1
        assert len(j.query(date_to=date(2024, 1, 15))) == 1


class TestSaveLoad:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ScenarioJournal(data_dir=tmpdir)
            j.add_record(make_record(1, symbol="EURUSD"))
            j.add_record(make_record(2, symbol="USDJPY"))
            path = j.save()
            assert os.path.exists(path)

            j2 = ScenarioJournal(data_dir=tmpdir)
            j2.load(path)
            assert len(j2.batch) == 2
            assert j2.get_by_id("REC-001").symbol == "EURUSD"
            assert j2.get_by_id("REC-002").symbol == "USDJPY"


class TestUpdateEvaluation:
    def test_update_success(self):
        j = ScenarioJournal()
        j.add_record(make_record(1))
        ev = ScenarioEvaluationInput(
            record_id="REC-001",
            entry_triggered=True,
            tp1_reached=True,
            result_classification=ResultClassification.WIN,
            realized_r_multiple=Decimal("2.5"),
        )
        assert j.update_evaluation(ev) is True
        r = j.get_by_id("REC-001")
        assert r.entry_triggered is True
        assert r.result_classification == ResultClassification.WIN
        assert r.realized_r_multiple == Decimal("2.5")
        assert r.evaluation_completed_at is not None

    def test_update_not_found(self):
        j = ScenarioJournal()
        ev = ScenarioEvaluationInput(record_id="NONEXISTENT")
        assert j.update_evaluation(ev) is False


class TestStatisticsReady:
    def test_filter(self):
        j = ScenarioJournal()
        j.add_record(make_record(1, result_classification=ResultClassification.WIN, data_quality_score=80))
        j.add_record(make_record(2, result_classification=ResultClassification.NOT_EVALUATED, data_quality_score=80))
        j.add_record(make_record(3, result_classification=ResultClassification.WIN, data_quality_score=30))
        ready = j.get_statistics_ready()
        assert len(ready) == 1
        assert ready[0].record_id == "REC-001"


class TestExportSummary:
    def test_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ScenarioJournal(data_dir=tmpdir)
            j.add_record(make_record(1))
            path = j.export_summary()
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
            assert len(lines) == 2  # header + 1 data
            assert "record_id" in lines[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
