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
- Dockerが使えること

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

### Dockerイメージ作成

初回のみ、Dockerイメージを作成します。

```sh
(cd sandbox; task build)
```

`sandbox`というイメージが作成されます。

### 実行方法

以下のようにDjangoを起動します。

```sh
task manage runserver
```

`http://localhost:8000/` を開いて `admin` でログインしてください。

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

### 環境変数

- Gemini APIを使用する場合は`.env`の`GEMINI_API_KEY`にAPIキーを指定してください。Geminiの場合、LLMモデルの「APIキーの環境変数名」は空欄でOKです。

### thinkingレベル

- thinkingレベルは、LLMモデルの「thinkingレベル」で指定しますが、LM Studioでは、この指定は無視されます。LM Studioでthinkingを変えたいときは、LM Studio側で設定してください。
- Gemini APIのthinkingレベルは、モデルによってデフォルト値（空欄時の値）が異なります。また、モデルによって指定可能なレベルが異なります。詳しくは <https://ai.google.dev/gemini-api/docs/thinking> を参照してください。

### サマリー計算

- `Result` は `group/item/llm_model`が同一の複数レコードが存在し得ます
- サマリーは生レコードの単純件数ではなく、重複キー平均化後の値を使用します

### マイグレーション（モデル変更時に必要）

```sh
task manage makemigrations
task manage migrate
```

### 国際化（I18N）

準備としてsettings.pyに以下を追加します。

```python
LOCALE_PATHS = [BASE_DIR / "locale"]
```

src以下のテンプレートから抽出する場合は、以下を実行します。

```sh
mkdir src/locale
(cd src; uv run django-admin makemessages -l ja)
```

そうでない場合は、`src/locale/ja/LC_MESSAGES/django.po`を下記のように作成します。

```text
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\n"

msgid "Apply Filters"
msgstr "フィルター適用"
```

`django.po`を修正後、以下を実行します。

```sh
(cd src; uv run django-admin compilemessages)
```

## ユーティリティ

### lint（コードのチェック）

```sh
task lint
```

※ `pyrefly`と`ruff`が必要

### test（単体テスト）

```sh
task test
```
