# Site Capture Mac Lite — 試作版

このZIPは**Mac対応ソースとアプリ生成用ファイル**です。まだ配布用の `.app` は含みません。
Windows v0.4の同梱説明書を基に再構築しました。Windowsの実行ファイルを変換したものではありません。

## 小さくする仕組み

利用者のMacにインストール済みの無料のGoogle Chromeを使い、Chromium本体を同梱しません。
PythonとPlaywrightの制御プログラムは、生成したアプリに含まれます。利用者はPythonをインストールする必要がありません。
その分配布サイズは減りますが、完成したMacアプリの容量はMacで生成して測定するまで未確定です。
このソースZIPの容量を、完成アプリの容量と取り違えないでください。

Chromeが未導入の場合は https://www.google.com/chrome/ から先にインストールしてください。
Safariのみでは動作しません。Chromeの通常の閲覧プロファイルは利用せず、ログイン状態は引き継ぎません。
既存Chromeの更新により互換性が変化する場合があります。

## Macアプリを作る（WindowsからGitHubを使う）

1. ZIPを解凍します。
2. GitHubリポジトリのルートに、このフォルダの「中身」を追加します。`main.py`と`requirements.txt`がルートに来るようにします。
3. `.github/workflows/build-mac.yml`も必ず追加します。隠しフォルダを見落とさないでください。Web画面で入れる場合は「Add file → Create new file」でこのパスのファイルを作り、YAMLの内容を貼り付けます。
4. リポジトリの「Actions」から「Build Mac Lite」を開き、「Run workflow」を実行します。
5. 両方のジョブが成功したら、実行結果の「Artifacts」から必要なZIPをダウンロードします。外側のArtifacts ZIPの中に配布用ZIPがあります。
6. `arm64`がApple Silicon（M1以降）、`x86_64`がIntel用です。両方を一つにせず別配布することでサイズを抑えます。
7. 実行結果のSummaryにZIP容量が表示されます。Mac利用者に動作確認してもらってから配布してください。

この操作は自動公開をしません。既存のWindows Releaseも変更しません。
GitHub Actionsの利用料金はアカウント・リポジトリの条件で異なります。実行前にGitHub側の利用枠を確認してください。

## Macで直接生成する

Python 3.12（Tkinter付き）とGoogle Chromeが必要です。
Macのターミナルでフォルダに移動し、次を実行します。

```sh
bash build_mac.command
```

`release/`にMacアプリのZIPを生成します。初回の依存パッケージ取得にはネット接続が必要です。

## 完成アプリの使い方

1. 配布用ZIPを解凍し、`SiteCapture.app`をApplicationsフォルダへ移動します。
2. アプリを開き、`https://`などで始まるサイトURLを入力します。
3. PC・スマホ、最大ページ数（1〜10）、保存先を選びます。
4. 「サイトをまるごと撮影」を押します。
5. 完了表示後、「保存フォルダを開く」を押します。

PCは1440×900、スマホは390×844、倍率1倍。各ページの縦長PNGを保存します。
初期保存先はホームフォルダ内の `Site Capture`。撮影ごとに別フォルダを作ります。
MacではCommand+Shift+F、WindowsではCtrl+Shift+Fでも開始できます。アプリが選択されている間のみ有効です。
「中止」やウィンドウを閉じる操作は、処理中の読み込みが返るまで最大数十秒程度待つ場合があります。
エラーのURLと内容は `capture-log.json` に残します。一部だけ成功した画像も残します。

## 初回に開けない場合

本試作版はApple Developer ID署名・公証をしていません。開発時のアドホック署名とAppleによる公証は別です。
信頼できる自分のビルドであることを確認の上、開こうとした後にMacの「システム設定 → プライバシーとセキュリティ」の「このまま開く」を確認してください。
企業の管理設定などによって開けない場合もあります。セキュリティ設定全体を無効にする必要はありません。

## 対応範囲と制限

- iPhone/iPad用ではありません。
- 同じスキーム・ホスト・ポートのページだけを巡回します。HTTP→HTTPS、wwwの有無で別サイトになるため、ブラウザで開いた後の最終URLを入力します。
- クエリとアンカーは除去します。`?id=...`で記事が変わるサイトやハッシュ型SPAは網羅できません。
- リンクが自動検出できるページのみ。クリック操作、ログイン、フォーム送信、Cookie同意操作は行いません。
- 外部の画像やフォントは表示のため取得します。外部ページへのトップレベル移動は遮断します。
- エラーURLも検出上限に含みます。リダイレクトによる重複を除くため、画像数が上限を下回ることがあります。
- 長いページ、無限スクロール、遅延画像、CAPTCHA、動画、固定表示は完全再現を保証しません。
- Windows v0.4と速度・画面・内部処理の完全一致は未検証です。現在は表示モードを順番に撮影します。
- 想定ビルド環境はmacOS 15、Python 3.12。古いmacOSでの動作は未確認です。

## 検証

```sh
python -m unittest discover -s tests -v
SITECAPTURE_INTEGRATION=1 python -m unittest discover -s tests -v
```

後者はGoogle Chromeが必要です。ローカルHTTPサーバーを使い、PC・スマホPNGの幅・高さ、動的リンク、HTTPエラー、外部リダイレクト遮断、重複除外を確認します。
GitHubのMacビルドはこのブラウザ検証を実行し、失敗した場合は成果物を生成しません。

参照: https://playwright.dev/python/docs/browsers 、 https://pyinstaller.org/en/stable/usage.html 、 https://github.com/actions/runner-images
