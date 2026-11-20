#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lookup.py — 社会组织控制权顾问 · 本地关键词检索

用途：在 references/ 目录内检索关键词，输出命中文件、行号与上下文。
纯离线，不联网，不修改任何文件。

用法：
    python3 scripts/lookup.py "换届 表决"
    python3 scripts/lookup.py "专项基金"
    python3 scripts/lookup.py "2/3 出席" -n 5
    python3 scripts/lookup.py "印章" --path 02-qa

参数：
    多个关键词用空格分隔，默认优先 AND（同一行同时包含全部关键词）；
    AND 无结果时自动改用 OR（任一命中），并给出提示。
    --any    直接按 OR 检索
    --all    列出所有命中行（默认每文件最多 6 行）
    -n N     每个文件最多显示 N 行（默认 6）
    --context N  命中行上下各显示 N 行
    --path   限定子目录，如 01-law、02-qa、03-templates
    --files  只列命中文件，不显示行
"""

import argparse
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")


def iter_files(root, subdir=None):
    target = os.path.join(root, subdir) if subdir else root
    if not os.path.isdir(target):
        return
    for dirpath, _dirnames, filenames in os.walk(target):
        for name in sorted(filenames):
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def collect(root, keywords, require_all, context, subdir=None):
    """返回 [(相对路径, [(行号, 命中词, 上下文块), ...]), ...]"""
    results = []
    for path in iter_files(root, subdir):
        hits = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(lines):
            low = line.lower()
            matched = [k for k in keywords if k.lower() in low]
            if (require_all and len(matched) == len(keywords)) or (not require_all and matched):
                block = []
                start = max(0, idx - context)
                end = min(len(lines), idx + context + 1)
                for j in range(start, end):
                    prefix = ">" if j == idx else " "
                    block.append("  {} {:4d} | {}".format(prefix, j + 1, lines[j].rstrip()))
                hits.append((idx + 1, matched, "\n".join(block)))
        if hits:
            results.append((os.path.relpath(path, root), hits))
    return results


def report(results, limit, files_only):
    for rel, hits in results:
        if files_only:
            print("{:<58} {} 处".format(rel, len(hits)))
            continue
        print("\n=== {} （命中 {} 处，显示 {} 处）".format(rel, len(hits), min(limit, len(hits))))
        for _lineno, _matched, block in hits[:limit]:
            print(block)
        if len(hits) > limit:
            print("  ... 另有 {} 处未显示，加 --all 查看".format(len(hits) - limit))


def main():
    ap = argparse.ArgumentParser(description="在 references/ 内检索关键词")
    ap.add_argument("query", nargs="+", help="关键词，空格分隔")
    ap.add_argument("--any", action="store_true", help="直接按任一关键词命中检索")
    ap.add_argument("--all", action="store_true", help="显示全部命中行")
    ap.add_argument("-n", type=int, default=6, help="每个文件最多显示行数")
    ap.add_argument("--context", type=int, default=0, help="命中行上下各显示 N 行")
    ap.add_argument("--path", default=None, help="限定子目录，如 01-law")
    ap.add_argument("--files", action="store_true", help="只列命中文件")
    args = ap.parse_args()

    keywords = []
    for chunk in args.query:
        keywords.extend([k for k in chunk.replace("，", " ").split() if k])
    keywords = list(dict.fromkeys(keywords))
    if not keywords:
        print("请提供至少一个关键词。")
        return 0

    if not os.path.isdir(BASE):
        print("未找到 references 目录：{}".format(os.path.normpath(BASE)))
        return 1

    limit = 10 ** 9 if args.all else max(1, args.n)

    if args.any:
        results = collect(BASE, keywords, False, args.context, args.path)
        mode = "任一命中"
    else:
        results = collect(BASE, keywords, True, args.context, args.path)
        mode = "全部命中"
        if not results and len(keywords) > 1:
            results = collect(BASE, keywords, False, args.context, args.path)
            mode = "自动改为任一命中"

    if not results:
        print("未命中：{}".format(" ".join(keywords)))
        print("提示：可换同义词，如“换届/改选”“公章/印章”“报酬/薪酬”“注销/终止”。")
        return 0

    if len(keywords) > 1:
        print("检索模式：{}".format(mode))
    report(results, limit, args.files)

    total_hits = sum(len(h) for _p, h in results)
    print("\n共 {} 个文件命中，{} 处。".format(len(results), total_hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
