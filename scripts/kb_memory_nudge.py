"""PostToolUse hook: Claude Code の auto-memory への書き込みを検知し、kb-save の検討を促す。

~/.claude/settings.json の hooks.PostToolUse (matcher: Write|Edit) から呼ばれる。
stdin に hook input JSON を受け取り、対象パスが memory ディレクトリのときだけ
additionalContext を返す。MEMORY.md (index) の更新は除外して二重発火を防ぐ。
"""

import json
import re
import sys
from pathlib import PureWindowsPath

REMINDER = (
    "memory への書き込みを検知した。いま保存した内容 (またはこのセッションで得た他の知見) が"
    "再利用可能な開発技術知見 (設計判断・実装パターン・解決したエラー・調査結果) を含むなら、"
    "kb-save skill に従って D:\\Claude-knowledge-bank にも保存すること。"
    "ユーザーの人物像・作業指示・好みに関する事実であれば memory のみでよい。"
)


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    path = (data.get("tool_input") or {}).get("file_path") or ""
    posix = PureWindowsPath(path).as_posix()
    if not re.search(r"/\.claude/projects/[^/]+/memory/", posix):
        return
    if posix.endswith("/MEMORY.md"):
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER,
        }
    }))


if __name__ == "__main__":
    main()
