#!/usr/bin/env python3
"""把 paperlist.tex 里裸写的 arXiv 号变成 \\cite 引用,并把 BibTeX 补进 refs.bib.

用法:
    python3 scripts/arxiv2bib.py            # 查询 + 改写 tex + 追加 bib
    python3 scripts/arxiv2bib.py --dry-run  # 只打印将要做的改动
    python3 scripts/arxiv2bib.py 2301.08243 2506.09985   # 只查询,打印 BibTeX

规则:
  * 正文里形如 2506.09985 / 2506.09985v2 的号会被识别(注释行、\\cite{...} 内部不动);
  * 用逗号/空格相连的一串号合并成一个 \\cite{a,b,c},渲染成 [1, 2, 3];
  * 已在 refs.bib 里(按 eprint 字段判断)的号不会重复查询,直接复用已有 key;
  * 查不到的号(拼错 / 尚未公开)原样保留并在终端报告。
"""
import argparse
import re
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEX = ROOT / "paperlist.tex"
BIB = ROOT / "refs.bib"
API = "https://export.arxiv.org/api/query?id_list={}&max_results={}"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

ID = r"\d{4}\.\d{4,5}(?:v\d+)?"
# 一串号:号之间只允许逗号与空白,如 "2506.09985,2512.10942, 2404.08471"
RUN = re.compile(rf"(?<![\d.\w/]){ID}(?:\s*,\s*{ID})*(?![\d\w])")
STOP = {"a", "an", "the", "on", "of", "in", "for", "to", "and", "with", "from", "is", "are"}


def strip_version(i):
    return re.sub(r"v\d+$", "", i)


def ascii_word(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fetch(ids):
    """批量查询 arXiv API,返回 {id: 元数据}."""
    out = {}
    for k in range(0, len(ids), 50):
        chunk = ids[k:k + 50]
        url = API.format(",".join(chunk), len(chunk))
        req = urllib.request.Request(url, headers={"User-Agent": "paperlist-arxiv2bib/1.0"})
        # 直连/代理下 export.arxiv.org 的 TLS 握手偶发被掐(SSL: UNEXPECTED_EOF),
        # 属瞬时网络抖动,自动重试几次再放弃
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = r.read()
                break
            except OSError as e:  # URLError/SSL/超时都是 OSError 的子类
                if attempt == 3:
                    raise
                wait = (attempt + 1) * 3
                print(f"  网络请求失败({type(e).__name__}),{wait} 秒后重试({attempt + 2}/4)...", file=sys.stderr)
                time.sleep(wait)
        root = ET.fromstring(body)
        for e in root.findall("a:entry", NS):
            title = e.findtext("a:title", "", NS)
            if not title or e.findtext("a:id", "", NS).endswith("/api/errors"):
                continue
            aid = strip_version(e.findtext("a:id", "", NS).rsplit("/abs/", 1)[-1])
            prim = e.find("arxiv:primary_category", NS)
            out[aid] = {
                "title": " ".join(title.split()),
                "authors": [a.findtext("a:name", "", NS).strip() for a in e.findall("a:author", NS)],
                "year": e.findtext("a:published", "", NS)[:4],
                "primary": prim.get("term") if prim is not None else "",
            }
        if k + 50 < len(ids):
            time.sleep(3)  # arXiv API 礼仪:请求间隔 3 秒
    return out


def make_key(meta, used):
    last = ascii_word(meta["authors"][0].split()[-1]) if meta["authors"] else "anon"
    word = next((ascii_word(w) for w in re.split(r"[\s:]+", meta["title"])
                 if ascii_word(w) and ascii_word(w) not in STOP), "paper")
    key = base = f"{last}{meta['year']}{word}"
    n = 1
    while key in used:
        n += 1
        key = f"{base}{chr(ord('a') + n - 1)}"
    used.add(key)
    return key


def bib_escape(s):
    return s.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")


def to_bibtex(key, aid, m):
    # 标题外加一层花括号保护大小写(LeWM、JEPA 等缩写不被小写化)
    return (
        f"@article{{{key},\n"
        f"  title         = {{{{{bib_escape(m['title'])}}}}},\n"
        f"  author        = {{{bib_escape(' and '.join(m['authors']))}}},\n"
        f"  journal       = {{arXiv preprint arXiv:{aid}}},\n"
        f"  year          = {{{m['year']}}},\n"
        f"  eprint        = {{{aid}}},\n"
        f"  archiveprefix = {{arXiv}},\n"
        f"  primaryclass  = {{{m['primary']}}},\n"
        f"  url           = {{https://arxiv.org/abs/{aid}}},\n"
        f"}}\n"
    )


def existing_bib():
    text = BIB.read_text(encoding="utf-8") if BIB.exists() else ""
    keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))
    by_id = {}
    for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", text, re.S):
        e = re.search(r"eprint\s*=\s*[{\"]([^}\"]+)", m.group(2))
        u = re.search(r"arxiv\.org/abs/(" + ID + ")", m.group(2))
        for hit in (e, u):
            if hit:
                by_id[strip_version(hit.group(1))] = m.group(1)
    return keys, by_id


