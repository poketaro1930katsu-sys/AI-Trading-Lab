"""
AI Trading Lab v1.2 - Scenario Parser
CSV/JSON/テキストの入出力パーサー

入力方式:
- CSV: 完全対応
- JSON: 完全対応
- テキスト: 候補抽出のみ（自動確定禁止）
- 画像OCR: 将来対応の設計
"""

import csv
import json
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

from scenario_models import (
    ScenarioRecord, ScenarioBatch, ScenarioInput,
    Direction, EntryType, MarketSession, ResultClassification,
    HumanReviewStatus, SourceType
)


# ==========================================
# 型変換ユーティリティ
# ==========================================

class TypeConverter:
    """CSV/JSONの文字列値を適切な型に変換"""

    @staticmethod
    def to_decimal(value: Any) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def to_datetime(value: Any) -> Optional[datetime]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        # ISO 8601形式を優先
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def to_date(value: Any) -> Optional[date]:
        if value is None or value == "":
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y%m%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        # datetimeからdateを抽出
        dt = TypeConverter.to_datetime(value)
        if dt:
            return dt.date()
        return None

    @staticmethod
    def to_bool(value: Any) -> Optional[bool]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("true", "1", "yes", "y", "はい", "有"):
            return True
        if s in ("false", "0", "no", "n", "いいえ", "無"):
            return False
        return None

    @staticmethod
    def to_enum(value: Any, enum_class) -> Any:
        if value is None or value == "":
            return enum_class.UNKNOWN if hasattr(enum_class, "UNKNOWN") else None
        if isinstance(value, enum_class):
            return value
        s = str(value).strip().upper()
        try:
            return enum_class(s)
        except ValueError:
            return enum_class.UNKNOWN if hasattr(enum_class, "UNKNOWN") else None

    @staticmethod
    def to_string_list(value: Any) -> Optional[List[str]]:
        if value is None or value == "":
            return None
        if isinstance(value, list):
            return [str(v) for v in value]
        # カンマ区切り文字列
        s = str(value)
        if "," in s:
            return [x.strip() for x in s.split(",") if x.strip()]
        return [s.strip()] if s.strip() else None


# ==========================================
# CSV Parser
# ==========================================

