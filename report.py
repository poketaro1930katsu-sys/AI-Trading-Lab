"""
report.py
=========
AI Trading Lab Version 1.1 暫定版
CSV・レポート出力モジュール

CSV出力、レポート生成、比較結果出力を担当。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


class CSVExporter:
    """シミュレーション結果をCSV形式で出力するクラス。"""

    def __init__(self, output_dir: str = 'outputs'):
        """
        Parameters
        ----------
        output_dir : str
            CSVの出力先ディレクトリ。
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_results(
        self,
        results: list,
        filename: str = 'fx_monte_carlo_results.csv',
    ) -> str:
        """全条件の結果をCSVに出力する。

        Parameters
        ----------
        results : list
            各条件の結果辞書のリスト。
        filename : str
            出力ファイル名。

        Returns
        -------
        str
            保存されたファイルパス。
        """
        records = []
        for r in results:
            record = {k: v for k, v in r.items() if k != '_raw'}
            records.append(record)

        df = pd.DataFrame(records)

        # 表示用の文字列は変更せず、並べ替え専用の数値列を作成する。
        # 「可変」など数値へ変換できない値は無限大として扱い、
        # 固定値を持つ条件より後ろに並べる。
        sort_columns = []

        if '勝率' in df.columns:
            df['勝率_sort'] = pd.to_numeric(
                df['勝率']
                .astype(str)
                .str.replace('%', '', regex=False),
                errors='coerce',
            ).fillna(float('inf'))
            sort_columns.append('勝率_sort')

        if 'RR比' in df.columns:
            df['RR_sort'] = pd.to_numeric(
                df['RR比']
                .astype(str)
                .str.replace('1:', '', regex=False),
                errors='coerce',
            ).fillna(float('inf'))
            sort_columns.append('RR_sort')

        if 'リスク率' in df.columns:
            df['リスク_sort'] = pd.to_numeric(
                df['リスク率']
                .astype(str)
                .str.replace('%', '', regex=False),
                errors='coerce',
            ).fillna(float('inf'))
            sort_columns.append('リスク_sort')

        if sort_columns:
            df = df.sort_values(sort_columns, kind='stable')
            df = df.drop(columns=sort_columns)

        path = self.output_dir / filename
        df.to_csv(path, index=False, encoding='utf-8-sig')
        return str(path)

    def export_raw_balances(
        self,
        result,
        filename: str = 'raw_balances.csv',
    ) -> str:
        """最終残高の生データをCSVに出力する。

        Parameters
        ----------
        result : MonteCarloResult
            単一条件の結果。
        filename : str
            出力ファイル名。

        Returns
        -------
        str
            保存されたファイルパス。
        """
        df = pd.DataFrame({
            'trial': range(1, len(result.final_balances) + 1),
            'final_balance': result.final_balances,
            'max_drawdown': result.max_drawdowns,
        })
        path = self.output_dir / filename
        df.to_csv(path, index=False, encoding='utf-8-sig')
        return str(path)


