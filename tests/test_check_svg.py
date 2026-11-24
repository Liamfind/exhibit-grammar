"""check_svg.py 的测试：python3 test_check_svg.py [要测的脚本，默认同目录的 check_svg.py]
每个用例是一张故意做对或做错的图，写明应该得到「通过」「不合格」还是「未检查」。只用标准库。"""
import math, subprocess, sys, tempfile
from pathlib import Path

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 220">%s</svg>'
PAGE = '<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>'
BAD = '8px 白字在浅灰上'

# (名字, 文件后缀, 内容, 应得结果, 输出里应出现的字, 额外参数)
CASES = [
    ('合规图：规范配色、标签直接标', '.svg', SVG % (
        '<rect x="0" y="0" width="360" height="220" fill="#FFFFFF"/>'
        '<rect x="80" y="20" width="200" height="24" fill="#003088"/><text x="90" y="37" font-size="12.5" fill="#FFFFFF">62%</text>'
        '<rect x="80" y="52" width="120" height="24" fill="#868E9A"/><text x="206" y="69" font-size="12.5" fill="#0F1419">37%</text>'
        '<text x="8" y="37" font-size="11.5" fill="#0F1419">自营</text><text x="8" y="69" font-size="11.5" fill="#5B6370">达人</text>'
        '<circle cx="300" cy="32" r="4" fill="#FF3100"/><text x="310" y="36" font-size="11.5" fill="#C42800">目标</text>'
        '<rect x="80" y="90" width="60" height="18" fill="#F2B705"/><text x="86" y="103" font-size="11.5" fill="#0F1419">提示</text>'
        '<text x="8" y="140" font-size="11.5" fill="#8A6100">黄色文字</text>'), '通过', '', []),
    ('字号和颜色写成属性', '.svg', SVG % (
        '<rect x="0" y="0" width="200" height="40" fill="#E8EBEF"/>'
        '<text x="10" y="25" font-size="8" fill="#FFFFFF">' + BAD + '</text>'), '不合格', '字号 8.0px', []),
    ('同样的错，写成 style=', '.svg', SVG % (
        '<rect x="0" y="0" width="200" height="40" style="fill:#E8EBEF"/>'
        '<text x="10" y="25" style="font-size:8px;fill:#FFFFFF">' + BAD + '</text>'), '不合格', '对比度 1.19', []),
    ('同样的错，写在外层分组上', '.svg', SVG % (
        '<rect x="0" y="0" width="200" height="40" fill="#E8EBEF"/>'
        '<g font-size="8" fill="#FFFFFF"><text x="10" y="25">' + BAD + '</text></g>'), '不合格', '字号 8.0px', []),
    ('同样的错，用 CSS 类和变量', '.svg', SVG % (
        '<style>:root{--paper:#FFFFFF;--g4:#E8EBEF}.t{font-size:8px;fill:var(--paper)}.blk{fill:var(--g4)}</style>'
        '<rect class="blk" x="0" y="0" width="200" height="40"/><text class="t" x="10" y="25">' + BAD + '</text>'), '不合格', '对比度 1.19', []),
    ('两条肉眼分不清的蓝线', '.svg', SVG % (
        '<polyline points="0,10 100,40" fill="none" stroke="#003088"/><polyline points="0,20 100,60" fill="none" stroke="#0A3A94"/>'
        '<text x="110" y="40" font-size="12" fill="#0F1419">A</text>'), '不合格', '太接近', []),
    ('深色字压在用路径画的深色块上', '.svg', SVG % (
        '<path d="M10 10 h120 v30 h-120 Z" fill="#003088"/><text x="20" y="30" font-size="12" fill="#0F1419">深字深底</text>'), '不合格', '对比度', []),
    ('白字压在用路径画的深色块上（应通过）', '.svg', SVG % (
        '<path d="M10 10 h120 v30 h-120 Z" fill="#003088"/><text x="20" y="30" font-size="12" fill="#FFFFFF">白字深底</text>'), '通过', '', []),
    ('次要文字加了 0.5 透明度', '.svg', SVG % (
        '<text x="10" y="25" font-size="12" fill="#5B6370" opacity="0.5">变淡的字</text>'), '不合格', '对比度', []),
    ('主色块加了 0.35 透明度，上面写白字', '.svg', SVG % (
        '<rect x="0" y="0" width="200" height="40" fill="#003088" fill-opacity="0.35"/>'
        '<text x="10" y="25" font-size="12" fill="#FFFFFF">白字</text>'), '不合格', '对比度', []),
    ('变量没有定义', '.svg', SVG % (
        '<text x="10" y="25" font-size="12" fill="var(--muted)">变量色</text>'), '未检查', '没有定义', []),
    ('用了 currentColor', '.svg', SVG % (
        '<text x="10" y="25" font-size="12" fill="currentColor">跟随色</text>'), '未检查', 'currentColor', []),
    ('用了 transform', '.svg', SVG % (
        '<rect x="0" y="0" width="200" height="40" fill="#E8EBEF"/>'
        '<g transform="translate(0,0)"><text x="10" y="25" font-size="12" fill="#FFFFFF">白字</text></g>'), '未检查', 'transform', []),
    ('哪里都没写字号', '.svg', SVG % ('<text x="10" y="25" fill="#0F1419">没字号</text>'), '未检查', '字号', []),
    ('字号写在复合选择器里', '.svg', SVG % (
        '<style>.chart text{font-size:8px}</style><g class="chart"><text x="10" y="25" font-size="12" fill="#0F1419">复合</text></g>'),
     '未检查', '复合选择器', []),
    ('字号写在 font 简写里（9px），页面正文 16px', '.html', PAGE % (
        'body{font-size:16px} .lab{font:9px/1.4 sans-serif}',
        '<svg viewBox="0 0 360 220"><text class="lab" x="10" y="25" fill="#0F1419">简写 9px</text></svg>'), '不合格', '字号 9.0px', []),
    ('font 简写和 font-size 属性同时出现', '.html', PAGE % (
        '.lab{font:9px sans-serif}',
        '<svg data-kind="framework" viewBox="0 0 360 220"><text class="lab" font-size="12" x="10" y="25" fill="#0F1419">两处字号</text></svg>'), '未检查', 'font', []),
    ('font 简写里不是 px', '.svg', SVG % (
        '<text x="10" y="25" style="font:0.6em sans-serif" fill="#0F1419">em 字号</text>'), '未检查', '不是 px', []),
    ('网页里内嵌的图，字号写在页面样式里', '.html', PAGE % (
        ':root{--ink:#0F1419} @media (prefers-color-scheme: dark){:root{--ink:#FFFFFF}} .lab{font-size:9px;fill:var(--ink)}',
        '<h1>标题</h1><svg viewBox="0 0 360 220"><text class="lab" x="10" y="25">9px 标签</text></svg>'), '不合格', '字号 9.0px', []),
    ('网页里的图是脚本在浏览器里画的', '.html', PAGE % (
        '', '<div id="c"></div><script>c.innerHTML=`<svg width="300"><text x="1" y="9" font-size="6">x</text></svg>`</script>'),
     '未检查', '脚本', []),
    ('网页里有图标，图标用 currentColor（应通过）', '.html', PAGE % (
        '', '<svg width="16" height="16"><path d="M2 2h12v12H2z" fill="none" stroke="currentColor"/></svg>'
        '<svg data-kind="framework" viewBox="0 0 360 220"><text x="10" y="25" font-size="12" fill="#0F1419">标签</text></svg>'), '通过', '图标', []),
    ('只有图标、没有带文字的图', '.html', PAGE % (
        '', '<svg width="16" height="16"><path d="M2 2h12v12H2z" fill="#003088"/></svg>'), '未检查', '没有带文字', []),
    ('网页里的数据图没写悬停数据', '.html', PAGE % (
        '', '<svg viewBox="0 0 360 220"><rect x="80" y="20" width="200" height="24" fill="#0030B8"/>'
        '<text x="8" y="37" font-size="11.5" fill="#0F1419">自营</text></svg>'), '不合格', '悬停（HR46）：1 张数据图里有 1 张没写悬停数据', []),
    ('网页里的图写了悬停数据，也有显示脚本（应通过）', '.html', PAGE % (
        '', '<svg viewBox="0 0 360 220"><rect x="80" y="20" width="360" height="24" fill="transparent" data-tip="自营｜2026 年｜62%｜后台数"/>'
        '<rect x="80" y="20" width="200" height="24" fill="#0030B8"/><text x="90" y="37" font-size="12.5" fill="#FFFFFF">62%</text>'
        '<text x="8" y="37" font-size="11.5" fill="#0F1419">自营</text></svg>'
        '<script>document.querySelectorAll("[data-tip]")</script>'), '通过', '网页里的数据图都有悬停数据', []),
    ('framework 示意图标了 data-kind，不要求悬停（应通过）', '.html', PAGE % (
        '', '<svg data-kind="framework" viewBox="0 0 360 220"><rect x="10" y="10" width="120" height="30" fill="#F3F4F6"/>'
        '<text x="20" y="30" font-size="12" fill="#0F1419">第一步</text></svg>'), '通过', '', []),
    ('网页里写了 data-tip 却没有显示脚本', '.html', PAGE % (
        '', '<svg viewBox="0 0 360 220"><rect x="80" y="20" width="200" height="24" fill="#0030B8" data-tip="自营｜2026 年｜62%｜后台数"/>'
        '<text x="8" y="37" font-size="11.5" fill="#0F1419">自营</text></svg>'), '不合格', '没有显示它的脚本', []),
    ('深色页面：白字直接写在页面上（给了底色参数，应通过）', '.svg', SVG % (
        '<text x="10" y="25" font-size="12" fill="#FFFFFF">深色页</text>'), '通过', '', ['360', '#0F1419']),
    ('显示宽度比画布窄，字被缩小', '.svg', SVG.replace('0 0 360 220', '0 0 720 440') % (
        '<text x="10" y="25" font-size="12" fill="#0F1419">缩小后 6px</text>'), '不合格', '字号 6.0px', []),
]


