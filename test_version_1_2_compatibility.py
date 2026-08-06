"""
Version 1.2 互換性テスト
Version 1.3環境でVersion 1.2の機能が正常に動作することを確認
"""
import pytest
import sys
import os

# Version 1.3のパス
sys.path.insert(0, "/mnt/agents/output/AI_Trading_Lab_v1_3")

from scenario_models import (
    ScenarioRecord, ScenarioBatch, ScenarioInput, ScenarioEvaluationInput,
    Direction, EntryType, MarketSession, ResultClassification,
    HumanReviewStatus, SourceType
)
from scenario_parser import (
    ScenarioParser, CSVScenarioParser, JSONScenarioParser,
    TextScenarioExtractor, TypeConverter
)
from scenario_journal import ScenarioJournal
from scenario_validator import ScenarioValidator, BatchValidator, ValidationIssue
from scenario_statistics import (
    ScenarioStatistics, wilson_ci, sample_size_status,
    StatisticsResult, WilsonCI, SampleSizeStatus, QualityMetrics
)
from scenario_report import ScenarioReport


class TestV12ModelsCompatibility:
    """Module 1: データモデル"""
    def test_scenario_record_creation(self):
        from datetime import datetime, date
        from decimal import Decimal
        r = ScenarioRecord(
            record_id="REC-001",
            source_id="SRC-001",
            scenario_date=date(2024, 1, 15),
            published_at=datetime(2024, 1, 15, 8, 0, 0),
            symbol="EURUSD",
            direction=Direction.LONG,
        )
        assert r.symbol == "EURUSD"
        assert r.direction == "LONG"  # Pydantic use_enum_values

    def test_scenario_batch_filter(self):
        from datetime import datetime, date
        batch = ScenarioBatch()
        batch.add_record(ScenarioRecord(
            record_id="R1", source_id="S1", scenario_date=date.today(),
            published_at=datetime.now(), symbol="EURUSD", direction=Direction.LONG
        ))
        assert len(batch.filter_by_symbol("EURUSD")) == 1


class TestV12ParserCompatibility:
    """Module 2: パーサー"""
    def test_parser_import(self):
        parser = ScenarioParser()
        assert parser is not None

    def test_type_converter(self):
        assert TypeConverter.to_decimal("1.0850") is not None
        assert TypeConverter.to_bool("true") is True


class TestV12JournalCompatibility:
    """Module 3: ジャーナル"""
    def test_journal_add_and_query(self):
        from datetime import datetime, date
        j = ScenarioJournal()
        j.add_record(ScenarioRecord(
            record_id="R1", source_id="S1", scenario_date=date.today(),
            published_at=datetime.now(), symbol="EURUSD"
        ))
        assert len(j.query(symbol="EURUSD")) == 1

    def test_journal_save_load(self):
        import tempfile
        from datetime import datetime, date
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ScenarioJournal(data_dir=tmpdir)
            j.add_record(ScenarioRecord(
                record_id="R1", source_id="S1", scenario_date=date.today(),
                published_at=datetime.now(), symbol="EURUSD"
            ))
            path = j.save()
            assert os.path.exists(path)


class TestV12ValidatorCompatibility:
    """Module 4: 検証"""
    def test_validator_basic(self):
        from datetime import datetime, date
        from decimal import Decimal
        v = ScenarioValidator()
        r = ScenarioRecord(
            record_id="R1", source_id="S1", scenario_date=date.today(),
            published_at=datetime.now(), symbol="EURUSD",
            direction=Direction.LONG,
            entry_price_low=Decimal("1.0850"),
            entry_price_high=Decimal("1.0860"),
            stop_loss=Decimal("1.0800"),
            take_profit_1=Decimal("1.0900"),
            original_text="Test"
        )
        valid, issues, score = v.validate(r)
        assert score >= 0
        assert score <= 100


class TestV12StatisticsCompatibility:
    """Module 5: 統計"""
    def test_wilson_ci(self):
        ci = wilson_ci(5, 10)
        assert 0 <= ci.lower <= ci.upper <= 1.0

    def test_sample_size_status(self):
        s = sample_size_status(15)
        assert s.display_allowed is False

    def test_statistics_summarize(self):
        from datetime import datetime, date
        records = [
            ScenarioRecord(
                record_id=f"R{i}", source_id=f"S{i}", scenario_date=date.today(),
                published_at=datetime.now(), symbol="EURUSD",
                direction=Direction.LONG,
                result_classification=ResultClassification.WIN if i < 5 else ResultClassification.LOSS,
                entry_triggered=True, data_quality_score=80
            )
            for i in range(10)
        ]
        stats = ScenarioStatistics(records)
        result = stats.summarize()
        assert result.total == 10


class TestV12ReportCompatibility:
    """Module 6: レポート"""
    def test_report_generation(self, tmp_path):
        from datetime import datetime, date
        records = [
            ScenarioRecord(
                record_id="R1", source_id="S1", scenario_date=date.today(),
                published_at=datetime.now(), symbol="EURUSD",
                result_classification=ResultClassification.WIN, entry_triggered=True
            )
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        paths = r.generate_all(records)
        assert os.path.exists(paths["data_quality_report"])
        assert os.path.exists(paths["analysis_report"])
        assert os.path.exists(paths["summary_csv"])


class TestV13NewFiles:
    """Module 1.3: 新規ファイルの存在確認"""
    def test_pb_template_exists(self):
        assert os.path.exists("/mnt/agents/output/AI_Trading_Lab_v1_3/config/pb_source_template.json")

    def test_discovery_guide_exists(self):
        assert os.path.exists("/mnt/agents/output/AI_Trading_Lab_v1_3/PB_LOG_DISCOVERY_GUIDE.md")

    def test_mapping_spec_exists(self):
        assert os.path.exists("/mnt/agents/output/AI_Trading_Lab_v1_3/PB_DATA_MAPPING_SPEC.md")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
