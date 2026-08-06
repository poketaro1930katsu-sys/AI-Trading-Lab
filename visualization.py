"""
visualization.py
================
AI Trading Lab Version 1.1 暫定版
可視化モジュール

パーセンタイルバンド、信頼帯、比較グラフの生成を担当。
"""

from __future__ import annotations

from typing import Sequence
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


class ColorPalette:
    """グラフ用カラーパレット。"""
    P5 = '#ffcccc'
    P25 = '#ff9999'
    P50 = '#cc0000'
    P75 = '#ff9999'
    P95 = '#ffcccc'
    INITIAL = '#666666'

    RR_1_1 = '#e74c3c'
    RR_1_15 = '#f39c12'
    RR_1_2 = '#27ae60'

    WR_45 = '#e74c3c'
    WR_50 = '#f39c12'
    WR_55 = '#3498db'
    WR_60 = '#27ae60'

    RISK_1 = '#27ae60'
    RISK_2 = '#3498db'
    RISK_5 = '#f39c12'
    RISK_10 = '#e74c3c'


class Visualizer:
    """シミュレーション結果の可視化を担当するクラス。"""

    def __init__(self, output_dir: str = 'outputs'):
        """
        Parameters
        ----------
        output_dir : str
            グラフの出力先ディレクトリ。
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.colors = ColorPalette()

    def _plot_percentile_bands(
        self,
        ax,
        percentile_bands: np.ndarray,
        trades: Sequence[int],
        color: str,
        label: str,
    ) -> None:
        """パーセンタイルバンドをプロットする。"""
        ax.fill_between(
            trades, percentile_bands[:, 0], percentile_bands[:, 4],
            alpha=0.15, color=color, label=f'{label} 5%-95%帯'
        )
        ax.fill_between(
            trades, percentile_bands[:, 1], percentile_bands[:, 3],
            alpha=0.25, color=color
        )
        ax.plot(
            trades, percentile_bands[:, 2],
            color=color, linewidth=2.5, label=f'{label} 中央値'
        )

    def plot_comparison_rr(
        self,
        results: list,
        win_rate: str,
        risk_rate: str,
        filename: str = 'comparison_rr.png',
    ) -> str:
        """RR比を変えた場合の比較グラフを生成する。"""
        fig, ax = plt.subplots(figsize=(12, 7))

        rr_colors = {'1:1.0': self.colors.RR_1_1, '1:1.5': self.colors.RR_1_15, '1:2.0': self.colors.RR_1_2}

        for r in results:
            if r['勝率'] == win_rate and r['リスク率'] == risk_rate:
                rr = r['RR比']
                raw = r['_raw']
                trades = range(len(raw.percentile_bands))
                self._plot_percentile_bands(
                    ax, raw.percentile_bands, trades, rr_colors[rr], rr
                )

        ax.axhline(y=1000, color=self.colors.INITIAL, linestyle='--', alpha=0.7, label='初期資金')
        ax.set_title(f'勝率{win_rate} / リスク{risk_rate} でのRR比比較（中央値＋パーセンタイル帯）',
                     fontsize=13, fontweight='bold')
        ax.set_xlabel('取引回数', fontsize=11)
        ax.set_ylabel('残高（円）', fontsize=11)
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)

        path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        return str(path)

    def plot_comparison_winrate(
        self,
        results: list,
        rr: str,
        risk_rate: str,
        filename: str = 'comparison_winrate.png',
    ) -> str:
        """勝率を変えた場合の比較グラフを生成する。"""
        fig, ax = plt.subplots(figsize=(12, 7))

        wr_colors = {'45%': self.colors.WR_45, '50%': self.colors.WR_50,
                     '55%': self.colors.WR_55, '60%': self.colors.WR_60}

        for r in results:
            if r['RR比'] == rr and r['リスク率'] == risk_rate:
                wr = r['勝率']
                raw = r['_raw']
                trades = range(len(raw.percentile_bands))
                self._plot_percentile_bands(
                    ax, raw.percentile_bands, trades, wr_colors[wr], wr
                )

        ax.axhline(y=1000, color=self.colors.INITIAL, linestyle='--', alpha=0.7, label='初期資金')
        ax.set_title(f'RR {rr} / リスク{risk_rate} での勝率比較（中央値＋パーセンタイル帯）',
                     fontsize=13, fontweight='bold')
        ax.set_xlabel('取引回数', fontsize=11)
        ax.set_ylabel('残高（円）', fontsize=11)
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)

        path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        return str(path)

    def plot_comparison_risk(
        self,
        results: list,
        win_rate: str,
        rr: str,
        filename: str = 'comparison_risk.png',
    ) -> str:
        """リスク率を変えた場合の比較グラフを生成する。"""
        fig, ax = plt.subplots(figsize=(12, 7))

        risk_colors = {'1%': self.colors.RISK_1, '2%': self.colors.RISK_2,
                       '5%': self.colors.RISK_5, '10%': self.colors.RISK_10}

        for r in results:
            if r['勝率'] == win_rate and r['RR比'] == rr:
                risk = r['リスク率']
                raw = r['_raw']
                trades = range(len(raw.percentile_bands))
                self._plot_percentile_bands(
                    ax, raw.percentile_bands, trades, risk_colors[risk], risk
                )

        ax.axhline(y=1000, color=self.colors.INITIAL, linestyle='--', alpha=0.7, label='初期資金')
        ax.set_title(f'勝率{win_rate} / RR {rr} でのリスク率比較（中央値＋パーセンタイル帯）',
                     fontsize=13, fontweight='bold')
        ax.set_xlabel('取引回数', fontsize=11)
        ax.set_ylabel('残高（円）', fontsize=11)
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)

        path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        return str(path)

    def plot_distribution(
        self,
        results: list,
        conditions: list,
        filename: str = 'distribution.png',
    ) -> str:
        """最終残高の分布グラフを生成する。"""
        n = len(conditions)
        ncols = 3
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(18, 5 * nrows))
        if nrows == 1:
            axes = axes.reshape(1, -1)

        colors = ['#e74c3c', '#f39c12', '#27ae60', '#3498db', '#9b59b6', '#1abc9c']

        for idx, (wr, rr, risk) in enumerate(conditions):
            ax = axes[idx // ncols, idx % ncols]

            for r in results:
                if r['勝率'] == wr and r['RR比'] == rr and r['リスク率'] == risk:
                    balances = r['_raw'].final_balances
                    color = colors[idx % len(colors)]

                    ax.hist(balances, bins=80, color=color, alpha=0.7, edgecolor='white', linewidth=0.3)
                    ax.axvline(1000, color='gray', linestyle='--', linewidth=2, label='初期資金')
                    ax.axvline(np.median(balances), color='black', linestyle='-', linewidth=2,
                               label=f'中央値 {np.median(balances):.0f}')
                    ax.axvline(np.mean(balances), color='white', linestyle='--', linewidth=2,
                               label=f'平均 {np.mean(balances):.0f}')

                    ax.set_title(f'{wr} / {rr} / {risk}', fontsize=12, fontweight='bold')
                    ax.set_xlabel('最終残高（円）')
                    ax.set_ylabel('頻度')
                    ax.legend(fontsize=8)
                    ax.grid(True, alpha=0.3, axis='y')

                    q99 = np.percentile(balances, 99)
                    ax.set_xlim(0, max(q99 * 1.1, 1500))

        for idx in range(n, nrows * ncols):
            axes[idx // ncols, idx % ncols].axis('off')

        plt.suptitle('最終残高の分布', fontsize=14, fontweight='bold')
        plt.tight_layout()
        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        return str(path)

    def plot_summary_dashboard(
        self,
        results: list,
        filename: str = 'dashboard.png',
    ) -> str:
        """サマリーダッシュボードを生成する。"""
        fig = plt.figure(figsize=(20, 14))
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

        for idx, rr in enumerate(['1:1.0', '1:1.5', '1:2.0']):
            ax = fig.add_subplot(gs[0, idx])
            self._plot_heatmap_metric(ax, results, rr, '平均残高', 'YlGn')
            ax.set_title(f'RR {rr} / 平均残高', fontsize=11, fontweight='bold')

        for idx, rr in enumerate(['1:1.0', '1:1.5', '1:2.0']):
            ax = fig.add_subplot(gs[1, idx])
            self._plot_heatmap_metric(ax, results, rr, '元本超え確率', 'Greens', is_pct=True)
            ax.set_title(f'RR {rr} / 元本超え確率', fontsize=11, fontweight='bold')

        for idx, rr in enumerate(['1:1.0', '1:1.5', '1:2.0']):
            ax = fig.add_subplot(gs[2, idx])
            self._plot_heatmap_metric(ax, results, rr, 'DD50%到達', 'Reds', is_pct=True)
            ax.set_title(f'RR {rr} / DD50%到達確率', fontsize=11, fontweight='bold')

        plt.suptitle('FX資金管理シミュレーション - ダッシュボード', fontsize=16, fontweight='bold')
        path = self.output_dir / filename
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        return str(path)

    def _plot_heatmap_metric(
        self,
        ax,
        results: list,
        rr: str,
        metric: str,
        cmap: str,
        is_pct: bool = False,
    ) -> None:
        """ヒートマップをプロットする（内部メソッド）。"""
        data = {}
        for r in results:
            if r['RR比'] == rr:
                wr = int(r['勝率'].replace('%', ''))
                risk = int(r['リスク率'].replace('%', ''))
                if metric == '平均残高':
                    val = r['平均残高']
                elif metric == '元本超え確率':
                    val = float(r['元本超え確率'].replace('%', ''))
                elif metric == 'DD50%到達':
                    val = float(r['DD50%到達'].replace('%', ''))
                else:
                    val = 0
                data[(wr, risk)] = val

        wrs = sorted(set(k[0] for k in data.keys()))
        risks = sorted(set(k[1] for k in data.keys()))
        matrix = np.array([[data.get((wr, risk), 0) for risk in risks] for wr in wrs])

        im = ax.imshow(matrix, cmap=cmap, aspect='auto')
        for i in range(len(wrs)):
            for j in range(len(risks)):
                val = matrix[i, j]
                text = f'{val:.0f}' if not is_pct else f'{val:.1f}'
                text_color = 'white' if val > matrix.max() * 0.6 else 'black'
                ax.text(j, i, text, ha='center', va='center', color=text_color, fontsize=10, fontweight='bold')

        ax.set_xticks(range(len(risks)))
        ax.set_xticklabels([f'{r}%' for r in risks])
        ax.set_yticks(range(len(wrs)))
        ax.set_yticklabels([f'{w}%' for w in wrs])
        ax.set_xlabel('リスク率')
        ax.set_ylabel('勝率')
        plt.colorbar(im, ax=ax, fraction=0.046)
