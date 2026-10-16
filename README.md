# AI-Environment

AI Army の動画制作から始まり、枝分かれして基盤モデルと複数プラットフォームで動く AI 開発環境を育てるリポジトリです。

## 目的

- 人の指示がなくても、DeepSeek と GLM が改善課題を見つけ、議論し、検証し、良いものだけを積み上げ続ける。
- 対象は二層です。
  1. **製品層**: 動画制作システム（台本、素材、音声、描画、検査、保存）と、そこから派生する制作ツール。
  2. **協調層**: AI 同士が役割を分けて協力する仕組み（司令、実装、批評、検証）そのもの。
- 最終的には基盤モデルの評価・微調整の仕組みと、複数プラットフォーム向けの成果物まで広げる。

## 構成

| パス | 役割 |
| --- | --- |
| `AGENTS.md` | 継続作業の実行指示。各タスク完了後の次タスク選定と中断時の記録 |
| `agent.md` | `AGENTS.md` への参照 |
| `docs/AUTONOMY_STATE.md` | 再開用の現在地、障害、次の実行可能な課題 |
| `AUTONOMY_CHARTER.md` | 自律運用の憲章。許可範囲、禁止事項、停止条件 |
| `docs/` | 設計、工程、教訓 |
| `tools/github_preflight.py` | GitHub CLI・ブランチ・送信先・公開承認の読み取り専用チェック |
| `docs/GITHUB_WORKFLOW.md` | GitHub CLIと認証済みアプリによる送信・確認手順 |
| `tools/ai_env.py` | オフラインで使えるプロジェクト・タスク台帳 |
| `tests/` | 台帳の回帰テスト |
| `workspaces/` | 将来の隔離作業領域 |

## 今すぐ使う

Python 3.10 以降、追加パッケージ不要です。

```sh
python3 tools/ai_env.py init
python3 tools/ai_env.py project add --name "字幕チェック" --objective "字幕の欠落を減らす"
python3 tools/ai_env.py task add --project 字幕チェック --title "要件を整理" --acceptance "受入条件が記録されている"
python3 tools/ai_env.py task list --project 字幕チェック
python3 tools/ai_env.py export --project 字幕チェック
```

現状、自律ループ、24時間常駐、独自基盤モデル学習は未実装です。動画制作VMの正本ファイルも未取り込みです。課金なし・公開なしを維持し、検証と記録を積み上げてから機能を広げます。
