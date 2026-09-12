# Translator

수집된 기사를 한국어로 번역하는 모듈입니다. 기본 엔진은 **Argos Translate**
(오픈소스, 오프라인, 무료)입니다 — 파파고/구글/DeepL은 전부 카드(결제 수단)
등록이 있어야 API 키를 받을 수 있어서, 카드 등록 없이 바로 쓸 수 있는 대안으로
도입했습니다. Claude(Anthropic API) 기반 엔진(`anthropic_engine.py`)과
GPT(OpenAI API) 기반 엔진(`openai_engine.py`)도 코드는 그대로 남아 있어
나중에 다시 켤 수 있습니다.

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

1. `db.fetch_untranslated_articles()`로 `articles.status = 'COLLECTED'`인 기사를
   우선순위 정렬에 필요한 메타데이터(`source_tier`, `quoted_reporter`,
   `independent_source_count`, `published_at`)와 함께 조회한다.
2. `priority.sort_by_priority()`로 처리 순서를 정한다 (아래 "우선순위 큐" 참고).
3. `DAILY_TRANSLATION_LIMIT`을 적용해 오늘 처리할 수 있는 만큼만 앞에서부터 자른다.
4. 그 안에 든 기사를 `translate_article()`로 번역한다 (`translate.py`). 전처리 → 번역 →
   후처리 순서로 진행된다.
5. 번역 결과를 `translations` 테이블에 저장하고, 해당 기사의 `status`를 `TRANSLATED`로
   갱신한다 (`db.save_translation()`). 한도를 넘겨 이번에 시도조차 하지 않은 기사는
   `COLLECTED` 상태 그대로 남아 다음 배치에서 다시 앞에서부터 시도된다.

## 우선순위 큐 (`priority.py`)

`status='COLLECTED'`인 기사는 사실상 번역 대기열이다. `DAILY_TRANSLATION_LIMIT`
(기본 300, 환경 변수로 조정 가능)으로 하루 처리량을 제한해 유료 엔진(OpenAI/Claude)
API 비용이 무한정 늘지 않게 하는데, 단순히 오래된 순으로 처리하면 하루 안에
중요한 속보가 뒤로 밀릴 수 있어 아래 우선순위로 정렬한다(숫자가 작을수록 먼저 처리):

1. **`source_tier == 1`**(대형/공식 매체)이거나 **`quoted_reporter`가 채워진**
   기사(Fabrizio Romano 등 신뢰도 높은 기자가 인용됨)
2. **이적 루머 스레드에 속한 기사** — `rumor_threads.independent_source_count`
   (48시간 이내 교차 보도한 매체 수, `docs/DB_SCHEMA.md` 참고) 내림차순
3. **나머지는 `published_at` 최신순**

`DAILY_TRANSLATION_LIMIT`을 넘긴 기사는 버려지지 않고 `COLLECTED` 상태 그대로
남아 다음 배치(scheduler.py 기준 대개 다음날)에 우선순위대로 다시 앞에서부터
처리된다 — 자동 이월이다. "오늘 이미 몇 건 처리했는지"는 `db.count_translated_today()`
가 `translations.translated_at`을 매 실행마다 다시 세어 판단한다(scheduler.py가
30분마다 새 프로세스로 이 스크립트를 실행하므로, 메모리에 상태를 들고 있을 수 없다).

배치가 끝나면 `오늘 처리: N건, 이월: M건 (엔진: ...)` 형식으로 요약을 stdout에
남긴다 — scheduler.py를 통해 실행 중이라면 scheduler.py가 리다이렉트한 로그
파일에 그대로 남는다. 이월 건수가 `CARRYOVER_WARNING_THRESHOLD`(기본 500, 환경
변수로 조정 가능)를 넘으면 `[WARNING]` 태그와 함께 `DAILY_TRANSLATION_LIMIT` 상향
검토를 제안하는 줄이 추가로 남는다.

**알려진 상호작용**: `source_tier=1`은 최우선이라, 본문이 영구히 비어 있어 매번
실패하는 tier-1 기사(예: 만료된 Sky Sports 라이브 블로그)도 매 배치 큐 맨 앞에서
재시도된다. API 호출 전에 빈 본문 가드가 막아주므로 비용은 들지 않지만, 이런
기사가 많으면 "번역 실패" 로그 줄이 늘어나고 한도 슬롯을 일부 차지한다(실제로
확인함, 2026-09-12).

### 전처리 (번역 입력 다듬기)

