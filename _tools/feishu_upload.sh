#!/bin/bash
# 分块上传大 markdown 文件到飞书 wiki。
# 用法: feishu_upload.sh <title> <parent_wiki_node> <md_file>
# 策略: 首块 create，后续块 +update --mode append。每块 < 25000 字节。

set -euo pipefail
TITLE="$1"
PARENT="$2"
FILE="$3"
CHUNK_BYTES=25000

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

# 按空行分段，累计到 CHUNK_BYTES 切一刀
awk -v max="$CHUNK_BYTES" -v dir="$tmpdir" '
BEGIN { buf=""; n=0; size=0 }
{
  line = $0 "\n"
  if (size + length(line) > max && size > 0) {
    n++
    f = dir "/chunk_" sprintf("%03d", n) ".md"
    printf "%s", buf > f
    close(f)
    buf = ""
    size = 0
  }
  buf = buf line
  size += length(line)
}
END {
  if (size > 0) {
    n++
    f = dir "/chunk_" sprintf("%03d", n) ".md"
    printf "%s", buf > f
    close(f)
  }
  print n
}
' "$FILE" > "$tmpdir/count.txt"

n=$(cat "$tmpdir/count.txt")
echo ">> 切分为 $n 块"

# 第一块 create
first="$tmpdir/chunk_001.md"
resp=$(MSYS_NO_PATHCONV=1 lark-cli docs +create \
  --title "$TITLE" \
  --wiki-node "$PARENT" \
  --markdown "$(cat "$first")")
echo "$resp"
doc_url=$(echo "$resp" | py -c "import sys,json; d=json.load(sys.stdin); print(d['data']['doc_url'])")
echo ">> 已建: $doc_url"

# 后续块 append
for i in $(seq 2 "$n"); do
  f=$(printf "%s/chunk_%03d.md" "$tmpdir" "$i")
  echo ">> 追加第 $i/$n 块 ($(stat -c '%s' "$f") bytes)"
  MSYS_NO_PATHCONV=1 lark-cli docs +update \
    --doc "$doc_url" \
    --mode append \
    --markdown "$(cat "$f")" > /dev/null
done

echo ">> ✅ 完成: $doc_url"
