# Ten_syoku_bot

## 概要

Ten_syoku_botは、Recruit Agentの求人情報を自動取得し、CSV形式で保存し、構造化データへ変換・分析するためのツールです。  
Webオートメーションによる求人票収集し、Pythonによるデータクレンジング・変換処理を統合し、最終的にはPower BIを用いてダッシュボード化し、求人市場の傾向分析に活用できます。


---

## 分析結果ハイライト(データソース 2026.01-2026.03)

- 求人職種別の募集件数分布（DS / DA / DE / BI / Consultant など）
- リモート勤務可否および勤務地条件の傾向分析
- 必須スキル・歓迎スキルの出現頻度分析
- 年収レンジと職種・スキル要件の相関分析
- 求人票テキスト情報のカテゴリ別構造化分析

---

## リポジトリ構成

```text
       起動
        ↓
        ↓ JDbot.py 実行
        ↓
    Full_Data.csv
        ↓
        ↓ Data-Cleansing.py 実行
        ↓
    Structured_Data.csv
        ↓
        ↓ One_Hot_Transformation.py 実行
        ↓
    One_Hot.csv
    Analysis_Report.txt
        ↓
        ↓ Power BIにて分析
        ↓
    分析報告Dashboard.pbix
```

---

## ファイル説明

| ファイル名 | 説明 |
|---|---|
| JDbot.py | Recruit Agent の求人情報を自動取得するスクレイピングスクリプト |
| Full_Data.csv | 取得した求人票の生データ |
| Data-Cleansing.py | データクレンジングおよび構造化処理 |
| Structured_Data.csv | クレンジング後の構造化データ |
| One_Hot_Transformation.py | One-Hot Encoding 変換処理 |
| One_Hot.csv | 分析用変換済みデータ |
| Analysis_Report.txt | 自動生成された分析レポート |
| 分析報告Dashboard.pbix | Power BI ダッシュボードファイル |

---

## 使用方法

### Step 1：スクリプト設定

1. `JDbot.py` を開きます。
2. 収集対象に応じて以下の内容を修正します。
   - 検索結果 URL
   - 更新日条件
3. 修正後、保存します。

---

### Step 2：求人情報の取得

1. メインプログラムを実行します。

```bash
python JDbot.py
```

2. 自動で起動したブラウザ画面で Recruit Agent にログインします。
3. CMD 画面に戻り、Enter キーを押すとスクレイピングが開始されます。
4. CMD 画面に「スキップ」と表示される件数が増え始めた場合、既取得データとの重複が発生しているため、任意のタイミングで手動停止してください。

---

### Step 3：データクレンジング

取得した生データを整形します。

1. 以下を実行します。

```bash
python Data-Cleansing.py
```

2. 不要文字除去、項目分割、欠損補完などの前処理が行われます。
3. `Structured_Data.csv` が生成されます。

---

### Step 4：One-Hot変換

カテゴリ変数を分析用形式へ変換します。

1. 以下を実行します。

```bash
python One_Hot_Transformation.py
```

2. スキル、勤務地、雇用条件などを One-Hot Encoding 形式に変換します。
3. 以下のファイルが生成されます。
   - `One_Hot.csv`
   - `Analysis_Report.txt`

---

## 分析方法

生成されたデータを Power BI に取り込み、以下のような分析を実施します。

- 職種別件数分析
- 年収分布分析
- スキル別出現率分析
- リモート可否分析
- 地域別求人分布分析
- スキル × 年収クロス分析

使用ファイル：

- `分析報告Dashboard.pbix`

---

## 実行環境

- Python 3.x
- Selenium
- pandas
- numpy
- Power BI Desktop
- Google Chrome
- ChromeDriver

---

## 必要ライブラリ

以下を事前にインストールしてください。

```bash
pip install selenium
pip install pandas
pip install numpy
```

---

## 注意事項

- 本ツールの利用には Recruit Agent のアカウントが必要です。
- ログイン処理は手動で行います。
- Web サイト仕様変更によりスクレイピング動作が影響を受ける可能性があります。
- 取得データは利用規約に従って取り扱ってください。

---

## 今後の改善予定

- 自動ログイン機能追加
- 検索条件 GUI 化
- 自動重複判定停止機能
- Power BI レポート自動更新
- 求人票テキストの自然言語解析対応

---

## 作者

個人学習および転職市場分析を目的として作成したプロジェクトです。  
Python を用いたデータ収集・前処理・可視化パイプライン構築の実践例として開発しました。