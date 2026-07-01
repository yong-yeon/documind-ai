import os   # 모듈 경로 처리용
import sys  # 모듈 경로 추가용
import streamlit as st

try:
    from core.rag import create_chain, get_sources                   # RAG 체인 생성, 출처 조회
    from core.memory import (
        init_memory, add_message, get_chat_history,
        get_history_as_string, clear_memory, save_history_to_json, get_message_count
    )
    from ui.styles import render_chat_message, render_source_card, render_badge  # UI 컴포넌트
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 루트 경로 추가
    from core.rag import create_chain, get_sources
    from core.memory import (
        init_memory, add_message, get_chat_history,
        get_history_as_string, clear_memory, save_history_to_json, get_message_count
    )
    from ui.styles import render_chat_message, render_source_card, render_badge


def render_chat(retriever, sidebar_settings: dict):
    init_memory()  # session_state에 chat_history 키가 없으면 빈 리스트로 초기화

    if sidebar_settings.get("clear_clicked"):   # 초기화 버튼이 눌린 경우
        clear_memory()                          # 대화 기록 삭제
        st.rerun()                              # 화면 즉시 리렌더링

    if sidebar_settings.get("save_clicked"):    # 저장 버튼이 눌린 경우
        json_str = save_history_to_json()       # 대화 기록을 JSON 문자열로 변환
        if json_str:
            st.sidebar.download_button(         # 사이드바에 다운로드 버튼 노출
                label="JSON 파일 다운로드",
                data=json_str,
                file_name="대화기록.json",
                mime="application/json"
            )
        else:
            st.sidebar.warning("저장할 대화가 없습니다.")

    history = get_chat_history()  # 현재 세션의 전체 대화 기록 가져오기

    if not history:
        st.info("문서가 업로드되었습니다. 질문을 입력해주세요.")  # 첫 진입 안내 메시지
    else:
        for msg in history:                                      # 기존 대화 기록을 순서대로 렌더링
            render_chat_message(msg["role"], msg["content"])

    question = st.chat_input("문서에 대해 질문해보세요...")  # 하단 입력창 렌더링

    if question:                                             # 질문이 입력된 경우
        render_chat_message("user", question)               # 사용자 말풍선 즉시 표시
        add_message("user", question)                       # 대화 기록에 저장

        with st.spinner("답변을 생성하는 중입니다..."):
            try:
                chat_history_str = get_history_as_string(max_turns=5)  # 최근 5턴 대화를 문자열로 변환
                chain = create_chain(                                   # RAG 체인 생성
                    retriever,
                    chat_history=chat_history_str,
                    mode=sidebar_settings.get("answer_mode", "hybrid")
                )
                answer  = chain.invoke(question)            # 질문을 체인에 전달해 답변 생성
                sources = get_sources(retriever, question)  # 참고 출처 목록 조회
            except Exception as e:
                answer  = f"답변 생성 중 오류가 발생했습니다: {str(e)}"
                sources = []

        render_chat_message("assistant", answer)  # AI 답변 말풍선 표시
        add_message("assistant", answer)          # 대화 기록에 저장

        if sources:
            st.markdown("**참고 출처**")
            for source in sources:
                render_source_card(source)        # 출처 카드 렌더링

        st.rerun()  # 입력창을 비우기 위해 리렌더링

    if history:                          # 대화 기록이 있을 때만 하단 통계 표시
        count = get_message_count()
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            render_badge(f"질문 {count['질문 수']}회", "info")
        with col2:
            render_badge(f"답변 {count['답변 수']}회", "success")
        with col3:
            render_badge(f"전체 메시지 {count['전체 메시지']}개", "warning")
