"""LDA 토픽 모델 학습/평가 함수 모음 (gensim)."""
from __future__ import annotations

import pandas as pd


# ──────────────────────────────────────────────────────────────
# 사전 / 코퍼스
# ──────────────────────────────────────────────────────────────
def build_corpus(
    token_lists: list[list[str]],
    no_below: int = 5,
    no_above: float = 0.5,
    keep_n: int | None = 100000,
):
    """토큰 리스트로 gensim 사전(Dictionary)과 BoW 코퍼스를 만든다.

    - no_below: 이 문서 수 미만으로 등장한 희귀어 제거
    - no_above: 전체 문서의 이 비율 초과로 등장한 과빈출어 제거 (행정 상투어 억제)
    - keep_n: 상위 빈도 단어 최대 개수 (None이면 무제한)
    반환: (dictionary, corpus)
    """
    from gensim.corpora import Dictionary

    dictionary = Dictionary(token_lists)
    dictionary.filter_extremes(no_below=no_below, no_above=no_above, keep_n=keep_n)
    corpus = [dictionary.doc2bow(toks) for toks in token_lists]
    return dictionary, corpus


# ──────────────────────────────────────────────────────────────
# 학습
# ──────────────────────────────────────────────────────────────
def train_lda(
    dictionary,
    corpus,
    num_topics: int,
    passes: int = 15,
    iterations: int = 100,
    random_state: int = 42,
    **kwargs,
):
    """LdaModel을 학습해 반환한다."""
    from gensim.models import LdaModel

    return LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        passes=passes,
        iterations=iterations,
        random_state=random_state,
        **kwargs,
    )


# ──────────────────────────────────────────────────────────────
# 토픽 수 탐색 (coherence)
# ──────────────────────────────────────────────────────────────
def compute_coherence(
    dictionary,
    corpus,
    token_lists: list[list[str]],
    start: int = 2,
    limit: int = 11,
    step: int = 1,
    passes: int = 5,
    random_state: int = 42,
) -> pd.DataFrame:
    """토픽 수를 start~limit 범위로 바꿔가며 c_v coherence를 계산해 DataFrame으로 반환한다.

    반환 컬럼: num_topics, coherence
    """
    from gensim.models import CoherenceModel

    rows = []
    for k in range(start, limit, step):
        lda = train_lda(dictionary, corpus, num_topics=k, passes=passes,
                        random_state=random_state)
        cm = CoherenceModel(model=lda, texts=token_lists, dictionary=dictionary,
                            coherence="c_v")
        rows.append({"num_topics": k, "coherence": cm.get_coherence()})
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────
# 결과 정리 / 시각화
# ──────────────────────────────────────────────────────────────
def topics_dataframe(lda, topn: int = 10) -> pd.DataFrame:
    """각 토픽의 상위 단어를 'w1, w2, ...' 문자열로 정리한 DataFrame을 반환한다.

    반환 컬럼: topic, keywords
    """
    rows = []
    for tid in range(lda.num_topics):
        words = [w for w, _ in lda.show_topic(tid, topn=topn)]
        rows.append({"topic": tid, "keywords": ", ".join(words)})
    return pd.DataFrame(rows)


def dominant_topics(lda, corpus) -> pd.DataFrame:
    """문서별 대표 토픽과 그 비중을 DataFrame으로 반환한다.

    반환 컬럼: dominant_topic, topic_pct
    """
    rows = []
    for bow in corpus:
        dist = lda.get_document_topics(bow)
        if dist:
            tid, pct = max(dist, key=lambda x: x[1])
        else:
            tid, pct = -1, 0.0
        rows.append({"dominant_topic": tid, "topic_pct": round(float(pct), 4)})
    return pd.DataFrame(rows)


def make_pyldavis(lda, corpus, dictionary):
    """pyLDAvis 시각화 객체를 준비해 반환한다. (노트북에서 display 또는 save_html)"""
    import pyLDAvis
    import pyLDAvis.gensim_models as gensimvis

    return gensimvis.prepare(lda, corpus, dictionary)
