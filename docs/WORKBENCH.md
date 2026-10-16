# ローカルプロジェクト台帳

Python 3.10 以降の標準ライブラリだけで、プロジェクト、完了条件つきタスク、進捗をローカルSQLiteに記録します。モデルやネットワーク接続を使わず、リポジトリ外への送信もしません。

## 始め方

```sh
python3 tools/ai_env.py init
python3 tools/ai_env.py project add --name "字幕チェック" --objective "字幕の欠落を早く見つける"
python3 tools/ai_env.py task add --project 字幕チェック --title "受入条件を書く" --acceptance "PASSとFAILの例がある" --owner qa
python3 tools/ai_env.py task list --project 字幕チェック
python3 tools/ai_env.py task status --project 字幕チェック --id 1 --to in_progress
python3 tools/ai_env.py export --project 字幕チェック
```

DBは既定で `.ai-environment/workbench.sqlite3` に作成します。別の保存先は各コマンドの前に `--db PATH` を指定します。Markdown出力は標準出力へ書くため、既存ファイルを上書きしません。出力を保存する場合はシェルからリダイレクトしてください。

プロジェクト名から日本語対応のIDを作ります。同名IDは上書きせずエラーにします。タスク状態は `todo`、`in_progress`、`blocked`、`done` で、無効な遷移は拒否します。追加と状態変更はイベントとして記録します。

## 役割と次の枝

自律開発は企画、調査、実装、検証の記録をこの台帳で追跡できます。次の製品候補は成果物の納品前監査、動画素材・字幕監査、データセット品質監査です。エージェントを常駐させる機能はまだありません。

この台帳だけでは課金を技術的に防ぐ仕組みにはなりません。無人モデル運転を追加する場合は、無料モデルID固定、課金資格情報の隔離、通信先制限、実行回数上限、監査ログ、公開禁止を別途実装してから有効化してください。

## 開発

```sh
python3 -m unittest discover -s tests -v
```
