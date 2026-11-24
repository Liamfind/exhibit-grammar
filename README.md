# exhibit-grammar

给 AI agent 用的图表规范技能。交付物（deck、报告、网页、看板、Excel 图）里只要有图表或示意图，agent 先读它，决定选什么图、怎么配色、字号多大、交付前怎么自检。

- `exhibit-grammar/SKILL.md`：规范正文，包括选图、配色、字号、46 条硬规则。
- `exhibit-grammar/scripts/check_svg.py`：自检脚本，只用 Python 标准库。它查字号、文字对比度、颜色是否分得清，还查网页图表有没有悬停数据。
- `exhibit-grammar/assets/chart-hover.js`：网页图表的悬停显示脚本，不需要图表库。

本仓库是正本。其他地方的副本（claude.ai 账号、各 agent 的技能目录）都从这里更新。

## 安装

技能本体是 `exhibit-grammar` 这个文件夹。

- **Claude（claude.ai、Claude 桌面、Claude Code）**：把 `exhibit-grammar` 文件夹打包成 `.skill` 文件（见下文「打包」），在 claude.ai 的技能设置里上传。已经装过的，在这个技能的「⋯」菜单里选「Upload new version」。
- **Skill Pilot**：

  ```bash
  python3 -m skill_pilot install https://github.com/Liamfind/exhibit-grammar/tree/main/exhibit-grammar --agent codex --yes
  ```

  `--agent` 可以写多个。以后 Skill Pilot 检查更新时会自动发现新版本。
- **其他 agent**：把 `exhibit-grammar` 文件夹复制到该 agent 的技能目录。

## 维护

1. 改 `exhibit-grammar/` 里的文件。改了版本号的，同步改 `SKILL.md` 第 0 节和下面的更新记录。
2. 跑测试，要显示「0 项不对」：

   ```bash
   python3 tests/test_check_svg.py exhibit-grammar/scripts/check_svg.py
   ```

3. 打包：

   ```bash
   zip -r exhibit-grammar.skill exhibit-grammar -x '*.DS_Store' '*__pycache__*'
   ```

4. 提交推送后，把 `.skill` 传到 claude.ai。用 Skill Pilot 装的电脑上，执行一次更新。

## 更新记录

- **v1.5（2026-11-23）**：
  - 配色改为单一主色 `#0030B8` 加灰，停用 `#003088` 和橙色。
  - 新增 HR46：网页图表第一稿就带悬停数据。
  - 自检脚本改成单独文件，并加了悬停检查。
  - 从 Knaflic《Storytelling with Data》补了「眼睛先落在哪」自检、`big_number` 图型，以及客户品牌色太浅时的做法。
  - 本仓库从这一版开始。