- `html_cleanup.clean_for_translation()`: RSS 원문에 섞인 HTML 태그/엔티티와
  워드프레스 특유의 "The post ... appeared first on ..." 푸터를 제거한다. 이걸
  안 하면 NMT가 `<a href="...">` 안의 URL까지 "번역"하려다 훼손하는 문제가 있었다.
- `preprocessing.remove_noise()`: "Read more...", "[+123 chars]"처럼 RSS 요약에
  흔한 잡음과 과도한 줄임표를 제거한다.
- `preprocessing.split_into_translatable_chunks()` (Argos 엔진 내부에서 사용,
  `argos_engine._translate_text`): 문장이 너무 길면(기본 40단어 초과) 접속사·
  세미콜론 경계에서 쪼갠 뒤 조각별로 번역하고 다시 이어 붙인다. Argos Translate
  같은 문장 단위 NMT는 짧은 문장에서 정확도가 높다는 전제다. 쪼갤 경계를 못
  찾으면 억지로 자르지 않고 원문 그대로 둔다(단어 수 기준으로 강제로 자르면
  문맥이 끊겨 오히려 품질이 나빠지기 때문).

위 전처리는 DB에 저장된 `content_original`(원문) 자체는 건드리지 않고, 번역
직전에만 적용된다.

### 후처리 (번역 결과 다듬기)

- `glossary.apply_glossary()`: 번역 결과에 남은 영문 축구 용어(예: "Midfielder",
  "here we go")를 정해진 한국어 용어로 치환하고, Argos가 아예 다른 뜻으로
  잘못 옮긴 것으로 확인된 몇몇 표현(`KOREAN_MISTRANSLATION_FIXES`, 예:
  "transfer window"를 "전송 창"으로 오역하는 경우)도 함께 바로잡는다.
  - **버그 수정 메모**: 이 함수는 원래 `\b`(단어 경계) 정규식으로 매칭했는데,
    Python 정규식은 한글도 "단어 문자"로 취급해서 "Midfielder는"처럼 영단어
    뒤에 한국어 조사가 공백 없이 붙는 실제 번역 결과에서 경계를 인식하지
    못해 매칭에 실패하는 버그가 있었다. `(?<![A-Za-z])`/`(?![A-Za-z])` 기반
    lookaround로 바꿔 고쳤다.
- `postprocessing.clean_translation_output()`: 실제 Argos 출력에서 반복 관찰된
  어색함 몇 가지를 규칙 기반으로 정리한다 — 조사 중복("이 이"), 형용사 어미 앞
  불필요한 공백("긍정적 인" → "긍정적인"), 구두점 앞 공백, 중복 공백. 완벽한
  교정이 아니라 눈에 띄는 어색함만 줄이는 수준이다.

## 엔진 구조 (교체 가능하도록 분리됨)

- `argos_engine.py`: 기본 엔진. Argos Translate로 오프라인 번역.
- `anthropic_engine.py`: Claude(Anthropic API) 엔진. 현재 비활성 상태지만 완전히
  삭제하지 않고 보존했다. `translate.py`의 `ENGINE = "anthropic"`으로 바꾸면
  다시 쓸 수 있다(`ANTHROPIC_API_KEY` 필요).
- `openai_engine.py`: GPT(OpenAI API) 엔진. 마찬가지로 현재 비활성 상태로
  보존했다. `translate.py`의 `ENGINE = "openai"`로 바꾸면 다시 쓸 수 있다
  (`OPENAI_API_KEY` 필요). 기본 모델은 비용 효율을 고려해 `gpt-5-mini`로
  설정했다. 인증 실패/rate limit/빈 응답/JSON 파싱 실패는 모두
  `openai_engine.TranslationError`로 통일해서 던지며, `translate.py`의
  `run_translation_batch()`가 이를 잡아 해당 기사만 건너뛰고(status는
  COLLECTED로 유지, 다음 배치에서 재시도) 나머지 기사는 계속 처리한다.
- `translate.py`의 `ENGINE` 상수(또는 `TRANSLATOR_ENGINE` 환경 변수)만 바꾸면
  어느 쪽을 쓸지 전환된다. 나중에 파파고/DeepL 등 다른 상용 API로 교체하고
  싶으면 같은 인터페이스(`translate(title, content) -> (title_ko, content_ko,
  model_version)`)로 새 엔진 모듈을 하나 추가하면 된다.

## 번역 품질에 대한 솔직한 평가