def rewrite_line(line, id2key):
    """把一行中的号串替换成 \\cite{...};注释部分与 \\cite{} 内部不动."""
    code, comment = re.match(r"((?:[^%\\]|\\.)*)(.*)", line, re.S).groups()

    def sub(m):
        ids = [strip_version(i) for i in re.findall(ID, m.group(0))]
        if not all(i in id2key for i in ids):
            return m.group(0)
        return r"\cite{" + ",".join(id2key[i] for i in ids) + "}"

    return RUN.sub(sub, code) + comment


def ids_in_tex(text):
    found = []
    for line in text.splitlines():
        code = re.match(r"((?:[^%\\]|\\.)*)", line).group(1)
        for run in RUN.finditer(code):
            for i in re.findall(ID, run.group(0)):
                i = strip_version(i)
                if i not in found:
                    found.append(i)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="只查询这些号并打印 BibTeX,不改文件")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.ids:
        ids = [strip_version(i) for i in args.ids]
        meta = fetch(ids)
        used = set()
        for i in ids:
            if i in meta:
                print(to_bibtex(make_key(meta[i], used), i, meta[i]))
            else:
                print(f"% 未找到 {i}", file=sys.stderr)
        return

    tex = TEX.read_text(encoding="utf-8")
    ids = ids_in_tex(tex)
    if not ids:
        print("paperlist.tex 里没有裸 arXiv 号,无事可做.")
        return
    keys, id2key = existing_bib()
    todo = [i for i in ids if i not in id2key]
    print(f"发现 {len(ids)} 个号,{len(ids) - len(todo)} 个已在 refs.bib,需查询 {len(todo)} 个.")

    meta = fetch(todo) if todo else {}
    missing = [i for i in todo if i not in meta]
    new_entries = []
    for i in todo:
        if i in meta:
            k = make_key(meta[i], keys)
            id2key[i] = k
            new_entries.append(to_bibtex(k, i, meta[i]))
            print(f"  + {i} -> {k}: {meta[i]['title']}")
    for i in missing:
        print(f"  ! {i} 在 arXiv 查不到,保留原文", file=sys.stderr)

    new_tex = "\n".join(rewrite_line(l, id2key) for l in tex.split("\n"))
    if args.dry_run:
        print(f"[dry-run] 将追加 {len(new_entries)} 条 BibTeX,并改写 tex.")
        return
    if new_entries:
        with BIB.open("a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(new_entries))
    TEX.write_text(new_tex, encoding="utf-8")
    print(f"已追加 {len(new_entries)} 条到 refs.bib,已改写 paperlist.tex.")


if __name__ == "__main__":
    main()
