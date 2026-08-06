"""
AI Trading Lab v1.2 - Scenario Report
Markdownレポート・品質レポート・分析レポート・CSV出力
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from scenario_statistics import (
    ScenarioStatistics, StatisticsResult, StatisticsWarning,
    SampleSizeStatus, QualityMetrics, WilsonCI
)
from scenario_models import (
    ScenarioRecord, Direction, ResultClassification,
    HumanReviewStatus, MarketSession
)


class ScenarioReport:
    """レポート生成クラス"""

    # 表現上の禁止事項チェック用
    FORBIDDEN_PHRASES = [
        "高確率で勝てる", "参加推奨", "必ず上がる", "必ず下がる",
        "信頼できる発信者", "優良発信者", "勝てるシナリオ"
    ]

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _format_datetime(self, dt) -> str:
        """datetime/dateを安全に文字列化"""
        if dt is None:
            return ""
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt)

    def _format_decimal(self, d) -> str:
        """Decimalを安全に文字列化"""
        if d is None:
            return ""
        return str(d)

    def _format_bool(self, b) -> str:
        """boolを安全に文字列化"""
        if b is None:
            return ""
        return "true" if b else "false"

    def _check_forbidden_phrases(self, text: str) -> List[str]:
        """禁止表現を検出"""
        found = []
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase in text:
                found.append(phrase)
        return found

    def _render_sample_size_box(self, status: SampleSizeStatus) -> str:
        """標本サイズ警告ボックス"""
        if status.status == "normal":
            return ""
        icon = "⚠️" if status.status in ("forbidden", "reference") else "ℹ️"
        return f"""
