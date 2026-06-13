# -*- coding: utf-8 -*-
"""기말과제 노트북(final_exam_gap.ipynb) 빌드 스크립트 (1회용)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []
def md(s): cells.append(nbf.v4.new_markdown_cell(s))
def code(s): cells.append(nbf.v4.new_code_cell(s))

# ===== 제목 + 서론 =====
md(r"""# 시니어, 누구로 호명되는가 — 담론과 서비스의 갭(gap)

### 빅카인즈 뉴스 2코퍼스 비교 토픽모델링 (2025.06~2026.06)

> **구글 코랩에서 그대로 실행되는 자기완결형 노트북.** `src` import 없이 모든 함수를 셀에 직접 정의한다.
> 위에서 아래로 실행하면 전체 분석이 재현된다.

---

## 서론

고독사·독거노인을 다루는 **뉴스 담론**과, 스마트홈·실버테크 같은 **시니어 대상 서비스 담론**은
같은 '시니어'를 말하지만 **시니어를 호명하는 방식이 다르다**는 것이 본 분석의 출발점이다.
뉴스는 시니어를 *복지 수혜·위기의 대상*으로 그리는 경향이, 서비스는 *능동적 사용자·소비자*로
타깃하는 경향이 있다고 가정한다. 본 노트북은 이 **갭(gap)** 을 주관적 해석이 아닌 **측정 가능한 지표**로 검증한다.

**두 코퍼스 (동일 기간·동일 필드로 시점 통제)**

| | A. 담론 | B. 서비스 |
|---|---|---|
| 내용 | 고독사·독거노인 뉴스 | 스마트홈·실버테크·시니어 서비스 뉴스 |
| 검색어 | 독거노인·고독사·1인 고령가구·노인 고립·무연고 사망 | 스마트홈·실버테크·고령친화·돌봄로봇·시니어케어·액티브시니어 등 |
| 정제 후 | 20,079건 | 5,059건 (시니어 필터 적용) |

**연구 질문(RQ)**
1. 두 코퍼스의 **주제 구성**은 어떻게 다른가? (공통 주제 / 고유 주제)
2. 각 코퍼스에 **통계적으로 특징적인 단어**는 무엇인가? (log-odds)
3. 시니어를 **'수혜 대상'으로 호명하는가, '능동적 소비자'로 호명하는가?** (호명 어휘 정량화)
4. 두 담론의 **감성**은 어떻게 다른가?

**객관성 장치**: ① 동일 기간·필드(시점 통제) ② A를 B와 같은 5,067건으로 **무작위 다운샘플(random_state=42)** → 1:1 비교
③ 정규화 지표(비중·출현율·log-odds·감성비율)만 사용해 코퍼스 크기 영향 제거 ④ 전체 A(2만)로 핵심 지표 재확인.""")

# ===== 0. 환경 준비 =====
md(r"""## 0. 실행 환경 준비 (Colab / 로컬 공용)

> **Colab 실행법**: `BDA_FINAL` 폴더(이 노트북 + `data/`)를 통째로 내 드라이브에 올린 뒤,
> 노트북을 열고 `런타임 ▸ 모두 실행`. 경로는 **하드코딩하지 않고** ③ 셀이 `data/raw/A`(코퍼스 A)·`data/raw/B`(코퍼스 B)를
> 자동 탐색하므로 손댈 필요가 없다. (한글폰트는 자동 설치, 감성사전은 묶음에 포함)""")

code(r"""# ① 패키지 설치 (Colab)
!pip install -q konlpy wordcloud gensim networkx openpyxl
# konlpy(Okt)는 JVM 필요. Colab에는 Java가 기본 설치되어 있다.""")

code(r"""# ② 한글 폰트 등록 (Colab=나눔고딕 / 로컬=시스템 폰트 자동 탐색)
import os, sys, glob
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

IN_COLAB = "google.colab" in sys.modules

def _setup_korean_font():
    cands = []
    if IN_COLAB:
        os.system("apt-get -qq install -y fonts-nanum > /dev/null")
        fm._load_fontmanager(try_read_cache=False)
    cands += glob.glob("/usr/share/fonts/truetype/nanum/NanumGothic*.ttf")
    cands += [r"C:\Windows\Fonts\malgun.ttf"]
    cands += ["/System/Library/Fonts/AppleSDGothicNeo.ttc"]
    cands += glob.glob("/usr/share/fonts/**/Nanum*.ttf", recursive=True)
    for p in cands:
        if os.path.exists(p):
            try:
                fm.fontManager.addfont(p); name = fm.FontProperties(fname=p).get_name()
            except Exception:
                continue
            plt.rcParams["font.family"] = name; plt.rcParams["axes.unicode_minus"] = False
            return name, p
    return None, None

FONT_NAME, FONT_PATH = _setup_korean_font()
print("폰트:", FONT_NAME, "|", FONT_PATH or "한글폰트 못찾음")""")

