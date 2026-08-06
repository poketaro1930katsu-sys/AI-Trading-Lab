"""
AI Trading Lab v1.2 - Scenario Journal
シナリオ記録の永続化・管理・検索
"""

from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import csv
import json
import os

from scenario_models import (
    ScenarioRecord, ScenarioBatch, ScenarioEvaluationInput,
    Direction, ResultClassification, HumanReviewStatus
)
from scenario_parser import ScenarioParser


class ScenarioJournal:
    """シナリオ記録の永続化管理クラス"""

    def __init__(self, data_dir: str = "outputs"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.parser = ScenarioParser()
        self._batch: Optional[ScenarioBatch] = None
        self._index: Dict[str, ScenarioRecord] = {}

    @property
    def batch(self) -> ScenarioBatch:
        if self._batch is None:
            self._batch = ScenarioBatch()
        return self._batch

    def load(self, filepath: Optional[str] = None) -> ScenarioBatch:
        """CSV/JSONファイルから読み込み"""
        if filepath is None:
            csv_path = self.data_dir / "scenario_records.csv"
            if csv_path.exists():
                filepath = str(csv_path)
            else:
                self._batch = ScenarioBatch()
                return self._batch

        batch, warnings = self.parser.read(filepath)
        self._batch = batch
        self._rebuild_index()
        if warnings:
            print(f"読み込み警告: {len(warnings)}件")
            for w in warnings[:5]:
                print(f"  - {w}")
        return batch

    def save(self, filepath: Optional[str] = None) -> str:
        """CSVファイルに保存"""
        if filepath is None:
            filepath = self.data_dir / "scenario_records.csv"
        else:
            filepath = Path(filepath)

        return self.parser.write_csv(self.batch, filepath)

    def add_record(self, record: ScenarioRecord) -> None:
        """レコードを追加"""
        if record.record_id in self._index:
            raise ValueError(f"重複record_id: {record.record_id}")
        self.batch.add_record(record)
        self._index[record.record_id] = record

    def get_by_id(self, record_id: str) -> Optional[ScenarioRecord]:
        """record_idで検索"""
        return self._index.get(record_id)

    def update_evaluation(self, eval_input: ScenarioEvaluationInput) -> bool:
        """評価結果を更新（既存レコードにマージ）"""
        record = self.get_by_id(eval_input.record_id)
        if record is None:
            return False

        update_fields = [
            "entry_triggered", "entry_triggered_at", "entry_price_actual",
            "highest_favorable_price", "lowest_adverse_price",
            "tp1_reached", "tp2_reached", "tp3_reached", "sl_reached",
            "invalidation_reached", "scenario_expired", "result_classification",
            "realized_r_multiple", "maximum_favorable_excursion_r",
            "maximum_adverse_excursion_r", "evaluation_notes"
        ]

        for field in update_fields:
            val = getattr(eval_input, field)
            if val is not None:
                setattr(record, field, val)

        record.evaluation_completed_at = datetime.utcnow()
        return True

    def _rebuild_index(self) -> None:
        """インデックスを再構築"""
        self._index = {r.record_id: r for r in self.batch.records}

    def query(
        self,
        symbol: Optional[str] = None,
        direction: Optional[Direction] = None,
        result: Optional[ResultClassification] = None,
        evaluated_only: bool = False,
        pending_review: bool = False,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[ScenarioRecord]:
        """条件でフィルタリング"""
        results = self.batch.records

        if symbol:
            results = [r for r in results if r.symbol.upper() == symbol.upper()]
        if direction:
            results = [r for r in results if r.direction == direction]
        if result:
            results = [r for r in results if r.result_classification == result]
        if evaluated_only:
            results = [r for r in results if r.is_evaluated()]
        if pending_review:
            results = [r for r in results if r.human_review_status == HumanReviewStatus.PENDING]
        if date_from:
            results = [r for r in results if r.scenario_date >= date_from]
        if date_to:
            results = [r for r in results if r.scenario_date <= date_to]

        return results

    def get_statistics_ready(self) -> List[ScenarioRecord]:
        """統計集計対象（評価済み・有効データ）を返す"""
        return [
            r for r in self.batch.records
            if r.is_evaluated()
            and r.result_classification != ResultClassification.NOT_EVALUATED
            and r.data_quality_score is not None
            and r.data_quality_score >= 50
        ]

    def export_summary(self, filepath: Optional[str] = None) -> str:
        """サマリーCSVを出力"""
        if filepath is None:
            filepath = self.data_dir / "scenario_summary.csv"

        records = self.batch.records
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "record_id", "source_id", "scenario_date", "symbol", "direction",
                "entry_type", "result_classification", "realized_r_multiple",
                "data_quality_score", "human_review_status"
            ])
            for r in records:
                writer.writerow([
                    r.record_id, r.source_id, r.scenario_date, r.symbol,
                    r.direction, r.entry_type, r.result_classification,
                    r.realized_r_multiple, r.data_quality_score, r.human_review_status
                ])
        return str(filepath)
