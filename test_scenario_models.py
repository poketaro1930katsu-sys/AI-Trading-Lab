"""
Tests for scenario_models.py
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

# モジュールパスを追加
import sys
sys.path.insert(0, "/mnt/agents/output/AI_Trading_Lab_v1_2")

from scenario_models import (
    Direction, EntryType, MarketSession, ResultClassification,
    HumanReviewStatus, SourceType,
    ScenarioRecord, ScenarioBatch, ScenarioInput, ScenarioEvaluationInput
)


class TestEnums:
    def test_direction_values(self):
        assert Direction.LONG == "LONG"
        assert Direction.SHORT == "SHORT"
        assert Direction.BOTH == "BOTH"
        assert Direction.NEUTRAL == "NEUTRAL"
        assert Direction.UNKNOWN == "UNKNOWN"

    def test_entry_type_values(self):
        assert EntryType.MARKET == "MARKET"
        assert EntryType.CONDITIONAL == "CONDITIONAL"

    def test_result_classification_values(self):
        assert ResultClassification.WIN == "WIN"
        assert ResultClassification.NOT_EVALUATED == "NOT_EVALUATED"
        assert ResultClassification.INVALIDATED_BEFORE_ENTRY == "INVALIDATED_BEFORE_ENTRY"


class TestScenarioRecord:
    def test_create_minimal(self):
        record = ScenarioRecord(
            record_id=str(uuid4()),
            source_id="SRC001",
            scenario_date=date(2024, 1, 15),
            published_at=datetime(2024, 1, 15, 8, 0, 0),
            symbol="EURUSD",
            direction=Direction.LONG,
        )
        assert record.symbol == "EURUSD"
        assert record.direction == "LONG"
        assert record.result_classification == "NOT_EVALUATED"
        assert record.is_evaluated() is False

    def test_create_full(self):
        record = ScenarioRecord(
            record_id="REC-001",
            source_id="SRC001",
            scenario_date=date(2024, 1, 15),
            published_at=datetime(2024, 1, 15, 8, 0, 0),
            symbol="EURUSD",
            direction=Direction.SHORT,
            entry_type=EntryType.LIMIT,
            entry_price_low=Decimal("1.0850"),
            entry_price_high=Decimal("1.0860"),
            stop_loss=Decimal("1.0900"),
            take_profit_1=Decimal("1.0800"),
            original_text="Sell EURUSD at 1.0850-60",
            parser_confidence=85,
            data_quality_score=90,
        )
        assert record.entry_price_low == Decimal("1.0850")
        zone = record.get_entry_zone()
        assert zone == (Decimal("1.0850"), Decimal("1.0860"))

    def test_score_validation(self):
        with pytest.raises(ValueError):
            ScenarioRecord(
                record_id="REC-002",
                source_id="SRC002",
                scenario_date=date.today(),
                published_at=datetime.now(),
                symbol="USDJPY",
                parser_confidence=150,  # 範囲外
            )

    def test_negative_score_validation(self):
        with pytest.raises(ValueError):
            ScenarioRecord(
                record_id="REC-003",
                source_id="SRC003",
                scenario_date=date.today(),
                published_at=datetime.now(),
                symbol="GBPUSD",
                data_quality_score=-10,
            )

    def test_is_evaluated(self):
        record = ScenarioRecord(
            record_id="REC-004",
            source_id="SRC004",
            scenario_date=date.today(),
            published_at=datetime.now(),
            symbol="AUDUSD",
            result_classification=ResultClassification.WIN,
        )
        assert record.is_evaluated() is True

    def test_entry_zone_single_price(self):
        record = ScenarioRecord(
            record_id="REC-005",
            source_id="SRC005",
            scenario_date=date.today(),
            published_at=datetime.now(),
            symbol="USDCAD",
            entry_price_low=Decimal("1.3500"),
        )
        zone = record.get_entry_zone()
        assert zone == (Decimal("1.3500"), Decimal("1.3500"))

    def test_entry_zone_none(self):
        record = ScenarioRecord(
            record_id="REC-006",
            source_id="SRC006",
            scenario_date=date.today(),
            published_at=datetime.now(),
            symbol="XAUUSD",
        )
        assert record.get_entry_zone() is None

    def test_to_flat_dict(self):
        record = ScenarioRecord(
            record_id="REC-007",
            source_id="SRC007",
            scenario_date=date(2024, 6, 1),
            published_at=datetime(2024, 6, 1, 12, 0),
            symbol="BTCUSD",
            direction=Direction.LONG,
        )
        d = record.to_flat_dict()
        assert d["symbol"] == "BTCUSD"
        assert d["direction"] == "LONG"
        assert isinstance(d["scenario_date"], str)


class TestScenarioBatch:
    def test_add_and_filter(self):
        batch = ScenarioBatch(batch_id="BATCH-01")

        r1 = ScenarioRecord(
            record_id="R1", source_id="S1", scenario_date=date.today(),
            published_at=datetime.now(), symbol="EURUSD", direction=Direction.LONG,
            result_classification=ResultClassification.WIN,
        )
        r2 = ScenarioRecord(
            record_id="R2", source_id="S2", scenario_date=date.today(),
            published_at=datetime.now(), symbol="USDJPY", direction=Direction.SHORT,
            result_classification=ResultClassification.NOT_EVALUATED,
        )
        r3 = ScenarioRecord(
            record_id="R3", source_id="S1", scenario_date=date.today(),
            published_at=datetime.now(), symbol="EURUSD", direction=Direction.LONG,
            result_classification=ResultClassification.LOSS,
        )

        batch.add_record(r1)
        batch.add_record(r2)
        batch.add_record(r3)

        assert len(batch) == 3
        assert len(batch.filter_by_symbol("EURUSD")) == 2
        assert len(batch.filter_by_direction(Direction.LONG)) == 2
        assert len(batch.filter_evaluated()) == 2
        assert len(batch.filter_pending_evaluation()) == 1
        assert batch.get_by_record_id("R2") == r2
        assert len(batch.get_by_source_id("S1")) == 2


class TestScenarioInput:
    def test_minimal_input(self):
        inp = ScenarioInput(
            source_id="SRC-IN-01",
            scenario_date=date(2024, 3, 15),
            published_at=datetime(2024, 3, 15, 10, 0, 0),
            symbol="EURUSD",
        )
        assert inp.direction == Direction.UNKNOWN


class TestScenarioEvaluationInput:
    def test_evaluation_input(self):
        ev = ScenarioEvaluationInput(
            record_id="REC-EVAL-01",
            entry_triggered=True,
            tp1_reached=True,
            sl_reached=False,
            result_classification=ResultClassification.WIN,
            realized_r_multiple=Decimal("2.5"),
        )
        assert ev.result_classification == ResultClassification.WIN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
