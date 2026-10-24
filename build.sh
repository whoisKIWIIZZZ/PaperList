#!/usr/bin/env bash
# 构建:TeX -> HTML(中文用 XeLaTeX 引擎;服务器端由 GitHub Actions 自动构建)
# 用法: ./build.sh          生成 docs/paperlist.html
#       ./build.sh pdf      额外再出一版 PDF
set -euo pipefail
cd "$(dirname "$0")"

rm -rf docs
mkdir -p docs

# html5 = 语义化标签; mathjax = 公式保留 LaTeX 源码、浏览器内渲染(对数学标题最稳)
make4ht -x paperlist.tex "html5,mathjax" -d docs 2>&1 | tail -3

# tex4ht 在未使用 \maketitle 时 <title> 是空的,补上(perl 写法 macOS/CI 皆可用)
perl -pi -e 's|<title>[^<]*</title>|<title>Paper List 文献清单</title>|' docs/paperlist.html

# 叠加自定义主题(theme.css 在 tex4ht 默认样式之后加载,覆盖其版面规则)
cp css/theme.css docs/theme.css
perl -pi -e 's|</head>|<link href="theme.css" rel="stylesheet" type="text/css" /></head>|' docs/paperlist.html

# GitHub Pages 根地址需要 index.html
mv docs/paperlist.html docs/index.html

if [ "${1:-}" = "pdf" ]; then
  latexmk -xelatex -interaction=nonstopmode paperlist.tex
  cp paperlist.pdf docs/
fi

echo "output: docs/paperlist.html"
