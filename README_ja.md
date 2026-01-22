[English](./README.md) | [中文版](./README_zh.md) | 日本語版

# 画像検索アプリケーション

## 概要

OceanBase のベクトルストレージと検索機能を活用して、画像検索アプリケーションを構築できます。このアプリケーションは、画像からベクトル埋め込み（embedding）を生成してデータベースに保存すると同時に、画像のテキスト説明（キャプション）も自動生成します。ベクトル検索・全文検索・ハイブリッド検索の 3 つのモードをサポートしており、ユーザーが画像をアップロードすると、データベースから最も類似した画像を検索して返します。

**主な機能**：
- **ベクトル検索**：画像の視覚的特徴に基づく類似度検索
- **自動説明生成**：API（Qwen-VLなど）を使用して画像のテキスト説明を自動生成
- **ハイブリッド検索**：ベクトル検索と全文検索を組み合わせて精度を向上
- **調整可能な重み**：ベクトルとテキストの重み比率の調整をサポート（0.0-1.0）
- **距離しきい値フィルタリング**：距離しきい値を設定して検索結果をフィルタリング

注意：画像を準備し、UI で `Image Base` 設定を更新する必要があります。ローカルに画像がない場合は、Kaggle の [Animals-10](https://www.kaggle.com/datasets/alessiocorrado99/animals10/data) データセットなどをダウンロードできます。

## 前提条件

1. [Python 3.9](https://www.python.org/downloads/) 以上と対応する [Pip](https://pip.pypa.io/en/stable/installation/) ツールをインストール

2. [Docker](https://docs.docker.com/get-docker/) をインストールして seekdb データベースコンテナを起動

3. 依存関係管理ツールとして [uv](https://github.com/astral-sh/uv) をインストール（以下のコマンドを参照）

```bash
python3 -m pip install uv
```

4. seekdb データベース接続情報を取得

## セットアップ手順

### 1. seekdb のデプロイ

以下のコマンドで seekdb docker コンテナを起動します：

```bash
docker run -d -p 2881:2881 -p 2886:2886 --name seekdb oceanbase/seekdb
```

データの永続化が必要な場合は、データディレクトリをマウントできます：

```bash
# Linux または MacOS
mkdir -p seekdb
docker run -d -p 2881:2881 -p 2886:2886 \
  -v $PWD/seekdb:/var/lib/oceanbase \
  --name seekdb oceanbase/seekdb

# Windows
docker volume create seekdb
docker run -d -p 2881:2881 -p 2886:2886 \
  -v seekdb:/var/lib/oceanbase \
  --name seekdb oceanbase/seekdb
```

seekdb の設定と使用方法の詳細については、[seekdb 公式リポジトリ](https://github.com/oceanbase/seekdb) を参照してください。

### 2. 依存関係のインストール

```bash
uv sync
```

### 3. 環境変数の設定

`.env.example` ファイルを提供しています。これを `.env` にコピーして、データベース接続情報と API 設定を入力する必要があります。以下のコマンドを参照してください：

```bash
cp .env.example .env
vi .env
```

**必須設定**：
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`：データベース接続情報
- `API_KEY`：画像説明生成用の API キー（例：Qwen DashScope API Key）
- `BASE_URL`：API エンドポイント（デフォルト：`https://dashscope.aliyuncs.com/compatible-mode/v1`）
- `MODEL`：モデル名（デフォルト：`qwen-vl-max`）

### 4. 画像検索 UI の起動

```bash
uv run streamlit run --server.runOnSave false image_search_ui.py
```

### 5. 画像データの処理と保存

アプリケーション画面を開くと、左側のサイドバーに `Image Base` の入力欄が表示されます。準備した画像ディレクトリの絶対パスを入力し、`Load Images` ボタンをクリックします。アプリケーションが画像データを処理して保存し、画面に処理の進捗が表示されます。

### 6. 画像検索の使用

画像の処理が完了すると、画面上部に画像アップロードセクションが表示されます。画像をアップロードして類似画像を検索できます。アプリケーションがデータベースから最も類似した画像を検索して返します。

#### 検索パラメータ

- **取得件数（Top-K）**：返される類似画像の数（1-30、デフォルト 10）
- **ベクトル重み**：検索モードを制御
  - `1.0`：純粋なベクトル検索（画像の視覚的特徴のみに基づく）
  - `0.7`（推奨）：ハイブリッド検索、ベクトル主体でテキスト補完
  - `0.5`：ベクトルとテキストの均等重み
  - `0.0`：純粋なテキスト検索（画像説明のマッチングのみに基づく）
- **距離しきい値（Threshold）**：この値以下の距離を持つ結果のみを表示（デフォルト 0.6。ベクトル検索／ハイブリッド検索の「ベクトル側」にのみ適用）

#### 検索結果

各検索結果には以下が表示されます：
- 類似画像
- 画像説明（キャプション）
- 距離（distance）：距離が小さいほど類似（純テキスト検索では表示されません）
- ファイルパス

![image_search_ui](./demo/image-search-demo.png)

## よくある質問

### 1. 画像説明APIキーの取得方法は？

このアプリケーションは、画像説明を生成するために OpenAI 互換 API をサポートするビジョンモデル API が必要です。**Qwen-VL**の使用を推奨します：

1. [Alibaba Cloud DashScope](https://dashscope.aliyun.com/) にアクセス
2. DashScope 上で Qwen サービスを有効化
3. API キーを作成
4. `.env` ファイルに `API_KEY` を設定

GPT-4V、Azure OpenAI などの OpenAI 互換サービスも利用でき、その場合は `BASE_URL` と `MODEL` の設定を適宜変更してください。

### 2. libGL.so.1 ファイルが見つからない場合の対処方法は？

アプリケーション UI の実行時に `ImportError: libGL.so.1: cannot open shared object file` エラーが発生した場合は、[この投稿](https://stackoverflow.com/questions/55313610/importerror-libgl-so-1-cannot-open-shared-object-file-no-such-file-or-directo) を参照してください。

CentOSの場合、以下のコマンドを実行：

```bash
sudo yum install mesa-libGL -y
```

Ubuntu/Debianの場合、以下のコマンドを実行：

```bash
sudo apt-get install libgl1
```

### 3. 適切なベクトル重みの選び方は？

検索ニーズに基づいて適切なベクトル重みを選択してください：

- **0.9-1.0**：視覚的類似性が最も重要（例：類似した構図、色、スタイルの画像を見つける）
- **0.6-0.8**：視覚主体で意味補完（推奨、最適なバランス）
- **0.3-0.5**：視覚と意味が同等に重要
- **0.0-0.2**：意味が最も重要（例：「すべてのキツネを見つける」、視覚的な違いは関係なし）

### 4. pkg_resources モジュールが見つからない場合の対処方法は？

アプリケーション UI の実行時に `ModuleNotFoundError: No module named 'pkg_resources'` エラーが発生した場合は、[この投稿](https://stackoverflow.com/questions/7446187/no-module-named-pkg-resources) を参照してください。

具体的には、以下のコマンドを参照してください：

```bash
python3 -m pip install --upgrade pip
python3 -m pip install setuptools
```
