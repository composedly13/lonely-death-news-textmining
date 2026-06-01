"""전처리 함수 모음: 다중 엑셀 로드, 정제/중복제거, Okt 명사추출, 불용어, 토큰화."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

import config

# ──────────────────────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────────────────────
ID_COL = "뉴스 식별자"
DATE_COL = "일자"
TITLE_COL = "제목"
BODY_COL = "본문"
EXCLUDE_COL = "분석제외 여부"

# 분석에서 제외할 '분석제외 여부' 플래그 값
EXCLUDE_FLAGS = {"예외", "중복", "중복, 예외"}

# 빈도/토픽 분석에서 거의 항상 노이즈인 기본 불용어 (config.STOP_WORDS와 합쳐 사용)
DEFAULT_STOP_WORDS = {
    "기자", "뉴스", "사진", "제공", "무단", "전재", "재배포", "금지", "연합뉴스",
    "오전", "오후", "이날", "지난", "올해", "최근", "관련", "통해", "위해", "대한",
    "이번", "당시", "이상", "이후", "이전", "정도", "가운데", "경우", "때문",
}


# ──────────────────────────────────────────────────────────────
# 로드 / 병합
# ──────────────────────────────────────────────────────────────
def load_raw(raw_dir: Path | str = config.RAW_DIR) -> pd.DataFrame:
    """data/raw/ 의 모든 .xlsx를 읽어 식별자 기준으로 병합·중복제거한 DataFrame을 반환한다.

    `뉴스 식별자`는 26자리 문자열 ID이므로 반드시 dtype=str로 읽는다
    (숫자로 읽으면 부동소수점 정밀도 손실로 중복제거가 깨진다).
    """
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"엑셀을 찾지 못했습니다: {raw_dir}")

    frames = [pd.read_excel(f, dtype={ID_COL: str}) for f in files]
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=ID_COL).reset_index(drop=True)
    return df


# ──────────────────────────────────────────────────────────────
# 정제 / 필터링
# ──────────────────────────────────────────────────────────────
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"\S+@\S+")
_NONKO_RE = re.compile(r"[^가-힣\s]")          # 한글·공백만 남김
_MULTISPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """URL·이메일·비한글 문자를 제거하고 공백을 정규화한다."""
    if not isinstance(text, str):
        return ""
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _NONKO_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text)
    return text.strip()


def filter_documents(df: pd.DataFrame) -> pd.DataFrame:
    """'분석제외' 플래그 행과 제목+본문 완전중복을 제거하고, 날짜 컬럼을 추가한다.

    추가 컬럼:
      - 날짜: `일자`(YYYYMMDD int)를 datetime으로 변환
    """
    out = df.copy()

    # 분석제외 여부 플래그 제거
    if EXCLUDE_COL in out.columns:
        out = out[~out[EXCLUDE_COL].isin(EXCLUDE_FLAGS)]

    # 제목+본문 완전중복 제거
    out = out.drop_duplicates(subset=[TITLE_COL, BODY_COL])

    # 날짜 파싱
    out["날짜"] = pd.to_datetime(out[DATE_COL].astype(str), format="%Y%m%d", errors="coerce")

    return out.reset_index(drop=True)


# ──────────────────────────────────────────────────────────────
# 형태소 분석 (Okt)
# ──────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_okt():
    """Okt 인스턴스를 (JVM 1회 기동으로) 싱글톤 반환한다."""
    from konlpy.tag import Okt
    return Okt()


def get_stop_words(extra: set[str] | None = None) -> set[str]:
    """기본 불용어 + config.STOP_WORDS + extra 를 합친 집합을 반환한다."""
    words = set(DEFAULT_STOP_WORDS)
    words |= set(getattr(config, "STOP_WORDS", []) or [])
    if extra:
        words |= set(extra)
    return words


@lru_cache(maxsize=1)
def _compound_parts(words: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """복합어 각각을 Okt 명사로 분해한 조각 튜플을 반환한다. (재결합용)"""
    okt = get_okt()
    return tuple(tuple(okt.nouns(w)) for w in words)


def _merge_compounds(nouns: list[str], compounds: tuple[str, ...]) -> list[str]:
    """명사 리스트에서 복합어 조각이 연속으로 나타나면 원래 복합어로 재결합한다.

    예) ['독거', '노인'] → ['독거노인']  (compounds에 '독거노인'이 있을 때)
    """
    parts_list = _compound_parts(compounds)
    # 긴 복합어부터 매칭
    order = sorted(range(len(compounds)), key=lambda i: -len(parts_list[i]))

    result: list[str] = []
    i = 0
    n = len(nouns)
    while i < n:
        matched = False
        for idx in order:
            parts = parts_list[idx]
            k = len(parts)
            if k >= 2 and tuple(nouns[i:i + k]) == parts:
                result.append(compounds[idx])
                i += k
                matched = True
                break
        if not matched:
            result.append(nouns[i])
            i += 1
    return result


def extract_nouns(
    text: str,
    min_len: int = 2,
    stop_words: set[str] | None = None,
    compounds: tuple[str, ...] | None = None,
) -> list[str]:
    """텍스트를 정제 후 Okt 명사를 추출한다.

    - min_len: 글자 수가 이 값 미만인 명사는 제거 (한 글자 명사 노이즈 제거)
    - stop_words: 제거할 불용어 집합 (None이면 get_stop_words())
    - compounds: 재결합할 복합어 튜플 (예: tuple(config.KEYWORDS)); None이면 결합 안 함
    """
    if stop_words is None:
        stop_words = get_stop_words()

    cleaned = clean_text(text)
    if not cleaned:
        return []

    nouns = get_okt().nouns(cleaned)

    if compounds:
        nouns = _merge_compounds(nouns, compounds)

    return [w for w in nouns if len(w) >= min_len and w not in stop_words]


def tokenize_dataframe(
    df: pd.DataFrame,
    text_col: str = BODY_COL,
    out_col: str = "nouns",
    min_len: int = 2,
    stop_words: set[str] | None = None,
    compounds: tuple[str, ...] | None = None,
    progress: bool = True,
) -> pd.DataFrame:
    """DataFrame의 text_col에 대해 명사 추출을 수행하고 out_col(list)을 추가해 반환한다."""
    if stop_words is None:
        stop_words = get_stop_words()

    texts = df[text_col].fillna("")
    if progress:
        from tqdm.auto import tqdm
        tqdm.pandas(desc="Okt 명사추출")
        tokens = texts.progress_apply(
            lambda t: extract_nouns(t, min_len, stop_words, compounds)
        )
    else:
        tokens = texts.apply(
            lambda t: extract_nouns(t, min_len, stop_words, compounds)
        )

    out = df.copy()
    out[out_col] = tokens
    return out


# ──────────────────────────────────────────────────────────────
# 저장 / 로드 (processed)
# ──────────────────────────────────────────────────────────────
def save_processed(df: pd.DataFrame, name: str) -> Path:
    """DataFrame을 data/processed/<name>.pkl 로 저장하고 경로를 반환한다."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PROCESSED_DIR / f"{name}.pkl"
    df.to_pickle(path)
    return path


def load_processed(name: str) -> pd.DataFrame:
    """data/processed/<name>.pkl 을 읽어 DataFrame으로 반환한다."""
    return pd.read_pickle(config.PROCESSED_DIR / f"{name}.pkl")
