"""
config.py
=========
AI Trading Lab Version 1.1 暫定版
設定・Configモジュール

保守性・拡張性を最優先した設定クラス群。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple
from enum import Enum, auto

import numpy as np


class RandomMethod(Enum):
    """乱数生成方式。"""
    COMMON = auto()
    INDEPENDENT = auto()


class ModelType(Enum):
    """シミュレーションモデルタイプ。"""
    FIXED_WIN_RATE = auto()
    REGIME = auto()


class RegimeParameters(NamedTuple):
    """単一レジームの取引パラメータ。

    Parameters
    ----------
    win_rate : float
        勝率（0.0〜1.0）。
    reward_ratio : float
        リスクリワード比（1:X の X）。
    name : str
        レジームの識別名。
    """
    win_rate: float
    reward_ratio: float
    name: str


@dataclass(frozen=True)
class SimulationConfig:
    """シミュレーション全体の設定。

    frozen=True で不変オブジェクトとし、
    複数条件での誤った変更を防ぐ。

    Parameters
    ----------
    initial_capital : float
        初期資金（円）。デフォルト1000.0。
    trading_days : int
        取引日数。デフォルト20。
    trades_per_day : int
        1日あたりの取引回数。デフォルト3。
    n_simulations : int
        モンテカルロ試行回数。デフォルト10000。
    risk_rates : list[float]
        1回あたりの総リスク率（残高に対する割合）。
        デフォルト [0.01, 0.02, 0.05, 0.10]。
    cost_rate : float
        コスト率（総リスク額に対する割合）。
        総リスク = 価格変動損失 + コスト として解釈される。
        デフォルト 0.05（5%）。
    min_tradeable : float
        最低取引可能額（円）。下回ると取引停止。
        デフォルト 50.0。
    rng_seed : int
        乱数シード（再現性確保）。デフォルト42。
    random_method : RandomMethod
        乱数生成方式。デフォルト COMMON。
    model_type : ModelType
        シミュレーションモデル。デフォルト FIXED_WIN_RATE。
    """
    initial_capital: float = 1000.0
    trading_days: int = 20
    trades_per_day: int = 3
    n_simulations: int = 10000
    risk_rates: list[float] = field(default_factory=lambda: [0.01, 0.02, 0.05, 0.10])
    cost_rate: float = 0.05
    min_tradeable: float = 50.0
    rng_seed: int = 42
    random_method: RandomMethod = RandomMethod.COMMON
    model_type: ModelType = ModelType.FIXED_WIN_RATE

    def __post_init__(self):
        if self.initial_capital <= 0:
            raise ValueError("初期資金は正の値である必要があります")
        if self.trading_days <= 0 or self.trades_per_day <= 0:
            raise ValueError("取引日数・回数は正の整数である必要があります")
        if self.n_simulations <= 0:
            raise ValueError("試行回数は正の整数である必要があります")
        if not all(0 < r <= 1.0 for r in self.risk_rates):
            raise ValueError("リスク率は0〜1.0の範囲である必要があります")
        if not 0 <= self.cost_rate < 1.0:
            raise ValueError("コスト率は0〜1.0未満である必要があります")
        if self.min_tradeable <= 0:
            raise ValueError("最低取引可能額は正の値である必要があります")
        if self.min_tradeable > self.initial_capital:
            raise ValueError("最低取引可能額は初期資金以下である必要があります")

    @property
    def total_trades(self) -> int:
        """総取引回数を返す。"""
        return self.trading_days * self.trades_per_day

    def get_seed_for_condition(self, condition_index: int) -> int:
        """条件インデックスに対する乱数シードを返す。

        COMMON: 全条件で同じseed（共通乱数法）。
        INDEPENDENT: 各条件で異なるseed。
        """
        if self.random_method == RandomMethod.COMMON:
            return self.rng_seed
        return self.rng_seed + condition_index * 1000


@dataclass(frozen=True)
class RegimeConfig:
    """レジームモデル（マルコフ連鎖）の設定。

    Parameters
    ----------
    regimes : list[RegimeParameters]
        各レジームのパラメータリスト。
    transition_matrix : np.ndarray
        遷移確率行列。shape=(n_regimes, n_regimes)。
        transition_matrix[i, j] = レジームiからjへの遷移確率。
    initial_probs : np.ndarray
        初期状態確率。shape=(n_regimes,)。
    """
    regimes: list[RegimeParameters]
    transition_matrix: np.ndarray
    initial_probs: np.ndarray

    def __post_init__(self):
        n = len(self.regimes)
        tm = self.transition_matrix
        ip = self.initial_probs

        if tm.shape != (n, n):
            raise ValueError(f"遷移行列の形状が不正: {tm.shape}, 期待: ({n}, {n})")
        if not np.allclose(tm.sum(axis=1), 1.0):
            raise ValueError("遷移行列の各行の和が1になっていません")
        if len(ip) != n:
            raise ValueError("初期状態確率の長さがレジーム数と一致しません")
        if not np.allclose(ip.sum(), 1.0):
            raise ValueError("初期状態確率の和が1になっていません")
        if not np.all(tm >= 0):
            raise ValueError("遷移行列に負の値が含まれています")
        if not np.all(ip >= 0):
            raise ValueError("初期状態確率に負の値が含まれています")

    @property
    def n_regimes(self) -> int:
        """レジーム数を返す。"""
        return len(self.regimes)

    def get_params(self, regime_idx: int) -> RegimeParameters:
        """レジームインデックスからパラメータを取得。"""
        return self.regimes[regime_idx]

    def transition(self, current_idx: int, rng: np.random.Generator) -> int:
        """マルコフ連鎖で次のレジームを決定する。"""
        probs = self.transition_matrix[current_idx]
        return rng.choice(self.n_regimes, p=probs)

    def get_stationary_distribution(self) -> np.ndarray:
        """定常分布を計算する。"""
        eigvals, eigvecs = np.linalg.eig(self.transition_matrix.T)
        idx = np.argmin(np.abs(eigvals - 1.0))
        stationary = eigvecs[:, idx].real
        return stationary / stationary.sum()


def create_default_regime_config() -> RegimeConfig:
    """デフォルトのレジーム設定を生成する。

    Bull/Normal/Bearの3状態マルコフモデル。

    【採用理由】
    市場レジームは「パーシスタンス（状態持続性）」を持つことが
    エンピリカルファクト（Hamilton, 1989）として知られている。

    【各レジームのパラメータ】
    - Bull:  勝率65%, RR 1:1.8（トレンド明確、勝率上昇、RRやや低下）
    - Normal:勝率50%, RR 1:1.5（ベースライン）
    - Bear:  勝率35%, RR 1:1.2（レンジ・逆行、勝率・RRともに低下）

    【遷移確率行列】
    Bull→Bull:70%, Bull→Normal:25%, Bull→Bear:5%
    Normal→Bull:20%, Normal→Normal:60%, Normal→Bear:20%
    Bear→Bull:5%, Bear→Normal:25%, Bear→Bear:70%

    【定常分布】
    Bull: 30.8%, Normal: 38.5%, Bear: 30.8%
    """
    regimes = [
        RegimeParameters(win_rate=0.65, reward_ratio=1.8, name="Bull"),
        RegimeParameters(win_rate=0.50, reward_ratio=1.5, name="Normal"),
        RegimeParameters(win_rate=0.35, reward_ratio=1.2, name="Bear"),
    ]
    transition = np.array([
        [0.70, 0.25, 0.05],
        [0.20, 0.60, 0.20],
        [0.05, 0.25, 0.70],
    ])
    initial = np.array([0.333, 0.334, 0.333])
    return RegimeConfig(regimes=regimes, transition_matrix=transition, initial_probs=initial)
