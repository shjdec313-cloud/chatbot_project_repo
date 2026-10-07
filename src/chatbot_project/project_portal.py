"""산출물 핵심 요약. 모든 자료는 앱과 함께 배포되는 파일에서 읽습니다."""
import csv
import json
from collections import Counter
from pathlib import Path

import streamlit as st

from portal_charts import COLORS, OUTCOMES, CATEGORIES, base_spec, category_spec, evaluation_groups, retrieval_groups, retrieval_spec
from portal_theme import hero, note, steps

ASSETS = Path(__file__).resolve().parent / "project_assets"
PAGES = ["프로젝트 한눈에", "매뉴얼 질문하기", "01 데이터·전처리", "02 데이터 분석", "03 검색·답변 구조", "04 검색 품질 평가"]


@st.cache_data(show_spinner=False)
def _json_file(name, modified):
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def data(name):
    path = ASSETS / name
    return _json_file(name, path.stat().st_mtime_ns)


@st.cache_data(show_spinner=False)
def _csv_file(name, modified):
    with (ASSETS / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def table(name):
    path = ASSETS / name
    return _csv_file(name, path.stat().st_mtime_ns)


@st.cache_data(show_spinner=False)
def _bytes_file(name, modified):
    return (ASSETS / name).read_bytes()


def download(name, label, mime="application/zip", key=None):
    path = ASSETS / name
    st.download_button(label, _bytes_file(name, path.stat().st_mtime_ns), file_name=path.name,
                       mime=mime, key=key or "download_" + name, width="stretch")


def metrics(items):
    for column, (title, value, help_text) in zip(st.columns(len(items)), items):
        column.metric(title, value, help=help_text)


def chart(spec, key):
    st.vega_lite_chart(spec=spec, theme=None, width="stretch", key=key)


def render_overview():
    hero("PROJECT NOTEBOOK", "매뉴얼이 답변이 되기까지", "매뉴얼을 검색 가능한 데이터로 만들고, 실제 질문으로 답변 품질을 확인한 과정을 네 단계로 정리했습니다.")
    metrics([("매뉴얼 조각", "1,874개", "질문과 관련 있는 본문을 찾기 위해 나눈 단위입니다."),
             ("분석한 장", "11개", "원본 매뉴얼의 장 구성입니다."),
             ("실제 평가", "30개", "2026년 10월 2일에 완료한 초기 평가 기록입니다.")])
    st.subheader("처음 보신다면, 이 순서로 읽어보세요")
    steps([("01 · 데이터·전처리", "PDF에서 글과 목차를 읽고, 검색에 필요한 크기로 나누었습니다."),
           ("02 · 데이터 분석", "데이터의 길이·중복·특징 단어를 살펴보았습니다."),
           ("03 · 검색·답변 구조", "질문에 가까운 글을 팀 DB에서 찾고, 그 글을 근거로 답합니다."),
           ("04 · 검색 품질 평가", "30개 질문의 실제 답변을 기준과 비교해 개선할 지점을 찾았습니다.")])
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("### 앱이 하는 일")
        st.write("질문과 관련 있는 매뉴얼 내용을 찾고, 출처 번호를 붙여 설명합니다. 답변의 번호를 검색 근거와 비교할 수 있습니다.")
    with right, st.container(border=True):
        st.markdown("### 자료를 읽는 방법")
        st.write("화면에는 핵심 결과를 먼저 보여줍니다. 세부 기준과 기록은 펼쳐 보고, 전체 제출 자료는 각 단계에서 내려받으세요.")
    note("매뉴얼 본문 검색에 이미지 연결과 제목·키워드 검색을 순서대로 추가했습니다. 개별 차량의 실시간 진단이나 충전소의 현재 빈자리를 확인하는 서비스는 아닙니다.")
    with st.container(border=True):
        st.subheader("검색과 답변을 어떻게 개선했나요?")
        steps([("초기 · 텍스트 벡터 검색", "30개를 평가해 기준선으로 남겼습니다. 통과 24개, 부분 통과 5개, 실패 1개입니다."),
               ("1차 · 매뉴얼 이미지 연결", "이미지 표시 버전의 30개 결과를 비교했습니다. 통과는 25개지만 검색 순위는 같았습니다."),
               ("2차 · 제목·키워드 검색 추가", "30개를 재평가했습니다. 답변 충족 25개, 근거 확보 22/23개이며 일부 질문은 회귀했습니다.")])
        st.caption("3단계에서 수정 내용을, 4단계에서 비교 근거와 확인 범위를 읽어보세요.")


def render_stage1():
    profile = data("dataset_profile.json")
    hero("01 / DATA & PREPROCESSING", "긴 매뉴얼을 작은 검색 단위로", "청크는 검색을 위해 나눈 글 조각입니다. 본문과 함께 제목·페이지 정보를 남겨, 답변의 출처를 찾을 수 있게 했습니다.")
    metrics([("전체 청크", f"{profile['rows']:,}개", "본문을 저장한 행 수입니다."),
             ("청크 길이 목표", "450토큰", "토큰은 모델이 글을 처리하는 작은 단위입니다. 단어 수와 같지는 않습니다."),
             ("이웃 청크의 겹침", "약 80토큰", "경계에서 내용이 끊기는 영향을 줄이기 위해 앞뒤 조각이 일부 내용을 공유합니다.")])
    st.subheader("어떻게 만들었나요?")
    steps([("PDF의 글과 목차를 읽습니다", "페이지의 텍스트와 장·절·소제목의 위치를 가져옵니다."),
           ("공백과 줄바꿈을 정리합니다", "과도한 공백과 빈 줄을 줄입니다. 원문을 새로 쓰거나 의미를 바꾸는 작업은 아닙니다."),
           ("목차 범위별로 글을 나눕니다", "장·절·하위 항목을 각각 처리하고, 긴 글은 길이 목표에 맞춰 분할합니다."),
           ("출처 정보를 붙입니다", "청크 ID, 제목, 목차, 페이지 범위를 함께 보관합니다."),
           ("검색용 입력을 준비합니다", "본문에 목차 정보를 더하고 passage:를 붙입니다. 최종 입력은 510토큰 기준으로 제한합니다.")])
    note("페이지 범위는 청크를 만든 목차 항목의 범위입니다. 청크 한 조각의 정확한 출처 페이지를 뜻하지는 않습니다.")
    with st.expander("데이터 한 행은 어떻게 생겼나요?"):
        sample = profile["samples"][0]
        st.caption(f"{sample['chunk_id']} · {sample['source_title']} · PDF {sample['page_start']}~{sample['page_end']}쪽")
        st.write(sample["chunk_text"])
        st.caption("예시 본문은 일부만 표시합니다. 전체 내용은 데이터셋 다운로드에 있습니다.")
    with st.expander("컬럼·자료형·빈칸을 확인하고 싶어요"):
        st.dataframe(profile["columns"], hide_index=True, width="stretch")
        st.write("절(section)과 하위 항목(subsection)의 빈칸에는 해당 목차가 없는 경우가 포함됩니다. 임의의 제목으로 채우지 않았습니다.")
        st.caption("분석 CSV는 14컬럼입니다. DB 본문 테이블은 검색 입력용 3컬럼을 제외한 11컬럼입니다.")
    with st.expander("청킹에서 알아둘 점"):
        st.write("상위 목차와 하위 목차의 원문 범위가 겹칠 수 있습니다. 일부 같은 본문이 다른 제목·출처 정보를 가진 청크로 만들어졌습니다.")
        st.write("450토큰은 목표값입니다. 실제 저장값은 최대 452토큰이며, 450을 넘는 행이 36개 있습니다. 이 단계는 초기 텍스트 전처리 기록입니다. 이후 이미지 연결과 검색 방식 변경은 3·4단계의 개선 기록에서 설명합니다.")
    st.subheader("전체 자료")
    download("downloads/stage1_data_preprocessing.zip", "데이터셋·데이터 명세·전처리 설명 내려받기")


def render_stage2():
    profile = data("dataset_profile.json")
    hero("02 / DATA EXPLORATION", "무엇이 많이 들어 있고, 어디를 살펴봐야 할까요?", "EDA는 데이터를 먼저 살펴보는 작업입니다. 여기서는 장별 분량, 글의 길이, 반복된 본문과 특징 단어를 확인했습니다.")
    metrics([("서로 다른 본문", "1,542개", "완전히 같은 글은 한 번만 센 값입니다."),
             ("중복 추가 행", "332개", "1,874행 중 동일 본문이 추가로 등장한 행입니다. 중복 그룹에 속한 전체 행은 553개입니다."),
             ("본문 길이 중앙값", "444토큰", "길이를 순서대로 놓았을 때 가운데 값입니다.")])
    with st.container(border=True):
        st.subheader("어느 장에서 청크가 많이 만들어졌나요?")
        values = [{"장": r["chapter"], "청크 수": int(r["chunks"]), "목차 항목": int(r["source_units"])} for r in table("analysis/chapter_statistics.csv")]
        spec = base_spec(values, 350)
        spec.update(mark={"type": "bar", "color": "#168269", "cornerRadiusEnd": 3}, encoding={
            "y": {"field": "장", "type": "nominal", "sort": "-x", "title": None, "axis": {"labelLimit": 180}},
            "x": {"field": "청크 수", "type": "quantitative", "title": "청크 수 (개)"},
            "tooltip": [{"field": "장"}, {"field": "청크 수"}, {"field": "목차 항목"}]})
        chart(spec, "chapter_chart")
        st.caption("편의 장치 411개, 운전자 보조 394개가 많습니다. 청크 수가 많다는 것이 사용자 질문이나 중요도가 더 높다는 뜻은 아닙니다.")
    with st.container(border=True):
        st.subheader("청크 길이는 어느 정도인가요?")
        spec = base_spec(profile["length_histogram"], 200)
        spec.update(mark={"type": "bar", "color": "#71a99a", "cornerRadiusTopLeft": 2, "cornerRadiusTopRight": 2},
                    encoding={"x": {"field": "start", "type": "quantitative", "title": "본문 길이 (토큰)", "bin": "binned"},
                              "x2": {"field": "end"}, "y": {"field": "count", "type": "quantitative", "title": "청크 수 (개)"},
                              "tooltip": [{"field": "start", "title": "구간 시작"}, {"field": "end", "title": "구간 끝 (미만)"}, {"field": "count", "title": "청크 수"}]})
        chart(spec, "length_chart")
        st.caption("많은 청크가 길이 목표에 가깝습니다. 저장된 토큰 수를 사용한 분석이며 모델을 다시 실행한 결과는 아닙니다.")
    with st.container(border=True):
        st.subheader("반복된 글은 바로 삭제하면 될까요?")
        st.write("같은 글에도 목차 정보가 다르게 붙을 수 있습니다. 본문이 같다는 이유만으로 삭제하기 전에, 실제 검색에서 같은 내용이 반복해서 나오는지 확인해야 합니다.")
        note("중복을 줄이면 검색이 반드시 좋아진다는 결론은 아직 없습니다. EDA의 관찰은 다음 검색 실험의 출발점입니다.")
    with st.expander("통계 검정 결과를 쉽게 읽어보기"):
        st.markdown("**장별 길이 차이**: 장에 따라 길이 분포가 다른 신호가 있지만 효과크기는 0.0348로 작습니다. 어느 두 장이 다른지는 이 검정만으로 정하지 않았습니다.")
        st.markdown("**페이지 범위와 청크 수**: 넓은 목차 범위에서 청크가 많이 만들어지는 경향이 있었습니다. 순위상관은 0.7496입니다. 검색이 더 정확하다는 뜻은 아닙니다.")
        st.caption("506개 목차 항목을 분석했습니다. 원문 범위가 겹칠 수 있어 확정적 결론보다 탐색적 진단으로 읽어야 합니다.")
        st.dataframe(table("analysis/statistical_tests.csv"), hide_index=True, width="stretch")
    with st.expander("TF-IDF: 각 장을 특징짓는 단어"):
        keywords = table("analysis/tfidf_chapter_keywords.csv")
        chapter = st.selectbox("살펴볼 장", list(dict.fromkeys(r["chapter"] for r in keywords)), key="tfidf_chapter")
        selected = [{"단어": r["term"], "평균 TF-IDF": round(float(r["mean_tfidf"]), 4)} for r in keywords if r["chapter"] == chapter][:10]
        st.write("자주 등장하면서 다른 글과 구별되는 단어를 찾아보는 방법입니다. 단어 점수는 정답률이 아닙니다.")
        st.dataframe(selected, hide_index=True, width="stretch")
    st.subheader("전체 자료")
    download("downloads/stage2_analysis.zip", "실행된 노트북·분석 보고서·상세 표 내려받기")


def render_stage3():
    audit = data("logs/dump_audit.json")
    hero("03 / RETRIEVAL & ANSWERING", "의미와 단어를 함께 찾아, 근거로 답합니다", "초기 벡터 검색에서 시작해 이미지 연결, 제목·키워드 검색을 추가했습니다. 기존 저장 데이터와 개선한 검색 경로를 구분해 설명합니다.")
    metrics([("저장된 본문", f"{audit['chunk_rows']:,}개", "제공된 덤프 파일을 확인한 값입니다."),
             ("저장된 임베딩", f"{audit['embedding_rows']:,}개", "본문과 같은 ID로 연결되는 숫자 벡터입니다."),
             ("벡터 길이", "768개 숫자", "문서와 질문을 같은 모델로 바꿔 의미를 비교합니다.")])
    store, ask = st.tabs(["기존 데이터 저장 과정", "초기 벡터 검색 과정"])
    with store:
        steps([("청크에 검색용 목차 정보를 더합니다", "제목과 본문을 묶어 passage:로 시작하는 입력을 만듭니다."),
               ("E5 모델로 숫자 벡터를 만듭니다", "문서의 의미를 비교할 수 있도록 768개의 숫자로 바꿉니다."),
               ("본문과 벡터를 따로 저장합니다", "casper_manual_chunks와 casper_manual_embeddings를 같은 chunk_id로 연결합니다."),
               ("개인 DB에서 팀 DB로 옮겼습니다", "기존 본문과 이미 만든 벡터를 함께 이관했습니다. 이관을 위해 임베딩을 다시 만들지는 않았습니다.")])
    with ask:
        steps([("질문을 같은 모델로 바꿉니다", "query:를 붙인 질문도 768개의 숫자로 표현합니다."),
               ("팀 DB에서 가까운 벡터를 찾습니다", "검색 함수 match_manual_chunks가 같은 모델·버전의 벡터를 비교합니다."),
               ("관련 본문과 출처를 가져옵니다", "기본 설정은 상위 5개입니다. 유사도는 정답 확률이 아닙니다."),
               ("LLM이 근거를 읽고 설명합니다", "근거 번호를 표시하고, 근거가 부족하면 확인할 수 없다고 답하도록 안내합니다.")])
    with st.expander("적재와 이관 기록은 어디까지 확인했나요?"):
        st.write("이전 노트북에는 개인 DB의 본문·임베딩 적재가 각각 1,874/1,874까지 진행된 출력이 남아 있습니다.")
        st.write("제공된 개인·팀 덤프 파일의 본문과 벡터 내용은 서로 일치했습니다. 본문과 벡터 사이에 연결되지 않은 행은 0개였습니다.")
        st.write("팀 DB 복원 완료와 연결 변경은 사용자가 확인한 기록입니다. 덤프 검사는 로컬 파일 검사이며 현재 DB 상태를 실시간으로 조회한 값은 아닙니다.")
        st.dataframe([{"확인 항목": "본문 행 수", "결과": str(audit['chunk_rows'])},
                      {"확인 항목": "임베딩 행 수", "결과": str(audit['embedding_rows'])},
                      {"확인 항목": "연결되지 않은 행", "결과": "0"},
                      {"확인 항목": "개인·팀 데이터 내용 일치", "결과": "일치"}], hide_index=True, width="stretch")
    with st.expander("검색 함수와 코드가 궁금해요"):
        st.write("아래는 초기 벡터 검색 함수입니다. 새 함수는 제목·본문의 단어 검색을 함께 수행하며 아래 개선 기록에서 볼 수 있습니다. ReAct나 질문 분해는 추가하지 않았습니다.")
        sql_path = ASSETS / "code/match_manual_chunks.sql"
        st.code(sql_path.read_text(encoding="utf-8"), language="sql")
    render_search_changes()
    st.subheader("전체 자료")
    download("downloads/stage3_code_logs.zip", "초기 인덱싱·RAG 코드·SQL·적재 기록 내려받기")
    download("downloads/search_improvements.zip", "개선 기록·수정 검색 함수·rag.py 내려받기")


def render_search_changes():
    changes = data("search_improvements.json")
    st.subheader("개선 기록 · 무엇을 바꾸었나요?")
    first, second = st.tabs(["1차 · 이미지 연결", "2차 · 제목·키워드 검색"])
    with first:
        st.write("텍스트 청크와 관련 그림을 연결해, 검색한 본문의 이미지 설명과 원본 그림을 사용할 수 있게 했습니다.")
        steps([("이미지를 별도로 저장합니다", "원본 그림 파일은 Supabase Storage에, 페이지·설명·OCR 등은 이미지 테이블에 저장합니다."),
               ("청크와 그림을 연결합니다", "연결 테이블 casper_manual_chunk_images로 한 청크의 여러 그림과 여러 청크에서 사용하는 그림을 연결합니다."),
               ("검색한 청크의 관련 그림을 읽습니다", "rag.py가 이미지 설명·OCR을 근거에 더하고, 선택한 실제 그림도 답변 모델에 보낼 수 있도록 수정했습니다.")])
        note("이미지 자체의 임베딩을 따로 검색하는 구조는 아닙니다. 먼저 텍스트 청크를 찾고 연결된 이미지를 가져옵니다. 관련 청크를 못 찾으면 그림도 빠질 수 있습니다.")
        st.caption("1차 30개 비교 때 실제 그림 전달은 미검증이었습니다. 2차 평가에서는 29/30개 질문에 실제 그림 전달 메시지를 관찰했습니다. 서버 요청 자체를 독립 확인한 것은 아닙니다.")
    with second:
        st.write("‘차량 제원’이나 ‘축거’가 본문에 있어도 벡터 유사도 상위에 들지 못하는 사례가 있었습니다. 의미 검색에 실제 단어 검색을 함께 사용하도록 바꾸었습니다.")
        steps([("질문의 원문을 임베딩합니다", "E5에 query: 접두사를 붙입니다. 질문을 LLM으로 다시 작성하지 않습니다."),
               ("검색 단어를 추출합니다", "‘크로스의 축거를 알려줘’에서 크로스·축거를 뽑습니다. 일부 조사와 불필요한 표현만 규칙으로 처리합니다."),
               ("두 경로에서 후보를 모읍니다", "match_manual_chunks_hybrid가 벡터 후보와 제목·본문 단어 후보를 기본 50개씩 찾습니다."),
               ("두 검색 순위를 합칩니다", "제목 일치와 드문 단어에 가중치를 주고, 두 후보 목록의 순위를 결합해 상위 5개를 선택합니다."),
               ("본문과 연결 그림으로 답합니다", "검색된 청크의 이미지 조회와 실제 이미지 전달 흐름은 유지했습니다.")])
        st.dataframe(changes["modifications"], hide_index=True, width="stretch")
        note("표 전처리·청킹·임베딩을 다시 만든 변경은 아닙니다. 표의 행·열 관계가 잘못 추출된 문제는 별도로 점검해야 합니다.")
        with st.expander("점수와 검색 근거를 읽는 법"):
            st.write("similarity는 이전과 같은 코사인 유사도이며 정답 확률이 아닙니다. 최종 순위는 hybrid_score로 결정하므로 유사도가 더 낮은 청크가 먼저 나올 수 있습니다.")
            st.write("vector_rank·keyword_rank는 각 후보 목록의 순위이고, matched_terms는 발견한 단어입니다. 제목에 같은 단어가 있다고 무조건 정답을 포함하는 것은 아닙니다.")
            st.caption("초기 가중치는 벡터 1, 키워드 2, 순위 상수 20입니다. 30개 재평가로 최적화한 값은 아닙니다. 문자열 포함 검색이며 완전한 한국어 형태소 분석은 아닙니다.")
        with st.expander("새 SQL과 개인·팀 DB 적용 상태"):
            st.write("사용자는 개인 DB의 manual_chunks·manual_embeddings에 함수를 적용하고 rag.py도 적용했다고 확인했습니다. 팀 DB 적용 완료는 이번 기록에서 확인하지 않았습니다.")
            st.write("vector 확장이 extensions에 있는 DB용 SQL입니다. 다른 DB에서는 테이블명과 확장 스키마를 먼저 확인해야 합니다.")
            choice = st.radio("SQL 대상", ["개인 DB", "팀 DB"], horizontal=True, key="hybrid_sql_target")
            filename = "match_manual_chunks_hybrid_personal.sql" if choice == "개인 DB" else "match_manual_chunks_hybrid.sql"
            st.code((ASSETS / "code" / filename).read_text(encoding="utf-8"), language="sql")


def render_stage4():
    hero("04 / QUALITY REVIEW", "초기 결과와 개선 결과를 나란히 봅니다", "같은 30개 질문의 초기·1차·2차 실제 기록을 비교합니다. 잘된 사례와 회귀, 별도 제원 질문 3개를 구분해 보여줍니다.")
    initial, image, hybrid = st.tabs(["초기 · 30개 평가", "1차 · 이미지 추가 비교", "2차 · 30개 검색 개선 평가"])
    with initial:
        render_baseline_evaluation()
    with image:
        render_image_comparison()
    with hybrid:
        render_hybrid_comparison()


def render_image_comparison():
    report = data("image_comparison.json")
    before, after = report["before_summary"], report["after_summary"]
    st.subheader("같은 30개 질문 · 이미지 표시 버전과 비교")
    st.dataframe([
        {"항목": "답변 통과", "초기": "24 / 30", "이미지 표시 버전": "25 / 30"},
        {"항목": "부분 통과", "초기": "5개", "이미지 표시 버전": "4개"},
        {"항목": "실패", "초기": "1개", "이미지 표시 버전": "1개"},
        {"항목": "정답 근거 확보 Hit@5", "초기": "20 / 23", "이미지 표시 버전": "20 / 23"},
        {"항목": "필수 사실 근거 확보", "초기": "46 / 50", "이미지 표시 버전": "46 / 50"},
    ], hide_index=True, width="stretch")
    metrics([("그림이 표시된 질문", f"{after['image_display_case_count']} / 30", "이미지 표시가 있었다는 뜻이며 모두 질문과 직접 관련됐다는 뜻은 아닙니다."),
             ("검색 순서가 같았던 질문", f"{after['same_retrieved_chunk_order_case_count']} / 30", "초기와 1차의 상위 5개 청크 ID와 순서가 같았습니다.")])
    st.write("Q003은 부분 통과에서 통과로 바뀌었지만 그 질문에는 이미지가 표시되지 않았습니다. 따라서 이 변화가 이미지 추가 때문에 발생했다고 단정할 수 없습니다.")
    note("1차 비교는 서로 다른 시점의 배포 앱 관찰입니다. 기능만 켜고 끈 통제 실험이 아니고, 실제 이미지 픽셀의 LLM 전달은 당시 서버 요청을 확인하지 않아 미검증이었습니다.")
    with st.expander("질문별 변화와 이미지의 관련성"):
        labels = {"direct": "직접 도움", "context": "주변 맥락", "unrelated": "관련 낮음", "none": "그림 없음"}
        st.dataframe([{"번호": c["test_id"], "질문": c["question"], "초기": OUTCOMES[c["before"]], "1차": OUTCOMES[c["after"]], "표시 그림": c["displayed_image_count"], "탐색적 관련성": labels[c["image_case_grade"]]} for c in report["cases"]], hide_index=True, width="stretch")
        st.caption("기존 30개는 텍스트 평가용으로 만들었습니다. 이미지 정답 목록을 미리 고정하지 않아 관련성 평가는 탐색적이며 이미지 검색 재현율은 계산하지 않았습니다.")
    download("downloads/image_comparison.zip", "1차 비교 상세 페이지·실행 기록 내려받기")


def render_hybrid_comparison():
    comparison = data("hybrid_comparison.json")
    result = data("hybrid_results.json")
    versions = comparison["versions"]
    latest = result["summary"]
    st.subheader("같은 30개 · 초기·1차·2차 비교")
    st.write("2차는 벡터 검색에 제목·본문 단어 검색을 더했습니다. 정답 근거를 더 찾았지만, 답변의 누락과 회귀도 남았습니다.")
    metrics([("2차 답변 충족", f"{latest['overall_counts']['pass']} / 30", "고정 내용·기대 행동을 모두 충족한 질문"),
             ("정답 근거 하나 이상", f"{latest['retrieval_hit_count']} / 23", "Hit@5. 일부 근거만 있어도 성공이므로 완전성도 함께 봅니다."),
             ("필수 근거 확보", f"{latest['covered_facts']} / {latest['total_facts']}", "50개 필수 내용 각각의 근거 유무")])
    values = [{"버전": v["label"], "판정": OUTCOMES[k], "질문 수": v["summary"]["overall_counts"].get(k, 0), "순서": n}
              for v in versions for n, k in enumerate(OUTCOMES)]
    spec = base_spec(values)
    spec["mark"] = {"type": "bar", "height": 38, "cornerRadius": 3}
    spec["encoding"] = {"y": {"field": "버전", "type": "nominal", "sort": [v["label"] for v in versions], "title": None},
                        "x": {"field": "질문 수", "type": "quantitative", "stack": "zero", "scale": {"domain": [0, 30]}, "title": "질문 수"},
                        "color": {"field": "판정", "type": "nominal", "scale": {"domain": list(COLORS), "range": list(COLORS.values())}},
                        "order": {"field": "순서"}, "tooltip": [{"field": "버전"}, {"field": "판정"}, {"field": "질문 수"}]}
    chart(spec, "three_version_outcomes")
    st.dataframe([{"버전": v["label"], "충족": v["summary"]["overall_counts"].get("pass", 0),
                   "부분": v["summary"]["overall_counts"].get("partial", 0), "미충족": v["summary"]["overall_counts"].get("fail", 0),
                   "근거 Hit@5": f"{v['summary']['retrieval_hit_count']} / 23", "필수 근거": f"{v['summary']['covered_facts']} / 50",
                   "평균 앱 처리 시간": f"{v['summary']['mean_app_elapsed_seconds']:.2f}초"} for v in versions], hide_index=True, width="stretch")
    st.info(comparison["conclusion"])
    steps([("Q005·Q018 · 필요한 근거를 찾았습니다", "충전 표시 시간과 안전벨트 위치·느슨함을 답했습니다. 제원 질문 3개도 별도로 확인했습니다."),
           ("Q025·Q027 · 검색 누락이 남았습니다", "LKA에 후보가 편중되어 LFA 답을 놓쳤고, 스마트키 오타 질문은 규격·개수를 모두 놓쳤습니다."),
           ("Q019·Q028 · 답변 행동도 보완해야 합니다", "진단 안내 또는 상황을 되묻는 행동이 빠졌습니다. 검색 함수만 바꿔 해결되는 문제는 아닙니다.")])
    with st.expander("30개 질문의 판정 변화"):
        st.dataframe([{"번호": c["test_id"], "질문": c["question"], "초기": OUTCOMES[c["initial"]], "1차": OUTCOMES[c["phase1"]],
                       "2차": OUTCOMES[c["phase2"]], "이유": c["notes"]} for c in comparison["cases"]], hide_index=True, width="stretch")
    ids = [r["test_id"] for r in result["results"]]
    chosen = st.selectbox("2차 실제 답변 살펴보기", ids, index=ids.index("Q025"), key="hybrid_case_select")
    r = next(r for r in result["results"] if r["test_id"] == chosen)
    st.markdown(f"**{r['question']}**")
    st.markdown(r["answer"])
    st.caption(r["review"]["notes"])
    with st.expander("검색된 본문 5개"):
        for s in r["retrieved_sources"]:
            st.markdown(f"**[{s['rank']}] {s['source_title']}**")
            st.caption(f"PDF {s['page_start']}~{s['page_end']}쪽 · 유사도 {s['similarity']:.4f}")
            st.write(s["chunk_text"])
    with st.expander("추가 제원 질문 3개 · 30개 점수에서 제외"):
        for r in result["supplementary_results"]:
            st.markdown(f"**{r['question']}**")
            st.markdown(r["answer"])
        st.caption("동일한 개선 전 실행 기록은 없고, 이전 실패는 사용자 보고입니다. 이번 답변은 PDF 63쪽 표의 크기·선택 사양·축거와 대조했습니다.")
    with st.expander("평가 방법과 해석 범위"):
        for text in result["metadata"]["limitations"]:
            st.write(text)
    download("downloads/hybrid_comparison.zip", "초기·1차·2차 비교 페이지·전체 실행 기록 내려받기", key="hybrid_comparison_download")
    download("downloads/casper_eval30_pdfs.zip", "30문항 평가지·초기 채점 기록 PDF 내려받기", key="hybrid_baseline_pdf")


def render_baseline_evaluation():
    dataset, results = data("evaluation_dataset.json"), data("evaluation_results.json")
    rows = results["results"]
    counts = Counter(r["review"]["overall_result"] for r in rows)
    scored = [r for r in rows if r["review"]["retrieval_hit_at_5"] is not None]
    hits = sum(r["review"]["retrieval_hit_at_5"] for r in scored)
    st.subheader("초기 평가 · 2026년 10월 2일")
    st.caption("이미지 추가와 하이브리드 검색 개선 전의 고정 기록입니다. 기존 30개 질문·정답 기준·판정을 유지했습니다.")
    metrics([("실제 실행", f"{len(rows)}개", "각 질문을 한 번씩 실행한 초기 평가입니다."),
             ("답변 기준 충족", f"{counts['pass']} / {len(rows)}", "부분 충족 5개와 미충족 1개는 포함하지 않습니다."),
             ("정답 근거 확보", f"{hits} / {len(scored)}", "답할 수 있는 질문 23개 중, 정답 근거를 하나 이상 찾은 질문입니다.")])
    with st.container(border=True):
        st.subheader("질문 유형에 따라 답변 결과가 달랐나요?")
        st.write("정상 질문은 매뉴얼에 답이 있는 질문, 답할 수 없는 질문은 실시간·개인 정보 등을 요구한 질문입니다. 경계 사례는 오타·모호함·비슷한 기능처럼 헷갈리기 쉬운 질문입니다.")
        mode = st.radio("그래프 표시", ["질문 수", "유형 안의 비율"], horizontal=True, key="evaluation_chart_mode")
        chart(category_spec(evaluation_groups(dataset, results), mode != "질문 수"), "evaluation_by_category")
        st.caption("정상 질문 18개 · 답할 수 없는 질문 6개 · 경계 사례 6개. 서로 다른 개수의 그룹을 비교할 때는 비율도 함께 보세요.")
        note("답할 수 없는 질문 6개는 모두 정보를 지어내지 않았습니다. 여기서의 ‘충족’은 답변 거절 또는 확인 불가 안내가 적절했다는 뜻입니다.")
    with st.container(border=True):
        st.subheader("검색을 못 했나요, 답변에서 빠뜨렸나요?")
        values, excluded = retrieval_groups(results)
        chart(retrieval_spec(values), "retrieval_vs_answer")
        st.caption("매뉴얼 근거가 있는 23개만 비교합니다. 답할 수 없는 질문 6개와 모호한 Q028은 이 그래프에서 제외했습니다.")
        st.write("필수 근거가 없었던 Q005·Q018·Q027은 검색 개선이 필요합니다. 근거가 있었던 Q003·Q012는 답변의 조건과 누락을 먼저 살펴볼 사례입니다.")
        st.caption("근거 확보는 필수 내용의 근거를 하나 이상 찾았다는 뜻입니다. 모든 근거의 완전성을 뜻하지는 않습니다. 이번 20개는 필수 내용도 모두 확보했습니다.")
    st.subheader("확인된 결과에서 무엇을 배웠나요?")
    steps([("질문 표현이 검색 결과에 영향을 줍니다", "Q007은 CR2032를 답했지만, 오타·구어체의 Q027은 규격을 찾지 못했습니다."),
           ("여러 질문이라고 반드시 실패하지는 않습니다", "Q013·Q025·Q030은 여러 항목을 함께 물어도 답했습니다. Q005 실패의 원인을 질문 개수 하나로 단정할 수 없습니다."),
           ("근거가 있어도 조건이 바뀌거나 설명이 빠질 수 있습니다", "Q003의 점검 조건 표현이 달라졌습니다. Q012는 고정 정답 기준의 D 기어 조건이 빠졌습니다."),
           ("모호한 상황은 먼저 확인해야 합니다", "Q028은 일반 확인 방법을 안내했지만 사용자에게 상황을 추가로 묻지 않았습니다.")])
    st.caption("Q012의 속도 범위 답변은 정확했습니다. 부분 충족은 질문보다 넓게 설정된 정답 기준에 D 조건이 포함된 데 따른 판정입니다.")
    st.subheader("실제 답변을 직접 확인해 보세요")
    a, b = st.columns(2)
    with a:
        category = st.selectbox("질문 유형", ["전체"] + list(CATEGORIES.values()), key="case_category")
    with b:
        outcome = st.selectbox("답변 판정", ["전체"] + list(OUTCOMES.values()), key="case_outcome")
    cases = {c["test_id"]: c for c in dataset["cases"]}
    filtered = [r for r in rows if (category == "전체" or CATEGORIES[cases[r['test_id']]['category']] == category)
                and (outcome == "전체" or OUTCOMES[r['review']['overall_result']] == outcome)]
    if not filtered:
        st.info("이 조건에 해당하는 질문이 없습니다.")
    else:
        ids = [r["test_id"] for r in filtered]
        index = ids.index("Q005") if "Q005" in ids else 0
        selected = st.selectbox("살펴볼 질문", ids, index=index,
                                format_func=lambda id: f"{id} · {cases[id]['question']}", key="selected_evaluation_case")
        r = next(r for r in filtered if r["test_id"] == selected)
        with st.container(border=True):
            st.caption(f"{selected} · {OUTCOMES[r['review']['overall_result']]} · 앱 표시 처리 시간 {r['elapsed_seconds']:.1f}초")
            st.markdown(f"**{r['question']}**")
            st.markdown(r["answer"])
            st.info(r["review"]["notes"])
        with st.expander("사전에 정한 답변 기준"):
            c = cases[selected]
            for f in c["required_facts"]:
                st.markdown(f"- {f['criterion']}")
            if not c["required_facts"]:
                st.write(c["expected_behavior"])
        with st.expander("실제로 검색된 근거 5개"):
            for source in r["retrieved_sources"]:
                st.markdown(f"**[{source['rank']}] {source['source_title']}**")
                st.caption(f"PDF {source['page_start']}~{source['page_end']}쪽 · 유사도 {source['similarity']:.4f}")
                st.write(source["chunk_text"])
                st.divider()
        with st.expander("전체 질문과 판정을 표로 보기"):
            st.dataframe([{"번호": x["test_id"], "질문": x["question"], "판정": OUTCOMES[x["review"]["overall_result"]]} for x in filtered],
                         hide_index=True, width="stretch")
    with st.expander("이 평가의 범위와 주의점"):
        st.write("30개는 선정한 초기 테스트 사례입니다. 전체 사용자 질문에 대한 성공률이나 대규모 검증 결과로 일반화하지 않습니다.")
        st.write("팀 DB와 gpt-6-luna 사용은 사용자 확인 정보입니다. 배포 서버의 실제 설정과 코드 커밋을 별도로 조회하지 않았습니다.")
        st.write("판정은 작성자의 초기 검토입니다. 독립 전문가 채점, 같은 질문의 반복 실행, 동시 사용자 부하 검증은 수행하지 않았습니다.")
        st.write("Q005를 짧게 바꿨을 때 성공한 사용자 추가 확인은 별도 기록으로 남겼습니다. 원래 Q005와 전체 통계는 바꾸지 않았습니다.")
        st.caption("그래프는 현재 앱에 다시 질문한 결과가 아닌, 2026.10.02에 수집한 고정 평가 기록입니다.")
    st.subheader("전체 자료와 그래프")
    a, b = st.columns(2)
    with a:
        download("downloads/stage4_evaluation.zip", "평가 질문·실행 결과·리포트 내려받기")
    with b:
        download("charts/evaluation_charts.html", "그래프 2개를 HTML로 내려받기", "text/html")


def render_project_page(page):
    {"프로젝트 한눈에": render_overview, "01 데이터·전처리": render_stage1,
     "02 데이터 분석": render_stage2, "03 검색·답변 구조": render_stage3,
     "04 검색 품질 평가": render_stage4}[page]()
