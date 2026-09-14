"""주기적으로 뉴스 수집 + 번역을 실행하는 스케줄러."""

import logging
import logging.handlers
import os
import subprocess

from apscheduler.schedulers.blocking import BlockingScheduler

import db
from rss_collector import collect_from_rss
from sources import RSS_SOURCES, CRAWL_SOURCES

# translator/는 collector/와 별도 모듈이다(각자 dependencies와 db.py를 따로 관리하며,
# 두 db.py 모두 "db"라는 같은 이름이라 같은 프로세스로 import하면 충돌한다). 그래서
# 같은 프로세스에서 import하는 대신 translate.py를 별도 파이썬 프로세스로 실행한다
# (translate.py의 `if __name__ == "__main__":`이 run_translation_batch()를 그대로 호출함).
_TRANSLATOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "translator")

# Task Scheduler로 백그라운드 실행하면 콘솔이 없어 stdout만으로는 "잘 돌고 있는지"
# 확인할 방법이 없다. collector/logs/scheduler.log에 자정마다 회전 저장(최근 30일치
# 보관)하고, 콘솔에도 그대로 출력한다(수동 실행 시 기존과 동일하게 눈으로 확인 가능).
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    _file_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(_LOG_DIR, "scheduler.log"), when="midnight", backupCount=30, encoding="utf-8"
    )
    _file_handler.setFormatter(_formatter)
    _console_handler = logging.StreamHandler()
    _console_handler.setFormatter(_formatter)
    logger.addHandler(_file_handler)
    logger.addHandler(_console_handler)


def run_collection_job():
    logger.info("수집 시작")
    all_articles = []

    for source in RSS_SOURCES:
        articles = collect_from_rss(
            source["name"],
            source["rss_url"],
            forced_club=source.get("forced_club"),
            source_tier=source.get("source_tier"),
        )
        all_articles.extend(articles)

    # CRAWL_SOURCES는 현재 등록된 소스가 없다 (sources.py 참고).
    # 크롤링 대상이 추가되면 crawler.crawl_article_list/crawl_article_detail을
    # 사용해 같은 방식으로 all_articles에 합류시킨다.
    if CRAWL_SOURCES:
        logger.info(f"CRAWL_SOURCES 처리 로직이 아직 없습니다: {len(CRAWL_SOURCES)}개 소스 건너뜀")

    engine = db.get_engine()
    saved_count = db.save_articles(engine, all_articles)

    logger.info(f"수집 완료: 조회 {len(all_articles)}건, 신규 저장 {saved_count}건")
    return all_articles


def run_translation_job():
    """방금 수집된 신규 기사를 바로 번역한다.

    번역 엔진은 TRANSLATOR_ENGINE 환경 변수를 그대로 물려받되, 지정돼 있지 않으면
    "openai"를 기본값으로 쓴다 — translate.py 자체 기본값(argos)은 이 환경에
    오프라인 모델이 설치돼 있지 않아 실제로 동작하지 않기 때문이다
    (docs/FEATURE_STATUS.md 11번 참고). 번역 배치가 실패해도(네트워크 오류,
    API 키 누락 등) 예외를 다시 던지지 않는다 — 다음 30분 주기에 재시도되므로
    수집 스케줄러 자체가 멈추면 안 된다.
    """
    env = {**os.environ, "TRANSLATOR_ENGINE": os.environ.get("TRANSLATOR_ENGINE", "openai")}

    logger.info("번역 배치 시작")
    result = subprocess.run(
        ["python", "translate.py"],
        cwd=_TRANSLATOR_DIR,
        env=env,
        capture_output=True,
        text=True,
        # translate.py의 한글 출력은 UTF-8로 쓰인다(자식 프로세스가 PYTHONIOENCODING을
        # 상속받음). encoding을 지정하지 않으면 text=True가 시스템 기본 코드페이지로
        # 디코딩을 시도하는데, 한국어 Windows의 기본 cp949는 UTF-8 바이트를 못 읽어
        # UnicodeDecodeError가 난다(실제로 스케줄러 운영 중 발생 확인).
        encoding="utf-8",
    )

    if result.stdout:
        logger.info(result.stdout.strip())
    if result.returncode != 0:
        logger.error(f"번역 배치 실행 실패(exit code {result.returncode}): {result.stderr.strip()}")
    else:
        logger.info("번역 배치 완료")


def run_collection_and_translation_job():
    """수집 직후 바로 번역까지 이어서 실행한다 (30분 주기, scheduler.py의 기본 잡).

    APScheduler는 잡 안에서 발생한 예외를 스케줄러 자체 로거로만 남기고 우리
    scheduler.log에는 남기지 않는다 — "에러가 있었다면 무엇인지"가 로그에 남아야
    하므로 여기서 직접 잡아 logger.exception()으로 기록하고, 다음 30분 주기가
    이어서 돌 수 있게 삼킨다(수집/번역 각자 내부에서도 이미 실패를 흡수하지만,
    예상 못 한 예외에 대한 마지막 안전망이다).
    """
    try:
        run_collection_job()
        run_translation_job()
    except Exception:
        logger.exception("수집+번역 배치 중 예기치 못한 오류 발생")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(run_collection_and_translation_job, "interval", minutes=30)

    logger.info("수집+번역 스케줄러 시작 (30분 간격)")
    run_collection_and_translation_job()  # 시작 시 1회 즉시 실행
    scheduler.start()
