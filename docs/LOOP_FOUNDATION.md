# 自律ループの基盤

`loop/controller.py` は、エージェントを有限の作業単位で回すための制御プログラムです。
テストは `python3 -m unittest discover -s tests -v` で実行します(標準ライブラリのみ)。

## 設計の要点
- **制御は外側のプログラムが持つ**: 状態、上限、再試行、完了の判定は controller が持ちます。エージェント(worker)は1回分の作業だけをする短命のプロセスです。
- **停止の条件を必ず決める**: `max_iterations`(回数の上限)、`time_limit_sec`(時間の上限)、`retry_budget`(連続失敗の上限)の3つです。どれかに達すると止まり、理由を記録します。
- **変更範囲の制限**: `allowed_paths` の外を変えたら、その回は失敗にします。
- **検証は作業と別**: `checks` のコマンドが0で終わったときだけ成功とします。エージェントの自己評価は使いません。
- **状態の保存**: `state.json` を一時ファイル経由で置き換えます(途中で落ちても壊れない)。再実行すると、続きから再開します。終わった状態は再実行しません。
- **失敗を隠さない**: 各回の結果は `log.md` に追記します。

## 契約(contract)の例
```json
{
  "goal": "字幕整形の関数を直す",
  "worker": ["opencode", "run", "-m", "opencode/glm-5.3-flash-free", "--dir", "/work", "直す"],
  "checks": [["python3", "-m", "pytest", "-q"]],
  "allowed_paths": ["src/", "tests/"],
  "max_iterations": 5,
  "retry_budget": 3,
  "time_limit_sec": 3600
}
```

## 実行
```
python3 loop/controller.py contract.json --workdir /path/to/work --state-dir /path/to/state
```
終了コードは、成功なら 0、それ以外は 1 です。

## 調べた出典
- 上限を2つ以上決める(成功条件、回数、時間、費用)こと、「とにかく続ける」指示は完了の基準がなく危険なこと: [Bounded AI Agent Loops: Checks, Retries, and Stop Rules](https://simeononsecurity.com/articles/effective-ai-bounded-agent-loops/)、[How to Build a Robust AI Loop: The Six-Component Toolkit](https://www.besthub.dev/articles/how-to-build-a-robust-ai-loop-the-six-component-toolkit-and-common-pitfalls-642bbd635f6b)
- 再試行回数を共有状態に持ち、閾値で人に知らせて止めること: [How to Design AI Agent Workflows](https://www.fast.io/resources/how-to-design-ai-agent-workflows.md)
- 2回までなど固定の試行予算と、編集可能なファイルの制限: [Loop Engineering: The Anatomy of Reliable Agentic AI](https://pub.towardsai.net/loop-engineering-the-anatomy-of-reliable-agentic-ai-d4dacca52549)
- 制御はシェルなどの外側に置き、エージェントは短命の作業者として JSON を返す: [nibzard wrappers](https://nibzard.com/wrappers/)
- ファイルの状態保存は分かりやすく持ち運べるが、書き込みの競合に注意する: [AI Agent Workflow State Persistence](https://www.fast.io/resources/ai-agent-workflow-state-persistence.md)
- 文脈を反復ごとにリセットし、進み具合はファイルと git の履歴に残す(Ralph 型のループ): [Ralph Loops](https://docs.praison.ai/docs/concepts/ralph-loops.md)
- 冪等な書き込みで、再試行しても重複しない: [Idempotent Operations for AI Agents](https://fast.io/resources/ai-agent-idempotent-operations.md)
- 並行するエージェントは git worktree で分けて作業する: [besthub.dev の同記事](https://www.besthub.dev/articles/how-to-build-a-robust-ai-loop-the-six-component-toolkit-and-common-pitfalls-642bbd635f6b)

※ 正式な標準のテンプレートは見つかりませんでした。上の構成は、これらの出典をもとにした設計です。
