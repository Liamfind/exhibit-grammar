"""图表自检：python3 check_svg.py 图.svg|页面.html [显示宽度px，默认 360] [页面底色，默认 #FFFFFF]
查三件事：1) 渲染后字号 ≥11px  2) 文字对它背后底色的对比度 ≥4.5:1  3) 有没有两个肉眼分不清的彩色（ΔE<20，填充和描边都算）。
三种结果：不合格（退出码 1）、未检查（退出码 2）、通过（退出码 0）。查不了的一律报「未检查」，不算通过。
认得的写法：属性、style=、外层继承、<style> 里的 标签/.类/#id 规则、:root 里定义的 var()、透明度、网页里内嵌的 SVG。
查不了的：transform、currentColor、渐变、复合选择器、em 或 % 字号、<use>、外部样式表、脚本在浏览器里画出来的图。
没查的规则：大号字 3:1 的放宽、图形对底色 3:1（HR34）、文字超出色块。只用标准库。
交的是网页（.html）时还查第四件事（HR46）：每张数据图都写了悬停数据 data-tip，页面里有显示它的脚本；缺了判不合格。
framework 示意图在 <svg> 上写 data-kind="framework" 就不查悬停。"""
import sys, re, math
from html.parser import HTMLParser

VOID = {'meta', 'link', 'br', 'img', 'input', 'hr'}
UNPAINTED = {'defs', 'clippath', 'mask', 'marker', 'pattern', 'symbol', 'lineargradient', 'radialgradient'}
SHAPES = ('rect', 'circle', 'ellipse', 'polygon', 'path')
ARGS = {'m': 2, 'l': 2, 'h': 1, 'v': 1, 'c': 6, 's': 4, 'q': 4, 't': 2, 'a': 7, 'z': 0}
COMPOUND = r'([a-zA-Z][\w-]*|\*)?((?:[.#][\w-]+)*)'

class Unknown(Exception): pass

class Tree(HTMLParser):  # 网页和 SVG 都用它读；<script> 里拼出来的 SVG 它看不到
    def __init__(self):
        super().__init__(); self.cur = self.root = {'tag': '', 'at': {}, 'kids': [], 'up': None, 'txt': ''}
    def handle_starttag(self, tag, attrs, closed=False):
        n = {'tag': tag, 'at': {k: v or '' for k, v in attrs}, 'kids': [], 'up': self.cur, 'txt': ''}
        self.cur['kids'].append(n)
        if not closed and tag not in VOID: self.cur = n
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs, True)
    def handle_endtag(self, tag):
        n = self.cur
        while n['up'] and n['tag'] != tag: n = n['up']
        if n['up']: self.cur = n['up']
    def handle_data(self, data): self.cur['txt'] += data

def walk(n):
    yield n
    for k in n['kids']: yield from walk(k)

def decls(s): return {k.strip(): v.strip() for k, v in (d.split(':', 1) for d in s.split(';') if ':' in d)}

def compound(sel):  # 'text.a#b' → (标签, {类}, [id])；不是这种简单写法就返回 None
    m = re.fullmatch(COMPOUND, sel)
    if not m or not sel: return None
    parts = re.findall(r'([.#])([\w-]+)', m.group(2))
    return (m.group(1) or '*').lower(), {v for k, v in parts if k == '.'}, [v for k, v in parts if k == '#']

def matches(c, n):
    return c[0] in ('*', n['tag']) and c[1] <= set(n['at'].get('class', '').split()) and all(i == n['at'].get('id') for i in c[2])

