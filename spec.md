# LLMベンチマークツール 仕様

## 1. 目的

複数のLLMに対して同一テストを実行し、モデル間の性能を比較できるブラウザベースのベンチマークツールを提供する。

## 2. スコープ

- MVPでは、単一ユーザーのローカル利用を前提とする
- ベンチマーク対象のLLMは複数指定可能
- テストは「テスト項目」と「テストグループ」で管理する

## 3. 必須要件

### 3.1 実行環境

- ブラウザで利用できること
- Python、Django、Tailwindで実装すること

### 3.2 モデル

- LlmModel
  - `model`: モデル名
  - `base_url`: URL
  - `api_key_name`: APIキーの環境変数名
  - `can_parallel`: 並列実行可能か

- Item
  - `name`: 名前
  - `problem`: 問題
  - `answer`: 正解

- Group
  - `name`: 名前

- GroupItem
  - `item`: Itemの外部キー
  - `group`: Groupの外部キー

- Result
  - `group`: Groupの外部キー
  - `item`: Itemの外部キー
  - `llm_model`: LlmModelの外部キー
  - `judge`: 判定結果

### 3.3 実行機能

- Groupを指定して実行できること
- ResultをGroupごと、Itemごと、LlmModelごとに一覧で表示できること

## 4. 画面要件（MVP）

管理画面を使うこと。

## 5. ディレクトリ

```text
benchmark-tools/
  pyproject.toml
  src/
    core/
    manage.py
    project/
    ...
```
