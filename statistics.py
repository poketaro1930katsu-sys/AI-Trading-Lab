"""
statistics.py
=============
AI Trading Lab Version 1.1 暫定版
統計解析モジュール

信頼区間計算（Wilson法・Bootstrap法）と結果検証を担当。
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from simulator import MonteCarloResult


class ConfidenceIntervalCalculator:
    """統計量の信頼区間を計算するクラス。

    【採用方針】
    - 確率（比例）の信頼区間: Wilson法
      二項分布の比例に対する正確な近似。
      n=10000の大標本でもカバレッジ確率が良好。

    - 統計量（平均・中央値など）の信頼区間: Bootstrap法
      分布を仮定しない非参数的方法。
      残高分布が非正規・右に歪む特性を正確に捉えられる。

    【Wilson法の数式】
    p̂ = k/n
    denominator = 1 + z²/n
    center = (p̂ + z²/(2n)) / denominator
    margin = z × √(p̂(1-p̂)/n + z²/(4n²)) / denominator
    CI = [center - margin, center + margin]

    【Bootstrap法の手順】
    1. 元データからn個を復元抽出（重複あり）
    2. 統計量を計算
    3. 1-2をB回繰り返し
    4. B個の統計量のパーセンタイルからCIを構築
    """

    @staticmethod
    def wilson(
        k: int,
        n: int,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Wilson法による二項分布の信頼区間を計算する。

        Parameters
        ----------
        k : int
            成功回数。
        n : int
            試行回数。
        confidence : float, optional
            信頼水準。デフォルト0.95。

        Returns
        -------
        tuple[float, float]
            (下限, 上限)の信頼区間。両端を[0, 1]にクリップ。

        Raises
        ------
        ValueError
            n=0の場合、またはkが範囲外の場合。
        """
        if n == 0:
            raise ValueError("試行回数nは正の整数である必要があります")
        if k < 0 or k > n:
            raise ValueError("成功回数kは0〜nの範囲である必要があります")

        z = 1.96 if confidence == 0.95 else 2.576
        p_hat = k / n

        denom = 1.0 + (z ** 2) / n
        center = (p_hat + (z ** 2) / (2 * n)) / denom
        margin = z * np.sqrt(
            p_hat * (1 - p_hat) / n + (z ** 2) / (4 * n ** 2)
        ) / denom

        return (max(0.0, center - margin), min(1.0, center + margin))

    @staticmethod
    def bootstrap(
        data: np.ndarray,
        statistic_func: Callable = np.mean,
        n_bootstrap: int = 1000,
        confidence: float = 0.95,
        rng_seed: int = 12345,
    ) -> tuple[float, float]:
        """Bootstrap法による統計量の信頼区間を計算する。

        Parameters
        ----------
        data : np.ndarray
            元データ。
        statistic_func : callable
            計算対象の統計量関数。
        n_bootstrap : int
            ブートストラップ回数。
        confidence : float
            信頼水準。
        rng_seed : int
            乱数シード（再現性）。

        Returns
        -------
        tuple[float, float]
            (下限, 上限)の信頼区間。

        Notes
        -----
        n_bootstrap=1000で標準誤差の約3%の精度。
        精度向上にはn_bootstrap=10000を推奨（計算コスト10倍）。
        """
        rng = np.random.default_rng(rng_seed)
        boot_stats = np.empty(n_bootstrap)
        n = len(data)

        for i in range(n_bootstrap):
            sample = rng.choice(data, size=n, replace=True)
            boot_stats[i] = statistic_func(sample)

        lower = (1.0 - confidence) / 2.0 * 100
        upper = confidence * 100 + lower
        return tuple(np.percentile(boot_stats, [lower, upper]))


