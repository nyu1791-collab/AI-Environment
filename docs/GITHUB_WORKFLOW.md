# GitHub CLIと送信手順

2026-10-16: 利用者は今回の変更を既存の公開リポジトリ
nyu1791-collab/AI-Environment の codex/autonomous-loop にcommit・pushすることを許可した。
可視性の変更、別リポジトリ、PR、デプロイ、以後の無人pushはこの承認に含めない。

## 読み取りと事前確認

Gitはローカル差分・コミット・送受信に、ghはGitHubの権限・可視性・リモート状態の確認に使う。

```sh
git status --short --branch
git diff --stat
gh --version
gh auth status --hostname github.com
gh repo view nyu1791-collab/AI-Environment --json nameWithOwner,isPrivate,viewerPermission,url
python3 tools/github_preflight.py --allow-public
```

事前確認スクリプトは読み取り専用。ブランチ、fetch/push先、認証、書込権限、
公開先の承認を確認し、不明な状態を成功にしない。各コマンドは20秒で打ち切る。
複数の送信先やURL内の資格情報は拒否する。認証情報を含み得る生のエラーは出力しない。
このスクリプト自体は秘密検査、テスト、実際のpushを行わない。

今回のVMにはgh 2.46.0があるが、ghは未認証で、通常のgit HTTPS pushも認証不足だった。
事前確認はこの状態で非ゼロ終了するのが正しい。
無断のgh auth login、トークン表示・発行・コピーはしない。
接続済みGitHubアプリに同じ対象への権限がある場合は代替できる。

## commitとpush

```sh
python3 -m unittest discover -s tests -v
git diff --check
git diff
# 変更内容と秘密情報が含まれないことを確認してから、対象ファイルだけをgit addする。
git diff --cached --check
git diff --cached
git -c user.name='AI Environment Local' -c user.email='local-loop@localhost' commit -m 'Describe the verified change'
python3 tools/github_preflight.py --allow-public --require-clean
git fetch origin
git log --oneline --decorate -8
git push -u origin HEAD:refs/heads/codex/autonomous-loop
git ls-remote --heads origin refs/heads/codex/autonomous-loop
git rev-parse HEAD
```

ユーザー名とメールは既存のローカルコミットに使われていた値。
グローバル設定は変えない。実際のpush時は非対話実行と適切なタイムアウトを使う。
push対象が既に存在する場合は、その先端との関係を確認してからfast-forwardで送信する。
競合や拒否ではforce-pushせず、リモートを再取得して原因を確認する。

## 認証済みアプリを代替に使う場合

VM内のgh認証とGitHubアプリの認証は別である。アプリの資格情報をVMへ取り出さない。
ローカルの検証済みファイルからGit blob/tree/commitを作り、作業ブランチのrefだけを更新する。
別の既定ブランチに混ぜない。既存refがある場合は期待する先端SHAを指定して競合を検出する。
未作成のrefは作成専用の操作で作り、既に存在した場合は読み直して判断する。

アプリで作成するcommitは作者・時刻等によりローカルとはSHAが異なる場合がある。
その場合はtree SHAの一致を検証し、ローカルの元コミットを退避ブランチに残したうえで、
クリーンな作業ツリーをリモートの作業ブランチに追従させる。差分があれば切り替えない。
ブランチ・コミットURL、内容の一致、利用した送信手段を報告する。

## エラー時の継続

- 401/403や未認証: 自動再試行しない。許可された別経路があれば使用し、なければ保留。
- 429/一時的通信障害: 上限3回と待機を設ける。無制限の再送はしない。
- タイムアウト: リモートのrefを読み、反映済みなら成功として扱う。
- 非fast-forward: 先端を再取得し、他者の変更を消さずに解決する。
- pushを保留しても、依存しないローカル改善を進められる。
- 成否不明や未検証の状態で「push成功」と記録しない。
