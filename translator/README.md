# Translator

수집된 기사를 한국어로 번역하는 모듈입니다. 기본 엔진은 **Argos Translate**
(오픈소스, 오프라인, 무료)입니다 — 파파고/구글/DeepL은 전부 카드(결제 수단)
등록이 있어야 API 키를 받을 수 있어서, 카드 등록 없이 바로 쓸 수 있는 대안으로
도입했습니다. Claude(Anthropic API) 기반 엔진도 코드는 그대로 남아 있어
(`anthropic_engine.py`) 나중에 다시 켤 수 있습니다.

## 실행 방법

```bash
pip install -r requirements.txt --break-system-packages
python setup_argos_model.py   # 최초 1회만: en->ko 모델 다운로드/설치 (약 130MB)
python translate.py
```

`setup_argos_model.py`는 최초 1회만 실행하면 되고, 이후로는 완전히 오프라인으로
번역할 수 있습니다(네트워크 연결 불필요). 이미 설치돼 있으면 다시 실행해도
아무 일도 하지 않으므로(idempotent) 여러 번 실행해도 안전합니다.

`TRANSLATOR_DB_URL`을 지정하지 않으면 `backend/docker-compose.yml`로 띄운 로컬 MySQL
(`mysql+pymysql://root:password@localhost:3306/liverpool_news`)에 연결을 시도한다.
collector와 동일한 `articles`/`translations` 테이블 스키마를 사용하므로, 먼저 backend를
한 번 실행해 테이블이 생성된 상태여야 한다.

`translator/.env`가 있으면 `db.py` import 시점에 `python-dotenv`가
`TRANSLATOR_DB_URL`을 자동으로 읽어들여 별도 `export` 없이 `python translate.py`만
실행해도 값이 적용된다. `.env`가 없으면 에러 없이 위 기본 접속 정보로 동작한다.

## 동작 방식

1. `db.fetch_untranslated_articles()`로 `articles.status = 'COLLECTED'`인 기사를 조회한다.
2. 각 기사를 `translate_article()`로 번역한다 (`translate.py`).
   - `html_cleanup.clean_for_translation()`으로 RSS 원문에 섞인 HTML 태그/엔티티와
     워드프레스 특유의 "The post ... appeared first on ..." 푸터를 먼저 제거한다.
     이 정리는 번역 직전에만 적용되며 DB에 저장된 `content_original`(원문) 자체는
     건드리지 않는다.
   - `argos_engine.translate()`(기본)로 실제 번역을 수행한다.
   - `glossary.apply_glossary()`로 번역 결과에 남은 영문 축구 용어를 정해진
     한국어 용어로 후처리 치환한다.
3. 번역 결과를 `translations` 테이블에 저장하고, 해당 기사의 `status`를 `TRANSLATED`로
   갱신한다 (`db.save_translation()`).

## 엔진 구조 (교체 가능하도록 분리됨)

- `argos_engine.py`: 기본 엔진. Argos Translate로 오프라인 번역.
- `anthropic_engine.py`: Claude(Anthropic API) 엔진. 현재 비활성 상태지만 완전히
  삭제하지 않고 보존했다. `translate.py`의 `ENGINE = "anthropic"`으로 바꾸면
  다시 쓸 수 있다(`ANTHROPIC_API_KEY` 필요).
- `translate.py`의 `ENGINE` 상수만 바꾸면 어느 쪽을 쓸지 전환된다. 나중에
  파파고/DeepL 등 다른 상용 API로 교체하고 싶으면 같은 인터페이스
  (`translate(title, content) -> (title_ko, content_ko, model_version)`)로 새
  엔진 모듈을 하나 추가하면 된다.

## 번역 품질에 대한 솔직한 평가

Argos Translate는 문장 단위 신경망 번역(NMT)이라 Claude 같은 LLM 기반 요약
번역보다 품질이 낮을 수 있다:

- 관용구·숙어를 단어별로 직역해 어색한 경우가 많다 (예: "pays tribute to" →
  "트리뷰를 지불하고"처럼 문자 그대로 옮겨지는 경우).
- 선수 이름 등 고유명사의 한글 표기가 관용적 표기와 다를 수 있다 (예: "Mo
  Salah" → "모 살라"; 흔히 쓰는 표기는 "살라"/"모하메드 살라").
- 요약 기능이 없다 — Claude 엔진과 달리 원문을 그대로 축약 없이 문장 단위로
  옮긴다. RSS가 이미 요약(summary)만 수집하므로 번역 대상 자체는 짧다.

번역 품질이 더 중요해지는 시점에는 위 "엔진 구조"대로 상용 API로 교체하면 된다.

## 파일 구성

- `translate.py`: 미번역 기사를 조회해 번역하는 메인 로직 (엔진 선택 + DB 배치 처리)
- `argos_engine.py`: Argos Translate 기반 번역 엔진 (기본)
- `anthropic_engine.py`: Claude(Anthropic API) 기반 번역 엔진 (현재 비활성, 보존용)
- `setup_argos_model.py`: en->ko Argos Translate 모델을 다운로드/설치하는 1회성 스크립트
- `html_cleanup.py`: 번역 직전에 RSS 원문의 HTML 태그/엔티티/워드프레스 푸터를 정리
- `glossary.py`: 축구 용어 일관성을 위한 용어집. LLM 프롬프트 삽입(`build_glossary_prompt`)과
  번역 결과 후처리 치환(`apply_glossary`) 두 가지 방식을 모두 제공한다
- `db.py`: 미번역 기사 조회 및 번역 결과 저장 (backend와 동일한 DB 스키마 사용)
- `tests/`: 단위/통합 테스트 (Argos/Claude 호출 모두 mock 처리, DB 로직은 in-memory DB로 검증)
