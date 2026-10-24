#!/usr/bin/env bash
# 构建:TeX -> HTML(中文用 XeLaTeX 引擎;服务器端由 GitHub Actions 自动构建)
# 用法: ./build.sh          生成 docs/paperlist.html
#       ./build.sh pdf      额外再出一版 PDF
set -euo pipefail
cd "$(dirname "$0")"

rm -rf docs
mkdir -p docs

# html5 = 语义化标签; mathjax = 公式在浏览器内渲染; fn-in = 脚注留在同一页(否则 tex4ht 把脚注拆到 paperlist2.html)
make4ht -x paperlist.tex "html5,mathjax,fn-in" -d docs 2>&1 | tail -3

if [ ! -s docs/paperlist.html ]; then
  echo "!! make4ht 没有产出 HTML,打印编译日志尾部:"
  tail -40 paperlist.lg paperlist.xlg 2>/dev/null
  exit 1
fi
echo "make4ht OK, $(sed -n 'p' docs/paperlist.html | wc -l) 行"

# tex4ht 在未使用 \maketitle 时 <title> 是空的,补上(perl 写法 macOS/CI 皆可用)
perl -pi -e 's|<title>[^<]*</title>|<title>Paper List 文献清单</title>|' docs/paperlist.html

# 叠加自定义主题(theme.css 在 tex4ht 默认样式之后加载,覆盖其版面规则)
cp css/theme.css docs/theme.css
perl -pi -e 's|</head>|<link href="theme.css" rel="stylesheet" type="text/css" /></head>|' docs/paperlist.html

# GitHub Pages 根地址需要 index.html
mv docs/paperlist.html docs/index.html
# 较新的 tex4ht 把引用写成 paperlist.html#X0-key,改名后会 404,统一改成页内锚点
perl -pi -e "s{href=(['\"])paperlist\.html#}{href=\$1#}g; s{href=(['\"])paperlist\.html\1}{href=\$1index.html\$1}g" docs/index.html
if grep -q "href=['\"]paperlist\.html" docs/index.html; then
  echo "!! index.html 里仍有指向 paperlist.html 的链接"; exit 1
fi

if [ "${1:-}" = "pdf" ]; then
  latexmk -xelatex -interaction=nonstopmode paperlist.tex
  cp paperlist.pdf docs/
fi

echo "output: docs/paperlist.html"
