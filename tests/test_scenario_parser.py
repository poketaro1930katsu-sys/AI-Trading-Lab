"""
Tests for scenario_parser.py
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
import json
import tempfile
import os

import sys
sys.path.insert(0, "/mnt/agents/output/AI_Trading_Lab_v1_2")

from scenario_parser import (
    TypeConverter, CSVScenarioParser, JSONScenarioParser,
    TextScenarioExtractor, ScenarioParser
)
from scenario_models import (
    Direction, EntryType, MarketSession, ResultClassification,
    HumanReviewStatus, SourceType, ScenarioBatch
)


class TestTypeConverter:
    def test_to_decimal_valid(self):
        assert TypeConverter.to_decimal("1.0850") == Decimal("1.0850")
        assert TypeConverter.to_decimal(1.0850) == Decimal("1.085")

    def test_to_decimal_none(self):
        assert TypeConverter.to_decimal(None) is None
        assert TypeConverter.to_decimal("") is None

    def test_to_decimal_invalid(self):
        assert TypeConverter.to_decimal("abc") is None

    def test_to_datetime_iso(self):
        dt = TypeConverter.to_datetime("2024-01-15T08:00:00+00:00")
        assert dt.year == 2024
        assert dt.hour == 8

    def test_to_datetime_space(self):
        dt = TypeConverter.to_datetime("2024-01-15 08:00:00")
        assert dt.year == 2024

    def test_to_datetime_none(self):
        assert TypeConverter.to_datetime(None) is None

    def test_to_date(self):
        d = TypeConverter.to_date("2024-01-15")
        assert d == date(2024, 1, 15)

    def test_to_date_from_datetime(self):
        d = TypeConverter.to_date("2024-01-15T08:00:00")
        assert d == date(2024, 1, 15)

    def test_to_bool(self):
        assert TypeConverter.to_bool("true") is True
        assert TypeConverter.to_bool("false") is False
        assert TypeConverter.to_bool("1") is True
        assert TypeConverter.to_bool("0") is False
        assert TypeConverter.to_bool("") is None

    def test_to_enum(self):
        assert TypeConverter.to_enum("LONG", Direction) == Direction.LONG
        assert TypeConverter.to_enum("long", Direction) == Direction.LONG
        assert TypeConverter.to_enum("INVALID", Direction) == Direction.UNKNOWN

    def test_to_string_list(self):
        assert TypeConverter.to_string_list("a, b, c") == ["a", "b", "c"]
        assert TypeConverter.to_string_list(["a", "b"]) == ["a", "b"]


class TestCSVScenarioParser:
    def test_parse_minimal_row(self):
        parser = CSVScenarioParser()
        row = {
            "record_id": "REC-001",
            "source_id": "SRC-001",
            "scenario_date": "2024-01-15",
            "published_at": "2024-01-15T08:00:00+00:00",
            "symbol": "EURUSD",
            "direction": "LONG",
        }
        record, warnings = parser.parse_row(row)
        assert record.symbol == "EURUSD"
        assert record.direction == "LONG"
        assert record.record_id == "REC-001"

    def test_parse_full_row(self):
        parser = CSVScenarioParser()
        row = {
            "record_id": "REC-002",
            "source_id": "SRC-002",
            "scenario_date": "2024-01-15",
            "published_at": "2024-01-15T08:00:00+00:00",
            "symbol": "USDJPY",
            "direction": "SHORT",
            "entry_type": "LIMIT",
            "entry_price_low": "145.00",
            "entry_price_high": "145.50",
            "stop_loss": "146.00",
            "take_profit_1": "144.00",
            "tp1_reached": "true",
            "sl_reached": "false",
            "result_classification": "WIN",
            "parser_confidence": "85",
            "data_quality_score": "90",
        }
        record, warnings = parser.parse_row(row)
        assert record.entry_price_low == Decimal("145.00")
        assert record.tp1_reached is True
        assert record.result_classification == "WIN"
        assert record.parser_confidence == 85

    def test_read_write_csv(self):
        parser = CSVScenarioParser()

        # テスト用CSV作成
        csv_content = """record_id,source_id,scenario_date,published_at,symbol,direction,entry_price_low,entry_price_high,stop_loss,take_profit_1