def run(script, case, folder):
    name, suffix, content, _, _, extra = case
    path = Path(folder) / ('case' + suffix)
    path.write_text(content, encoding='utf-8')
    r = subprocess.run([sys.executable, str(script), str(path), *extra], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if 'Traceback' in out:
        return '报错', out.splitlines()[-1][:60]
    return {0: '通过', 1: '不合格', 2: '未检查'}.get(r.returncode, '报错'), out


def known_answers(script):
    """规范正文里写明的对比度数字，脚本的算法必须算得出同样的值（只对新脚本有效）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location('checked', script); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    if not hasattr(m, 'mix'):
        return ['（旧脚本没有透明度混色，跳过）']
    c = lambda h: m.color(h)[:3]
    white, f = c('#FFFFFF'), lambda v: round(v, 2)  # 规范里的数是两位小数
    table = [('灰 1 对白', m.contrast(c('#6B7280'), white), 4.83), ('灰 2 对白', m.contrast(c('#868E9A'), white), 3.31),
             ('灰 2 加 0.9 透明度对白', m.contrast(m.mix(c('#868E9A'), white, .9), white), 2.87),
             ('提示黄字对白', m.contrast(c('#8A6100'), white), 5.54), ('亮黄对白', m.contrast(c('#F2B705'), white), 1.82),
             ('主文字在亮黄上', m.contrast(c('#0F1419'), c('#F2B705')), 10.18), ('灰 2 在深色底上', m.contrast(c('#868E9A'), c('#0F1419')), 5.60),
             ('主色 #0030B8 对白', m.contrast(c('#0030B8'), white), 9.92), ('色阶第 4 档上的白字', m.contrast(white, c('#476ACC')), 4.99)]
    ok = lambda v, want: want in (f(v), math.floor(v * 100) / 100)  # 四舍五入或截断（HR11 不往上取）都算对
    return [f"{'对' if ok(v, want) else '错'} | 规范写 {want} | 算出 {v:.4f} | {name}" for name, v, want in table]


def main(script):
    failed = 0
    with tempfile.TemporaryDirectory() as folder:
        for case in CASES:
            got, out = run(script, case, folder)
            ok = got == case[3] and case[4] in out and (got != '通过' or out.startswith('通过：字号、对比度、颜色区分度都合格'))
            failed += not ok
            print(f"{'对' if ok else '错'} | 应得 {case[3]} | 实得 {got} | {case[0]}")
            if not ok:
                print('     输出：' + out.replace('\n', ' / ')[:200])
    answers = known_answers(script)
    print('\n'.join(answers))
    failed += sum(a.startswith('错') for a in answers)
    print(f'{len(CASES)} 张测试图加 {len(answers)} 个已知数字，{failed} 项不对')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('check_svg.py')))
