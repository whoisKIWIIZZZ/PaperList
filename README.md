# PaperList 文献列表

把 BibTeX 文献库直接发布成静态网页,供浏览与引用。

线上页面:<https://whoiskiwiizzz.github.io/PaperList/>

## 用法

| 步骤 | 做法 |
|---|---|
| 新增文献 | 在 `refs.bib` 粘贴一条 BibTeX 条目 |
| 分类 | 写条目的 `keywords` 字段,可多个;每个标签对应 `paperlist.tex` 里一个 `\printbibliography[keyword=…]` 小节 |
| 正文引用 | `\parencite{key}`,生成 “Yao 等 (2023)” 并自动链接到下方条目 |
| 发布 | `git push` 后 Actions 自动构建部署,无需本地编译 |
| 本地预览 | `./build.sh`,打开 `docs/paperlist.html`(pdf:`./build.sh pdf`) |

## 构建

TeX 用 XeLaTeX + ctex 编译中文,`make4ht -x` 生成 HTML,
数学公式保留 LaTeX 源码并以 MathJax 在浏览器内渲染。
`paperlist.mk4` 指定 biber 多轮编译流程;CI 端使用 `xu-cheng/texlive-action` 提供的完整 TeX Live。