REC-001,SRC-001,2024-01-15,2024-01-15T08:00:00+00:00,EURUSD,LONG,1.0850,1.0860,1.0900,1.0800
REC-002,SRC-002,2024-01-16,2024-01-16T09:00:00+00:00,USDJPY,SHORT,145.00,145.50,146.00,144.00"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            batch, warnings = parser.read_csv(temp_path)
            assert len(batch) == 2
            assert batch.records[0].symbol == "EURUSD"
            assert batch.records[1].symbol == "USDJPY"

            # 書き出しテスト
            out_path = temp_path.replace(".csv", "_out.csv")
            parser.write_csv(batch, out_path)
            assert os.path.exists(out_path)

            # 再読み込み
            batch2, _ = parser.read_csv(out_path)
            assert len(batch2) == 2
        finally:
            os.unlink(temp_path)
            if os.path.exists(out_path):
                os.unlink(out_path)


class TestJSONScenarioParser:
    def test_read_write_json(self):
        parser = JSONScenarioParser()
        csv_parser = CSVScenarioParser()

        # テスト用JSON作成
        json_data = {
            "records": [
                {
                    "record_id": "REC-001",
                    "source_id": "SRC-001",
                    "scenario_date": "2024-01-15",
                    "published_at": "2024-01-15T08:00:00+00:00",
                    "symbol": "EURUSD",
                    "direction": "LONG",
                },
                {
                    "record_id": "REC-002",
                    "source_id": "SRC-002",
                    "scenario_date": "2024-01-16",
                    "published_at": "2024-01-16T09:00:00+00:00",
                    "symbol": "USDJPY",
                    "direction": "SHORT",
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(json_data, f)
            temp_path = f.name

        try:
            batch, warnings = parser.read_json(temp_path)
            assert len(batch) == 2

            # 書き出しテスト
            out_path = temp_path.replace(".json", "_out.json")
            parser.write_json(batch, out_path)
            assert os.path.exists(out_path)

            with open(out_path) as f:
                data = json.load(f)
            assert data["record_count"] == 2
            assert data["version"] == "1.2"
        finally:
            os.unlink(temp_path)
            if os.path.exists(out_path):
                os.unlink(out_path)


class TestTextScenarioExtractor:
    def test_extract_eurusd_long(self):
        extractor = TextScenarioExtractor()
        text = "Buy EURUSD at 1.0850. Target 1.0900. Stop 1.0800. 4H timeframe."
        published = datetime(2024, 1, 15, 8, 0, 0)
        result = extractor.extract_candidates(text, "SRC-TEXT-001", published)

        assert "EURUSD" in result["candidates"].get("symbol", [])
        assert result["candidates"].get("direction") == Direction.LONG
        assert "4H" in result["candidates"].get("timeframe", [])

    def test_extract_usdjpy_short(self):
        extractor = TextScenarioExtractor()
        text = "Sell USDJPY at 145.00. Target 144.00."
        published = datetime(2024, 1, 15, 8, 0, 0)
        result = extractor.extract_candidates(text, "SRC-TEXT-002", published)

        assert "USDJPY" in result["candidates"].get("symbol", [])
        assert result["candidates"].get("direction") == Direction.SHORT

    def test_extract_no_match(self):
        extractor = TextScenarioExtractor()
        text = "今日はいい天気ですね。"
        published = datetime(2024, 1, 15, 8, 0, 0)
        result = extractor.extract_candidates(text, "SRC-TEXT-003", published)

        assert result["parser_confidence"] == 0
        assert "人間レビューが必要" in result["warnings"][0]


class TestScenarioParser:
    def test_auto_detect_csv(self):
        parser = ScenarioParser()
        csv_content = "record_id,source_id,scenario_date,published_at,symbol,direction\nREC-001,SRC-001,2024-01-15,2024-01-15T08:00:00+00:00,EURUSD,LONG"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            batch, warnings = parser.read(temp_path)
            assert len(batch) == 1
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
