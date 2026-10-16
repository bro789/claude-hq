"""安装指挥中心。

用法：python install.py <目标文件夹>
例如：python install.py ~/Desktop/00-Headquarters

把 headquarters/ 里的文件复制到目标文件夹，并把文件里的 {{HQ_DIR}}、{{CLAUDE_DIR}} 换成实际路径。
目标文件夹里已有的 resources.json 和 hq_registry.json 不会被覆盖。
另外生成 global-CLAUDE.snippet.md，它的内容要你自己追加到 ~/.claude/CLAUDE.md。
本脚本不改 ~/.claude 里的任何文件。
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEEP = {"resources.json", "hq_registry.json"}  # 已有就不覆盖
PLACEHOLDER = re.compile(r"\{\{(HQ_DIR|CLAUDE_DIR)\}\}((?:/[^/\s`'\"，。；、（）()|]+)*/?)")


def render(text, hq_dir, claude_dir):
    def sub(m):
        base = hq_dir if m.group(1) == "HQ_DIR" else claude_dir
        tail = m.group(2)
        path = os.path.join(base, *[p for p in tail.split("/") if p])
        return path + os.sep if tail.endswith("/") else path
    return PLACEHOLDER.sub(sub, text)


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    target = os.path.abspath(os.path.expanduser(sys.argv[1]))
    claude_dir = os.path.join(os.path.expanduser("~"), ".claude")
    src = os.path.join(HERE, "headquarters")
    os.makedirs(target, exist_ok=True)
    for name in sorted(os.listdir(src)):
        dst = os.path.join(target, name)
        if name in KEEP and os.path.exists(dst):
            print(f"保留已有的 {dst}")
            continue
        with open(os.path.join(src, name), encoding="utf-8") as f:
            write(dst, render(f.read(), target, claude_dir))
        print(f"写入 {dst}")

    resources = os.path.join(target, "resources.json")
    if not os.path.exists(resources):
        shutil.copyfile(os.path.join(target, "resources.example.json"), resources)
        print(f"写入 {resources}（照着你的机器改）")

    with open(os.path.join(HERE, "global-CLAUDE.md"), encoding="utf-8") as f:
        snippet = render(f.read(), target, claude_dir)
    snippet_path = os.path.join(target, "global-CLAUDE.snippet.md")
    write(snippet_path, snippet)

    print(f"""
装好了，还剩三步：
1. 编辑 {resources}，登记你的显卡、长期占用的端口、要加写锁的共享文件。
2. 把 {snippet_path} 的内容追加到 {os.path.join(claude_dir, "CLAUDE.md")}。
3. 在 {os.path.join(claude_dir, "settings.json")} 里加上 "crossSessionInbound": "accept"，然后重开要参与的对话。
之后新开一个对话，对它说"你是指挥中心"。""")


if __name__ == "__main__":
    main()
