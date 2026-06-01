# 고독사 · 독거노인 뉴스 텍스트마이닝

빅카인즈 뉴스 엑셀을 입력으로 **EDA → 빈도 → 워드클라우드 → LDA 토픽모델 → 동시출현 네트워크 → 감성 분석**을 수행하는 프로젝트.

## 프로젝트 구조

```
BDA/
├── data/
│   ├── raw/                      # 빅카인즈 원본 엑셀 (직접 넣음, repo 미포함)
│   ├── processed/                # 전처리 캐시 pkl (생성물, repo 미포함)
│   └── lexicon/                  # KNU 감성사전 (직접 받음, repo 미포함)
├── src/                          # 무거운 로직(함수) — 노트북에서 import
│   ├── __init__.py
│   ├── preprocess.py             # 엑셀 로드·병합, 정제, Okt 명사추출, 복합어 보존, 불용어
│   ├── topic_model.py            # LDA 사전/코퍼스, coherence 탐색, 학습, pyLDAvis
│   ├── network.py                # 동시출현 계산, 네트워크 구성, 중심성, 시각화
│   └── sentiment.py              # KNU 사전 로드, 감성 토큰(Okt pos), 문서 점수화
├── notebooks/
│   ├── 01_eda.ipynb              # EDA·빈도·워드클라우드
│   ├── 02_topic_model.ipynb      # LDA 토픽 모델
│   ├── 03_network.ipynb          # 동시출현 네트워크
│   ├── 04_sentiment.ipynb        # 감성 분석
│   └── 99_final_report.ipynb     # 발표용 최종 보고서 (코랩 자기완결형)
├── outputs/
│   ├── figures/                  # 그림 png·pyLDAvis html (생성물, repo 미포함)
│   └── tables/                   # 결과 표 csv
├── config.py                     # 경로·키워드·불용어·한글폰트 설정
├── requirements.txt
├── README.md
└── .gitignore
```

> **repo에 포함되지 않는 것**(`.gitignore`): 원본 뉴스 엑셀(`data/raw/*.xlsx`, 저작권), 전처리 캐시(`data/processed/`),
> 감성사전(`data/lexicon/`), 그림(`outputs/figures/`), `.claude/`(로컬 설정). → 클론 후 **데이터 넣기 + 감성사전 받기**를 먼저 해야 한다.

## 데이터 수집 명세