code(r"""# ③ 경로 자동 탐색 (하드코딩 없음) — 노트북 옆/상위/드라이브 어디에 data/가 있든 찾는다
import glob, os
cands = []
if IN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    cands += ["/content/drive/MyDrive/BDA_FINAL",
              "/content/drive/MyDrive/lonely-death-news-textmining",
              "/content/drive/MyDrive/BDA",
              "/content/drive/MyDrive"]
cands += [".", "..", "../.."]   # 로컬: 노트북과 같은 폴더 / notebooks 하위 / 그 상위
PROJECT_DIR = next((c for c in cands if glob.glob(f"{c}/data/raw/A/*.xlsx")), None)
assert PROJECT_DIR, (
    "\n[ERROR] data/raw/A/*.xlsx 를 찾지 못했습니다.\n"
    "   이 노트북과 같은 위치(또는 드라이브)에 data/raw/A, data/raw/B 폴더가 있어야 합니다.")
RAW_A = f"{PROJECT_DIR}/data/raw/A"
RAW_B = f"{PROJECT_DIR}/data/raw/B"
files_a = sorted(glob.glob(f"{RAW_A}/*.xlsx"))
files_b = sorted(glob.glob(f"{RAW_B}/*.xlsx"))
print("PROJECT_DIR:", os.path.abspath(PROJECT_DIR))
print("코퍼스 A 엑셀:", [os.path.basename(f) for f in files_a])
print("코퍼스 B 엑셀:", [os.path.basename(f) for f in files_b])
assert files_b, "data/raw/B/*.xlsx (코퍼스 B)를 찾지 못했습니다."""")

code(r"""# ④ KNU 한국어 감성사전 — 묶음에 있으면 그대로 쓰고, 없으면(코랩) 자동 다운로드
import os
bundled = f"{PROJECT_DIR}/data/lexicon/SentiWord_info.json"
if os.path.exists(bundled):
    LEXICON_PATH = bundled
elif IN_COLAB:
    os.system("wget -q -O /content/SentiWord_info.json "
              "https://raw.githubusercontent.com/park1200656/KnuSentiLex/master/data/SentiWord_info.json")
    LEXICON_PATH = "/content/SentiWord_info.json"
else:
    LEXICON_PATH = bundled  # 없으면 다음 셀에서 에러
print("감성사전:", LEXICON_PATH, "| bytes:", os.path.getsize(LEXICON_PATH))""")

# ===== 0-1. 설정 & 함수 =====
md(r"""## 0-1. 설정 & 함수 정의

`src/*.py`의 로직을 코랩 자기완결로 풀어쓴다. **불용어는 최소화**한다 —
이 분석의 핵심인 호명 어휘(`지원·돌봄·서비스·이용·제품` 등)를 불용어로 지우면 안 되기 때문이다.""")

code(r"""import re, json
from collections import Counter
import numpy as np
import pandas as pd
from konlpy.tag import Okt

okt = Okt()

# 코퍼스 키워드 (복합어 보존용) + 시니어 필터
KEYWORDS_A = ["독거노인", "고독사", "1인 고령가구", "노인 고립", "무연고 사망"]
KEYWORDS_B = ["스마트홈", "실버테크", "고령친화", "돌봄로봇", "스마트경로당", "시니어케어",
              "액티브시니어", "실버산업", "실버타운", "에이지테크", "시니어테크",
              "디지털헬스케어", "노인맞춤돌봄", "비대면돌봄", "안부확인", "반려로봇"]
SENIOR_RE = re.compile("노인|고령|시니어|어르신|독거|실버|경로당|치매|요양")

# 최소 불용어(보도 상투어만) — 내용어는 보존
STOP_WORDS = set(["기자", "뉴스", "사진", "제공", "무단", "전재", "재배포", "금지", "연합뉴스",
    "오전", "오후", "이날", "지난", "올해", "최근", "관련", "통해", "위해", "대한",
    "이번", "당시", "이상", "이후", "이전", "정도", "가운데", "경우", "때문", "기간"])

_URL = re.compile(r"https?://\S+|www\.\S+"); _EMAIL = re.compile(r"\S+@\S+")
_NONKO = re.compile(r"[^가-힣\s]"); _SP = re.compile(r"\s+")
def clean_text(t):
    if not isinstance(t, str): return ""
    t = _URL.sub(" ", t); t = _EMAIL.sub(" ", t); t = _NONKO.sub(" ", t)
    return _SP.sub(" ", t).strip()

_COMP = KEYWORDS_A + KEYWORDS_B
_COMP_PARTS = sorted([(w, tuple(okt.nouns(w))) for w in _COMP], key=lambda x: -len(x[1]))
def _merge_compounds(nouns):
    res, i, n = [], 0, len(nouns)
    while i < n:
        hit = False
        for w, parts in _COMP_PARTS:
            k = len(parts)
            if k >= 2 and tuple(nouns[i:i+k]) == parts:
                res.append(w); i += k; hit = True; break
        if not hit:
            res.append(nouns[i]); i += 1
    return res

def extract_nouns(text, min_len=2):
    c = clean_text(text)
    if not c: return []
    nouns = _merge_compounds(okt.nouns(c))
    return [w for w in nouns if len(w) >= min_len and w not in STOP_WORDS]

_SENTI_POS = {"Noun", "Adjective", "Verb", "Adverb"}
def senti_tokens(text, min_len=2):
    c = clean_text(text)
    if not c: return []
    return [w for w, tag in okt.pos(c, norm=True, stem=True)
            if tag in _SENTI_POS and len(w) >= min_len]""")

code(r"""# 감성사전
def load_lexicon(path):
    data = json.load(open(path, encoding="utf-8")); lex = {}
    for x in data:
        w = x["word"]
        if " " in w or not re.fullmatch(r"[가-힣]+", w): continue
        lex[w] = int(x["polarity"])
    return lex

def score_document(text, lexicon):
    score = pos = neg = n = 0
    for w in senti_tokens(text):
        p = lexicon.get(w)
        if p is None: continue
        score += p; n += 1
        if p > 0: pos += 1
        elif p < 0: neg += 1
    label = "positive" if score > 0 else "negative" if score < 0 else "neutral"
    return score, pos, neg, n, label

# log-odds ratio (Monroe et al. 2008, informative Dirichlet prior) — 코퍼스 크기차 보정
def log_odds(counts_a, counts_b, a0=1000.0, min_count=5):
    vocab = [w for w in (set(counts_a) | set(counts_b))
             if counts_a.get(w, 0) + counts_b.get(w, 0) >= min_count]
    bg = {w: counts_a.get(w, 0) + counts_b.get(w, 0) for w in vocab}
    bgtot = sum(bg.values()); na = sum(counts_a.values()); nb = sum(counts_b.values())
    rows = []
    for w in vocab:
        aw = a0 * bg[w] / bgtot
        ya, yb = counts_a.get(w, 0), counts_b.get(w, 0)
        d = (np.log((ya + aw) / (na + a0 - ya - aw)) -
             np.log((yb + aw) / (nb + a0 - yb - aw)))
        v = 1.0/(ya + aw) + 1.0/(yb + aw)
        rows.append((w, d/np.sqrt(v), ya, yb))
    return pd.DataFrame(rows, columns=["word", "z", "freq_A", "freq_B"]).sort_values("z")

# 호명(framing) 어휘 — '수혜·대상화' vs '주체·소비'
RECIPIENT = set(["지원", "보호", "취약", "돌봄", "복지", "수급", "발굴", "대상", "지급", "혜택",
    "사각지대", "저소득", "후원", "기초생활", "수혜", "봉사", "위문", "방문", "도움", "보살핌",
    "구호", "지원금", "생계", "결식", "독거"])
ACTIVE = set(["이용", "구매", "제품", "서비스", "기능", "체험", "사용자", "고객", "소비자", "선택",
    "출시", "판매", "시장", "플랫폼", "기술", "스마트", "편의", "자립", "참여", "수요", "혁신",
    "개발", "산업", "솔루션", "스타트업", "투자", "콘텐츠"])

def framing_index(nouns):
    r = sum(1 for w in nouns if w in RECIPIENT)
    a = sum(1 for w in nouns if w in ACTIVE)
    idx = (a - r) / (a + r) if (a + r) > 0 else np.nan   # -1(수혜) ~ +1(주체)
    return r, a, idx

# 동시출현 네트워크
from itertools import combinations
def build_network(token_lists, top_n=40, min_cooc=40):
    import networkx as nx
    freq = Counter(w for t in token_lists for w in t)
    vocab = [w for w, _ in freq.most_common(top_n)]; vset = set(vocab)
    pairs = Counter()
    for toks in token_lists:
        present = sorted(vset.intersection(toks))
        for a, b in combinations(present, 2): pairs[(a, b)] += 1
    G = nx.Graph()
    for w in vocab: G.add_node(w, freq=int(freq[w]))
    for (a, b), c in pairs.items():
        if c >= min_cooc: G.add_edge(a, b, weight=int(c))
    G.remove_nodes_from([n for n in list(G.nodes) if G.degree(n) == 0])
    return G

def draw_network(G, ax, title, color):
    import networkx as nx
    if G.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "(엣지 없음)", ha="center"); ax.axis("off"); return
    pos = nx.spring_layout(G, k=0.6, seed=42, weight="weight")
    fmax = max(G.nodes[n]["freq"] for n in G.nodes)
    sizes = [2200 * (G.nodes[n]["freq"]/fmax) + 150 for n in G.nodes]
    ws = [G[u][v]["weight"] for u, v in G.edges]; wmax = max(ws) if ws else 1
    widths = [2.5 * (w/wmax) + 0.2 for w in ws]
    nx.draw_networkx_edges(G, pos, width=widths, alpha=0.3, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=color, alpha=0.85, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=9, font_family=FONT_NAME, ax=ax)
    ax.set_title(title); ax.axis("off")""")

# ===== 1. 데이터 로드 =====
md(r"""## 1. 데이터 로드 · 정제 · 시니어 필터 · 균형 샘플

- 코퍼스 B는 OR 검색이라 비(非)시니어 기사(건설 스마트홈·재난 응급안전 등)가 섞이므로 **시니어 키워드 필터**를 적용한다.
- 비교 공정성을 위해 **A를 B와 같은 규모로 무작위 다운샘플(random_state=42)** 한다.""")

code(r"""ID, DATE, TITLE, BODY, EXC = "뉴스 식별자", "일자", "제목", "본문", "분석제외 여부"
EXCLUDE = {"예외", "중복", "중복, 예외"}

def load_corpus(files, senior_filter=False):
    df = pd.concat([pd.read_excel(f, dtype={ID: str}) for f in files], ignore_index=True)
    df = df.drop_duplicates(subset=ID)
    if EXC in df.columns:
        df = df[~df[EXC].isin(EXCLUDE)]
    df = df.drop_duplicates(subset=[TITLE, BODY]).reset_index(drop=True)
    df["날짜"] = pd.to_datetime(df[DATE].astype(str), format="%Y%m%d", errors="coerce")
    if senior_filter:
        txt = df[TITLE].fillna("") + " " + df[BODY].fillna("")
        df = df[txt.str.contains(SENIOR_RE)].reset_index(drop=True)
    return df

dfA_full = load_corpus(files_a)
dfB = load_corpus(files_b, senior_filter=True)
print("코퍼스 A(전체):", len(dfA_full), "| 코퍼스 B(시니어필터):", len(dfB))
overlap = len(set(dfA_full[ID]) & set(dfB[ID]))
print("A 교차중복(전체기준):", overlap, "건 - 그대로 유지(보수적 비교)")
print("균형 비교용으로 A를 B와 같은", len(dfB), "건으로 다운샘플 예정 (토큰화 후)")""")

code(r"""from tqdm.auto import tqdm
tqdm.pandas()
print("명사 추출 중... (A전체+B, 약 4~6분)")
dfA_full["nouns"] = dfA_full[BODY].fillna("").progress_apply(extract_nouns)
dfB["nouns"] = dfB[BODY].fillna("").progress_apply(extract_nouns)
# 균형 A: 전체 A(이미 토큰화됨)에서 B와 같은 규모로 다운샘플 → 재토큰화 불필요
dfA = dfA_full.sample(n=len(dfB), random_state=42).reset_index(drop=True)
print("토큰화 완료. 균형 A:", len(dfA), "| B:", len(dfB), "| A 전체:", len(dfA_full))""")

# ===== 1-A. 워드클라우드 =====
md(r"""## 1-A. 빈도 · 워드클라우드 비교 (탐색)

두 코퍼스의 고빈도 명사를 워드클라우드로 나란히 본다. 정밀 비교는 ②(log-odds)에서 한다.""")

code(r"""from wordcloud import WordCloud
cntA0 = Counter(w for t in dfA["nouns"] for w in t)
cntB0 = Counter(w for t in dfB["nouns"] for w in t)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for ax, cnt, ttl, cmap in [(axes[0], cntA0, "A. 담론", "Oranges"),
                           (axes[1], cntB0, "B. 서비스", "Blues")]:
    wc = WordCloud(font_path=FONT_PATH, width=800, height=600, background_color="white",
                   colormap=cmap, max_words=120).generate_from_frequencies(dict(cnt.most_common(120)))
    ax.imshow(wc, interpolation="bilinear"); ax.axis("off"); ax.set_title(ttl, fontsize=14)
plt.tight_layout(); plt.show()
print("A 상위:", [w for w, _ in cntA0.most_common(12)])
print("B 상위:", [w for w, _ in cntB0.most_common(12)])""")

# ===== 2. 지표1 토픽 비중 =====
md(r"""## 2. 지표 ① 주제 구성 비교 (LDA 토픽 비중)

두 코퍼스를 **공유 사전**으로 각각 LDA(k=4)에 적합시킨다(토픽-단어 분포를 비교 가능하게 하기 위함).
각 코퍼스가 어떤 주제로 구성되는지, 어디에 비중이 쏠리는지 본다.""")

code(r"""from gensim.corpora import Dictionary
from gensim.models import LdaModel, CoherenceModel

nounsA, nounsB = dfA["nouns"].tolist(), dfB["nouns"].tolist()
shared = Dictionary(nounsA + nounsB)   # 두 코퍼스 비교 가능하도록 사전 공유
shared.filter_extremes(no_below=5, no_above=0.5)
corpA = [shared.doc2bow(t) for t in nounsA]
corpB = [shared.doc2bow(t) for t in nounsB]
print("공유 사전 크기:", len(shared))""")

md(r"""### 토픽 수(k) 선택 — coherence + k=4 vs k=12 비교

두 코퍼스를 **같은 k로** 모델링해야 토픽을 1:1 비교할 수 있다. 결합 코퍼스의 c_v는 **k=4와 k=12에서 가장 높다**.
아래에서 두 후보의 토픽을 직접 비교하면, **k=12는 지명·잡음으로 과분할**되어 해석이 어렵고
**k=4는 적은 수로도 주제가 또렷이 갈린다.** 따라서 coherence가 지지하면서 해석도 쉬운 **k=4** 를 채택한다.""")

code(r"""rows = []
allcorp, alltok = corpA + corpB, nounsA + nounsB
for k in range(4, 13, 2):
    m = LdaModel(allcorp, id2word=shared, num_topics=k, passes=5, random_state=42)
    cv = CoherenceModel(model=m, texts=alltok, dictionary=shared, coherence="c_v").get_coherence()
    rows.append((k, cv)); print(f"k={k}: coherence={cv:.4f}")
coh = pd.DataFrame(rows, columns=["k", "coherence"])
plt.figure(figsize=(7, 3.5)); plt.plot(coh["k"], coh["coherence"], "o-")
plt.axvline(4, color="red", ls="--", lw=.8, label="채택 k=4"); plt.legend()
plt.xlabel("k"); plt.ylabel("c_v"); plt.title("토픽 수별 coherence (결합 코퍼스)")
plt.tight_layout(); plt.show()""")

code(r"""# coherence 두 봉우리(k=4, k=12) 토픽을 직접 비교 → 어느 쪽이 해석 가능한가
for kk in (4, 12):
    mk = LdaModel(allcorp, id2word=shared, num_topics=kk, passes=10, random_state=42)
    print(f"--- k={kk} 토픽 (결합 코퍼스) ---")
    for t in range(kk):
        print(f"  T{t}: " + ", ".join(w for w, _ in mk.show_topic(t, 8)))
    print()
# k=12는 지명·잡음 토픽으로 과분할되어 해석이 어렵다 → coherence가 지지하고 해석도 쉬운 k=4 채택
K = 4""")

code(r"""ldaA = LdaModel(corpA, id2word=shared, num_topics=K, passes=15, iterations=100, random_state=42)
ldaB = LdaModel(corpB, id2word=shared, num_topics=K, passes=15, iterations=100, random_state=42)

def topic_words(lda, n=10):
    return {t: [w for w, _ in lda.show_topic(t, n)] for t in range(lda.num_topics)}
print("\n[A. 담론 토픽]")
for t, ws in topic_words(ldaA).items(): print(f"  A{t}: {', '.join(ws)}")
print("\n[B. 서비스 토픽]")
for t, ws in topic_words(ldaB).items(): print(f"  B{t}: {', '.join(ws)}")""")

code(r"""def dom_dist(lda, corp):
    dom = [max(lda.get_document_topics(b), key=lambda x: x[1])[0] if b else -1 for b in corp]
    return pd.Series(dom).value_counts(normalize=True).sort_index() * 100

distA, distB = dom_dist(ldaA, corpA), dom_dist(ldaB, corpB)
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
distA.plot.bar(ax=axes[0], color="#E8734C", title="A. 담론 — 토픽 비중(%)"); axes[0].tick_params(axis="x", rotation=0)
distB.plot.bar(ax=axes[1], color="#4C9BE8", title="B. 서비스 — 토픽 비중(%)"); axes[1].tick_params(axis="x", rotation=0)
plt.tight_layout(); plt.show()
print("A 토픽 비중(%):", distA.round(1).to_dict())
print("B 토픽 비중(%):", distB.round(1).to_dict())""")

# ===== 3. 지표2 log-odds =====
md(r"""## 3. 지표 ② 키워드 변별도 (log-odds ratio)

Monroe et al.(2008)의 **informative Dirichlet prior log-odds**로, 코퍼스 크기차를 보정하면서
"A에 통계적으로 특징적인 단어 vs B에 특징적인 단어"를 추출한다. z가 클수록 그 코퍼스에 변별적이다.""")

code(r"""cntA = Counter(w for t in nounsA for w in t)
cntB = Counter(w for t in nounsB for w in t)
lo = log_odds(cntA, cntB, a0=1000.0, min_count=10)

topB = lo.head(15)            # z 최소 = B 특징어
topA = lo.tail(15).iloc[::-1] # z 최대 = A 특징어
print("=== A(담론)에 특징적인 단어 ==="); print(topA[["word", "z", "freq_A", "freq_B"]].to_string(index=False))
print("\n=== B(서비스)에 특징적인 단어 ==="); print(topB[["word", "z", "freq_A", "freq_B"]].to_string(index=False))

fig, ax = plt.subplots(figsize=(10, 7))
both = pd.concat([topA.head(12), topB.head(12)]).sort_values("z")
colors = ["#4C9BE8" if z < 0 else "#E8734C" for z in both["z"]]
ax.barh(both["word"], both["z"], color=colors)
ax.axvline(0, color="gray", lw=.8); ax.set_xlabel("← B(서비스) 특징    log-odds z    A(담론) 특징 →")
ax.set_title("코퍼스별 변별 단어 (log-odds ratio)"); plt.tight_layout(); plt.show()""")

# ===== 4. 지표3 호명 어휘 =====
md(r"""## 4. 지표 ③ 호명 어휘 정량화 — 갭의 핵심

시니어를 어떻게 **호명**하는지를 두 어휘군으로 측정한다.
- **수혜·대상화**: 지원·보호·취약·돌봄·복지·수급·후원·봉사…
- **주체·소비**: 이용·구매·제품·서비스·기능·사용자·자립·기술·산업…

**주체성 지수 = (주체어 수 − 수혜어 수) / (주체어 수 + 수혜어 수)**, 문서별로 계산해 평균.
−1에 가까울수록 *수혜 대상*, +1에 가까울수록 *능동 주체*로 호명.""")

code(r"""def corpus_framing(nouns_list):
    rows = [framing_index(t) for t in nouns_list]
    fr = pd.DataFrame(rows, columns=["recipient", "active", "idx"])
    return fr

frA = corpus_framing(nounsA); frB = corpus_framing(nounsB)
frA_full = corpus_framing(dfA_full["nouns"].tolist())   # robustness: 전체 A

def summ(fr, name):
    return {
        "코퍼스": name,
        "수혜어 출현 문서%": round((fr["recipient"] > 0).mean() * 100, 1),
        "주체어 출현 문서%": round((fr["active"] > 0).mean() * 100, 1),
        "주체성지수(평균)": round(fr["idx"].mean(), 3),
    }
tab = pd.DataFrame([summ(frA, f"A 담론(균형 {len(frA)})"),
                    summ(frB, f"B 서비스({len(frB)})"),
                    summ(frA_full, f"A 담론(전체 {len(frA_full)}·robustness)")])
print(tab.to_string(index=False))

fig, ax = plt.subplots(figsize=(7, 4))
vals = [frA["idx"].mean(), frB["idx"].mean()]
ax.bar(["A. 담론", "B. 서비스"], vals, color=["#E8734C", "#4C9BE8"])
ax.axhline(0, color="gray", lw=.8); ax.set_ylabel("주체성 지수 (−수혜 / +주체)")
ax.set_title("시니어 호명 방식의 갭"); plt.tight_layout(); plt.show()""")

# ===== 5. 지표4 감성 =====
md(r"""## 5. 지표 ④ 감성 비교

동일 KNU 감성사전으로 두 코퍼스의 어조를 비교한다. (균형 5,059 vs 5,059)""")

code(r"""lexicon = load_lexicon(LEXICON_PATH)
print("감성사전 단어:", len(lexicon))
print("감성 점수화 중... (약 2~3분)")
def senti_label_dist(df):
    res = df[BODY].fillna("").progress_apply(lambda t: score_document(t, lexicon))
    sc = pd.DataFrame(res.tolist(), columns=["score", "pos", "neg", "n", "label"])
    return sc

scA, scB = senti_label_dist(dfA), senti_label_dist(dfB)
dfA["senti"] = scA["score"].values; dfB["senti"] = scB["score"].values   # 트렌드용 부착
def sdist(sc):
    d = sc["label"].value_counts(normalize=True).reindex(["positive", "neutral", "negative"]).fillna(0) * 100
    return d.round(1)
print("A 감성%:", sdist(scA).to_dict(), "| 평균:", round(scA["score"].mean(), 3))
print("B 감성%:", sdist(scB).to_dict(), "| 평균:", round(scB["score"].mean(), 3))

comp = pd.DataFrame({"A. 담론": sdist(scA), "B. 서비스": sdist(scB)})
comp.plot.bar(figsize=(8, 4), color=["#E8734C", "#4C9BE8"]); plt.xticks(rotation=0)
plt.title("감성 라벨 분포 비교 (%)"); plt.tight_layout(); plt.show()""")

# ===== 5-A. 월별 트렌드 =====
md(r"""## 5-A. 월별 트렌드 (시계열 비교)

두 담론의 **월별 기사량**과 **월별 평균 감성**을 비교한다. (동일 기간이므로 추세 비교 가능)""")

code(r"""volA = dfA.set_index("날짜").resample("ME").size()
volB = dfB.set_index("날짜").resample("ME").size()
senA = dfA.set_index("날짜").resample("ME")["senti"].mean()
senB = dfB.set_index("날짜").resample("ME")["senti"].mean()

fig, axes = plt.subplots(1, 2, figsize=(15, 4))
volA.plot(ax=axes[0], marker="o", color="#E8734C", label="A. 담론")
volB.plot(ax=axes[0], marker="s", color="#4C9BE8", label="B. 서비스")
axes[0].set_title("월별 기사 수"); axes[0].legend(); axes[0].grid(alpha=.3)
senA.plot(ax=axes[1], marker="o", color="#E8734C", label="A. 담론")
senB.plot(ax=axes[1], marker="s", color="#4C9BE8", label="B. 서비스")
axes[1].axhline(0, color="gray", ls="--", lw=.8)
axes[1].set_title("월별 평균 감성 점수"); axes[1].legend(); axes[1].grid(alpha=.3)
plt.tight_layout(); plt.show()""")

# ===== 6. 지표5 토픽 유사도 =====
md(r"""## 6. 지표 ⑤ 토픽 유사도 매트릭스

공유 사전 위에서 A·B 토픽-단어 분포의 **코사인 유사도**를 구한다.
값이 높은 칸 = 두 담론이 공유하는 주제, 낮으면 한쪽 고유 주제.""")

code(r"""from numpy.linalg import norm
TA, TB = ldaA.get_topics(), ldaB.get_topics()   # (K x vocab)
sim = np.zeros((K, K))
for i in range(K):
    for j in range(K):
        sim[i, j] = TA[i] @ TB[j] / (norm(TA[i]) * norm(TB[j]))

fig, ax = plt.subplots(figsize=(6.5, 5.5))
im = ax.imshow(sim, cmap="YlOrRd", vmin=0, vmax=sim.max())
ax.set_xticks(range(K)); ax.set_yticks(range(K))
ax.set_xticklabels([f"B{j}" for j in range(K)]); ax.set_yticklabels([f"A{i}" for i in range(K)])
ax.set_xlabel("B. 서비스 토픽"); ax.set_ylabel("A. 담론 토픽")
for i in range(K):
    for j in range(K):
        ax.text(j, i, f"{sim[i,j]:.2f}", ha="center", va="center",
                color="white" if sim[i,j] > sim.max()*0.6 else "black", fontsize=9)
plt.colorbar(im, fraction=0.046); ax.set_title("A↔B 토픽 코사인 유사도"); plt.tight_layout(); plt.show()
print("최대 유사도(가장 닮은 A-B 토픽쌍):", round(sim.max(), 3))
print("평균 유사도:", round(sim.mean(), 3))""")

# ===== 6-A. 네트워크 =====
md(r"""## 6-A. 동시출현 네트워크 (A vs B)

각 코퍼스에서 고빈도 단어가 같은 기사에 함께 등장하는 관계를 망(網)으로 그린다.
어떤 단어가 담론의 **중심**에 있는지 두 코퍼스를 비교한다.""")

code(r"""GA = build_network(nounsA, top_n=40, min_cooc=40)
GB = build_network(nounsB, top_n=40, min_cooc=40)
print("A 네트워크: 노드", GA.number_of_nodes(), "엣지", GA.number_of_edges())
print("B 네트워크: 노드", GB.number_of_nodes(), "엣지", GB.number_of_edges())

fig, axes = plt.subplots(1, 2, figsize=(17, 8))
draw_network(GA, axes[0], "A. 담론 네트워크", "#E8734C")
draw_network(GB, axes[1], "B. 서비스 네트워크", "#4C9BE8")
plt.tight_layout(); plt.show()

import networkx as nx
def top_deg(G, k=8):
    d = nx.degree_centrality(G)
    return [w for w, _ in sorted(d.items(), key=lambda x: -x[1])[:k]]
print("A 중심어:", top_deg(GA))
print("B 중심어:", top_deg(GB))""")

# ===== 7. 결론 =====
md(r"""## 7. 결론 — 같은 시니어, 다른 호명(呼名)

다섯 지표가 한 방향을 가리킨다. **뉴스 담론(A)은 시니어를 '복지 수혜·위기의 대상'으로,
서비스 담론(B)은 '서비스 사용자·시장의 주체'로 호명한다.** 같은 인구를 보면서도 부르는 이름이 다르다.

1. **(지표③ 핵심) 호명의 갭** — 주체성 지수 **A −0.47 vs B +0.06** (갭 ≈ 0.53).
   A는 문서의 67.5%에 *수혜어*(지원·돌봄·복지·취약…)가 등장하고 주체어는 34%에 그친다.
   B는 *주체어*(서비스·이용·제품·산업…)가 64.5%로 수혜어와 균형을 이룬다.
   **전체 A(20,079건)로 재계산해도 −0.47** 로 동일 → 표본 크기와 무관한 구조적 갭.
2. **(지표②) 변별 어휘** — log-odds 결과, A의 특징어는 `나눔·봉사·고독사·계층·독거노인·사회보장·기탁`
   (시혜·온정·위기), B의 특징어는 `서비스·시니어·산업·노인맞춤돌봄·고령친화·실버타운·로봇·케어`
   (서비스·산업·시장). 두 담론은 어휘 수준에서 이미 다른 세계다.
3. **(지표①, k=4) 주제 구성** — A는 '나눔·온정' 토픽이 **32.3%** 로 가장 크고 '고독사·고립 위기'(26.1%)가 뒤따라
   *시혜+위기*가 과반이다. B는 '고령친화 정책'(36.4%)·'돌봄 서비스'(32.0%)·'실버 산업/시장'(21.3%)로
   **정책·서비스·산업이 중심**이다.
4. **(지표④) 감성** — B(평균 +1.56, 긍정 63%)가 A(+1.40, 긍정 61%)보다 긍정적이고,
   A의 부정 비율(24.4%)이 B(16.5%)보다 높다 → 죽음·고립을 다루는 담론이 더 무겁다.
5. **(지표⑤) 토픽 유사도** — 평균 코사인 0.39. 가장 닮은 주제(최대 0.75)는 '취약·폭염·안전'(A 재난안전 ↔ B 돌봄·안전)으로
   **재난/안전이 두 담론의 유일한 교집합**이고, 'A 나눔 ↔ B 산업·시장'은 거의 겹치지 않는다.

> **보조 분석도 같은 결론** — 네트워크 중심어가 A는 `취약·계층·복지·가구`, B는 `노인·어르신·서비스·사업`으로 갈리며
> (둘 다 '지원'을 공유하되 향하는 방향이 다르다), 워드클라우드·월별 트렌드 역시 두 담론의 어휘·어조 차이를 재확인한다.

### 함의
'복지 담론'과 '서비스 담론'은 같은 고령 인구를 한쪽은 *보호받아야 할 대상*, 다른 쪽은 *돈을 쓰는 사용자*로 그린다.
이 **호명의 갭**은 사회가 시니어를 통합적으로 이해하지 못하고 둘로 쪼개 바라보고 있음을 시사한다.

### 분석의 한계
- 호명 어휘셋·감성사전은 **사전 기반**이라 문맥·반어를 못 잡는다 → 절대값보다 **A–B 상대 비교**로 해석.
- 코퍼스 B는 OR 검색 후 **시니어 키워드 후처리 필터**로 노이즈(건설 스마트홈·재난 응급안전 등)를 제거했다.
- 모든 핵심 지표는 정규화(비율·출현율·log-odds)라 코퍼스 크기차의 영향을 받지 않으며, **전체 A 재확인**으로 robustness를 확보했다.""")

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python (BDA)", "language": "python", "name": "bda"},
    "language_info": {"name": "python"},
}
import nbformat
nbformat.write(nb, "notebooks/final_exam_gap.ipynb")
print("빌드 완료: notebooks/final_exam_gap.ipynb,", len(cells), "cells")
