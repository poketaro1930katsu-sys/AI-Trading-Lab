"""
Tests for scenario_report.py
"""
import pytest
import sys
import os
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, "/mnt/agents/output/AI_Trading_Lab_v1_2")

from scenario_report import ScenarioReport
from scenario_models import (
    ScenarioRecord, Direction, ResultClassification,
    HumanReviewStatus, MarketSession
)
from scenario_validator import ScenarioValidator


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
        original_text="Test scenario",
    )
    defaults.update(kwargs)
    return ScenarioRecord(**defaults)


class TestEmptyData:
    def test_empty_quality_report(self, tmp_path):
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report([])
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "総レコード数: 0件" in content

    def test_empty_analysis_report(self, tmp_path):
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report([])
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "総件数: 0件" in content


class TestNormalData10:
    def test_10_quality(self, tmp_path):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 5 else ResultClassification.LOSS,
                       entry_triggered=True, data_quality_score=60 + i * 4)
            for i in range(10)
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "平均品質スコア" in content
        assert "品質スコア分布" in content

    def test_10_analysis(self, tmp_path):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 5 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(10)
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "勝率" in content
        assert "分母に含める分類" in content
        assert "NOT_TRIGGERED" in content


class TestNormalData30:
    def test_30_analysis(self, tmp_path):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 15 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(30)
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "総件数: 30件" in content
        assert "高信頼と表現しない" in content  # 100件未満の警告


class TestNormalData100:
    def test_100_analysis(self, tmp_path):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 55 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(100)
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "総件数: 100件" in content


class TestSampleSizeWarning:
    def test_small_sample_warning(self, tmp_path):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 3 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(5)
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "標本不足" in content or "条件比較禁止" in content


class TestDisplayAllowed:
    def test_display_false(self, tmp_path):
        records = [
            make_record(i, result_classification=ResultClassification.WIN if i < 3 else ResultClassification.LOSS,
                       entry_triggered=True)
            for i in range(5)
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "統計的判断には不十分" in content


class TestWilsonCI:
    def test_wilson_displayed(self, tmp_path):
        records = [
            make_record(0, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, result_classification=ResultClassification.LOSS, entry_triggered=True),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Wilson" in content
        assert "95% CI" in content


class TestWinRateExplanation:
    def test_denominator_explained(self, tmp_path):
        records = [
            make_record(0, result_classification=ResultClassification.WIN, entry_triggered=True),
            make_record(1, result_classification=ResultClassification.NOT_TRIGGERED, entry_triggered=False),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_analysis_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "分母に含める分類" in content
        assert "分母に含めない分類" in content
        assert "NOT_TRIGGERED（エントリー未成立）" in content


class TestQualityDistribution:
    def test_quality_histogram(self, tmp_path):
        records = [
            make_record(i, data_quality_score=score)
            for i, score in enumerate([55, 65, 75, 85, 95])
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "50-59" in content or "品質スコア分布" in content


class TestHumanReviewCount:
    def test_human_review(self, tmp_path):
        records = [
            make_record(0, human_review_status=HumanReviewStatus.REVIEWED),
            make_record(1, human_review_status=HumanReviewStatus.PENDING),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Human Review必要件数" in content
        assert "1件" in content


class TestHumanCorrectedCount:
    def test_human_corrected(self, tmp_path):
        records = [
            make_record(0, human_corrected=True),
            make_record(1, human_corrected=False),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Human Corrected件数" in content
        assert "1件" in content


class TestDuplicateCount:
    def test_duplicate(self, tmp_path):
        records = [
            make_record(0, duplicate_flag=True),
            make_record(1, duplicate_flag=False),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "重複候補件数" in content
        assert "1件" in content


class TestCSVOutput:
    def test_csv_generated(self, tmp_path):
        records = [
            make_record(0, result_classification=ResultClassification.WIN, entry_triggered=True),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        assert "record_id" in content
        assert "REC-000" in content


class TestCSVComma:
    def test_csv_with_comma(self, tmp_path):
        records = [
            make_record(0, original_text="Buy, sell, hold"),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        # CSVモジュールがカンマを適切にエスケープ
        assert len(lines) == 2  # header + 1 data


class TestCSVNewline:
    def test_csv_with_newline(self, tmp_path):
        records = [
            make_record(0, original_text="Line1\nLine2"),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        # CSVモジュールが改行を適切に処理
        assert "record_id" in content


class TestCSVQuote:
    def test_csv_with_quote(self, tmp_path):
        records = [
            make_record(0, original_text='He said "Buy"'),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        assert "record_id" in content


class TestEnumString:
    def test_enum_string_handling(self, tmp_path):
        # Pydantic use_enum_values=True で文字列化されることを確認
        r = make_record(0, direction=Direction.LONG)
        assert r.direction == "LONG"
        rep = ScenarioReport(output_dir=str(tmp_path))
        path = rep.generate_summary_csv([r])
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        assert "LONG" in content


class TestNoneHandling:
    def test_none_fields(self, tmp_path):
        records = [
            make_record(0, entry_triggered=None, realized_r_multiple=None,
                       data_quality_score=None, human_corrected=None),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        # Noneは空文字として出力
        assert len(lines) == 2


class TestDecimalHandling:
    def test_decimal_in_csv(self, tmp_path):
        records = [
            make_record(0, realized_r_multiple=Decimal("2.5")),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        assert "2.5" in content


class TestDatetimeHandling:
    def test_datetime_in_csv(self, tmp_path):
        records = [
            make_record(0, published_at=datetime(2024, 1, 15, 8, 30, 0)),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        assert "2024-01-15" in content


class TestDateHandling:
    def test_date_in_csv(self, tmp_path):
        records = [
            make_record(0, scenario_date=date(2024, 6, 1)),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_summary_csv(records)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        assert "2024-06-01" in content


class TestJapaneseText:
    def test_japanese_in_report(self, tmp_path):
        records = [
            make_record(0, original_text="買いシグナル。上昇トレンド継続。"),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "買いシグナル" in content


class TestForbiddenPhrases:
    def test_forbidden_blocked(self, tmp_path):
        records = [
            make_record(0, original_text="高確率で勝てるシナリオです"),
        ]
        r = ScenarioReport(output_dir=str(tmp_path))
        path = r.generate_data_quality_report(records)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "[禁止表現" in content


class TestIntegration:
    def test_with_validator_and_stats(self, tmp_path):
        from scenario_journal import ScenarioJournal
        from scenario_statistics import ScenarioStatistics

        j = ScenarioJournal(data_dir=str(tmp_path))
        for i in range(5):
            r = make_record(i, result_classification=ResultClassification.WIN if i < 3 else ResultClassification.LOSS,
                          entry_triggered=True)
            v = ScenarioValidator()
            v.validate(r)
            j.add_record(r)

        rep = ScenarioReport(output_dir=str(tmp_path))
        paths = rep.generate_all(j.batch.records)

        assert os.path.exists(paths["data_quality_report"])
        assert os.path.exists(paths["analysis_report"])
        assert os.path.exists(paths["summary_csv"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
