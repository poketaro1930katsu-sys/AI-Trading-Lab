# Changelog

## Version 1.2 (2026-08-05)

### 新規モジュール（Module 1〜6）

#### Module 1: データモデル (scenario_models.py)
- Pydanticベースの完全データモデル `ScenarioRecord`
- 6種類のEnum定義（Direction, EntryType, MarketSession, ResultClassification, HumanReviewStatus, SourceType）
- バッチ管理クラス `ScenarioBatch`
- 最小入力モデル `ScenarioInput`
- 評価入力モデル `ScenarioEvaluationInput`

#### Module 2: 入出力パーサー (scenario_parser.py)
- CSV読み書き（完全対応）
- JSON読み書き（単一/配列/ラップ形式）
- テキスト候補抽出（自動確定禁止・人間レビュー前提）
- 型変換ユーティリティ（Decimal, datetime, bool, Enum, list）
- JSON Schema定義 (scenario_schema.json)
- CSVテンプレート (scenario_template.csv)

#### Module 3: ジャーナル (scenario_journal.py)
- シナリオ記録の永続化管理
- CSV保存・再読込
- record_idインデックス検索
- 評価結果のマージ更新
- 条件クエリ（symbol, direction, result, date range等）
- 統計対象データ抽出（品質スコア50以上）
- サマリーCSV出力

#### Module 4: 検証 (scenario_validator.py)
- 必須/推奨フィールドチェック
- 価格整合性（entry zone, SL/TP位置）
- 日時整合性（timezone混在検出、期限逆転）
- 方向性・価格矛盾チェック
- 品質スコア計算（0-100、減点根拠一覧）
- 重複チェック（完全重複 vs 重複候補）
- human_review_status自動更新
- missing_required_fields / ambiguous_fields / duplicate_flag 更新

#### Module 5: 統計 (scenario_statistics.py)
- 基本集計（総件数、評価済み、方向別、銘柄別等）
- Wilson法95%信頼区間（共通関数・将来拡張対応）
- 標本サイズルール（20/30/100件閾値、display_allowed/comparison_allowed）
- 勝率計算（WIN/LOSS/PARTIALのみ母数、NOT_TRIGGERED等は除外）
- 条件別集計（by_symbol, by_direction, by_session, by_timeframe, by_source, by_result）
- 品質分析（平均/中央値/最小/最大/標準偏差/ヒストグラム）
- Dataclass化（StatisticsResult, WilsonCI, SampleSizeStatus, QualityMetrics等）

#### Module 6: レポート (scenario_report.py)
- データ品質レポート（Markdown）
- シナリオ分析レポート（Markdown、Wilson CI表示、標本サイズ警告）
- サマリーCSV（csvモジュール使用、カンマ/改行/引用符対応）
- 禁止表現チェック・自動置換
- 免責事項自動挿入
- 一括生成 `generate_all()`

### テスト
- 全6モジュールの単体テスト
- 合計123テスト、全件PASS

---

## Version 1.1 (2026-08-05)

### 新機能
- パーセンタイルバンド（各時点の5%, 25%, 50%, 75%, 95%）
- 信頼帯グラフ（5%-95%帯 + 中央値太線）
- 2倍達成の分離（最終2倍 vs 期間中2倍）
- 総リスク計算（価格変動損失 + スプレッド + 手数料）
- 自動検証の強化（DD単調性、CI整合性）
- DD計算の強化（コスト後・勝敗後・停止時・破産時）
- 共通乱数法（全条件で同じ乱数ストリーム）
- 相場レジームモデル（Bull/Normal/Bearの3状態マルコフ連鎖）
- DD到達率（DD20%, DD30%, DD50%）
- 95%信頼区間（Wilson法 + Bootstrap法）

### 設計改善
- モジュール化（config / simulator / statistics / visualization / report）
- 型ヒントの追加
- NumPy Docstring形式のドキュメント
- frozen dataclassによる不変性保証
- 例外処理・バリデーションの強化

---

## Version 1.0 (2026-08-03)

### 初版
- 勝率固定モデルのモンテカルロ・シミュレーション
- 基本統計量（平均、中央値、元本超え確率、2倍達成確率、破産確率）
- 資金曲線グラフ（最良・最悪・中央値）
- ヒートマップ・分布グラフ
- CSV出力
