"""
main.py
=======
AI Trading Lab Version 1.1 暫定版
メイン実行スクリプト

使用方法:
    python main.py

出力:
    outputs/fx_monte_carlo_results.csv
    outputs/comparison_rr.png
    outputs/comparison_winrate.png
    outputs/comparison_risk.png
    outputs/distribution.png
    outputs/dashboard.png
    outputs/execution_report.md
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from config import (
    SimulationConfig, RegimeConfig, RegimeParameters,
    RandomMethod, ModelType, create_default_regime_config
)
from simulator import TradeSimulator, MonteCarloEngine, MonteCarloResult
from statistics import ConfidenceIntervalCalculator, ResultValidator, add_confidence_intervals
from visualization import Visualizer
from report import CSVExporter, ReportGenerator


def run_simulation_suite(
    win_rates: list[float],
    reward_ratios: list[float],
    risk_rates: list[float],
    config: SimulationConfig,
    regime_config: RegimeConfig | None = None,
    label_prefix: str = "",
) -> list[dict]:
    """シミュレーションスイートを実行する。

    Parameters
    ----------
    win_rates : list[float]
        勝率のリスト。
    reward_ratios : list[float]
        RR比のリスト。
    risk_rates : list[float]
        リスク率のリスト。
    config : SimulationConfig
        シミュレーション設定。
    regime_config : RegimeConfig | None
        レジームモデル設定。
    label_prefix : str
        条件ラベルの接頭辞。

    Returns
    -------
    list[dict]
        各条件の結果辞書のリスト。
    """
    engine = MonteCarloEngine(config, regime_config)
    ci_calc = ConfidenceIntervalCalculator()
    validator = ResultValidator()

    results = []
    total = len(win_rates) * len(reward_ratios) * len(risk_rates)
    condition_idx = 0

    for win_rate in win_rates:
        for rr in reward_ratios:
            for risk in risk_rates:
                condition_idx += 1
                label = f"{label_prefix}勝率{int(win_rate*100)}%/RR{rr}/リスク{int(risk*100)}%"
                print(f"  [{condition_idx:2d}/{total}] {label} ... ", end="", flush=True)
                t0 = time.time()

                seed = config.get_seed_for_condition(condition_idx)
                raw = engine.run(win_rate, rr, risk, seed)
                raw = add_confidence_intervals(raw, config.n_simulations, seed, ci_calc)

                validator.validate(raw, label)
                validator.add_ci_validation(raw, label)

                results.append({
                    'モデル': 'レジーム' if regime_config else '勝率固定',
                    '乱数法': '共通' if config.random_method == RandomMethod.COMMON else '独立',
                    '勝率': f"{int(win_rate*100)}%" if not regime_config else '可変',
                    'RR比': f"1:{rr}",
                    'リスク率': f"{int(risk*100)}%",
                    '平均残高': round(raw.mean_final, 1),
                    '中央値残高': round(raw.median_final, 1),
                    '5%点': round(raw.p5_final, 1),
                    '25%点': round(raw.p25_final, 1),
                    '75%点': round(raw.p75_final, 1),
                    '95%点': round(raw.p95_final, 1),
                    '元本超え確率': f"{(1-raw.below_initial_prob)*100:.1f}%",
                    '元本超えCI': f"[{raw.ci_above_initial[0]*100:.1f}%, {raw.ci_above_initial[1]*100:.1f}%]",
                    '最終2倍達成': f"{raw.final_doubled_prob*100:.1f}%",
                    '最終2倍CI': f"[{raw.ci_final_doubled[0]*100:.1f}%, {raw.ci_final_doubled[1]*100:.1f}%]",
                    '期間中2倍到達': f"{raw.ever_doubled_prob*100:.1f}%",
                    '期間中2倍CI': f"[{raw.ci_ever_doubled[0]*100:.1f}%, {raw.ci_ever_doubled[1]*100:.1f}%]",
                    '破産確率': f"{raw.bankrupt_prob*100:.1f}%",
                    '破産CI': f"[{raw.ci_bankrupt[0]*100:.1f}%, {raw.ci_bankrupt[1]*100:.1f}%]",
                    '取引停止確率': f"{raw.stopped_prob*100:.1f}%",
                    '停止CI': f"[{raw.ci_stopped[0]*100:.1f}%, {raw.ci_stopped[1]*100:.1f}%]",
                    '元本割れ確率': f"{raw.below_initial_prob*100:.1f}%",
                    'DD20%到達': f"{raw.dd20_prob*100:.1f}%",
                    'DD20%CI': f"[{raw.ci_dd20[0]*100:.1f}%, {raw.ci_dd20[1]*100:.1f}%]",
                    'DD30%到達': f"{raw.dd30_prob*100:.1f}%",
                    'DD30%CI': f"[{raw.ci_dd30[0]*100:.1f}%, {raw.ci_dd30[1]*100:.1f}%]",
                    'DD50%到達': f"{raw.dd50_prob*100:.1f}%",
                    'DD50%CI': f"[{raw.ci_dd50[0]*100:.1f}%, {raw.ci_dd50[1]*100:.1f}%]",
                    '最大DD中央値': f"{np.median(raw.max_drawdowns)*100:.1f}%",
                    '平均残高CI': f"[{raw.ci_mean[0]:.1f}, {raw.ci_mean[1]:.1f}]",
                    '中央値残高CI': f"[{raw.ci_median[0]:.1f}, {raw.ci_median[1]:.1f}]",
                    '_raw': raw,
                })
                print(f"完了 ({time.time()-t0:.1f}s)")

    print(f"\n{validator.report()}")
    return results


def main():
    """メイン実行関数。"""
    print("=" * 80)
    print("【AI Trading Lab Version 1.1 暫定版】")
    print("【FX資金管理モンテカルロ・シミュレーション】")
    print("=" * 80)

    # パラメータ設定
    WIN_RATES = [0.45, 0.50, 0.55, 0.60]
    REWARD_RATIOS = [1.0, 1.5, 2.0]
    RISK_PER_TRADE = [0.01, 0.02, 0.05, 0.10]

    total_conditions = len(WIN_RATES) * len(REWARD_RATIOS) * len(RISK_PER_TRADE)
    print(f"条件数: {total_conditions}（勝率×RR比×リスク率）")
    print(f"試行回数: 10,000回/条件")
    print(f"総取引回数: 60回/試行")
    print("=" * 80)

    # 実行1: 勝率固定モデル（共通乱数）
    print("\n【実行1: 勝率固定モデル - 共通乱数法】")
    print("-" * 80)
    cfg_common = SimulationConfig(
        n_simulations=10000, rng_seed=42, random_method=RandomMethod.COMMON
    )
    results_fixed_common = run_simulation_suite(
        WIN_RATES, REWARD_RATIOS, RISK_PER_TRADE, cfg_common
    )

    # 実行2: 勝率固定モデル（独立乱数）
    print("\n【実行2: 勝率固定モデル - 独立乱数法】")
    print("-" * 80)
    cfg_indep = SimulationConfig(
        n_simulations=10000, rng_seed=42, random_method=RandomMethod.INDEPENDENT
    )
    results_fixed_indep = run_simulation_suite(
        WIN_RATES, REWARD_RATIOS, RISK_PER_TRADE, cfg_indep
    )

    # 実行3: レジームモデル（代表的条件のみ）
    print("\n【実行3: レジームモデル - 共通乱数法（代表的条件）】")
    print("-" * 80)
    print("※ レジームモデルはリスク率2%・5%の6条件のみ実行")
    regime_cfg = create_default_regime_config()
    cfg_regime = SimulationConfig(
        n_simulations=10000, rng_seed=42,
        random_method=RandomMethod.COMMON,
        model_type=ModelType.REGIME
    )
    results_regime = run_simulation_suite(
        [0.5], REWARD_RATIOS, [0.02, 0.05], cfg_regime, regime_cfg, "レジーム/"
    )

    # グラフ生成
    print("\n【グラフ生成】")
    print("-" * 80)
    viz = Visualizer(output_dir='outputs')

    print("  RR比較グラフ...")
    viz.plot_comparison_rr(results_fixed_common, '50%', '2%')

    print("  勝率比較グラフ...")
    viz.plot_comparison_winrate(results_fixed_common, '1:1.5', '2%')

    print("  リスク比較グラフ...")
    viz.plot_comparison_risk(results_fixed_common, '50%', '1:1.5')

    print("  分布グラフ...")
    viz.plot_distribution(
        results_fixed_common,
        [('50%', '1:1.5', '2%'), ('45%', '1:2.0', '1%'),
         ('55%', '1:1.5', '2%'), ('60%', '1:2.0', '2%')]
    )

    print("  ダッシュボード...")
    viz.plot_summary_dashboard(results_fixed_common)

    # CSV出力
    print("\n【CSV出力】")
    print("-" * 80)
    exporter = CSVExporter(output_dir='outputs')

    print("  勝率固定（共通乱数）...")
    exporter.export_results(results_fixed_common, 'fx_monte_carlo_fixed_common.csv')

    print("  勝率固定（独立乱数）...")
    exporter.export_results(results_fixed_indep, 'fx_monte_carlo_fixed_indep.csv')

    print("  レジームモデル...")
    exporter.export_results(results_regime, 'fx_monte_carlo_regime.csv')

    # レポート生成
    print("\n【レポート生成】")
    print("-" * 80)
    reporter = ReportGenerator(output_dir='outputs')

    print("  実行レポート...")
    reporter.generate_markdown_report(results_fixed_common, cfg_common)

    print("  比較レポート...")
    reporter.generate_comparison_report(results_fixed_common, results_fixed_indep)

    print("\n" + "=" * 80)
    print("【全処理完了】")
    print("=" * 80)
    print("\n出力ファイル:")
    for f in sorted(Path('outputs').glob('*')):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
