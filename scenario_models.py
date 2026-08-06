"""
AI Trading Lab v1.2 - Scenario Models
データモデル定義（Pydanticベース）
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ==========================================
# Enum定義
# ==========================================

class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class EntryType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    ZONE = "ZONE"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


class MarketSession(str, Enum):
    TOKYO = "TOKYO"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OVERLAP = "OVERLAP"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ResultClassification(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    PARTIAL_WIN = "PARTIAL_WIN"
    PARTIAL_LOSS = "PARTIAL_LOSS"
    NOT_TRIGGERED = "NOT_TRIGGERED"
    INVALIDATED_BEFORE_ENTRY = "INVALIDATED_BEFORE_ENTRY"
    EXPIRED = "EXPIRED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_EVALUATED = "NOT_EVALUATED"


class HumanReviewStatus(str, Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    CORRECTED = "CORRECTED"
    SKIP = "SKIP"


class SourceType(str, Enum):
    CSV = "CSV"
    JSON = "JSON"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


# ==========================================
# データモデル
# ==========================================

class ScenarioRecord(BaseModel):
    """シナリオ記録の完全データモデル"""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    # --- 基本情報 ---
    record_id: str = Field(..., description="ユニークレコードID（UUID推奨）")
    source_id: str = Field(..., description="ソース固有ID")
    scenario_date: date = Field(..., description="シナリオ対象日")
    published_at: datetime = Field(..., description="公開日時（原文の公開時刻）")
    timezone: Optional[str] = Field(default="UTC", description="公開時刻のタイムゾーン")
    recorded_at: datetime = Field(default_factory=datetime.utcnow, description="システム記録日時")
    source_type: SourceType = Field(default=SourceType.UNKNOWN, description="入力ソース種別")
    original_text: Optional[str] = Field(default=None, description="原文（改変不可）")
    source_image_path: Optional[str] = Field(default=None, description="ソース画像パス")
    source_url: Optional[str] = Field(default=None, description="ソースURL")

    # --- 市場情報 ---
    symbol: str = Field(..., description="銘柄記号（例: EURUSD）")
    asset_class: Optional[str] = Field(default=None, description="資産クラス")
    timeframe: Optional[str] = Field(default=None, description="時間足（例: 1H, 4H, D1）")
    scenario_valid_from: Optional[datetime] = Field(default=None, description="シナリオ有効開始日時")
    scenario_valid_until: Optional[datetime] = Field(default=None, description="シナリオ有効期限日時")
    market_session: MarketSession = Field(default=MarketSession.UNKNOWN, description="市場セッション")
    direction: Direction = Field(default=Direction.UNKNOWN, description="方向性")
    entry_type: EntryType = Field(default=EntryType.UNKNOWN, description="エントリー種別")
    entry_price_low: Optional[Decimal] = Field(default=None, description="エントリー価格下限")
    entry_price_high: Optional[Decimal] = Field(default=None, description="エントリー価格上限")
    stop_loss: Optional[Decimal] = Field(default=None, description="損切り価格")
    take_profit_1: Optional[Decimal] = Field(default=None, description="利確目標1")
    take_profit_2: Optional[Decimal] = Field(default=None, description="利確目標2")
    take_profit_3: Optional[Decimal] = Field(default=None, description="利確目標3")

    # --- シナリオ内容 ---
    scenario_summary: Optional[str] = Field(default=None, description="シナリオ要約")
    stated_reasons: Optional[str] = Field(default=None, description="根拠・理由")
    important_levels: Optional[str] = Field(default=None, description="重要レベル")
    invalidation_condition: Optional[str] = Field(default=None, description="無効化条件")
    alternative_scenario: Optional[str] = Field(default=None, description="代替シナリオ")
    economic_event_warning: Optional[str] = Field(default=None, description="経済指標警告")
    author_confidence_text: Optional[str] = Field(default=None, description="投稿者の信頼度表現")

    # --- 結果 ---
    entry_triggered: Optional[bool] = Field(default=None, description="エントリー成立フラグ")
    entry_triggered_at: Optional[datetime] = Field(default=None, description="エントリー成立日時")
    entry_price_actual: Optional[Decimal] = Field(default=None, description="実際のエントリー価格")
    highest_favorable_price: Optional[Decimal] = Field(default=None, description="最良値（有利方向）")
    lowest_adverse_price: Optional[Decimal] = Field(default=None, description="最悪値（不利方向）")
    tp1_reached: Optional[bool] = Field(default=None, description="TP1到達フラグ")
    tp2_reached: Optional[bool] = Field(default=None, description="TP2到達フラグ")
    tp3_reached: Optional[bool] = Field(default=None, description="TP3到達フラグ")
    sl_reached: Optional[bool] = Field(default=None, description="SL到達フラグ")
    invalidation_reached: Optional[bool] = Field(default=None, description="無効化到達フラグ")
    scenario_expired: Optional[bool] = Field(default=None, description="期限切れフラグ")
    result_classification: ResultClassification = Field(default=ResultClassification.NOT_EVALUATED, description="結果分類")
    realized_r_multiple: Optional[Decimal] = Field(default=None, description="実現R倍数")
    maximum_favorable_excursion_r: Optional[Decimal] = Field(default=None, description="最大有利変動R")
    maximum_adverse_excursion_r: Optional[Decimal] = Field(default=None, description="最大不利変動R")
    evaluation_completed_at: Optional[datetime] = Field(default=None, description="評価完了日時")
    evaluation_notes: Optional[str] = Field(default=None, description="評価者メモ")

    # --- 品質 ---
    missing_required_fields: Optional[List[str]] = Field(default=None, description="欠損必須フィールド一覧")
    ambiguous_fields: Optional[List[str]] = Field(default=None, description="曖昧フィールド一覧")
    parser_confidence: Optional[int] = Field(default=None, ge=0, le=100, description="パーサー信頼度(0-100)")
    human_review_status: HumanReviewStatus = Field(default=HumanReviewStatus.PENDING, description="人間レビュー状態")
    human_corrected: Optional[bool] = Field(default=None, description="人間修正フラグ")
    duplicate_flag: Optional[bool] = Field(default=None, description="重複フラグ")
    data_quality_score: Optional[int] = Field(default=None, ge=0, le=100, description="データ品質スコア(0-100)")

    # --- 推論メタデータ ---
    inferred_fields: Optional[List[str]] = Field(default=None, description="AI推論補完フィールド一覧")

    @field_validator('parser_confidence', 'data_quality_score', mode='before')
    @classmethod
    def validate_score_range(cls, v):
        if v is None:
            return v
        if not isinstance(v, (int, float)):
            raise ValueError("スコアは数値である必要があります")
        if not 0 <= v <= 100:
            raise ValueError("スコアは0-100の範囲である必要があります")
        return int(v)

    def is_evaluated(self) -> bool:
        """評価済みかどうか"""
        return self.result_classification != ResultClassification.NOT_EVALUATED

    def is_entry_triggered_confirmed(self) -> bool:
        """エントリー確定済みか"""
        return self.entry_triggered is True

    def get_entry_zone(self) -> Optional[tuple]:
        """エントリーゾーンを取得（low, high）"""
        if self.entry_price_low is not None and self.entry_price_high is not None:
            return (self.entry_price_low, self.entry_price_high)
        elif self.entry_price_low is not None:
            return (self.entry_price_low, self.entry_price_low)
        elif self.entry_price_high is not None:
            return (self.entry_price_high, self.entry_price_high)
        return None

    def to_flat_dict(self) -> dict:
        """フラット辞書に変換（CSV出力用）"""
        return self.model_dump(mode='json')


class ScenarioBatch(BaseModel):
    """シナリオバッチ（複数レコードの集合）"""
    model_config = ConfigDict(populate_by_name=True)

    records: List[ScenarioRecord] = Field(default_factory=list)
    batch_id: Optional[str] = Field(default=None, description="バッチID")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def add_record(self, record: ScenarioRecord) -> None:
        self.records.append(record)

    def get_by_record_id(self, record_id: str) -> Optional[ScenarioRecord]:
        for r in self.records:
            if r.record_id == record_id:
                return r
        return None

    def get_by_source_id(self, source_id: str) -> List[ScenarioRecord]:
        return [r for r in self.records if r.source_id == source_id]

    def filter_by_symbol(self, symbol: str) -> List[ScenarioRecord]:
        return [r for r in self.records if r.symbol.upper() == symbol.upper()]

    def filter_by_direction(self, direction: Direction) -> List[ScenarioRecord]:
        return [r for r in self.records if r.direction == direction]

    def filter_evaluated(self) -> List[ScenarioRecord]:
        return [r for r in self.records if r.is_evaluated()]

    def filter_pending_evaluation(self) -> List[ScenarioRecord]:
        return [r for r in self.records if not r.is_evaluated()]

    def filter_human_review_required(self) -> List[ScenarioRecord]:
        return [r for r in self.records if r.human_review_status == HumanReviewStatus.PENDING]

    def __len__(self) -> int:
        return len(self.records)


# ==========================================
# 軽量モデル（入力用）
# ==========================================

class ScenarioInput(BaseModel):
    """最小入力モデル（必須項目のみ）"""
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    source_id: str
    scenario_date: date
    published_at: datetime
    symbol: str
    direction: Direction = Direction.UNKNOWN
    original_text: Optional[str] = None


class ScenarioEvaluationInput(BaseModel):
    """評価入力モデル"""
    model_config = ConfigDict(populate_by_name=True)

    record_id: str
    entry_triggered: Optional[bool] = None
    entry_triggered_at: Optional[datetime] = None
    entry_price_actual: Optional[Decimal] = None
    highest_favorable_price: Optional[Decimal] = None
    lowest_adverse_price: Optional[Decimal] = None
    tp1_reached: Optional[bool] = None
    tp2_reached: Optional[bool] = None
    tp3_reached: Optional[bool] = None
    sl_reached: Optional[bool] = None
    invalidation_reached: Optional[bool] = None
    scenario_expired: Optional[bool] = None
    result_classification: ResultClassification = ResultClassification.NOT_EVALUATED
    realized_r_multiple: Optional[Decimal] = None
    maximum_favorable_excursion_r: Optional[Decimal] = None
    maximum_adverse_excursion_r: Optional[Decimal] = None
    evaluation_notes: Optional[str] = None
