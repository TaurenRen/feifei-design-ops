#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""sync_github.py —— 把本地仓库全量同步到 GitHub（以本地为准，含二进制文件）。

为什么不用 git push：本机 git 的 HTTPS 通道被代理拦死（curl 28 / CONNECT tunnel failed），
但 gh CLI 走 api.github.com 是通的。故改用 Git Data API 一次提交全量文件。
二进制（png/mp4/jpg）走 base64，文本走 utf-8。

用法：
    python scripts/sync_github.py                  # message 自动生成
    python scripts/sync_github.py -m "add xxx"
    python scripts/sync_github.py --create         # 仓库不存在时先建（public）

前提：gh 已登录（gh auth status）
"""
import base64
import datetime
import json
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GH = os.environ.get("GH_EXE") or r"D:/WorkBuddy/.workbuddy/binaries/tools/bin/gh.exe"
OWNER = os.environ.get("GH_OWNER") or "TaurenRen"
NAME = os.environ.get("GH_NAME") or "feifei-design-ops"
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TMP = os.path.join(REPO, ".sync-tmp")
MAX_BLOB = 40 * 1024 * 1024      # 单个文件上限，超过的跳过（GitHub API 限制更严，见下）


def gh(args, inp_path=None, allow_fail=False):
    cmd = [GH, "api"] + args
    if inp_path:
        cmd += ["--input", "-"]
        with open(inp_path, "rb") as fh:
            r = subprocess.run(cmd, stdin=fh, capture_output=True, text=True, encoding="utf-8")
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 and not allow_fail:
        print("FAIL:", " ".join(args))
        print((r.stdout or "")[:1500], (r.stderr or "")[:800])
        sys.exit(1)
    try:
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except Exception:
        return {}


def main():
    os.makedirs(TMP, exist_ok=True)
    msg = None
    if "-m" in sys.argv:
        msg = sys.argv[sys.argv.index("-m") + 1]
    if not msg:
        msg = "sync %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if "--create" in sys.argv:
        r = subprocess.run([GH, "repo", "create", "%s/%s" % (OWNER, NAME), "--public",
                            "--description", "huashu-design 3.0 的落地增强层：环境体检、导出修坑、交付前复核"],
                           capture_output=True, text=True, encoding="utf-8")
        print("create:", (r.stdout or r.stderr or "").strip()[:200])

    info = gh(["repos/%s/%s" % (OWNER, NAME)])
    branch = info.get("default_branch", "main")
    print("repo:", info.get("full_name"), "branch:", branch, "size:", info.get("size"))

    files = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files"],
                           cwd=REPO, capture_output=True, text=True, encoding="utf-8").stdout.split()
    if not files:
        print("git ls-files 为空 —— 先 git add")
        sys.exit(1)

    tree, skipped = [], []
    for f in files:
        p = os.path.join(REPO, f.replace("/", os.sep))
        size = os.path.getsize(p)
        if size > MAX_BLOB:
            skipped.append((f, size))
            continue
        data = open(p, "rb").read()
        try:
            entry = {"path": f, "mode": "100644", "type": "blob", "content": data.decode("utf-8")}
        except UnicodeDecodeError:
            entry = {"path": f, "mode": "100644", "type": "blob",
                     "content": base64.b64encode(data).decode("ascii"), "encoding": "base64"}
        tree.append(entry)
    print("files =", len(tree), "skipped =", len(skipped))
    for f, s in skipped:
        print("   skip", f, f"{s/1e6:.1f} MB")

    tree_path = os.path.join(TMP, "tree.json")
    with open(tree_path, "w", encoding="utf-8") as fh:
        json.dump({"tree": tree}, fh, ensure_ascii=False)

    head = gh(["repos/%s/%s/git/refs/heads/%s" % (OWNER, NAME, branch)], allow_fail=True)
    if not head.get("object"):
        readme = open(os.path.join(REPO, "README.md"), "rb").read()
        init_path = os.path.join(TMP, "init.json")
        with open(init_path, "w", encoding="utf-8") as fh:
            json.dump({"message": "init", "content": base64.b64encode(readme).decode("ascii")}, fh)
        subprocess.run([GH, "api", "-X", "PUT",
                        "repos/%s/%s/contents/README.md" % (OWNER, NAME), "--input", "-"],
                       stdin=open(init_path, "rb"), capture_output=True, text=True, encoding="utf-8")
        print("init branch done")
        parents = []
    else:
        parents = [head["object"]["sha"]]

    t = gh(["-X", "POST", "repos/%s/%s/git/trees" % (OWNER, NAME)], inp_path=tree_path)
    print("tree   =", t.get("sha"))

    commit_path = os.path.join(TMP, "commit.json")
    with open(commit_path, "w", encoding="utf-8") as fh:
        json.dump({"message": msg, "tree": t["sha"], "parents": parents}, fh, ensure_ascii=False)
    c = gh(["-X", "POST", "repos/%s/%s/git/commits" % (OWNER, NAME)], inp_path=commit_path)
    print("commit =", c.get("sha"))

    ref_path = os.path.join(TMP, "ref.json")
    with open(ref_path, "w", encoding="utf-8") as fh:
        json.dump({"sha": c["sha"], "force": True}, fh)
    gh(["-X", "PATCH", "repos/%s/%s/git/refs/heads/%s" % (OWNER, NAME, branch)], inp_path=ref_path)
    print("DONE -> https://github.com/%s/%s" % (OWNER, NAME))


if __name__ == "__main__":
    main()
