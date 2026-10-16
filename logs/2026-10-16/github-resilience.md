# 復旧・継続規則とGitHub運用

## 利用者の指示

commit・push、エラーを減らして復旧・継続する規則の追記、GitHub CLIの適用。
既存リポジトリがpublicであることを提示し、利用者は今回の公開先へのpushを明示承認した。

## 変更

- AGENTS.mdに実行前検査、原子的な状態保存、冪等性、期限、排他、
  原因別の再試行、監視と復旧、GitHub CLI運用を追加。
- 憲章と工程文書を今回のpush承認に合わせた。包括的な無人pushの許可にはしていない。
- docs/GITHUB_WORKFLOW.mdにgh/git手順、認証不足と競合時の扱いを記載。
- tools/github_preflight.pyに読み取り専用の事前検査を実装。
  ブランチ、fetch/push先、gh認証、権限、公開承認を確認する。
- 新規テスト6件で拒否条件と期限・秘密出力抑止を検証。

## 検証

- PASS: python3 -m unittest discover -s tests -v — 11件成功。
- PASS: git diff --check。
- PASS（異常検出）: python3 tools/github_preflight.py --allow-public は
  gh未認証を検出して終了コード2。認証済みと偽装しない。
- gh 2.46.0は導入済み。gh repo viewは認証不足。
- 通常のgit push --dry-runも資格情報不足で失敗。再試行ループは行わない。
- GitHubアプリは対象リポジトリのpublic設定とpush権限を確認できた。

## 送信方針

アプリ経由で検証済みの作業ツリーをGitHubの作業ブランチへ送る。
APIが作成するcommitはローカルの作者・時刻と異なるためSHAが変わり得る。
元のローカルコミットは退避ブランチに保存し、tree一致を確認して追従させる。
リモート確認と最終SHAは実際の送信結果で報告する。

## 限界と次の一手

無エラー・無停止の保証はしない。常駐ループ、監視サービス、故障注入試験は未実装・未起動。
次はdocs/AUTONOMY_STATE.mdに従い、dry-run可能なループと停止・再開の制御を実装する。
課金・有料モデル・デプロイ・PR作成は行わない。