class Styles:
    def __init__(self, root):
        css = re.sub(r'/\*.*?\*/', '', ''.join(n['txt'] for n in walk(root) if n['tag'] == 'style'), flags=re.S)
        css = re.sub(r'@[^{};]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}|@[^{};]*;', '', css)  # @media 里的（深色模式）不算
        self.simple, self.complex, self.var = [], [], {}
        for i, (sels, body) in enumerate(re.findall(r'([^{}]+)\{([^{}]*)\}', css)):
            d = decls(body)
            for sel in (s.strip() for s in sels.split(',')):
                if sel in (':root', 'html', 'body', 'svg', '*'): self.var.update({k: v for k, v in d.items() if k.startswith('--')})
                if re.search(r':(hover|focus|active|visited)|::', sel) or sel == ':root': continue
                c = compound(sel)
                if c: self.simple.append((c, d, i))
                else: self.complex.append((sel, d))
    def own(self, n, prop):  # 这个元素自己的值：style= 高于 CSS 规则，高于属性
        st = decls(n['at'].get('style', ''))
        if prop in st: return st[prop]
        for sel, d in self.complex:
            c = compound(re.sub(r':[\w-]+(\([^)]*\))?|\[[^\]]*\]', '', re.split(r'[\s>+~]+', sel)[-1]))
            if prop in d and c and matches(c, n): raise Unknown(f'样式写在复合选择器「{sel}」里')
        hits = [(len(c[2]), len(c[1]), c[0] != '*', i, d[prop]) for c, d, i in self.simple if prop in d and matches(c, n)]
        return max(hits)[-1] if hits else n['at'].get(prop)
    def get(self, n, prop, default=None):  # 自己没写就往外层找
        while n:
            v = self.own(n, prop)
            if v not in (None, 'inherit'): return self.sub(v)
            n = n['up']
        return default
    def font_px(self, n):  # 字号：认 font-size 和 font 简写，自己没写就往外层找
        while n:
            size, short = self.own(n, 'font-size'), self.own(n, 'font')
            if size and short: raise Unknown('同一个元素上既有 font 又有 font-size，算不准谁生效')
            m = re.search(r'(?<![\w.])([\d.]+)px', self.sub(short)) if short else re.fullmatch(r'([\d.]+)(px)?', self.sub(size)) if size else None
            if m: return float(m.group(1))
            if (short or size) and size != 'inherit': raise Unknown(f'字号「{short or size}」不是 px')
            n = n['up']
        raise Unknown('哪里都没写字号')
    def sub(self, v):
        m = re.fullmatch(r'var\(\s*(--[\w-]+)\s*(?:,\s*([^)]+))?\)', v.strip())
        if not m: return v.strip()
        if m.group(1) in self.var: return self.sub(self.var[m.group(1)])
        if m.group(2): return self.sub(m.group(2))
        raise Unknown(f'变量 {m.group(1)} 没有定义')
    def alpha(self, n, prop):  # 自己和外层的 opacity 连乘，再乘 fill-opacity
        a = frac(self.get(n, prop, '1'))
        while n:
            a *= frac(self.sub(self.own(n, 'opacity') or '1')); n = n['up']
        return a

def frac(v):
    m = re.fullmatch(r'([\d.]+)(%)?', v.strip())
    if not m: raise Unknown(f'透明度「{v}」算不了')
    return min(1.0, float(m.group(1)) / (100 if m.group(2) else 1))

def color(v):  # → (r, g, b, a)，没有颜色返回 None，算不了就抛 Unknown
    v = {'white': '#FFFFFF', 'black': '#000000'}.get(v.strip().lower(), v.strip())
    if v.lower() in ('none', 'transparent'): return None
    m = re.fullmatch(r'#([0-9a-fA-F]{3,8})', v)
    if m and len(m.group(1)) in (3, 4, 6, 8):
        h = m.group(1); h = ''.join(c * 2 for c in h) if len(h) < 6 else h
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (int(h[6:8] or 'ff', 16) / 255,)
    m = re.fullmatch(r'rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,/\s]+([\d.]+))?\s*\)', v)
    if m: return tuple(float(m.group(i)) / 255 for i in (1, 2, 3)) + (float(m.group(4) or 1),)
    raise Unknown(f'颜色「{v}」算不了')

def mix(fg, bg, a): return tuple(round((f * a + b * (1 - a)) * 255) / 255 for f, b in zip(fg, bg))  # 屏幕上是 8 位色
def hexs(c): return '#' + ''.join(f'{round(v * 255):02X}' for v in c[:3])
def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def rgb(c): return color(c)[:3] if isinstance(c, str) else c[:3]  # 十六进制字符串或 (r, g, b) 都收
hex2rgb = rgb
def lum(c): r, g, b = map(lin, rgb(c)); return 0.2126 * r + 0.7152 * g + 0.0722 * b
def contrast(a, b): x, y = sorted((lum(a), lum(b)), reverse=True); return (x + 0.05) / (y + 0.05)

def lab(c):
    r, g, b = map(lin, rgb(c))
    X = (r * .4124 + g * .3576 + b * .1805) / .95047; Y = r * .2126 + g * .7152 + b * .0722; Z = (r * .0193 + g * .1192 + b * .9505) / 1.08883
    t = lambda v: v ** (1 / 3) if v > .008856 else 7.787 * v + 16 / 116
    return 116 * t(Y) - 16, 500 * (t(X) - t(Y)), 200 * (t(Y) - t(Z))

