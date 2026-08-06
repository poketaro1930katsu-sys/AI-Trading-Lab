# プロジェクト構造詳細

## Tree形式

```
AI_Trading_Lab_v1_2/
│
├── Version 1.1（モンテカルロ・シミュレーション）
│   ├── config.py
│   ├── simulator.py
│   ├── statistics.py
│   ├── report.py
│   ├── main.py
│   └── requirements.txt
│
├── Version 1.2（シナリオ検証基盤）
│   ├── scenario_models.py
│   ├── scenario_parser.py
│   ├── scenario_schema.json
│   ├── scenario_template.csv
│   ├── scenario_journal.py
│   ├── scenario_validator.py
│   ├── scenario_statistics.py
│   └── scenario_report.py
│
├── tests/
│   ├── test_scenario_models.py
│   ├── test_scenario_parser.py
│   ├── test_scenario_journal.py
│   ├── test_scenario_validator.py
│   ├── test_scenario_statistics.py
│   └── test_scenario_report.py
│
├── outputs/
│   ├── scenario_records.csv
│   ├── scenario_summary.csv
│   ├── scenario_data_quality_report.md
│   └── scenario_analysis_report.md
│
├── README.md
├── CHANGELOG.md
├── LICENSE.md
├── PROJECT_STRUCTURE.md
├── ROADMAP.md
└── execution_report.md
```

---

## 役割と責務

### Version 1.1

| ファイル | 役割 | 責務 |
|:---|:---|:---|
| config.py | 設定管理 | シミュレーション設定、レジーム設定、バリデーション |
| simulator.py | シミュレーション | 単一試行・モンテカルロ実行、資金曲線計算 |
| statistics.py | 統計解析 | Wilson法・Bootstrap法による信頼区間、結果検証 |
| report.py | 出力 | CSV出力、Markdownレポート生成、比較レポート |
| main.py | エントリーポイント | 全条件のシミュレーション実行、グラフ生成 |

### Version 1.2

| ファイル | 役割 | 責務 |
|:---|:---|:---|
| scenario_models.py | データモデル | Pydanticモデル、Enum定義、バッチ管理 |
| scenario_parser.py | 入出力 | CSV/JSON/テキストの読み書き、型変換 |
| scenario_journal.py | 永続化 | レコード管理、検索、評価更新、CSV入出力 |
| scenario_validator.py | 検証 | 入力検証、品質スコア、重複チェック |
| scenario_statistics.py | 統計 | 集計、Wilson CI、標本サイズ警告、条件別分析 |
| scenario_report.py | レポート | Markdown/CSV出力、禁止表現チェック、免責挿入 |

---

## 依存関係

```
scenario_models.py
    ↑
scenario_parser.py → scenario_schema.json, scenario_template.csv
    ↑
scenario_journal.py
    ↑
scenario_validator.py
    ↑
scenario_statistics.py
    ↑
scenario_report.py
```

### 依存の方向

- **下位 → 上位**: 上位モジュールは下位モジュールに依存
- **scenario_models.py** はすべてのモジュールの基盤
- **scenario_parser.py** は models にのみ依存
- **scenario_journal.py** は models, parser に依存
- **scenario_validator.py** は models にのみ依存
- **scenario_statistics.py** は models にのみ依存
- **scenario_report.py** は models, statistics に依存

### Version 1.1 との独立性

- Version 1.1（config.py, simulator.py, statistics.py, report.py, main.py）は独立して動作
- Version 1.2 は Version 1.1 を参照しない
- 両方を同じディレクトリに配置しても名前衝突は発生しない

---

## 命名規則

### ファイル名

- Version 1.1: `snake_case.py`（単語）
- Version 1.2: `scenario_snake_case.py`（プレフィックス付き）
- テスト: `test_scenario_snake_case.py`
- 設定: `snake_case.json`, `snake_case.csv`

### クラス名

- PascalCase（例: `ScenarioRecord`, `BatchValidator`）

### 関数名

- snake_case（例: `summarize`, `validate_batch`）

### 定数名

- UPPER_SNAKE_CASE（例: `REQUIRED_FIELDS`）

---

## コメント・Docstring規約

- モジュール先頭に概要コメント
- クラス・メソッドにDocstring（Args, Returns, Raises）
- 複雑なロジックにインラインコメント
- 日本語・英語混在可（内部コメントは日本語優先）
