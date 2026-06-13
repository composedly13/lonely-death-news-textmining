"""프로젝트 공통 설정: 경로, 키워드, 불용어, 한글 폰트.

로컬 윈도우를 기준으로 하되 코랩/Linux/Mac에서도 동작하도록 폰트는 자동 탐지한다.
"""
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 경로
# ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "A"      # 코퍼스 A(고독사·독거노인). 코퍼스 B는 data/raw/B
RAW_B_DIR = DATA_DIR / "raw" / "B"    # 코퍼스 B(스마트홈·시니어 서비스, 기말과제)
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUTS_DIR = BASE_DIR / "outputs"
FIG_DIR = OUTPUTS_DIR / "figures"
TABLE_DIR = OUTPUTS_DIR / "tables"

# ──────────────────────────────────────────────────────────────
# 분석 키워드 / 불용어
# ──────────────────────────────────────────────────────────────
KEYWORDS = ["독거노인", "고독사", "1인 고령가구", "노인 고립", "무연고 사망"]

STOP_WORDS = [
    # 변별력 없는 행정·보도자료 상투어 (모든 토픽에 깔리는 단어)
    "지역", "사회", "사업", "지원", "추진", "협의", "전달", "나눔", "서비스",
    "운영", "마련", "실시", "진행", "제공", "활동", "대상", "계획", "참여", "행사",
]

# ──────────────────────────────────────────────────────────────
# 한글 폰트
#   1순위: 윈도우 맑은 고딕
#   fallback: 코랩/Linux 나눔고딕, Mac 애플고딕
# ──────────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\malgun.ttf"),                              # Windows
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),          # Colab / Linux
    Path("/Library/Fonts/AppleGothic.ttf"),                           # macOS
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),       # macOS (대체)
]


def get_font_path():
    """존재하는 한글 폰트 파일 경로(str)를 반환한다. 없으면 None. (WordCloud 등 폰트 파일이 필요한 경우용)"""
    for font_path in FONT_CANDIDATES:
        if font_path.exists():
            return str(font_path)
    return None


def set_korean_font():
    """존재하는 한글 폰트를 자동 탐지해 matplotlib에 등록하고 폰트명을 반환한다."""
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt

    for font_path in FONT_CANDIDATES:
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))
            font_name = fm.FontProperties(fname=str(font_path)).get_name()
            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            return font_name

    # 후보 폰트를 못 찾으면 마이너스 깨짐만 방지하고 경고
    plt.rcParams["axes.unicode_minus"] = False
    print("[set_korean_font] 한글 폰트를 찾지 못했습니다. 폰트를 설치하거나 FONT_CANDIDATES에 경로를 추가하세요.")
    return None