class ReportGenerator:
    """シミュレーション結果のレポートを生成するクラス。"""

    def __init__(self, output_dir: str = 'outputs'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_markdown_report(
        self,
        results: list,
        config,
        filename: str = 'execution_report.md',
    ) -> str:
        """Markdown形式のレポートを生成する。

        Parameters
        ----------
        results : list
            結果のリスト。
        config : SimulationConfig
            シミュレーション設定。
        filename : str
            出力ファイル名。

        Returns
        -------
        str
            保存されたファイルパス。
        """
        lines = []
        lines.append("# FX資金管理モンテカルロ・シミュレーション レポート")
        lines.append("")
        lines.append(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("## シミュレーション設定")
        lines.append("")
        lines.append(f"| 項目 | 値 |")
        lines.append(f"|:---|:---|")
        lines.append(f"| 初期資金 | {config.initial_capital}円 |")
        lines.append(f"| 取引期間 | {config.trading_days}日（{config.total_trades}回取引） |")
        lines.append(f"| 試行回数 | {config.n_simulations:,}回 |")
        lines.append(f"| コスト率 | {config.cost_rate*100:.0f}%（総リスク額に対する割合） |")
        lines.append(f"| 最低取引可能額 | {config.min_tradeable}円 |")
        lines.append(f"| 乱数シード | {config.rng_seed} |")
        lines.append(f"| 乱数方式 | {'共通乱数法' if config.random_method.name == 'COMMON' else '独立乱数法'} |")
        lines.append("")
        lines.append("## 結果一覧")
        lines.append("")

        headers = ['モデル', '乱数法', '勝率', 'RR比', 'リスク率', '平均残高', '中央値',
                   '元本超え', '最終2倍', '期間中2倍', '破産', '停止', 'DD20%', 'DD30%', 'DD50%']
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join([":---:"] * len(headers)) + " |")

        for r in results:
            row = [
                r.get('モデル', ''),
                r.get('乱数法', ''),
                r.get('勝率', ''),
                r.get('RR比', ''),
                r.get('リスク率', ''),
                str(r.get('平均残高', '')),
                str(r.get('中央値残高', '')),
                r.get('元本超え確率', ''),
                r.get('最終2倍達成', ''),
                r.get('期間中2倍到達', ''),
                r.get('破産確率', ''),
                r.get('取引停止確率', ''),
                r.get('DD20%到達', ''),
                r.get('DD30%到達', ''),
                r.get('DD50%到達', ''),
            ]
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")
        lines.append("## 注意事項")
        lines.append("")
        lines.append("- 本シミュレーションは教育目的であり、将来の利益を保証するものではありません。")
        lines.append("- 「RR比を上げても勝率が一定」という仮定は、実際の市場では成り立たない可能性があります。")
        lines.append("- 過去のシミュレーション結果は、将来の市場環境を反映するものではありません。")

        content = "\n".join(lines)
        path = self.output_dir / filename
        path.write_text(content, encoding='utf-8')
        return str(path)

    def generate_comparison_report(
        self,
        common_results: list,
        independent_results: list,
        filename: str = 'comparison_report.md',
    ) -> str:
        """共通乱数法と独立乱数法の比較レポートを生成する。"""
        lines = []
        lines.append("# 共通乱数法 vs 独立乱数法 比較レポート")
        lines.append("")
        lines.append("## 比較表")
        lines.append("")
        lines.append("| 勝率 | RR比 | リスク率 | 共通-平均 | 独立-平均 | 差分 | 共通-中央値 | 独立-中央値 | 差分 |")
        lines.append("|:---|:---|:---|---:|---:|---:|---:|---:|---:|")

        for c, i in zip(common_results, independent_results):
            lines.append(
                f"| {c['勝率']} | {c['RR比']} | {c['リスク率']} | "
                f"{c['平均残高']:.1f} | {i['平均残高']:.1f} | {c['平均残高']-i['平均残高']:+.1f} | "
                f"{c['中央値残高']:.1f} | {i['中央値残高']:.1f} | {c['中央値残高']-i['中央値残高']:+.1f} |"
            )

        lines.append("")
        lines.append("## 解説")
        lines.append("")
        lines.append("共通乱数法は条件間の比較ばらつき（モンテカルロ誤差）を低減する技法です。")
        lines.append("同じ乱数ストリームを使用することで、条件間の差異を「パラメータの違い」に")
        lines.append("帰因させ、乱数の違いによるノイズを除去します。")
        lines.append("")
        lines.append("独立乱数法は各条件で独立した乱数を使用するため、")
        lines.append("条件間の相関が低くなりますが、比較時のばらつきが大きくなります。")

        content = "\n".join(lines)
        path = self.output_dir / filename
        path.write_text(content, encoding='utf-8')
        return str(path)


def generate_changelog() -> str:
    """Version1からVersion1.1の変更点を生成する。"""
    return """
# Version1.1 変更点一覧

## 新機能

### 1. パーセンタイルバンド（各時点の中央値）
- **変更前**: 最終残高が中央値だった1本の資金曲線
- **変更後**: 各取引時点における全試行の5%, 25%, 50%, 75%, 95%パーセンタイルを計算
- **理由**: 過程（path）の不確実性を可視化するため

### 2. 信頼帯グラフ
- **変更前**: best_curve / worst_curve を表示
- **変更後**: 5%〜95%の信頼帯をグラフ表示、中央値を太線で表示
- **理由**: 極端値（最良・最悪）ではなく、統計的に意味のある範囲を表示

### 3. 2倍達成の分離
- **変更前**: 「2倍達成確率」のみ
- **変更後**:
  - 「最終残高が2倍以上」（期間終了時点）
  - 「期間中に一度でも2倍到達」（過程）
- **理由**: 途中で2倍になってもその後減少するケースと、最終的に2倍を維持するケースを区別

### 4. 総リスク計算
- **変更前**: 価格変動損失のみをリスクとしていた
- **変更後**: 総リスク = 価格変動損失 + スプレッド + 手数料
- **数式**:
  - total_risk = balance × risk_pct
  - cost = total_risk × cost_rate
  - price_risk = total_risk - cost
  - 勝ち: balance = balance - cost + price_risk × RR
  - 負け: balance = balance - total_risk

### 5. 自動検証の修正
- **削除**: 平均値が5%点〜95%点の範囲内
- **追加**: 5%点 <= 中央値 <= 95%点
- **追加**: 25%点 <= 中央値 <= 75%点
- **追加**: DD到達率の単調性（DD20 >= DD30 >= DD50）
- **追加**: 信頼区間の整合性検証

### 6. DD計算の強化
- **変更前**: 勝敗更新後のみDD計算
- **変更後**: コスト控除後・勝敗更新後・停止時・破産時のすべてでDD更新
- **理由**: トレーダーの心理的痛苦は瞬間的な資金減少に反応するため

### 7. 共通乱数法
- **新規**: 全条件で同じ乱数ストリームを使用
- **比較**: 独立乱数法（各条件で異なる乱数）も実装
- **理由**: 条件間の比較ばらつき（モンテカルロ誤差）を低減

### 8. 相場レジームモデル
- **新規**: Bull/Normal/Bearの3状態マルコフ連鎖
- **勝率固定モデル**: 従来通り（勝率・RRが固定）
- **レジームモデル**: 状態遷移により勝率・RRが動的に変化
- **遷移確率**:
  - Bull→Bull:70%, Normal→Normal:60%, Bear→Bear:70%
  - 各レジームの勝率: Bull 65%, Normal 50%, Bear 35%

### 9. DD到達率
- **新規**: DD20%, DD30%, DD50%到達確率を追加集計
- **理由**: 資金がどの程度減少する可能性があるかを段階的に把握

### 10. 95%信頼区間
- **Wilson法**: 確率（元本超え確率など）の信頼区間
- **Bootstrap法**: 統計量（平均残高など）の信頼区間
- **採用理由**: Wilson法は二項分布の正確な近似、Bootstrap法は非正規分布に対応

## 設計改善

### モジュール化
- Module1: 設定・Config
- Module2: シミュレーター本体
- Module3: 統計解析
- Module4: グラフ生成
- Module5: CSV・レポート

### 型ヒント
- 全関数・メソッドに型ヒントを追加
- NumPy Docstring形式のドキュメント

### 例外処理
- 設定値のバリデーション
- 遷移行列・確率の整合性検証

### 拡張性
- RegimeConfigによるレジーム追加の容易化
- Visualizationのメソッド追加による新規グラフ対応
"""