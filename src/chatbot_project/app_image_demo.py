"""개인 DB에서 본문 검색과 연결 이미지 표시를 확인하는 실행 화면."""
import streamlit as st

# app2가 페이지 설정과 기존 화면 구성 함수를 제공합니다.
from app2 import (
    apply_theme, initialize_state, render_header, render_sidebar,
    ensure_rag_ready, render_question_form, render_result, footer,
)


def main():
    apply_theme()
    initialize_state()
    render_header()
    render_sidebar()
    ensure_rag_ready()
    question_column, result_column = st.columns([1, 2], gap='large')
    with question_column:
        render_question_form()
    with result_column:
        render_result()
    footer()


if __name__ == '__main__':
    main()
