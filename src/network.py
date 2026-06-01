"""단어 동시출현(co-occurrence) 네트워크 함수 모음 (networkx)."""
from __future__ import annotations

from collections import Counter
from itertools import combinations

import pandas as pd


# ──────────────────────────────────────────────────────────────
# 동시출현 계산
# ──────────────────────────────────────────────────────────────
def top_vocab(token_lists: list[list[str]], top_n: int = 50) -> list[str]:
    """전체 토큰에서 빈도 상위 top_n 단어를 반환한다."""
    cnt = Counter(w for toks in token_lists for w in toks)
    return [w for w, _ in cnt.most_common(top_n)]


def cooccurrence(token_lists: list[list[str]], vocab: list[str]) -> Counter:
    """문서 단위 동시출현 빈도를 계산한다.

    한 문서 안에 vocab 단어가 함께 등장하면 그 쌍을 1회 카운트한다(문서당 중복 무시).
    반환: Counter{(w1, w2): count}  (w1 < w2 정렬)
    """
    vocab_set = set(vocab)
    pair_counts: Counter = Counter()
    for toks in token_lists:
        present = sorted(vocab_set.intersection(toks))
        for w1, w2 in combinations(present, 2):
            pair_counts[(w1, w2)] += 1
    return pair_counts


# ──────────────────────────────────────────────────────────────
# 그래프 구성
# ──────────────────────────────────────────────────────────────
def build_network(
    token_lists: list[list[str]],
    top_n: int = 50,
    min_cooc: int = 10,
):
    """상위 단어로 동시출현 네트워크(networkx.Graph)를 만든다.

    - top_n: 노드로 쓸 빈도 상위 단어 수
    - min_cooc: 이 값 미만 동시출현 쌍은 엣지에서 제외
    노드 속성 'freq'(단어 빈도), 엣지 속성 'weight'(동시출현 수)를 부여한다.
    """
    import networkx as nx

    vocab = top_vocab(token_lists, top_n)
    freq = Counter(w for toks in token_lists for w in toks)
    pairs = cooccurrence(token_lists, vocab)

    G = nx.Graph()
    for w in vocab:
        G.add_node(w, freq=int(freq[w]))
    for (w1, w2), c in pairs.items():
        if c >= min_cooc:
            G.add_edge(w1, w2, weight=int(c))

    G.remove_nodes_from([n for n in list(G.nodes) if G.degree(n) == 0])
    return G


# ──────────────────────────────────────────────────────────────
# 중심성
# ──────────────────────────────────────────────────────────────
def centrality(G) -> pd.DataFrame:
    """연결·매개·고유벡터 중심성을 계산해 DataFrame으로 반환한다.

    반환 컬럼: node, degree, betweenness, eigenvector, freq
    """
    import networkx as nx

    deg = nx.degree_centrality(G)
    bet = nx.betweenness_centrality(G, weight="weight")
    try:
        eig = nx.eigenvector_centrality(G, weight="weight", max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        eig = {n: float("nan") for n in G.nodes}

    rows = [
        {
            "node": n,
            "degree": round(deg[n], 4),
            "betweenness": round(bet[n], 4),
            "eigenvector": round(eig[n], 4),
            "freq": G.nodes[n].get("freq", 0),
        }
        for n in G.nodes
    ]
    return pd.DataFrame(rows).sort_values("degree", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────
# 시각화
# ──────────────────────────────────────────────────────────────
def draw_network(G, ax=None, seed: int = 42, scale_node: float = 3000.0):
    """스프링 레이아웃으로 네트워크를 그린다. (노드 크기=빈도, 엣지 굵기=동시출현)"""
    import networkx as nx
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(13, 10))

    pos = nx.spring_layout(G, k=0.6, seed=seed, weight="weight")

    freqs = [G.nodes[n].get("freq", 1) for n in G.nodes]
    fmax = max(freqs) or 1
    node_sizes = [scale_node * (f / fmax) + 200 for f in freqs]

    weights = [G[u][v]["weight"] for u, v in G.edges]
    wmax = max(weights) or 1
    edge_widths = [3.0 * (w / wmax) + 0.2 for w in weights]

    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.3, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="#4C9BE8",
                           alpha=0.85, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=11,
                            font_family=plt.rcParams["font.family"][0], ax=ax)
    ax.axis("off")
    return ax