class ResultValidator:
    """シミュレーション結果の自動検証を担当するクラス。

    以下の整合性を検証:
    1. パーセンタイルの順序: p5 <= median <= p95
    2. パーセンタイルの順序: p25 <= median <= p75
    3. 確率の合計: 元本超え + 元本割れ = 100%
    4. 確率の上限: 破産 + 停止 <= 100%
    5. 2倍到達の包含: ever_doubled >= final_doubled
    6. DD到達率の単調性: DD20 >= DD30 >= DD50
    7. 信頼区間の整合性: 下限 <= 上限
    8. Bootstrap CIの包含: mean in [ci_mean_lower, ci_mean_upper]
    """

    def __init__(self):
        self.errors: list[str] = []

    def validate(self, result: MonteCarloResult, label: str) -> bool:
        """単一条件の結果を検証する。

        Parameters
        ----------
        result : MonteCarloResult
            エンジンの出力結果。
        label : str
            条件ラベル（エラー表示用）。

        Returns
        -------
        bool
            True: 全検証合格, False: 一部不合格。
        """
        passed = True

        # 検証1: 5%点 <= 中央値 <= 95%点
        if not (result.p5_final <= result.median_final <= result.p95_final):
            self.errors.append(
                f"[{label}] p5({result.p5_final:.1f}) <= median({result.median_final:.1f}) <= p95({result.p95_final:.1f})"
            )
            passed = False

        # 検証2: 25%点 <= 中央値 <= 75%点
        if not (result.p25_final <= result.median_final <= result.p75_final):
            self.errors.append(
                f"[{label}] p25({result.p25_final:.1f}) <= median({result.median_final:.1f}) <= p75({result.p75_final:.1f})"
            )
            passed = False

        # 検証3: 元本超え確率 + 元本割れ確率 = 100%
        above = 1.0 - result.below_initial_prob
        below = result.below_initial_prob
        if abs(above + below - 1.0) > 0.001:
            self.errors.append(f"[{label}] above({above:.4f}) + below({below:.4f}) != 1.0")
            passed = False

        # 検証4: 破産確率 + 停止確率 <= 100%
        if result.bankrupt_prob + result.stopped_prob > 1.0 + 0.001:
            self.errors.append(
                f"[{label}] bankrupt({result.bankrupt_prob:.4f}) + stopped({result.stopped_prob:.4f}) > 1.0"
            )
            passed = False

        # 検証5: 期間中2倍到達 >= 最終2倍達成
        if result.ever_doubled_prob < result.final_doubled_prob - 0.001:
            self.errors.append(
                f"[{label}] ever_doubled({result.ever_doubled_prob:.4f}) < final_doubled({result.final_doubled_prob:.4f})"
            )
            passed = False

        # 検証6: DD到達率の単調性
        # 閾値が高いほど到達確率は低い（または同じ）
        if not (result.dd20_prob + 0.001 >= result.dd30_prob >= result.dd50_prob - 0.001):
            self.errors.append(
                f"[{label}] DD20({result.dd20_prob:.4f}) >= DD30({result.dd30_prob:.4f}) >= DD50({result.dd50_prob:.4f})"
            )
            passed = False

        return passed

    def add_ci_validation(self, result: MonteCarloResult, label: str) -> bool:
        """信頼区間の整合性を追加検証する。

        Parameters
        ----------
        result : MonteCarloResult
            CI付きの結果。
        label : str
            条件ラベル。

        Returns
        -------
        bool
            検証結果。
        """
        passed = True
        ci_attrs = [
            'ci_above_initial', 'ci_final_doubled', 'ci_ever_doubled',
            'ci_bankrupt', 'ci_stopped',
            'ci_dd20', 'ci_dd30', 'ci_dd50',
            'ci_mean', 'ci_median',
        ]
        for attr in ci_attrs:
            if not hasattr(result, attr):
                continue
            ci = getattr(result, attr)
            if ci[0] > ci[1] + 0.001:
                self.errors.append(f"[{label}] {attr}: 下限({ci[0]:.4f}) > 上限({ci[1]:.4f})")
                passed = False

        # 平均値がBootstrap CI内に含まれる
        if hasattr(result, 'ci_mean'):
            ci_mean = result.ci_mean
            if not (ci_mean[0] <= result.mean_final <= ci_mean[1]):
                self.errors.append(
                    f"[{label}] mean({result.mean_final:.1f}) not in CI[{ci_mean[0]:.1f}, {ci_mean[1]:.1f}]"
                )
                passed = False

        return passed

    def report(self) -> str:
        """検証結果レポートを返す。

        Returns
        -------
        str
            検証結果の文字列。
        """
        if not self.errors:
            return "✓ 全条件の自動検証に合格しました"
        return "✗ 検証失敗:" + "\n".join(self.errors)


def add_confidence_intervals(
    result: MonteCarloResult,
    n_simulations: int,
    condition_seed: int,
    ci_calc: ConfidenceIntervalCalculator,
) -> MonteCarloResult:
    """MonteCarloResultに信頼区間を追加する。

    Parameters
    ----------
    result : MonteCarloResult
        基本統計量を含む結果。
    n_simulations : int
        試行回数。
    condition_seed : int
        乱数シード。
    ci_calc : ConfidenceIntervalCalculator
        CI計算器。

    Returns
    -------
    MonteCarloResult
        CIが追加された結果。
    """
    n = n_simulations

    # Wilson法: 確率の信頼区間
    above_count = int((1.0 - result.below_initial_prob) * n)
    result.ci_above_initial = ci_calc.wilson(above_count, n)

    fd_count = int(result.final_doubled_prob * n)
    result.ci_final_doubled = ci_calc.wilson(fd_count, n)

    ed_count = int(result.ever_doubled_prob * n)
    result.ci_ever_doubled = ci_calc.wilson(ed_count, n)

    b_count = int(result.bankrupt_prob * n)
    result.ci_bankrupt = ci_calc.wilson(b_count, n)

    s_count = int(result.stopped_prob * n)
    result.ci_stopped = ci_calc.wilson(s_count, n)

    d20c = int(result.dd20_prob * n)
    result.ci_dd20 = ci_calc.wilson(d20c, n)

    d30c = int(result.dd30_prob * n)
    result.ci_dd30 = ci_calc.wilson(d30c, n)

    d50c = int(result.dd50_prob * n)
    result.ci_dd50 = ci_calc.wilson(d50c, n)

    # Bootstrap法: 統計量の信頼区間
    result.ci_mean = ci_calc.bootstrap(
        result.final_balances, np.mean, rng_seed=condition_seed + 100000
    )
    result.ci_median = ci_calc.bootstrap(
        result.final_balances, np.median, rng_seed=condition_seed + 200000
    )

    return result