class CSVScenarioParser:
    """CSV形式のシナリオデータを読み書きするパーサー"""

    FIELD_NAMES = [
        "record_id", "source_id", "scenario_date", "published_at", "timezone",
        "recorded_at", "source_type", "original_text", "source_image_path", "source_url",
        "symbol", "asset_class", "timeframe", "scenario_valid_from", "scenario_valid_until",
        "market_session", "direction", "entry_type", "entry_price_low", "entry_price_high",
        "stop_loss", "take_profit_1", "take_profit_2", "take_profit_3",
        "scenario_summary", "stated_reasons", "important_levels", "invalidation_condition",
        "alternative_scenario", "economic_event_warning", "author_confidence_text",
        "entry_triggered", "entry_triggered_at", "entry_price_actual", "highest_favorable_price",
        "lowest_adverse_price", "tp1_reached", "tp2_reached", "tp3_reached", "sl_reached",
        "invalidation_reached", "scenario_expired", "result_classification", "realized_r_multiple",
        "maximum_favorable_excursion_r", "maximum_adverse_excursion_r", "evaluation_completed_at",
        "evaluation_notes", "missing_required_fields", "ambiguous_fields", "parser_confidence",
        "human_review_status", "human_corrected", "duplicate_flag", "data_quality_score",
        "inferred_fields"
    ]

    TYPE_MAP = {
        "record_id": str, "source_id": str, "timezone": str,
        "original_text": str, "source_image_path": str, "source_url": str,
        "symbol": str, "asset_class": str, "timeframe": str,
        "scenario_summary": str, "stated_reasons": str, "important_levels": str,
        "invalidation_condition": str, "alternative_scenario": str,
        "economic_event_warning": str, "author_confidence_text": str,
        "evaluation_notes": str,
        "scenario_date": "date", "published_at": "datetime", "recorded_at": "datetime",
        "scenario_valid_from": "datetime", "scenario_valid_until": "datetime",
        "entry_triggered_at": "datetime", "evaluation_completed_at": "datetime",
        "entry_price_low": "decimal", "entry_price_high": "decimal",
        "stop_loss": "decimal", "take_profit_1": "decimal",
        "take_profit_2": "decimal", "take_profit_3": "decimal",
        "entry_price_actual": "decimal", "highest_favorable_price": "decimal",
        "lowest_adverse_price": "decimal", "realized_r_multiple": "decimal",
        "maximum_favorable_excursion_r": "decimal", "maximum_adverse_excursion_r": "decimal",
        "entry_triggered": "bool", "tp1_reached": "bool", "tp2_reached": "bool",
        "tp3_reached": "bool", "sl_reached": "bool", "invalidation_reached": "bool",
        "scenario_expired": "bool", "human_corrected": "bool", "duplicate_flag": "bool",
        "parser_confidence": int, "data_quality_score": int,
        "direction": Direction, "entry_type": EntryType,
        "market_session": MarketSession, "result_classification": ResultClassification,
        "human_review_status": HumanReviewStatus, "source_type": SourceType,
        "missing_required_fields": "str_list", "ambiguous_fields": "str_list",
        "inferred_fields": "str_list",
    }

    # 空値時のデフォルト値
    DEFAULTS = {
        "source_type": SourceType.UNKNOWN,
        "market_session": MarketSession.UNKNOWN,
        "direction": Direction.UNKNOWN,
        "entry_type": EntryType.UNKNOWN,
        "result_classification": ResultClassification.NOT_EVALUATED,
        "human_review_status": HumanReviewStatus.PENDING,
    }

    def parse_row(self, row: Dict[str, str]) -> Tuple[ScenarioRecord, List[str]]:
        """1行のCSVデータをScenarioRecordに変換"""
        warnings = []
        kwargs = {}

        for field_name in self.FIELD_NAMES:
            raw_value = row.get(field_name, "")
            type_hint = self.TYPE_MAP.get(field_name, str)

            if raw_value == "":
                # デフォルト値があれば設定
                if field_name in self.DEFAULTS:
                    kwargs[field_name] = self.DEFAULTS[field_name]
                else:
                    kwargs[field_name] = None
                continue

            try:
                if type_hint == "date":
                    kwargs[field_name] = TypeConverter.to_date(raw_value)
                elif type_hint == "datetime":
                    kwargs[field_name] = TypeConverter.to_datetime(raw_value)
                elif type_hint == "decimal":
                    kwargs[field_name] = TypeConverter.to_decimal(raw_value)
                elif type_hint == "bool":
                    kwargs[field_name] = TypeConverter.to_bool(raw_value)
                elif type_hint == "str_list":
                    kwargs[field_name] = TypeConverter.to_string_list(raw_value)
                elif type_hint == int:
                    kwargs[field_name] = int(raw_value) if raw_value else None
                elif isinstance(type_hint, type):
                    kwargs[field_name] = TypeConverter.to_enum(raw_value, type_hint)
                else:
                    kwargs[field_name] = raw_value
            except Exception as e:
                warnings.append(f"フィールド\'{field_name}\'の変換失敗: {raw_value} -> {e}")
                kwargs[field_name] = self.DEFAULTS.get(field_name, None)

        # record_idが空の場合は自動生成
        if not kwargs.get("record_id"):
            kwargs["record_id"] = str(uuid4())
            warnings.append("record_idが空のため自動生成しました")

        # 必須フィールドの確認
        required = ["source_id", "scenario_date", "published_at", "symbol"]
        missing = [f for f in required if kwargs.get(f) is None]
        if missing:
            warnings.append(f"必須フィールド欠損: {', '.join(missing)}")

        # recorded_atが空の場合は現在時刻
        if kwargs.get("recorded_at") is None:
            kwargs["recorded_at"] = datetime.utcnow()

        try:
            record = ScenarioRecord(**kwargs)
            return record, warnings
        except Exception as e:
            warnings.append(f"ScenarioRecord生成失敗: {e}")
            raise

    def read_csv(self, filepath: str | Path) -> Tuple[ScenarioBatch, List[str]]:
        """CSVファイルを読み込み、ScenarioBatchを返す"""
        filepath = Path(filepath)
        batch = ScenarioBatch(batch_id=f"csv-{filepath.stem}")
        all_warnings = []

        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                try:
                    record, warnings = self.parse_row(row)
                    batch.add_record(record)
                    if warnings:
                        all_warnings.extend([f"行{i}: {w}" for w in warnings])
                except Exception as e:
                    all_warnings.append(f"行{i}: パース失敗 - {e}")

        return batch, all_warnings

    def write_csv(self, batch: ScenarioBatch, filepath: str | Path) -> str:
        """ScenarioBatchをCSVファイルに書き出す"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELD_NAMES)
            writer.writeheader()
            for record in batch.records:
                row = {}
                flat = record.to_flat_dict()
                for field in self.FIELD_NAMES:
                    val = flat.get(field)
                    if val is None:
                        row[field] = ""
                    elif isinstance(val, list):
                        row[field] = ", ".join(str(v) for v in val)
                    else:
                        row[field] = str(val)
                writer.writerow(row)

        return str(filepath)


# ==========================================
# JSON Parser
# ==========================================

class JSONScenarioParser:
    """JSON形式のシナリオデータを読み書きするパーサー"""

    def read_json(self, filepath: str | Path) -> Tuple[ScenarioBatch, List[str]]:
        """JSONファイルを読み込み"""
        filepath = Path(filepath)
        all_warnings = []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        batch = ScenarioBatch(batch_id=f"json-{filepath.stem}")

        if isinstance(data, list):
            records_data = data
        elif isinstance(data, dict):
            if "records" in data:
                records_data = data["records"]
            else:
                records_data = [data]
        else:
            raise ValueError(f"未対応のJSON形式: {type(data)}")

        csv_parser = CSVScenarioParser()
        for i, item in enumerate(records_data, 1):
            try:
                str_dict = {k: str(v) if v is not None else "" for k, v in item.items()}
                record, warnings = csv_parser.parse_row(str_dict)
                batch.add_record(record)
                if warnings:
                    all_warnings.extend([f"要素{i}: {w}" for w in warnings])
            except Exception as e:
                all_warnings.append(f"要素{i}: パース失敗 - {e}")

        return batch, all_warnings

    def write_json(self, batch: ScenarioBatch, filepath: str | Path, indent: int = 2) -> str:
        """ScenarioBatchをJSONファイルに書き出す"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        records = [r.to_flat_dict() for r in batch.records]
        output = {
            "version": "1.2",
            "batch_id": batch.batch_id,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "record_count": len(batch),
            "records": records
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=indent, default=str)

        return str(filepath)


