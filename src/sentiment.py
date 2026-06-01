"""감성 점수 산출 함수 모음 (KNU 한국어 감성사전 기반)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

import config
from src.preprocess import clean_text, get_okt

# KNU 감성사전 경로 (data/lexicon/SentiWord_info.json)
LEXICON_PATH = config.DATA_DIR / "lexicon" / "SentiWord_info.json"

# 감성 의미를 담는 품사 (명사/형용사/동사/부사)
_SENTI_POS = {"Noun", "Adjective", "Verb", "Adverb"}
_KO_RE = re.compile(r"[가-힣]+")


# ──────────────────────────────────────────────────────────────
# 사전 로드
# ──────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_lexicon(path: str | Path = LEXICON_PATH) -> dict[str, int]:
    """KNU 감성사전에서 한 단어(공백 없음) 한글 엔트리만 골라 {단어: 극성(int)} 사전을 만든다.

    극성은 -2 ~ +2 정수. 여러 어절 표현은 단일 토큰 매칭이 어려워 제외한다.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    lex: dict[str, int] = {}
    for x in data:
        w = x["word"]
        if " " in w or not _KO_RE.fullmatch(w):
            continue
        lex[w] = int(x["polarity"])
    return lex


# ──────────────────────────────────────────────────────────────
# 감성 토큰 / 점수
# ──────────────────────────────────────────────────────────────
def senti_tokens(text: str, min_len: int = 2) -> list[str]:
    """감성 매칭용 토큰을 추출한다. Okt.pos(norm, stem)으로 어간을 복원해
    명사·형용사·동사·부사만 남긴다 (예: '행복한' → '행복하다')."""
    cleaned = clean_text(text)
    if not cleaned:
        return []
    return [
        w for w, tag in get_okt().pos(cleaned, norm=True, stem=True)
        if tag in _SENTI_POS and len(w) >= min_len
    ]


def score_document(text: str, lexicon: dict[str, int] | None = None) -> dict:
    """문서 1건의 감성 점수를 계산한다.

    반환: {score, pos, neg, n_match, label}
      - score: 매칭 단어 극성의 합
      - pos/neg: 긍정/부정 단어 수
      - n_match: 감성사전에 매칭된 단어 수
      - label: 'positive' | 'negative' | 'neutral'
    """
    if lexicon is None:
        lexicon = load_lexicon()

    score = pos = neg = n = 0
    for w in senti_tokens(text):
        p = lexicon.get(w)
        if p is None:
            continue
        score += p
        n += 1
        if p > 0:
            pos += 1
        elif p < 0:
            neg += 1

    if score > 0:
        label = "positive"
    elif score < 0:
        label = "negative"
    else:
        label = "neutral"

    return {"score": score, "pos": pos, "neg": neg, "n_match": n, "label": label}


def score_dataframe(
    df: pd.DataFrame,
    text_col: str = "본문",
    lexicon: dict[str, int] | None = None,
    progress: bool = True,
) -> pd.DataFrame:
    """DataFrame 각 문서의 감성 점수를 계산해 score/pos/neg/n_match/label 컬럼을 추가한다."""
    if lexicon is None:
        lexicon = load_lexicon()

    texts = df[text_col].fillna("")
    if progress:
        from tqdm.auto import tqdm
        tqdm.pandas(desc="감성 점수")
        scored = texts.progress_apply(lambda t: score_document(t, lexicon))
    else:
        scored = texts.apply(lambda t: score_document(t, lexicon))

    out = df.copy()
    scored_df = pd.DataFrame(list(scored), index=out.index)
    for col in ["score", "pos", "neg", "n_match", "label"]:
        out[f"senti_{col}" if col != "label" else "senti_label"] = scored_df[col]
    return out
