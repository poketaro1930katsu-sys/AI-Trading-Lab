"""
AI Trading Lab v1.2 - Scenario Statistics
統計集計・Wilson 95% CI・サンプルサイズ警告
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from collections import Counter
import math

from scenario_models import (
    ScenarioRecord, Direction, ResultClassification, MarketSession, SourceType
)


# ==========================================
# Data Classes
# ==========================================

@dataclass
class SampleSizeStatus:
    """標本サイズに基づく表示制御"""
    n: int
    status: str  # "forbidden", "reference", "caution", "normal"
    warning: str
    display_allowed: bool
    comparison_allowed: bool


@dataclass
class StatisticsWarning:
    """統計警告"""
    code: str
    message: str
    severity: str  # "info", "warning", "critical"


@dataclass
class WilsonCI:
    """Wilson信頼区間"""
    point_estimate: float
    lower: float
    upper: float
    n: int
    k: int


@dataclass
class QualityMetrics:
    """品質スコア分析"""
    mean: float
    median: float
    minimum: Optional[int]
    maximum: Optional[int]
    std_dev: Optional[float]
    histogram: Dict[str, int]  # 10-point bins
    count: int


@dataclass
class DirectionBreakdown:
    """方向別内訳"""
    direction: str
    count: int
    win_count: int
    loss_count: int
    win_rate: Optional[float]
    win_rate_ci: Optional[WilsonCI]
    sample_status: SampleSizeStatus


@dataclass
class ResultBreakdown:
    """結果分類別内訳"""
    result: str
    count: int
    percentage: float


@dataclass
class StatisticsResult:
    """統計結果の完全データクラス"""
    # 基本集計
    total: int
    evaluated: int
    pending_evaluation: int

    # 方向別
    direction_counts: Dict[str, int]
    direction_breakdown: List[DirectionBreakdown]

    # 銘柄別
    symbol_counts: Dict[str, int]

    # 時間足別
    timeframe_counts: Dict[str, int]

    # セッション別
    session_counts: Dict[str, int]

    # ソース別
    source_counts: Dict[str, int]

    # 結果分類
    result_counts: Dict[str, int]
    result_breakdown: List[ResultBreakdown]

    # Entry・未成立・無効化・曖昧
    entry_rate: float
    entry_rate_ci: WilsonCI
    not_triggered_rate: float
    not_triggered_rate_ci: WilsonCI
    invalidated_rate: float
    invalidated_rate_ci: WilsonCI
    ambiguous_rate: float
    ambiguous_rate_ci: WilsonCI

    # 勝率
    win_rate: Optional[float]
    win_rate_eligible_n: int
    win_rate_ci: Optional[WilsonCI]
    win_rate_sample_status: SampleSizeStatus

    # 品質
    quality_metrics: QualityMetrics
    human_review_rate: float
    human_corrected_rate: float

    # 警告
    warnings: List[StatisticsWarning] = field(default_factory=list)


# ==========================================
# 共通関数
# ==========================================

def wilson_ci(k: int, n: int, confidence: float = 0.95) -> WilsonCI:
    """Wilson法による信頼区間

    Args:
        k: 成功/該当件数
        n: 総件数
        confidence: 信頼水準（デフォルト95%）

    Returns:
        WilsonCI: 点推定値とCI
    """
    if n == 0:
        return WilsonCI(point_estimate=0.0, lower=0.0, upper=0.0, n=0, k=0)

    z = 1.96 if confidence == 0.95 else 2.576
    p = k / n

    denom = 1.0 + (z ** 2) / n
    center = (p + (z ** 2) / (2 * n)) / denom
    margin = z * math.sqrt(
        p * (1 - p) / n + (z ** 2) / (4 * n ** 2)
    ) / denom

    return WilsonCI(
        point_estimate=p,
        lower=max(0.0, center - margin),
        upper=min(1.0, center + margin),
        n=n,
        k=k
    )


def sample_size_status(n: int) -> SampleSizeStatus:
    """標本サイズに基づく表示制御

    Version1.2ルール:
    - n < 20: 条件比較禁止
    - n < 30: 参考値・標本不足
    - n < 100: 高信頼と表現しない
    - n >= 100: 通常表示
    """
    if n < 20:
        return SampleSizeStatus(
            n=n,
            status="forbidden",
            warning="条件比較禁止・標本不足",
            display_allowed=False,
            comparison_allowed=False
        )
    elif n < 30:
        return SampleSizeStatus(
            n=n,
            status="reference",
            warning="参考値・標本不足",
            display_allowed=True,
            comparison_allowed=False
        )
    elif n < 100:
        return SampleSizeStatus(
            n=n,
            status="caution",
            warning="高信頼と表現しない",
            display_allowed=True,
            comparison_allowed=True
        )
    else:
        return SampleSizeStatus(
            n=n,
            status="normal",
            warning="",
            display_allowed=True,
            comparison_allowed=True
        )


# ==========================================
# メインクラス
# ==========================================

class ScenarioStatistics:
    """シナリオ記録の統計集計"""

    def __init__(self, records: List[ScenarioRecord]):
        self.records = records
        self.n = len(records)
        self.warnings: List[StatisticsWarning] = []

    def summarize(self) -> StatisticsResult:
        """基本集計"""
        if not self.records:
            self.warnings.append(StatisticsWarning(
                code="NO_DATA",
                message="データがありません",
                severity="critical"
            ))
            return self._empty_result()

        total = self.n
        evaluated = [r for r in self.records if r.is_evaluated()]
        n_eval = len(evaluated)

        # 方向別
        direction_counts = Counter(r.direction for r in self.records)

        # 方向別勝率内訳
        direction_breakdown = self._build_direction_breakdown()

        # 銘柄別
        symbol_counts = Counter(r.symbol for r in self.records)

        # 時間足別
        timeframe_counts = Counter(r.timeframe for r in self.records if r.timeframe)

        # セッション別
        session_counts = Counter(r.market_session for r in self.records)

        # ソース別
        source_counts = Counter(r.source_id for r in self.records)

        # 結果分類
        result_counts = Counter(r.result_classification for r in evaluated)
        result_breakdown = [
            ResultBreakdown(result=k, count=v, percentage=v/n_eval if n_eval>0 else 0)
            for k, v in result_counts.items()
        ]

        # Entry率（評価済み中でentry_triggered=True）
        entry_triggered = [r for r in evaluated if r.entry_triggered is True]
        entry_rate = len(entry_triggered) / n_eval if n_eval > 0 else 0
        entry_rate_ci = wilson_ci(len(entry_triggered), n_eval)

        # NOT_TRIGGERED率
        nt_count = result_counts.get(ResultClassification.NOT_TRIGGERED, 0)
        nt_rate = nt_count / n_eval if n_eval > 0 else 0
        nt_rate_ci = wilson_ci(nt_count, n_eval)

        # INVALIDATED_BEFORE_ENTRY率
        inv_count = result_counts.get(ResultClassification.INVALIDATED_BEFORE_ENTRY, 0)
        inv_rate = inv_count / n_eval if n_eval > 0 else 0
        inv_rate_ci = wilson_ci(inv_count, n_eval)

        # AMBIGUOUS率
        amb_count = result_counts.get(ResultClassification.AMBIGUOUS, 0)
        amb_rate = amb_count / n_eval if n_eval > 0 else 0
        amb_rate_ci = wilson_ci(amb_count, n_eval)

        # 勝率計算
        # 母数: WIN + LOSS + PARTIAL_WIN + PARTIAL_LOSS のみ
        # 理由: これらは「方向が一致し、Entryが成立した」シナリオのみを対象とする。
        # NOT_TRIGGERED（未成立）、INVALIDATED_BEFORE_ENTRY（無効化）、
        # EXPIRED（期限切れ）、NOT_EVALUATED（未評価）、AMBIGUOUS（同一足到達）
        # は「シナリオの方向性が正しかったか」の判定に含めない。
        win_loss_eligible = sum([
            result_counts.get(ResultClassification.WIN, 0),
            result_counts.get(ResultClassification.LOSS, 0),
            result_counts.get(ResultClassification.PARTIAL_WIN, 0),
            result_counts.get(ResultClassification.PARTIAL_LOSS, 0),
        ])
        wins = result_counts.get(ResultClassification.WIN, 0)
        partial_wins = result_counts.get(ResultClassification.PARTIAL_WIN, 0)
        win_rate = (wins + partial_wins * 0.5) / win_loss_eligible if win_loss_eligible > 0 else None
        win_rate_ci = wilson_ci(wins + partial_wins, win_loss_eligible) if win_loss_eligible > 0 else None
        win_rate_status = sample_size_status(win_loss_eligible)

        if win_loss_eligible > 0 and win_loss_eligible < 20:
            self.warnings.append(StatisticsWarning(
                code="SMALL_SAMPLE_WIN_RATE",
                message=f"勝率母数が{win_loss_eligible}件（条件比較禁止）",
                severity="warning"
            ))

        # 品質分析
        quality_metrics = self._build_quality_metrics()

        # Human Review率
        reviewed = [r for r in self.records if r.human_review_status != "PENDING"]
        human_review_rate = len(reviewed) / total if total > 0 else 0

        # Human Corrected率
        corrected = [r for r in self.records if r.human_corrected is True]
        human_corrected_rate = len(corrected) / total if total > 0 else 0

        return StatisticsResult(
            total=total,
            evaluated=n_eval,
            pending_evaluation=total - n_eval,
            direction_counts={k: v for k, v in direction_counts.items()},
            direction_breakdown=direction_breakdown,
            symbol_counts=dict(symbol_counts),
            timeframe_counts=dict(timeframe_counts),
            session_counts={k: v for k, v in session_counts.items()},
            source_counts=dict(source_counts),
            result_counts={k: v for k, v in result_counts.items()},
            result_breakdown=result_breakdown,
            entry_rate=entry_rate,
            entry_rate_ci=entry_rate_ci,
            not_triggered_rate=nt_rate,
            not_triggered_rate_ci=nt_rate_ci,
            invalidated_rate=inv_rate,
            invalidated_rate_ci=inv_rate_ci,
            ambiguous_rate=amb_rate,
            ambiguous_rate_ci=amb_rate_ci,
            win_rate=win_rate,
            win_rate_eligible_n=win_loss_eligible,
            win_rate_ci=win_rate_ci,
            win_rate_sample_status=win_rate_status,
            quality_metrics=quality_metrics,
            human_review_rate=human_review_rate,
            human_corrected_rate=human_corrected_rate,
            warnings=self.warnings
        )

    def _empty_result(self) -> StatisticsResult:
        return StatisticsResult(
            total=0, evaluated=0, pending_evaluation=0,
            direction_counts={}, direction_breakdown=[],
            symbol_counts={}, timeframe_counts={}, session_counts={},
            source_counts={}, result_counts={}, result_breakdown=[],
            entry_rate=0.0, entry_rate_ci=wilson_ci(0, 0),
            not_triggered_rate=0.0, not_triggered_rate_ci=wilson_ci(0, 0),
            invalidated_rate=0.0, invalidated_rate_ci=wilson_ci(0, 0),
            ambiguous_rate=0.0, ambiguous_rate_ci=wilson_ci(0, 0),
            win_rate=None, win_rate_eligible_n=0,
            win_rate_ci=None, win_rate_sample_status=sample_size_status(0),
            quality_metrics=QualityMetrics(
                mean=0.0, median=0.0, minimum=None, maximum=None,
                std_dev=None, histogram={}, count=0
            ),
            human_review_rate=0.0, human_corrected_rate=0.0,
            warnings=self.warnings
        )


    def _median(self, values: List[int]) -> float:
        """中央値計算"""
        s = sorted(values)
        n = len(s)
        if n % 2 == 1:
            return float(s[n // 2])
        return (s[n // 2 - 1] + s[n // 2]) / 2.0

    def _stdev(self, values: List[int]) -> float:
        """標準偏差計算"""
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def _build_direction_breakdown(self) -> List[DirectionBreakdown]:
        """方向別勝率内訳"""
        breakdown = []
        directions = set(r.direction for r in self.records)

        for d in directions:
            dir_records = [r for r in self.records if r.direction == d]
            evaluated = [r for r in dir_records if r.is_evaluated()]

            wins = sum(1 for r in evaluated if r.result_classification == ResultClassification.WIN)
            losses = sum(1 for r in evaluated if r.result_classification == ResultClassification.LOSS)
            partial_wins = sum(1 for r in evaluated if r.result_classification == ResultClassification.PARTIAL_WIN)
            partial_losses = sum(1 for r in evaluated if r.result_classification == ResultClassification.PARTIAL_LOSS)

            eligible = wins + losses + partial_wins + partial_losses
            win_rate = (wins + partial_wins * 0.5) / eligible if eligible > 0 else None
            win_rate_ci = wilson_ci(wins + partial_wins, eligible) if eligible > 0 else None

            breakdown.append(DirectionBreakdown(
                direction=d,
                count=len(dir_records),
                win_count=wins,
                loss_count=losses,
                win_rate=win_rate,
                win_rate_ci=win_rate_ci,
                sample_status=sample_size_status(eligible)
            ))

        return breakdown

    def _build_quality_metrics(self) -> QualityMetrics:
        """品質スコア分析"""
        scores = [r.data_quality_score for r in self.records if r.data_quality_score is not None]

        if not scores:
            return QualityMetrics(
                mean=0.0, median=0.0, minimum=None, maximum=None,
                std_dev=None, histogram={}, count=0
            )

        # ヒストグラム（10点刻み）
        histogram = {}
        for score in scores:
            bin_key = f"{(score // 10) * 10}-{(score // 10) * 10 + 9}"
            histogram[bin_key] = histogram.get(bin_key, 0) + 1

        return QualityMetrics(
            mean=sum(scores) / len(scores),
            median=self._median(scores),
            minimum=min(scores),
            maximum=max(scores),
            std_dev=self._stdev(scores) if len(scores) > 1 else 0.0,
            histogram=histogram,
            count=len(scores)
        )

    # ==========================================
    # 条件別集計
    # ==========================================

    def by_symbol(self, symbol: str) -> StatisticsResult:
        """銘柄別集計"""
        filtered = [r for r in self.records if r.symbol.upper() == symbol.upper()]
        return ScenarioStatistics(filtered).summarize()

    def by_direction(self, direction: Direction) -> StatisticsResult:
        """方向別集計"""
        filtered = [r for r in self.records if r.direction == direction]
        return ScenarioStatistics(filtered).summarize()

    def by_session(self, session: MarketSession) -> StatisticsResult:
        """セッション別集計"""
        filtered = [r for r in self.records if r.market_session == session]
        return ScenarioStatistics(filtered).summarize()

    def by_timeframe(self, timeframe: str) -> StatisticsResult:
        """時間足別集計"""
        filtered = [r for r in self.records if r.timeframe == timeframe]
        return ScenarioStatistics(filtered).summarize()

    def by_source(self, source_id: str) -> StatisticsResult:
        """ソース別集計"""
        filtered = [r for r in self.records if r.source_id == source_id]
        return ScenarioStatistics(filtered).summarize()

    def by_result(self, result: ResultClassification) -> StatisticsResult:
        """結果別集計"""
        filtered = [r for r in self.records if r.result_classification == result]
        return ScenarioStatistics(filtered).summarize()
