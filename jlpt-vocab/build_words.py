"""JLPT N2/N1 단어 목록으로 docs/jlpt-vocab/words.json을 만든다.

1) 원본 CSV(elzup/jlpt-word-list, MIT, 원 출처 tanos.co.uk)를 받아 words.base.json으로 정리
2) ko/*.json(키 → 한국어 뜻)을 합쳐 words.json 작성. 뜻이 하나라도 빠지면 쓰지 않는다.

    python jlpt-vocab/build_words.py            원본을 다시 받는다
    python jlpt-vocab/build_words.py --offline  source/*.csv 재사용
"""
import csv
import html
import io
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
SRC = 'https://raw.githubusercontent.com/elzup/jlpt-word-list/master/src/n{}.csv'
SOURCE = HERE / 'source'
BASE = HERE / 'words.base.json'
KO_DIR = HERE / 'ko'
OUT = HERE.parent / 'docs' / 'jlpt-vocab' / 'words.json'


def read_csv(level, offline):
    path = SOURCE / f'n{level}.csv'
    if not offline:
        SOURCE.mkdir(exist_ok=True)
        with urllib.request.urlopen(SRC.format(level)) as res:
            path.write_bytes(res.read())
    return path.read_text(encoding='utf-8')


def base_words(offline):
    words, seen = [], set()
    for lv in (2, 1):  # N2 먼저: 학습 순서이자 중복 시 N2 우선
        for row in csv.DictReader(io.StringIO(read_csv(lv, offline))):
            k, r = row['expression'].strip(), row['reading'].strip()
            if f'{k}|{r}' in seen:
                continue
            seen.add(f'{k}|{r}')
            words.append({'k': k, 'r': r, 'en': ' '.join(html.unescape(row['meaning']).replace(' ', ' ').split()), 'lv': lv})
    return words


KANJI = re.compile(r'[一-鿿]')


def kanji_order(words):
    """같은 한자 단어끼리 붙여 놓는다.

    단어마다 다른 단어와 공유하는 한자 중 가장 드문 것을 기준으로 묶는다(出·気처럼
    흔한 한자로 묶으면 묶음이 수십 개가 된다). 묶음은 N2 단어가 있는 것부터,
    그다음 원래 순서대로. 묶음 안은 N2 → N1. 공유 한자가 없는 단어는 혼자 한 묶음.
    """
    chars = [list(dict.fromkeys(KANJI.findall(w['k']))) for w in words]
    freq = Counter(c for cs in chars for c in cs)
    groups = {}
    for i, cs in enumerate(chars):
        shared = [c for c in cs if freq[c] > 1]
        anchor = min(shared, key=lambda c: (freq[c], cs.index(c))) if shared else i
        groups.setdefault(anchor, []).append(i)
    ordered = sorted(groups.values(), key=lambda g: (min(words[i]['lv'] for i in g) != 2, g[0]))
    return [words[i] for g in ordered for i in sorted(g, key=lambda i: (words[i]['lv'] != 2, i))]


def main():
    words = base_words('--offline' in sys.argv)
    assert len(words) > 4000, f'단어 수가 이상하다: {len(words)}'
    BASE.write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding='utf-8')

    ko = {}
    for f in sorted(KO_DIR.glob('*.json')):
        ko.update(json.loads(f.read_text(encoding='utf-8')))
    keys = {f"{w['k']}|{w['r']}" for w in words}
    missing = [w for w in words if not ko.get(f"{w['k']}|{w['r']}", '').strip()]
    extra = [k for k in ko if k not in keys]
    print(f'단어 {len(words)}개, 한국어 뜻 없음 {len(missing)}개, 목록에 없는 뜻 {len(extra)}개')
    if extra:
        print('목록에 없는 키 예:', ', '.join(extra[:5]))
    if missing:
        print('words.json을 쓰지 않았다. 뜻 없는 단어 예:', ', '.join(w['k'] for w in missing[:5]))
        return 1

    out = [{'k': w['k'], 'r': w['r'], 'ko': ko[f"{w['k']}|{w['r']}"].strip(), 'en': w['en'], 'lv': w['lv']}
           for w in kanji_order(words)]
    assert sorted(f"{w['k']}|{w['r']}" for w in out) == sorted(keys), '정렬 중 단어가 빠지거나 겹쳤다'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('썼다:', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
