#!/usr/bin/env python3
"""Сборка сайта «Вкусно дома» в один файл index.html."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / 'src'

prod_js = (SRC / 'products.js').read_text(encoding='utf-8')
raw = re.search(r'PRODUCTS_RAW = `(.*?)`', prod_js, re.S).group(1)
products = {}
for line in raw.strip().splitlines():
    name, kcal, p, f, c, piece, price, aliases, group = line.split('|')
    products[name] = dict(k=float(kcal), p=float(p), f=float(f), c=float(c),
                          w=float(piece) if piece else None, pr=float(price) if price else None,
                          a=[a.strip() for a in aliases.split(',') if a.strip()], g=group)
pantry = re.findall(r"'([^']+)'", re.search(r'PANTRY = \[(.*?)\]', prod_js, re.S).group(1))

CATS = {'soup': 'Первые блюда', 'main': 'Вторые блюда', 'salad': 'Салаты',
        'snack': 'Закуски', 'breakfast': 'Завтраки', 'dessert': 'Выпечка и десерты'}
METHODS = ['плита', 'духовка', 'микроволновка', 'аэрогриль', 'мангал', 'мультиварка', 'без нагрева']

recipes, errors = [], []
FILES = [f'{p}{c}.txt' for p in ('r-', 'r2-') for c in ('soup', 'main', 'salad', 'snack', 'breakfast', 'dessert')]
for fname in FILES:
    text = (SRC / fname).read_text(encoding='utf-8')
    cat = re.search(r'^#(\w+)', text, re.M).group(1)
    blocks = [b.strip() for b in re.split(r'\n\s*\n', text.split('\n', 1)[1]) if b.strip()]
    for b in blocks:
        lines = b.split('\n')
        if len(lines) != 4:
            errors.append(f'{fname}: блок из {len(lines)} строк: {lines[0]}'); continue
        head, desc, ings, steps = lines
        name, methods, minutes, serv = [x.strip() for x in head.split('|')]
        ms = [m.strip() for m in methods.split(',')]
        for m in ms:
            if m not in METHODS: errors.append(f'{name}: способ «{m}»')
        ing_list = []
        for part in ings.split(';'):
            part = part.strip()
            m = re.match(r'^(.*?)\s+([\d.]+)(шт)?$', part)
            if m:
                iname, amount, pcs = m.group(1), float(m.group(2)), bool(m.group(3))
                if iname not in products:
                    errors.append(f'{name}: нет продукта «{iname}»'); continue
                if pcs:
                    w = products[iname]['w']
                    if not w: errors.append(f'{name}: у «{iname}» нет веса штуки'); continue
                    ing_list.append([iname, round(amount * w, 1), amount])
                else:
                    ing_list.append([iname, amount, None])
            else:
                if part not in pantry:
                    errors.append(f'{name}: «{part}» без количества и не из списка специй')
                ing_list.append([part, None, None])
        # склеиваем повторы (например, сахар в тесто и в крем)
        merged = {}
        for n_, g_, pc in ing_list:
            if n_ in merged and g_:
                merged[n_][1] = (merged[n_][1] or 0) + g_
                merged[n_][2] = None
            else:
                merged[n_] = [n_, g_, pc]
        st = [s.strip() for s in steps.split(' > ') if s.strip()]
        recipes.append(dict(id=len(recipes) + 1, n=name, c=cat, m=ms, t=int(minutes), s=int(serv),
                            d=desc.strip(), i=list(merged.values()), st=st))

if errors:
    print('\n'.join(errors)); sys.exit(1)

# Проверка справочника: энергия по формуле 4·Б + 9·Ж + 4·У (МУ 4287-86, ТР ТС 022/2011)
# против табличной калорийности. Расхождение выше 12 % печатается как предупреждение.
ORG_ACIDS = {'лимон': 5.7}  # органические кислоты, г/100 г; коэффициент 3 ккал/г по ТР ТС 022/2011
warn = []
for n, x in products.items():
    x['oa'] = ORG_ACIDS.get(n, 0)
    atw = 4 * x['p'] + 9 * x['f'] + 4 * x['c'] + 3 * x['oa']
    if x['k'] and abs(x['k'] - atw) > 5 and abs(x['k'] - atw) / x['k'] > 0.12:
        warn.append(f'  {n}: в таблице {x["k"]:.0f} ккал, по БЖУ {atw:.0f} ккал')
    x['ka'] = round(atw, 1)
print('Продуктов:', len(products), '| расхождение калорийности > 12 %:', len(warn))
if warn: print('\n'.join(warn))

names = [r['n'] for r in recipes]
dups = {n for n in names if names.count(n) > 1}
if dups: print('Дубликаты:', dups); sys.exit(1)

print('Рецептов:', len(recipes), {CATS[c]: sum(r['c'] == c for r in recipes) for c in CATS})

data = dict(products=products, pantry=pantry, cats=CATS, methods=METHODS, recipes=recipes)
data_js = 'const DATA=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';'
(ROOT / 'data.js').write_text(data_js, encoding='utf-8')

if (SRC / 'app.html').exists():
    html = (SRC / 'app.html').read_text(encoding='utf-8')
    html = html.replace('/*__DATA__*/', data_js)
    html = html.replace('/*__GEO__*/', (SRC / 'geo.js').read_text(encoding='utf-8'))
    (ROOT / 'index.html').write_text(html, encoding='utf-8')
    print('index.html:', len(html.encode()) // 1024, 'КБ')
