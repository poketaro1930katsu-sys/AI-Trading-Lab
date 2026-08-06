"""
simulator.py
============
AI Trading Lab Version 1.1 暫定版
シミュレーター本体モジュール

1試行あたりの取引シミュレーションと、全試行のモンテカルロ実行を担当。
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from config import SimulationConfig, RegimeConfig


class SingleTrialResult:
    """単一試行のシミュレーション結果を保持するクラス。

    Attributes
    ----------
    final_balance : float
        最終残高。
    max_drawdown : float
        最大ドローダウン率（0.0〜1.0）。
    ever_doubled : bool
        期間中に一度でも2倍到達したか。
    is_bankrupt : bool
        破産（残高<=0）したか。
    is_stopped : bool
        取引停止（0<残高<最低取引可能額）したか。
    balance_history : np.ndarray
        各取引時点の残高。shape=(n_trades+1,)。
    """

    __slots__ = ['final_balance', 'max_drawdown', 'ever_doubled',
                 'is_bankrupt', 'is_stopped', 'balance_history']

    def __init__(
        self,
        final_balance: float,
        max_drawdown: float,
        ever_doubled: bool,
        is_bankrupt: bool,
        is_stopped: bool,
        balance_history: np.ndarray,
    ):
        self.final_balance = final_balance
        self.max_drawdown = max_drawdown
        self.ever_doubled = ever_doubled
        self.is_bankrupt = is_bankrupt
        self.is_stopped = is_stopped
        self.balance_history = balance_history


class TradeSimulator:
    """単一試行のFX取引シミュレーションを実行する。

    【総リスク計算方式】
    ユーザーが指定する「1回のリスク率」は「総リスク（価格変動損失＋コスト）」
    として解釈される。

    total_risk = balance × risk_pct
    cost       = total_risk × cost_rate
    price_risk = total_risk - cost

    勝ち: balance = balance - cost + price_risk × RR
    負け: balance = balance - cost - price_risk = balance - total_risk

    これにより、負けた場合の総損失がちょうど balance × risk_pct となり、
    リスク管理の直感性が保たれる。

    【ドローダウン計算タイミング】
    以下すべてのタイミングでDDを更新:
    (a) コスト控除後
    (b) 勝敗更新後
    (c) 取引停止時
    (d) 破産時
    """

    def __init__(
        self,
        config: SimulationConfig,
        regime_config: Optional[RegimeConfig] = None,
    ):
        """
        Parameters
        ----------
        config : SimulationConfig
            シミュレーション設定。
        regime_config : RegimeConfig | None
            レジームモデル設定。Noneの場合は勝率固定モデル。
        """
        self.config = config
        self.regime_config = regime_config
        self.use_regime = regime_config is not None
        self.n_regimes = len(regime_config.regimes) if self.use_regime else 1

    def _update_drawdown(
        self,
        balance: float,
        peak: float,
        max_dd: float,
    ) -> tuple[float, float]:
        """残高とピークを更新し、最大ドローダウンを計算する。"""
        if balance > peak:
            peak = balance
        if peak > 0:
            dd = (peak - balance) / peak
            if dd > max_dd:
                max_dd = dd
        return peak, max_dd

    def run_single(
        self,
        win_rate: float,
        reward_ratio: float,
        risk_pct: float,
        rng: np.random.Generator,
    ) -> SingleTrialResult:
        """単一試行のシミュレーションを実行する。

        Parameters
        ----------
        win_rate : float
            勝率固定モデル時の勝率（レジームモデルでは上書きされる）。
        reward_ratio : float
            勝率固定モデル時のRR比（レジームモデルでは上書きされる）。
        risk_pct : float
            総リスク率。
        rng : np.random.Generator
            乱数生成器。

        Returns
        -------
        SingleTrialResult
            シミュレーション結果。
        """
        cfg = self.config
        balance = float(cfg.initial_capital)
        balance_history = [balance]
        peak = balance
        max_dd = 0.0
        is_bankrupt = False
        is_stopped = False
        ever_doubled = False
        regime_idx = 0

        # 初期レジーム決定
        if self.use_regime:
            regime_idx = rng.choice(self.n_regimes, p=self.regime_config.initial_probs)

        for t in range(cfg.total_trades):
            if is_bankrupt or is_stopped:
                balance_history.append(balance)
                if self.use_regime:
                    regime_idx = self.regime_config.transition(regime_idx, rng)
                else:
                    rng.random()  # ダミー呼び出し（共通乱数法のため）
                continue

            # --- レジーム遷移（レジームモデルの場合） ---
            if self.use_regime:
                regime_idx = self.regime_config.transition(regime_idx, rng)
                rp = self.regime_config.get_params(regime_idx)
                win_rate = rp.win_rate
                reward_ratio = rp.reward_ratio

            # --- 総リスク計算 ---
            total_risk = balance * risk_pct
            cost = total_risk * cfg.cost_rate
            price_risk = total_risk - cost

            # コスト控除（勝ち負けに関わらず差し引く）
            balance -= cost
            peak, max_dd = self._update_drawdown(balance, peak, max_dd)

            # コスト控除後のチェック
            if balance <= 0:
                balance = 0
                is_bankrupt = True
                peak, max_dd = self._update_drawdown(balance, peak, max_dd)
                balance_history.append(balance)
                continue

            if balance < cfg.min_tradeable:
                is_stopped = True
                peak, max_dd = self._update_drawdown(balance, peak, max_dd)
                balance_history.append(balance)
                continue

            # 勝ち負け判定
            if rng.random() < win_rate:
                # 勝ち: balance = balance - cost + price_risk × RR
                balance += price_risk * reward_ratio
            else:
                # 負け: balance = balance - total_risk
                balance -= price_risk

            # 勝敗更新後のDD計算
            peak, max_dd = self._update_drawdown(balance, peak, max_dd)

            # 2倍到達チェック
            if balance >= cfg.initial_capital * 2:
                ever_doubled = True

            # 破産チェック
            if balance <= 0:
                balance = 0
                is_bankrupt = True
                peak, max_dd = self._update_drawdown(balance, peak, max_dd)

            # 停止チェック
            if not is_bankrupt and balance < cfg.min_tradeable:
                is_stopped = True
                peak, max_dd = self._update_drawdown(balance, peak, max_dd)

            balance_history.append(balance)

        return SingleTrialResult(
            final_balance=balance,
            max_drawdown=max_dd,
            ever_doubled=ever_doubled,
            is_bankrupt=is_bankrupt,
            is_stopped=is_stopped,
            balance_history=np.array(balance_history),
        )


class MonteCarloResult:
    """モンテカルロ全試行の結果を保持するクラス。

    Attributes
    ----------
    final_balances : np.ndarray
        最終残高の配列。shape=(n_simulations,)。
    max_drawdowns : np.ndarray
        最大ドローダウンの配列。shape=(n_simulations,)。
    percentile_bands : np.ndarray
        各時点のパーセンタイルバンド。shape=(n_trades+1, 5)。
        列: [5%, 25%, 50%, 75%, 95%]
    ever_doubled_prob : float
        期間中に一度でも2倍到達した確率。
    final_doubled_prob : float
        最終残高が2倍になった確率。
    bankrupt_prob : float
        破産確率。
    stopped_prob : float
        取引停止確率。
    below_initial_prob : float
        元本割れ確率。
    dd20_prob : float
        DD20%到達確率。
    dd30_prob : float
        DD30%到達確率。
    dd50_prob : float
        DD50%到達確率。
    mean_final : float
        最終残高の平均値。
    median_final : float
        最終残高の中央値。
    p5_final, p25_final, p75_final, p95_final : float
        最終残高の各パーセンタイル。
    ci_* : tuple[float, float]
        各統計量の95%信頼区間。
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MonteCarloEngine:
    """モンテカルロ・シミュレーションの全試行を管理・実行する。"""

    def __init__(
        self,
        config: SimulationConfig,
        regime_config: Optional[RegimeConfig] = None,
    ):
        """
        Parameters
        ----------
        config : SimulationConfig
            シミュレーション設定。
        regime_config : RegimeConfig | None
            レジームモデル設定。
        """
        self.config = config
        self.simulator = TradeSimulator(config, regime_config)

    def run(
        self,
        win_rate: float,
        reward_ratio: float,
        risk_pct: float,
        condition_seed: int,
    ) -> MonteCarloResult:
        """指定条件でモンテカルロ・シミュレーションを実行する。

        Parameters
        ----------
        win_rate : float
            勝率。
        reward_ratio : float
            RR比。
        risk_pct : float
            総リスク率。
        condition_seed : int
            この条件用の乱数シード。

        Returns
        -------
        MonteCarloResult
            全試行の統計結果。
        """
        cfg = self.config
        n_sims = cfg.n_simulations
        n_trades = cfg.total_trades

        rng = np.random.default_rng(condition_seed)

        # 結果格納配列
        final_balances = np.empty(n_sims)
        max_drawdowns = np.empty(n_sims)
        ever_doubled = np.zeros(n_sims, dtype=bool)
        final_doubled = np.zeros(n_sims, dtype=bool)
        bankrupt = np.zeros(n_sims, dtype=bool)
        stopped = np.zeros(n_sims, dtype=bool)
        below_initial = np.zeros(n_sims, dtype=bool)
        all_curves = np.empty((n_sims, n_trades + 1))
        dd_20 = np.zeros(n_sims, dtype=bool)
        dd_30 = np.zeros(n_sims, dtype=bool)
        dd_50 = np.zeros(n_sims, dtype=bool)

        for i in range(n_sims):
            result = self.simulator.run_single(win_rate, reward_ratio, risk_pct, rng)

            final_balances[i] = result.final_balance
            max_drawdowns[i] = result.max_drawdown
            ever_doubled[i] = result.ever_doubled
            final_doubled[i] = result.final_balance >= cfg.initial_capital * 2
            bankrupt[i] = result.is_bankrupt
            stopped[i] = result.is_stopped
            below_initial[i] = result.final_balance < cfg.initial_capital
            all_curves[i] = result.balance_history
            dd_20[i] = result.max_drawdown >= 0.20
            dd_30[i] = result.max_drawdown >= 0.30
            dd_50[i] = result.max_drawdown >= 0.50

        # --- パーセンタイルバンド計算（各時点） ---
        percentile_bands = np.empty((n_trades + 1, 5))
        for t in range(n_trades + 1):
            percentile_bands[t] = np.percentile(all_curves[:, t], [5, 25, 50, 75, 95])

        # --- 基本統計量 ---
        mean_final = final_balances.mean()
        median_final = np.median(final_balances)

        return MonteCarloResult(
            final_balances=final_balances,
            max_drawdowns=max_drawdowns,
            percentile_bands=percentile_bands,
            ever_doubled_prob=ever_doubled.mean(),
            final_doubled_prob=final_doubled.mean(),
            bankrupt_prob=bankrupt.mean(),
            stopped_prob=stopped.mean(),
            below_initial_prob=below_initial.mean(),
            dd20_prob=dd_20.mean(),
            dd30_prob=dd_30.mean(),
            dd50_prob=dd_50.mean(),
            mean_final=mean_final,
            median_final=median_final,
            p5_final=np.percentile(final_balances, 5),
            p25_final=np.percentile(final_balances, 25),
            p75_final=np.percentile(final_balances, 75),
            p95_final=np.percentile(final_balances, 95),
        )
