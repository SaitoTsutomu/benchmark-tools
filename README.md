# benchmark-tools

## 概要

`benchmark-tools` は、テスト項目とLLMモデルの組み合わせでベンチマークを実行し、結果をDjango Adminで管理・集計するツールです。

## 主な機能

- テストグループごとのベンチマーク実行
- 実行結果（`Result`）の保存
- 管理画面での検索・フィルター
- テストグループごと、LLMごとのサマリー表示

## 使用方法

### 前提条件

- Python `3.14` 以上
- `uv`
- `taskipy`（`uv tool install taskipy`）
- `.env`（`.env.sample` をコピーして作成）

```sh
cp .env.sample .env
```

`.env` には少なくとも以下を設定してください。

- `DJANGO_SUPERUSER_PASSWORD`（`task init_db` で作成する管理ユーザー `admin` のパスワード）
- 実行したい `LlmModel.api_key_name` に対応するAPIキー環境変数

### 初期化

以下でDB初期化・管理ユーザー作成・初期データ投入を行います。

```sh
task init_db
```

初回のみ、Tailwindを初期化します。

```sh
task manage tailwind install
```

### 実行方法

以下のようにDjangoを起動します。

```sh
task manage runserver
```

参考:

以下のようにするとDjangoとTailwindの監視を同時に起動します。デザインの開発時に便利です。

```sh
task manage tailwind dev
```

その後、`http://localhost:8000/admin/` を開いて `admin` でログインしてください。

### ベンチマーク実行手順

1. テストグループ画面で対象グループを選択
2. アクション `選択したテストグループでベンチマークを実行` を実行
3. テスト結果画面で結果を確認

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
```

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
