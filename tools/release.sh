#!/bin/sh
# 发布一个新版本：检查 → 测试 → 提交推送 → 打包 →（可选）Skill Pilot 更新本机和团队商店。
# 用法：tools/release.sh 版本号 "更新记录一句" [--dry-run]
#   版本号要先写进 SKILL.md 第 0 节，例如 **v1.6（2026-12-01）**。
#   敏感词清单放在本机（默认 ~/.config/exhibit-grammar/blocklist.txt，每行一个词），不进仓库。
#   设了 SKILL_PILOT_DIR（Skill Pilot 项目文件夹）才会更新本机副本并重新上架团队商店。
#   --dry-run 只做检查和测试，不提交、不推送、不发布。
set -eu
cd "$(dirname "$0")/.."
fail() { echo "停下：$1" >&2; exit 1; }
[ $# -ge 2 ] || fail "用法：tools/release.sh 版本号 \"更新记录一句\" [--dry-run]"
V=$1 LOG=$2 DRY=${3:-}
S=exhibit-grammar/SKILL.md

# 1. 只允许改技能文件夹和 README
other=$(git status --porcelain | awk '{print $2}' | grep -v -E '^(exhibit-grammar/|README\.md$)' || true)
[ -z "$other" ] || fail "技能文件夹和 README 以外有改动：$other"
grep -q "\*\*$V（" "$S" || fail "SKILL.md 第 0 节还没写 $V"
grep -q "$V" README.md || fail "README 更新记录还没写 $V"

# 2. 去敏：本机敏感词清单 + 停用色只许出现在「已停用的颜色」那一行
BL=${EXHIBIT_BLOCKLIST:-$HOME/.config/exhibit-grammar/blocklist.txt}
[ -s "$BL" ] || fail "找不到敏感词清单 $BL"
hit=$(cat "$S" README.md | sed 's#Liamfind/exhibit-grammar##g' | grep -n -i -F -f "$BL" || true)
[ -z "$hit" ] || fail "有敏感词：$hit"
old=$(grep -n -E '#003088|#FF3100|#C42800' "$S" | grep -v '已停用的颜色' || true)
[ -z "$old" ] || fail "出现了已停用的颜色：$old"

# 3. 测试
python3 tests/test_check_svg.py exhibit-grammar/scripts/check_svg.py | tail -1 | grep -q '0 项不对' || fail "自检脚本测试没过"

# 4. 改动大小：新版本应以新增为主，删改超过 15 行就交给人看
del=$(git diff --numstat HEAD -- . | awk '{s+=$2} END {print s+0}')
[ "$del" -le 15 ] || fail "删改了 $del 行，超过 15 行"

[ "$DRY" = "--dry-run" ] && { echo "检查全部通过（--dry-run，没有提交）"; exit 0; }

# 5. 提交推送
git add exhibit-grammar README.md
git commit -q -m "exhibit-grammar $V：$LOG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin main
echo "已推送 $(git rev-parse --short HEAD)"

# 6. 打包（给 claude.ai 上传用）
rm -f exhibit-grammar.skill
zip -qr exhibit-grammar.skill exhibit-grammar -x '*.DS_Store' '*__pycache__*'
echo "已打包 $(pwd)/exhibit-grammar.skill"

# 7. Skill Pilot：更新本机副本，重新上架团队商店（推荐语每次都要带上，不带会被清空）
if [ -n "${SKILL_PILOT_DIR:-}" ]; then
  cd "$SKILL_PILOT_DIR"
  export PYTHONDONTWRITEBYTECODE=1
  python3 -m skill_pilot update exhibit-grammar --yes
  python3 -m skill_pilot team publish exhibit-grammar --yes --note "exhibit-grammar=图表规范：做 deck、报告、网页里的图表前先装。告诉 agent 选什么图、怎么配色、字号多大，网页图表第一稿就带悬停数据，交付前有自检脚本。"
fi