> {icon} **標本サイズ警告**: {status.warning}
> - 母数: {status.n}件
> - 表示: {"許可" if status.display_allowed else "制限"}
> - 条件比較: {"許可" if status.comparison_allowed else "禁止"}
"""

    def _render_wilson_ci(self, ci: Optional[WilsonCI], label: str) -> str:
        """Wilson CI表示"""
        if ci is None:
            return f"- {label}: 計算不可（データ不足）"
        return f"- {label}: {ci.point_estimate*100:.1f}% (Wilson 95% CI: [{ci.lower*100:.1f}%, {ci.upper*100:.1f}%])"

    # ==========================================
    # A. データ品質レポート
    # ==========================================

    def generate_data_quality_report(
        self,
        records: List[ScenarioRecord],
        filepath: Optional[Path] = None
    ) -> str:
        """データ品質レポートを生成"""
        if filepath is None:
            filepath = self.output_dir / "scenario_data_quality_report.md"

        stats = ScenarioStatistics(records)
        result = stats.summarize()
        qm = result.quality_metrics

        lines = []
        lines.append("# シナリオデータ品質レポート")
        lines.append(f"生成日時: {datetime.now().isoformat()}")
        lines.append("")

        # 概要
        lines.append("## 概要")
        lines.append(f"- 総レコード数: {result.total}件")

        if qm.count > 0:
            lines.append(f"- 平均品質スコア: {qm.mean:.1f}/100")
            lines.append(f"- 中央値: {qm.median:.1f}")
            lines.append(f"- 最小: {qm.minimum}")
            lines.append(f"- 最大: {qm.maximum}")
            if qm.std_dev is not None:
                lines.append(f"- 標準偏差: {qm.std_dev:.2f}")
        else:
            lines.append("- 品質スコアデータなし")

        lines.append("")

        # 品質スコア分布
        lines.append("## 品質スコア分布")
        if qm.histogram:
            for bin_range, count in sorted(qm.histogram.items()):
                lines.append(f"- {bin_range}点: {count}件")
        else:
            lines.append("- データなし")
        lines.append("")

        # 必須項目欠損
        missing_req = [r for r in records if r.missing_required_fields]
        lines.append(f"## 必須項目欠損")
        lines.append(f"- {len(missing_req)}件")
        lines.append("")

        # 曖昧項目
        ambiguous = [r for r in records if r.ambiguous_fields]
        lines.append(f"## 曖昧項目")
        lines.append(f"- {len(ambiguous)}件")
        lines.append("")

        # AI推定項目
        inferred = [r for r in records if r.inferred_fields]
        lines.append(f"## AI推定項目あり")
        lines.append(f"- {len(inferred)}件")
        lines.append("")

        # Human Review
        pending = [r for r in records if r.human_review_status == "PENDING"]
        lines.append(f"## Human Review必要件数")
        lines.append(f"- {len(pending)}件")
        lines.append("")

        # Human Corrected
        corrected = [r for r in records if r.human_corrected is True]
        lines.append(f"## Human Corrected件数")
        lines.append(f"- {len(corrected)}件")
        lines.append("")

        # 重複候補
        dup = [r for r in records if r.duplicate_flag is True]
        lines.append(f"## 重複候補件数")
        lines.append(f"- {len(dup)}件")
        lines.append("")

        # 原文サンプル
        lines.append("## 原文サンプル")
        for r in records[:5]:
            if r.original_text:
                text = str(r.original_text)[:100]
                lines.append(f"- [{r.record_id}] {text}")
        lines.append("")

        # 禁止表現チェック
        lines.append("## 禁止表現チェック")
        found_forbidden = []
        for r in records:
            if r.original_text:
                found = self._check_forbidden_phrases(str(r.original_text))
                found_forbidden.extend(found)
        if found_forbidden:
            lines.append(f"- ⚠️ 検出: {set(found_forbidden)}")
        else:
            lines.append("- 検出なし")

        content = "\n".join(lines)

        # 禁止表現が含まれていないか最終チェック
        for phrase in self.FORBIDDEN_PHRASES:
            content = content.replace(phrase, f"[禁止表現:{phrase}]")

        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    # ==========================================
    # B. シナリオ分析レポート
    # ==========================================

    def generate_analysis_report(
        self,
        records: List[ScenarioRecord],
        filepath: Optional[Path] = None
    ) -> str:
        """シナリオ分析レポートを生成"""
        if filepath is None:
            filepath = self.output_dir / "scenario_analysis_report.md"

        stats = ScenarioStatistics(records)
        result = stats.summarize()

        lines = []
        lines.append("# シナリオ分析レポート")
        lines.append(f"生成日時: {datetime.now().isoformat()}")
        lines.append("")

        # サンプルサイズ警告（先頭に表示）
        lines.append("## 標本サイズ評価")
        lines.append(self._render_sample_size_box(result.win_rate_sample_status))
        lines.append("")

        # 基本集計
        lines.append("## 基本集計")
        lines.append(f"- 総件数: {result.total}件")
        lines.append(f"- 評価済み: {result.evaluated}件")
        lines.append(f"- 未評価: {result.pending_evaluation}件")
        lines.append("")

        # 方向別
        lines.append("## 方向別件数")
        if result.direction_counts:
            for direction, count in result.direction_counts.items():
                lines.append(f"- {direction}: {count}件")
        else:
            lines.append("- データなし")
        lines.append("")

        # 銘柄別
        lines.append("## 銘柄別件数")
        if result.symbol_counts:
            for symbol, count in sorted(result.symbol_counts.items(), key=lambda x: -x[1]):
                lines.append(f"- {symbol}: {count}件")
        else:
            lines.append("- データなし")
        lines.append("")

        # 時間足別
        lines.append("## 時間足別件数")
        if result.timeframe_counts:
            for tf, count in result.timeframe_counts.items():
                lines.append(f"- {tf}: {count}件")
        else:
            lines.append("- データなし")
        lines.append("")

        # セッション別
        lines.append("## 市場セッション別件数")
        if result.session_counts:
            for session, count in result.session_counts.items():
                lines.append(f"- {session}: {count}件")
        else:
            lines.append("- データなし")
        lines.append("")

        # 結果分類
        lines.append("## 結果分類別件数")
        if result.result_breakdown:
            for rb in sorted(result.result_breakdown, key=lambda x: -x.count):
                lines.append(f"- {rb.result}: {rb.count}件 ({rb.percentage*100:.1f}%)")
        else:
            lines.append("- データなし")
        lines.append("")

        # Entry・未成立・無効化・曖昧
        lines.append("## 到達率")
        lines.append(self._render_wilson_ci(result.entry_rate_ci, "Entry率"))
        lines.append(self._render_wilson_ci(result.not_triggered_rate_ci, "NOT_TRIGGERED率"))
        lines.append(self._render_wilson_ci(result.invalidated_rate_ci, "INVALIDATED_BEFORE_ENTRY率"))
        lines.append(self._render_wilson_ci(result.ambiguous_rate_ci, "AMBIGUOUS率"))
        lines.append("")

        # 勝率
        lines.append("## 勝率")
        lines.append("")
        lines.append("### 分母に含める分類")
        lines.append("- WIN")
        lines.append("- LOSS")
        lines.append("- PARTIAL_WIN")
        lines.append("- PARTIAL_LOSS")
        lines.append("")
        lines.append("### 分母に含めない分類")
        lines.append("- NOT_TRIGGERED（エントリー未成立）")
        lines.append("- INVALIDATED_BEFORE_ENTRY（エントリー前無効化）")
        lines.append("- EXPIRED（期限切れ）")
        lines.append("- AMBIGUOUS（同一足でTP・SL両到達）")
        lines.append("- NOT_EVALUATED（未評価）")
        lines.append("")
        lines.append("### PARTIALの扱い")
        lines.append("- PARTIAL_WIN: 0.5勝として計算")
        lines.append("- PARTIAL_LOSS: 0.5敗として計算")
        lines.append("- 変更が必要な場合は設定で調整可能")
        lines.append("")

        if result.win_rate is not None:
            if result.win_rate_sample_status.display_allowed:
                lines.append(f"### 観測された勝率")
                lines.append(f"- 勝率: {result.win_rate*100:.1f}%")
                if result.win_rate_ci:
                    lines.append(f"- Wilson 95% CI: [{result.win_rate_ci.lower*100:.1f}%, {result.win_rate_ci.upper*100:.1f}%]")
                lines.append(f"- 母数: {result.win_rate_eligible_n}件")
            else:
                lines.append(f"### 観測された勝率（参考値）")
                lines.append(f"- 勝率: {result.win_rate*100:.1f}%")
                lines.append(f"- ⚠️ **{result.win_rate_sample_status.warning}**")
                lines.append(f"- 統計的判断には不十分です。追加データが必要です。")
        else:
            lines.append("- 勝率計算対象データなし")
        lines.append("")

        # 警告一覧
        if result.warnings:
            lines.append("## 統計警告")
            for w in result.warnings:
                lines.append(f"- [{w.severity}] {w.code}: {w.message}")
            lines.append("")

        # 免責
        lines.append("## 免責事項")
        lines.append("- 本レポートは観測データ上の集計結果です。")
        lines.append("- 過去の結果は将来の市場環境を反映するものではありません。")
        lines.append("- 売買推奨・利益保証・未来予測を行うものではありません。")

        content = "\n".join(lines)

        # 禁止表現最終チェック
        for phrase in self.FORBIDDEN_PHRASES:
            content = content.replace(phrase, f"[禁止表現:{phrase}]")

        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    # ==========================================
    # C. サマリーCSV
    # ==========================================

    def generate_summary_csv(
        self,
        records: List[ScenarioRecord],
        filepath: Optional[Path] = None
    ) -> str:
        """サマリーCSVを生成（csvモジュール使用）"""
        if filepath is None:
            filepath = self.output_dir / "scenario_summary.csv"

        headers = [
            "record_id", "source_id", "scenario_date", "published_at",
            "symbol", "timeframe", "market_session", "direction",
            "entry_type", "entry_triggered", "result_classification",
            "realized_r_multiple", "data_quality_score",
            "human_review_status", "human_corrected", "duplicate_flag"
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)

            for r in records:
                row = [
                    r.record_id,
                    r.source_id,
                    self._format_datetime(r.scenario_date),
                    self._format_datetime(r.published_at),
                    r.symbol,
                    r.timeframe or "",
                    r.market_session,
                    r.direction,
                    r.entry_type,
                    self._format_bool(r.entry_triggered),
                    r.result_classification,
                    self._format_decimal(r.realized_r_multiple),
                    r.data_quality_score if r.data_quality_score is not None else "",
                    r.human_review_status,
                    self._format_bool(r.human_corrected),
                    self._format_bool(r.duplicate_flag),
                ]
                writer.writerow(row)

        return str(filepath)

    # ==========================================
    # 一括生成
    # ==========================================

    def generate_all(self, records: List[ScenarioRecord]) -> dict:
        """全レポートを一括生成"""
        return {
            "data_quality_report": self.generate_data_quality_report(records),
            "analysis_report": self.generate_analysis_report(records),
            "summary_csv": self.generate_summary_csv(records),
        }