def de(a, b): return math.dist(lab(a), lab(b))
def chroma(c): return math.hypot(*lab(c)[1:])

def num(n, key, whole=0.0):  # 取第一个数；百分比按画布宽或高折算
    m = re.match(r'\s*(-?[\d.]+)\s*(%)?', n['at'].get(key, ''))
    return float(m.group(1)) * (whole / 100 if m.group(2) else 1) if m else 0.0

def path_polys(d):  # 把路径当成折线多边形，曲线只取端点
    polys, cur, x, y, start = [], [], 0.0, 0.0, (0.0, 0.0)
    for cmd, args in re.findall(r'([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)', d):
        nums = [float(v) for v in re.findall(r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', args)]
        k, rel = ARGS[cmd.lower()], cmd.islower()
        if cmd in 'Zz': x, y = start; continue
        for i in range(0, len(nums) - k + 1, k):
            a = nums[i:i + k]
            if cmd in 'Hh': x = a[0] + (x if rel else 0)
            elif cmd in 'Vv': y = a[0] + (y if rel else 0)
            else: x, y = a[-2] + (x if rel else 0), a[-1] + (y if rel else 0)
            if cmd in 'Mm' and i == 0:
                if cur: polys.append(cur)
                cur, start = [], (x, y)
            cur.append((x, y))
    return polys + ([cur] if cur else [])

def pip(pts, x, y):
    c = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c

def inside(n, x, y, w, h):
    t = n['tag']
    if t == 'rect': return num(n, 'x', w) <= x <= num(n, 'x', w) + num(n, 'width', w) and num(n, 'y', h) <= y <= num(n, 'y', h) + num(n, 'height', h)
    if t == 'circle': return math.hypot(x - num(n, 'cx', w), y - num(n, 'cy', h)) <= num(n, 'r')
    if t == 'ellipse': return ((x - num(n, 'cx', w)) / (num(n, 'rx') or 1e-9)) ** 2 + ((y - num(n, 'cy', h)) / (num(n, 'ry') or 1e-9)) ** 2 <= 1
    if t == 'polygon':
        p = [float(v) for v in re.findall(r'-?[\d.]+', n['at'].get('points', ''))]; return pip(list(zip(p[::2], p[1::2])), x, y)
    return any(pip(p, x, y) for p in path_polys(n['at'].get('d', '')) if len(p) > 2)

def check_svg(st, svg, disp, base, bad, unknown):
    vb = [float(v) for v in re.findall(r'-?[\d.]+', svg['at'].get('viewbox', ''))]
    w, h = (vb[2], vb[3]) if len(vb) == 4 else (num(svg, 'width'), num(svg, 'height'))
    k = disp / w if len(vb) == 4 and w else 1.0  # 没有 viewBox 就不缩放
    els = [n for n in walk(svg) if not any(p['tag'] in UNPAINTED for p in iter_up(n))]
    if not any(n['tag'] == 'text' and ''.join(x['txt'] for x in walk(n)).strip() for n in els): return None  # 没有文字的当图标，不查
    moved =any('transform' in n['at'] or 'transform' in n['at'].get('style', '') or n['tag'] == 'use' for n in els)
    shapes, colors, checked = [n for n in els if n['tag'] in SHAPES], set(), 0
    for n in els:
        for prop in ('fill', 'stroke'):  # 颜色区分度：填充和描边都算
            try:
                c = color(st.get(n, prop) or 'none') if n['tag'] in SHAPES + ('line', 'polyline', 'text', 'tspan') else None
                if c: colors.add(hexs(c))
            except Unknown as e: unknown.append(f'未检查 <{n["tag"]}> 的{prop}：{e}')
        label = ''.join(x['txt'] for x in walk(n)).strip()
        if n['tag'] not in ('text', 'tspan') or not label: continue
        if n['tag'] == 'tspan' and not {'fill', 'font-size', 'class', 'style', 'x', 'y', 'opacity'} & set(n['at']): continue  # 跟着外层 text 查
        try:
            if moved: raise Unknown('这张图用了 transform 或 <use>，算不准文字压在哪个色块上')
            size = st.font_px(n); px = size * k
            x, y = (num(n if key in n['at'] else n['up'], key, whole) for key, whole in (('x', w), ('y', h)))
            fg = color(st.get(n, 'fill', '#000000'))
            if not fg: raise Unknown('文字没有填充色')
            bg = base
            for s in shapes:  # 按文档顺序从下往上叠
                if inside(s, x, y - size * .35, w, h):
                    c = color(st.get(s, 'fill', '#000000'))
                    if c: bg = mix(c, bg, c[3] * st.alpha(s, 'fill-opacity'))
            fg = mix(fg, bg, fg[3] * st.alpha(n, 'fill-opacity')); checked += 1
            if px < 11: bad.append(f'字号 {px:.1f}px <11：「{label}」')
            r = contrast(fg, bg)
            if r < 4.5: bad.append(f'对比度 {math.floor(r * 100) / 100:.2f}:1 <4.5：「{label}」 {hexs(fg)} 在 {hexs(bg)} 上')
        except Unknown as e: unknown.append(f'未检查「{label[:20]}」：{e}')
    col = sorted(c for c in colors if chroma(c) > 15)
    for i, a in enumerate(col):
        for b in col[i + 1:]:
            if de(a, b) < 20: bad.append(f'颜色 {a} 和 {b} 太接近（ΔE {de(a, b):.1f} <20），不能当两个系列')
    return checked

def iter_up(n):
    while n: yield n; n = n['up']

def hover_bad(root, svgs, counts):  # HR46：网页里的数据图必须带悬停数据；framework 示意图在 <svg> 上写 data-kind="framework" 豁免
    bad, tagged, missing = [], False, []
    charts = [svg for svg, c in zip(svgs, counts) if c is not None and svg['at'].get('data-kind') != 'framework']  # 图标、framework 不算
    for i, svg in enumerate(charts, 1):
        if any('data-tip' in n['at'] for n in walk(svg)): tagged = True; continue
        first = next(t for t in (''.join(x['txt'] for x in walk(n)).strip() for n in walk(svg) if n['tag'] == 'text') if t)
        missing.append(f'第 {i} 张「{first[:12]}」')
    if missing:
        more = f' 等 {len(missing)} 张' if len(missing) > 6 else ''
        bad.append(f'悬停（HR46）：{len(charts)} 张数据图里有 {len(missing)} 张没写悬停数据 data-tip：{"、".join(missing[:6])}{more}；是 framework 示意图就在 <svg> 上写 data-kind="framework"')
    if tagged and not any('data-tip' in n['txt'] for n in walk(root) if n['tag'] == 'script'):
        bad.append('悬停（HR46）：图上写了 data-tip，但页面里没有显示它的脚本，把 assets/chart-hover.js 放进页面末尾的 <script>')
    return bad

def main(path, disp=360.0, base='#FFFFFF'):
    tree = Tree(); tree.feed(open(path, encoding='utf-8').read())
    svgs = [n for n in walk(tree.root) if n['tag'] == 'svg' and not any(p['tag'] == 'svg' for p in iter_up(n['up']))]
    st, bad, unknown = Styles(tree.root), [], []
    counts = [check_svg(st, svg, disp, color(base), bad, unknown) for svg in svgs]
    charts, checked = [c for c in counts if c is not None], sum(c or 0 for c in counts)
    if not charts:
        drawn = any('<svg' in n['txt'] for n in walk(tree.root) if n['tag'] == 'script')
        unknown.append('未检查：' + ('图是脚本在浏览器里画出来的，这个脚本看不到，请在浏览器里核对或导出 SVG 再查' if drawn else '文件里没有带文字的 SVG 图'))
    html = path.lower().endswith(('.html', '.htm'))
    if html: bad += hover_bad(tree.root, svgs, counts)
    bad, unknown = list(dict.fromkeys(bad)), list(dict.fromkeys(unknown))
    head = '不合格' if bad else '未检查，不算通过' if unknown else '通过：字号、对比度、颜色区分度都合格' + ('，网页里的数据图都有悬停数据' if html else '')
    icons = f'，另有 {len(svgs) - len(charts)} 个没有文字的当图标跳过' if len(svgs) > len(charts) else ''
    print('\n'.join(bad + unknown + [f'{head}（{len(charts)} 张图{icons}，查了 {checked} 个文字标签，{len(bad)} 处不合格，{len(unknown)} 处未检查；显示宽度按 {disp:g}px、页面底色按 {base} 算）']))
    return 1 if bad else 2 if unknown else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 360.0, sys.argv[3] if len(sys.argv) > 3 else '#FFFFFF'))
