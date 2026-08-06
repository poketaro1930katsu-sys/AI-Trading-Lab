# AI Trading Lab Version 1.2

FX取引シナリオの公平な検証基盤

---

## 1. プロジェクト概要

### AI Trading Labとは

AI Trading Labは、FX（外国為替証拠金取引）における「シナリオ」（方向性・エントリー価格・損切り・利確目標の予測セット）を**公平に検証する**ための研究基盤です。

### Version 1.2の目的

- **利益保証ではない**: 将来の利益を保証するものではありません
- **公平な検証基盤**: 誰が投稿したシナリオでも、同じ基準で検証できます
- matureなデータモデルと統計的に適切な集計を提供します
- **研究目的**: トレーダーの学習・戦略検証・市場理解の支援を目的とします

### 核心原則

```
利益保証ではなく、公平な検証基盤であること
```

---

## 2. ディレクトリ構成

```
AI_Trading_Lab_v1_2/
├── Version 1.1（モンテカルロ・シミュレーション）
│   ├── config.py              # シミュレーション設定
│   ├── simulator.py           # シミュレーター本体
│   ├── statistics.py          # 統計解析（Wilson法・Bootstrap法）
│   ├── report.py              # CSV・レポート出力
│   ├── main.py                # メイン実行スクリプト
│   └── requirements.txt       # 依存ライブラリ
│
├── Version 1.2（シナリオ検証基盤）
│   ├── scenario_models.py     # データモデル（Pydantic）
│   ├── scenario_parser.py     # CSV/JSON/テキスト入出力
│   ├── scenario_schema.json   # JSON Schema定義
│   ├── scenario_template.csv  # CSVテンプレート
│   ├── scenario_journal.py    # 永続化・管理・検索
│   ├── scenario_validator.py  # 入力検証・品質スコア
│   ├── scenario_statistics.py # 統計集計・Wilson CI
│   └── scenario_report.py     # Markdownレポート・CSV出力
│
├── tests/                     # 単体テスト
│   ├── test_scenario_models.py
│   ├── test_scenario_parser.py
│   ├── test_scenario_journal.py
│   ├── test_scenario_validator.py
│   ├── test_scenario_statistics.py
│   └── test_scenario_report.py
│
├── outputs/                   # 出力ディレクトリ
│   ├── scenario_records.csv
│   ├── scenario_summary.csv
│   ├── scenario_data_quality_report.md
│   └── scenario_analysis_report.md
│
├── README.md                  # 本ファイル
├── CHANGELOG.md               # 変更履歴
├── LICENSE.md                 # MITライセンス
├── PROJECT_STRUCTURE.md       # プロジェクト構造詳細
├── ROADMAP.md                 # 開発ロードマップ
└── execution_report.md        # 実行状況レポート
```

---

## 3. インストール方法

### 前提条件

- Python 3.12+
- pip

### 手順

```bash
# 1. リポジトリをクローンまたはZIPを展開
cd AI_Trading_Lab_v1_2

# 2. 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 3. 依存ライブラリをインストール
pip install -r requirements.txt
```

---

## 4. 実行方法

### Version 1.1（モンテカルロ・シミュレーション）

```bash
python main.py
```

### Version 1.2（シナリオ検証基盤）

```python
from scenario_journal import ScenarioJournal
from scenario_validator import ScenarioValidator, BatchValidator
from scenario_statistics import ScenarioStatistics
from scenario_report import ScenarioReport

# 1. ジャーナル作成
journal = ScenarioJournal()

# 2. CSV読み込み
journal.load("path/to/scenarios.csv")

# 3. バッチ検証
validator = BatchValidator()
report = validator.validate_batch(journal.batch.records)

# 4. 統計集計
stats = ScenarioStatistics(journal.get_statistics_ready())
result = stats.summarize()

# 5. レポート生成
reporter = ScenarioReport()
reporter.generate_all(journal.batch.records)
```

---

## 5. テスト方法

```bash
# 全テスト実行
pytest tests/

# 特定モジュールのテスト
pytest tests/test_scenario_models.py -v
pytest tests/test_scenario_parser.py -v
pytest tests/test_scenario_journal.py -v
pytest tests/test_scenario_validator.py -v
pytest tests/test_scenario_statistics.py -v
pytest tests/test_scenario_report.py -v
```

---

## 6. データの流れ

```
CSV / JSON / テキスト
        ↓
   scenario_parser.py
        ↓
   scenario_journal.py
        ↓
   scenario_validator.py
        ↓
   scenario_statistics.py
        ↓
   scenario_report.py
        ↓
Markdown / CSV
```

---

## 7. 注意事項

### 研究目的

本プロジェクトは**研究・教育目的**のシステムです。

### 未来予測ではない

過去のシナリオ検証結果は、将来の市場環境を反映するものではありません。

### 売買推奨ではない

本システムはいかなる売買の推奨も行いません。

### 利益保証ではない

本シミュレーション・検証結果は、将来の利益を保証するものではありません。

---

## ライセンス

MIT License - 詳細は [LICENSE.md](LICENSE.md) を参照

---

## 開発者向け

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - プロジェクト構造詳細
- [ROADMAP.md](ROADMAP.md) - 開発ロードマップ
- [execution_report.md](execution_report.md) - 現在の実行状況