빅카인즈([bigkinds.or.kr](https://www.bigkinds.or.kr))에서 아래 명세대로 뉴스를 검색·수집해 엑셀(`.xlsx`)로 내려받아 `data/raw/`에 넣는다.

| 항목 | 값 |
|---|---|
| 출처 | 빅카인즈 (BigKinds) |
| 수집 기간 | **2025-06-01 ~ 2026-06-01** (1년, 전수) |
| 검색식 | 5개 키워드를 `OR`(쉼표)로 묶어 수집 |
| 검색어 | `독거노인, 고독사, 1인 고령가구, 노인 고립, 무연고 사망` |
| 검색 필드 | 제목 + 본문 |
| 총 건수 | **20,521건** (식별자 기준 중복 0) |

> **분할 수집**: 빅카인즈는 1회 다운로드가 최대 20,000건이라, 기간을 둘로 나눠 받아 누락 없이 전수를 확보한다.
> 전처리 로더는 `data/raw/*.xlsx`를 모두 읽어 `뉴스 식별자` 기준으로 병합·중복제거한다.
>
> | 파일 | 기간 | 건수 |
> |---|---|---|
> | `NewsResult_20250601-20251130.xlsx` | 2025-06-01 ~ 2025-11-30 | 10,498 |
> | `NewsResult_20251201-20260601.xlsx` | 2025-12-01 ~ 2026-06-01 | 10,023 |

> ⚠️ **`뉴스 식별자`는 반드시 문자열(`dtype=str`)로 읽는다.** 26자리 ID(예: `01400351.20251130220115001`)를 숫자로 읽으면 부동소수점 정밀도 손실로 서로 다른 기사가 같은 ID로 뭉개져 중복제거가 오작동한다.

수집 키워드 5개 (출처: `config.py`의 `KEYWORDS`):

- 독거노인
- 고독사
- 1인 고령가구
- 노인 고립
- 무연고 사망

## 실행 순서

1. **데이터 넣기** — 위 키워드로 빅카인즈에서 내려받은 뉴스 엑셀(들)을 `data/raw/`에 넣는다. (여러 개여도 로더가 자동 병합)
2. `notebooks/01_eda.ipynb` — 탐색적 분석, 빈도, 워드클라우드
3. `notebooks/02_topic_model.ipynb` — LDA 토픽 모델
4. `notebooks/03_network.ipynb` — 단어 동시출현 네트워크
5. `notebooks/04_sentiment.ipynb` — 감성 분석
6. `notebooks/99_final_report.ipynb` — 발표용 최종 보고서

## 노트북에서 src 임포트

각 노트북 첫 셀에서 프로젝트 루트를 `sys.path`에 추가하면 `src` 패키지를 import할 수 있다.

```python
import sys; sys.path.append("..")   # notebooks/ 기준 프로젝트 루트
from src import preprocess, topic_model, network, sentiment
import config
```

## 환경 설정

```bash
pip install -r requirements.txt
```

- **JDK 필요**: 형태소 분석기로 KoNLPy의 Okt를 사용한다. Okt는 JVM이 필요하므로 **JDK(8 이상)를 설치하고 `JAVA_HOME` 환경변수를 설정**해야 한다.
- **Jupyter 커널**: 의존성이 설치된 환경을 Jupyter 커널로 등록하고(예: `python -m ipykernel install --user --name bda --display-name "Python (BDA)"`), 노트북을 열 때 그 커널을 선택한다.
- **감성사전 (04)**: KNU 한국어 감성사전이 필요하다. `data/lexicon/SentiWord_info.json`에 두며, 다음으로 받는다.
  ```bash
  curl -L -o data/lexicon/SentiWord_info.json \
    https://raw.githubusercontent.com/park1200656/KnuSentiLex/master/data/SentiWord_info.json
  ```

## 구글 코랩에서 실행 (`99_final_report.ipynb`)

`99_final_report.ipynb`는 **코랩에서 그대로 실행되는 자기완결형 노트북**이다. `src` import에 의존하지 않고
필요한 함수를 셀에 직접 풀어쓰며, 상단에 `pip install`·나눔폰트 설치·드라이브 마운트·감성사전 다운로드 셀을 갖춘다.
(`01~04`는 로컬에서 `src`를 import하는 개발용 노트북이라 코랩 실행 대상이 아니다.)

**실행 순서**

1. **데이터 업로드** — 빅카인즈 엑셀(들)을 본인 구글 드라이브에 올린다. 예: `내 드라이브/BDA/data/raw/`
2. **노트북 열기** — `99_final_report.ipynb`를 코랩에서 연다.
   ([colab.research.google.com](https://colab.research.google.com) → GitHub 탭에서 이 repo URL 붙여넣기, 또는 드라이브에서 열기)
3. **경로 수정** — `0. 실행 환경 준비`의 **③ 드라이브 마운트 셀**에서 `PROJECT_DIR`을 본인 경로로 바꾼다.
   ```python
   PROJECT_DIR = "/content/drive/MyDrive/BDA"   # data/raw/ 가 이 아래에 있어야 함
   ```
4. **위에서부터 순서대로 실행** — `런타임 > 모두 실행`. ①pip ②나눔폰트 ③드라이브마운트 ④감성사전 셀이
   자동으로 환경을 구성한다. (전체 약 8~10분: Okt 토큰화·LDA·감성 점수화 포함)
5. **토픽 라벨 확인** — `3. LDA` 결과의 토픽 ID 순서는 환경에 따라 달라질 수 있다.
   출력된 키워드를 보고 `TOPIC_LABELS` 매핑만 맞춰주면 된다. (결론의 수치는 ID 매핑과 무관하게 성립)

> 별도 `pip install`·폰트 설치·`JAVA_HOME` 설정이 필요 없다 — 코랩은 Java가 기본 내장되어 있고, 설치 셀이 나머지를 처리한다.