Argos Translate는 문장 단위 신경망 번역(NMT)이라 Claude 같은 LLM 기반 요약
번역보다 품질이 낮을 수 있다. 전/후처리로 일부는 보정했지만, 구조적으로 규칙
기반 전/후처리로는 고치기 어려운 문제도 있다:

**전/후처리로 개선된 것:**
- 영문 축구 용어가 번역 결과에 그대로 남는 문제 (`apply_glossary` + `\b` 버그 수정)
- 몇몇 확인된 오역 패턴 ("transfer window" → "전송 창")
- 형용사 어미 앞 불필요한 공백 ("긍정적 인" → "긍정적인")
- HTML 엔티티/태그로 인한 링크 훼손, RSS 잡음("Read more...", "[+N chars]")

**여전히 남아있는 문제 (규칙 기반으로 고치기 어려움):**
- **동음이의어 오역**: 구단 별칭 "Forest"(Nottingham Forest)를 "숲"(나무)으로,
  "stance"(입장)를 "계단"으로, "outlined"(설명함)를 "비스듬한"으로 옮기는 등
  문맥을 무시하고 흔한 뜻으로 잘못 고르는 경우가 있다. 축구 용어집으로는 못
  잡는다 — 일반 단어의 문맥 의존적 오역이기 때문이다.
- **강조 표현의 의미 반전**: "massive mistake"(심각한 실수)를 "매력적인
  실수"(매력적/긍정적 뉘앙스)로 옮기는 등, 정도를 넘어 어감 자체가 반대로
  바뀌는 경우가 있다.
- 관용구·숙어를 단어별로 직역해 어색한 경우 (예: "pays tribute to" →
  "트리뷰를 지불하고"처럼 문자 그대로 옮겨지는 경우).
- 선수 이름 등 고유명사의 한글 표기가 관용적 표기와 다를 수 있다 (예: "Mo
  Salah" → "모 살라"; 흔히 쓰는 표기는 "살라"/"모하메드 살라").
- 요약 기능이 없다 — Claude 엔진과 달리 원문을 그대로 축약 없이 문장 단위로
  옮긴다. RSS가 이미 요약(summary)만 수집하므로 번역 대상 자체는 짧다.

이런 이유로 번역 결과를 무조건 저장하지 않고, 위와 같은 심각한 오역이 보이는
기사는 저장을 보류하고 있다(수동 검수 필요). 번역 품질이 더 중요해지는
시점에는 위 "엔진 구조"대로 상용 API로 교체하면 된다.

## 파일 구성

- `translate.py`: 미번역 기사를 조회해 번역하는 메인 로직 (엔진 선택 + 우선순위 큐 + DB 배치 처리)
- `priority.py`: 하루 한도를 넘긴 COLLECTED 기사 중 무엇을 먼저 처리할지 정하는
  우선순위 정렬 로직(`sort_by_priority`) — 위 "우선순위 큐" 참고
- `argos_engine.py`: Argos Translate 기반 번역 엔진 (기본)
- `anthropic_engine.py`: Claude(Anthropic API) 기반 번역 엔진 (현재 비활성, 보존용)
- `openai_engine.py`: GPT(OpenAI API) 기반 번역 엔진 (현재 비활성, 보존용)
- `setup_argos_model.py`: en->ko Argos Translate 모델을 다운로드/설치하는 1회성 스크립트
- `html_cleanup.py`: 번역 직전에 RSS 원문의 HTML 태그/엔티티/워드프레스 푸터를 정리
- `preprocessing.py`: RSS 잡음 제거(`remove_noise`)와 긴 문장 분할
  (`split_into_translatable_chunks`) — 번역 입력을 다듬는 전처리
- `postprocessing.py`: 번역 결과에 흔히 남는 어색함(조사 중복, 어색한 띄어쓰기 등)을
  규칙 기반으로 정리하는 후처리(`clean_translation_output`)
- `glossary.py`: 축구 용어 일관성을 위한 용어집. LLM 프롬프트 삽입(`build_glossary_prompt`),
  번역 결과 후처리 치환(`apply_glossary`), 확인된 오역 패턴 교정
  (`KOREAN_MISTRANSLATION_FIXES`) 세 가지를 제공한다
- `db.py`: 미번역 기사 조회 및 번역 결과 저장 (backend와 동일한 DB 스키마 사용)
- `tests/`: 단위/통합 테스트 (Argos/Claude/GPT 호출 모두 mock 처리, DB 로직은 in-memory DB로 검증)
