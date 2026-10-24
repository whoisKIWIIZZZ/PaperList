# PaperList 文献列表

把 BibTeX 文献库直接发布成静态网页,供浏览与引用。

线上页面:<https://whoiskiwiizzz.github.io/PaperList/>

## 用法

| 步骤 | 做法 |
|---|---|
| 新增 arXiv 文献 | 正文直接写号(如 `2506.09985,2512.10942`),运行 `python3 scripts/arxiv2bib.py`:自动查 arXiv、追加 BibTeX 到 `refs.bib`、把号改写成 `\cite{…}` |
| 新增其他文献 | 在 `refs.bib` 粘贴一条 BibTeX 条目,正文 `\cite{key}` |
| 分类 | 写条目的 `keywords` 字段,可多个;每个标签对应 `paperlist.tex` 里一个 `\printbibliography[keyword=…]` 小节 |
| 正文引用 | `\parencite{key}`,渲染成 `[3]` 这样的编号,并链接到文末条目 |
| 条目链接 | 有 `url` 字段的条目,文献表里 *arXiv preprint arXiv:xxxx* 可点击跳转 |
| 版式 | 仿 NeurIPS 模板(Times、标题双线、绿色引用);网页宽度改 `css/theme.css` 的 `--measure` |
| 发布 | `git push` 后 Actions 自动构建部署,无需本地编译 |
| 本地预览 | `./build.sh`,打开 `docs/paperlist.html`(pdf:`./build.sh pdf`) |

## 构建

TeX 用 XeLaTeX + ctex 编译中文,`make4ht -x` 生成 HTML,
数学公式保留 LaTeX 源码并以 MathJax 在浏览器内渲染。
`paperlist.mk4` 指定 biber 多轮编译流程;CI 端使用 `xu-cheng/texlive-action` 提供的完整 TeX Live。