# ==========================================
# テキスト抽出（候補抽出のみ）
# ==========================================

class TextScenarioExtractor:
    """テキストからシナリオ情報の候補を抽出（自動確定禁止）"""

    PATTERNS = {
        "symbol": re.compile(r"([A-Z]{3,6}/?[A-Z]{3,6}|EURUSD|USDJPY|GBPUSD|AUDUSD|USDCAD|XAUUSD|BTCUSD)", re.IGNORECASE),
        "direction_long": re.compile(r"\b(buy|long|bull|買い|ロング|上昇)\b", re.IGNORECASE),
        "direction_short": re.compile(r"\b(sell|short|bear|売り|ショート|下降)\b", re.IGNORECASE),
        "price_decimal": re.compile(r"([0-9]+\.?[0-9]*)", re.IGNORECASE),
        "timeframe": re.compile(r"\b(1m|5m|15m|30m|1h|4h|d1|w1|mn|1分|5分|15分|30分|1時間|4時間|日足|週足)\b", re.IGNORECASE),
        "session_tokyo": re.compile(r"\b(東京|tokyo|asian)\b", re.IGNORECASE),
        "session_london": re.compile(r"\b(ロンドン|london|european)\b", re.IGNORECASE),
        "session_ny": re.compile(r"\b(ニューヨーク|new york|ny|us session)\b", re.IGNORECASE),
    }

    def extract_candidates(self, text: str, source_id: str, published_at: datetime) -> Dict[str, Any]:
        """テキストから候補情報を抽出"""
        candidates = {
            "source_id": source_id,
            "published_at": published_at,
            "original_text": text,
            "source_type": SourceType.TEXT,
            "parser_confidence": 0,
            "candidates": {},
            "warnings": ["テキスト抽出は候補のみ。人間レビューが必要です。"],
        }

        symbols = self.PATTERNS["symbol"].findall(text)
        if symbols:
            candidates["candidates"]["symbol"] = list(set(s.upper() for s in symbols))

        long_matches = len(self.PATTERNS["direction_long"].findall(text))
        short_matches = len(self.PATTERNS["direction_short"].findall(text))
        if long_matches > 0 and short_matches == 0:
            candidates["candidates"]["direction"] = Direction.LONG
        elif short_matches > 0 and long_matches == 0:
            candidates["candidates"]["direction"] = Direction.SHORT
        elif long_matches > 0 and short_matches > 0:
            candidates["candidates"]["direction"] = Direction.BOTH
            candidates["warnings"].append("LONGとSHORTの両方が検出されました")

        tfs = self.PATTERNS["timeframe"].findall(text)
        if tfs:
            candidates["candidates"]["timeframe"] = list(set(tfs))

        sessions = []
        if self.PATTERNS["session_tokyo"].search(text):
            sessions.append(MarketSession.TOKYO)
        if self.PATTERNS["session_london"].search(text):
            sessions.append(MarketSession.LONDON)
        if self.PATTERNS["session_ny"].search(text):
            sessions.append(MarketSession.NEW_YORK)
        if sessions:
            candidates["candidates"]["market_session"] = sessions

        prices = self.PATTERNS["price_decimal"].findall(text)
        if prices:
            unique_prices = []
            seen = set()
            for p in prices:
                try:
                    d = Decimal(p)
                    if d not in seen:
                        seen.add(d)
                        unique_prices.append(d)
                except:
                    pass
            if len(unique_prices) >= 2:
                candidates["candidates"]["price_candidates"] = sorted(unique_prices)

        n_extracted = len(candidates["candidates"])
        candidates["parser_confidence"] = min(30, n_extracted * 10)

        return candidates

    def to_scenario_input(self, candidates: Dict[str, Any], scenario_date: date) -> ScenarioInput:
        """候補から最小入力モデルを生成（人間確認前提）"""
        c = candidates.get("candidates", {})
        return ScenarioInput(
            source_id=candidates["source_id"],
            scenario_date=scenario_date,
            published_at=candidates["published_at"],
            symbol=c.get("symbol", ["UNKNOWN"])[0] if isinstance(c.get("symbol"), list) else "UNKNOWN",
            direction=c.get("direction", Direction.UNKNOWN),
            original_text=candidates.get("original_text"),
        )


# ==========================================
# 統合パーサー
# ==========================================

class ScenarioParser:
    """統合パーサー（CSV/JSON/テキストの入出力を一元管理）"""

    def __init__(self):
        self.csv_parser = CSVScenarioParser()
        self.json_parser = JSONScenarioParser()
        self.text_extractor = TextScenarioExtractor()

    def read(self, filepath: str | Path) -> Tuple[ScenarioBatch, List[str]]:
        """ファイル形式を自動判定して読み込み"""
        filepath = Path(filepath)
        suffix = filepath.suffix.lower()

        if suffix == ".csv":
            return self.csv_parser.read_csv(filepath)
        elif suffix in (".json", ".jsonl"):
            return self.json_parser.read_json(filepath)
        else:
            raise ValueError(f"未対応のファイル形式: {suffix}")

    def write_csv(self, batch: ScenarioBatch, filepath: str | Path) -> str:
        return self.csv_parser.write_csv(batch, filepath)

    def write_json(self, batch: ScenarioBatch, filepath: str | Path) -> str:
        return self.json_parser.write_json(batch, filepath)

    def extract_from_text(self, text: str, source_id: str, published_at: datetime) -> Dict[str, Any]:
        return self.text_extractor.extract_candidates(text, source_id, published_at)
