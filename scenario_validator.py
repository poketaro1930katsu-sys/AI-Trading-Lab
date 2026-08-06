"""
AI Trading Lab v1.2 - Scenario Validator
入力検証・品質スコア計算・重複チェック
"""

from datetime import datetime, date, timezone
from typing import List, Tuple, Optional, Set, Dict, Any
from decimal import Decimal

from scenario_models import (
    ScenarioRecord, Direction, EntryType, ResultClassification,
    HumanReviewStatus
)


class ValidationIssue:
    """検証 issue の詳細"""
    def __init__(self, field: str, message: str, severity: str, deduction: int):
        self.field = field
        self.message = message
        self.severity = severity  # "critical", "major", "minor", "info"
        self.deduction = deduction

    def __repr__(self):
        return f"ValidationIssue({self.field}: {self.message} [-{self.deduction}])"


class ScenarioValidator:
    """単一レコードの検証と品質スコアリング"""

    REQUIRED_FIELDS = [
        "record_id", "source_id", "scenario_date", "published_at", "symbol"
    ]

    RECOMMENDED_FIELDS = [
        "direction", "entry_type", "stop_loss", "take_profit_1",
        "scenario_valid_from", "scenario_valid_until", "original_text"
    ]

    def validate(self, record: ScenarioRecord) -> Tuple[bool, List[ValidationIssue], int]:
        """完全検証を実行

        Returns:
            (valid, issues, quality_score)
        """
        issues: List[ValidationIssue] = []

        # 1. 必須フィールドチェック
        issues.extend(self._check_required(record))

        # 2. 推奨フィールドチェック
        issues.extend(self._check_recommended(record))

        # 3. 価格整合性チェック
        issues.extend(self._check_price_consistency(record))

        # 4. 日時整合性チェック
        issues.extend(self._check_time_consistency(record))

        # 5. 方向性・価格整合性
        issues.extend(self._check_direction_consistency(record))

        # 6. AI推論・原文チェック
        issues.extend(self._check_source_quality(record))

        # スコア計算
        score = 100 - sum(i.deduction for i in issues)
        score = max(0, min(100, score))

        # valid = 必須欠損がない
        has_critical = any(i.severity == "critical" for i in issues)
        valid = not has_critical

        # レコードにメタデータを反映
        record.missing_required_fields = [
            i.field for i in issues if i.severity == "critical" and "必須" in i.message
        ] or None

        record.ambiguous_fields = [
            i.field for i in issues if i.severity in ("major", "minor") and "矛盾" in i.message
        ] or None

        # human_review_status更新
        if any(i.severity in ("critical", "major") for i in issues):
            record.human_review_status = HumanReviewStatus.PENDING

        record.data_quality_score = score

        return valid, issues, score

    def _check_required(self, record: ScenarioRecord) -> List[ValidationIssue]:
        issues = []
        for field in self.REQUIRED_FIELDS:
            val = getattr(record, field)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                issues.append(ValidationIssue(
                    field=field,
                    message=f"必須フィールド '{field}' が欠損",
                    severity="critical",
                    deduction=20
                ))
        return issues

    def _check_recommended(self, record: ScenarioRecord) -> List[ValidationIssue]:
        issues = []
        for field in self.RECOMMENDED_FIELDS:
            val = getattr(record, field)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                issues.append(ValidationIssue(
                    field=field,
                    message=f"推奨フィールド '{field}' が欠損",
                    severity="minor",
                    deduction=5
                ))
        return issues

    def _check_price_consistency(self, record: ScenarioRecord) -> List[ValidationIssue]:
        issues = []
        direction = record.direction

        # entry_price_low <= entry_price_high
        if record.entry_price_low is not None and record.entry_price_high is not None:
            if record.entry_price_low > record.entry_price_high:
                issues.append(ValidationIssue(
                    field="entry_price",
                    message="entry_price_low > entry_price_high（価格帯逆転）",
                    severity="major",
                    deduction=15
                ))

        # LONG・SHORT以外はSL・TP位置検証をスキップ
        if direction not in ("LONG", "SHORT", Direction.LONG.value, Direction.SHORT.value):
            return issues

        entry = record.get_entry_zone()
        sl = record.stop_loss
        tp1 = record.take_profit_1

        if entry is None:
            return issues

        # LONG: SL < Entry_low, TP > Entry_high
        if direction == "LONG" or direction == Direction.LONG.value:
            if sl is not None and sl >= entry[0]:
                issues.append(ValidationIssue(
                    field="stop_loss",
                    message="LONG方向でSLがエントリー価格以上（損切り位置矛盾）",
                    severity="major",
                    deduction=15
                ))
            if tp1 is not None and tp1 <= entry[1]:
                issues.append(ValidationIssue(
                    field="take_profit_1",
                    message="LONG方向でTP1がエントリー価格以下（利確位置矛盾）",
                    severity="major",
                    deduction=15
                ))

        # SHORT: SL > Entry_high, TP < Entry_low
        elif direction == "SHORT" or direction == Direction.SHORT.value:
            if sl is not None and sl <= entry[1]:
                issues.append(ValidationIssue(
                    field="stop_loss",
                    message="SHORT方向でSLがエントリー価格以下（損切り位置矛盾）",
                    severity="major",
                    deduction=15
                ))
            if tp1 is not None and tp1 >= entry[0]:
                issues.append(ValidationIssue(
                    field="take_profit_1",
                    message="SHORT方向でTP1がエントリー価格以上（利確位置矛盾）",
                    severity="major",
                    deduction=15
                ))

        return issues

    def _check_time_consistency(self, record: ScenarioRecord) -> List[ValidationIssue]:
        issues = []

        # timezone混在検出
        def has_tz(dt):
            return dt is not None and dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

        def is_naive(dt):
            return dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None)

        dt_fields = {
            "published_at": record.published_at,
            "scenario_valid_from": record.scenario_valid_from,
            "scenario_valid_until": record.scenario_valid_until,
        }

        tz_aware = [k for k, v in dt_fields.items() if has_tz(v)]
        tz_naive = [k for k, v in dt_fields.items() if is_naive(v)]

        if tz_aware and tz_naive:
            issues.append(ValidationIssue(
                field="timezone",
                message=f"timezone混在: aware={tz_aware}, naive={tz_naive}",
                severity="major",
                deduction=10
            ))
            return issues  # 混在時は比較を中止

        # valid_from < valid_until
        if record.scenario_valid_from is not None and record.scenario_valid_until is not None:
            if record.scenario_valid_from >= record.scenario_valid_until:
                issues.append(ValidationIssue(
                    field="scenario_valid_until",
                    message="有効期限開始が終了以上（期限逆転）",
                    severity="major",
                    deduction=10
                ))

        # published_at <= valid_from
        if record.published_at is not None and record.scenario_valid_from is not None:
            if record.published_at > record.scenario_valid_from:
                issues.append(ValidationIssue(
                    field="published_at",
                    message="公開日時が有効開始日時より後（整合性矛盾）",
                    severity="major",
                    deduction=10
                ))

        return issues

    def _check_direction_consistency(self, record: ScenarioRecord) -> List[ValidationIssue]:
        issues = []
        if record.direction == "UNKNOWN" or record.direction == Direction.UNKNOWN.value and record.entry_price_low is not None:
            issues.append(ValidationIssue(
                field="direction",
                message="方向性UNKNOWNだがエントリー価格が指定されている",
                severity="major",
                deduction=10
            ))
        return issues

    def _check_source_quality(self, record: ScenarioRecord) -> List[ValidationIssue]:
        issues = []
        if record.original_text is None or str(record.original_text).strip() == "":
            issues.append(ValidationIssue(
                field="original_text",
                message="原文が未設定（追跡不可能）",
                severity="critical",
                deduction=20
            ))
        if record.inferred_fields and len(record.inferred_fields) > 0:
            issues.append(ValidationIssue(
                field="inferred_fields",
                message=f"AI推論補完フィールドが未確認: {record.inferred_fields}",
                severity="minor",
                deduction=5
            ))
        return issues

    def check_duplicates(self, records: List[ScenarioRecord]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str, str]]]:
        """重複チェック

        Returns:
            (完全重複リスト[(record_id, key)], 重複候補リスト[(record_id, key, reason)])
        """
        # A. 完全重複: 同一record_id
        seen_ids: Set[str] = set()
        exact_dups: List[Tuple[str, str]] = []

        for r in records:
            if r.record_id in seen_ids:
                exact_dups.append((r.record_id, f"record_id={r.record_id}"))
            seen_ids.add(r.record_id)

        # B. 重複候補: 同一source_id + scenario_date + symbol
        seen_candidates: Dict[str, str] = {}  # key -> first_record_id
        candidate_dups: List[Tuple[str, str, str]] = []

        for r in records:
            key = f"{r.source_id}:{r.scenario_date}:{r.symbol}"
            if key in seen_candidates:
                candidate_dups.append((
                    r.record_id,
                    key,
                    f"source_id={r.source_id}, date={r.scenario_date}, symbol={r.symbol}"
                ))
            else:
                seen_candidates[key] = r.record_id

        return exact_dups, candidate_dups


class BatchValidator:
    """バッチ単位の検証"""

    def __init__(self):
        self.validator = ScenarioValidator()

    def validate_batch(self, records: List[ScenarioRecord]) -> dict:
        """バッチ全体の検証レポート"""
        results = {
            "total": len(records),
            "valid": 0,
            "invalid": 0,
            "issues": [],
            "quality_scores": [],
            "exact_duplicates": [],
            "candidate_duplicates": [],
        }

        for record in records:
            valid, issues, score = self.validator.validate(record)
            if valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
            results["issues"].extend(issues)
            results["quality_scores"].append(score)

        exact, candidates = self.validator.check_duplicates(records)
        results["exact_duplicates"] = exact
        results["candidate_duplicates"] = candidates

        # duplicate_flag更新
        for rid, key, reason in candidates:
            for r in records:
                if r.record_id == rid:
                    r.duplicate_flag = True

        results["avg_quality"] = sum(results["quality_scores"]) / len(results["quality_scores"]) if results["quality_scores"] else 0

        return results
