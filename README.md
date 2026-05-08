# benchmark-tools

## 概要

`benchmark-tools` は、テスト項目とLLMモデルの組み合わせでベンチマークを実行し、結果をDjango Adminで管理・集計するツールです。

## 主な機能

- テストグループごとのベンチマーク実行
- 実行結果（`Result`）の保存
- 管理画面での検索・フィルター
- テストグループごと、LLMごとのサマリー表示

## 使用方法

### 準備

`uv`をインストールし、`uv tool install taskipy`でtaskipyをインストールしておいてください。
以下でDBを初期化します。

```sh
task init_db
```

下記でtailwindを初期化してください。

```sh
task manage tailwind install
```

### 実行方法

下記を実行し、`http://localhost:8000`を開いてください。

```sh
task manage runserver
# あるいは
task manage tailwind dev
```

## データモデル

- `Group`: テストグループ
- `Item`: テスト項目（問題・正解）
- `LlmModel`: 実行対象モデル
- `Result`: 実行結果（解答、実行時間、判定）

## ベンチマーク実行フロー

1. `Group` に紐づく `Item` と `LlmModel` を取得
2. 各組み合わせを実行
3. `Result` を保存
4. Adminサマリーで集計結果を確認

## 補足

### サマリー計算

- `Result` は `group/item/llm_model`が同一の複数レコードが存在し得ます
- サマリーは生レコードの単純件数ではなく、重複キー平均化後の値を使用します

### マイグレーション（モデル変更時に必要）

```sh
task manage makemigrations
task manage migrate
``

## ユーティリティ

### lint（コードのチェック）

```sh
task lint
```

### test（単体テスト）

```sh
task test
```

### pip-audit（脆弱性確認）

```sh
task pip-audit
```
