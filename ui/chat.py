import os
import streamlit as st

try:
    from core.rag import create_chain, get_sources
    from core.memory import (
        init_memory,
        add_message,
        get_chat_history,
        get_history_as_string,
        clear_memory,
        save_history_to_json,
        get_message_count
    )
    from ui.styles import (
        render_chat_message,
        render_source_card,
        render_empty_state,
        render_badge
    )
except ModuleNotFoundError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.rag import create_chain, get_sources
    from core.memory import (
        init_memory,
        add_message,
        get_chat_history,
        get_history_as_string,
        clear_memory,
        save_history_to_json,
        get_message_count
    )
    from ui.styles import (
        render_chat_message,
        render_source_card,
        render_empty_state,
        render_badge
    )


def render_chat(retriever, sidebar_settings: dict):
    """
    채팅 화면 전체를 그리는 함수

    Args:
        retriever        : vectorstore.py 에서 만든 검색기
        sidebar_settings : sidebar.py 에서 받은 설정값 딕셔너리
    """
    # 1. 대화 메모리 초기화 (처음 한 번만 실행됨)
    init_memory()

    # 2. 사이드바에서 "초기화" 버튼 눌렀으면 대화 비우기
    if sidebar_settings.get("clear_clicked"):
        clear_memory()
        st.rerun()

    # 3. 사이드바에서 "저장" 버튼 눌렀으면 JSON 다운로드 제공
    if sidebar_settings.get("save_clicked"):
        json_str = save_history_to_json()
        if json_str:
            st.sidebar.download_button(
                label="📥 JSON 파일 다운로드",
                data=json_str,
                file_name="대화기록.json",
                mime="application/json"
            )
        else:
            st.sidebar.warning("저장할 대화가 없어요!")

    # 4. 기존 대화 기록 화면에 그리기
    history = get_chat_history()

    if not history:
        render_empty_state()
    else:
        for msg in history:
            render_chat_message(msg["role"], msg["content"])

    # 5. 질문 입력창
    question = st.chat_input("문서에 대해 질문해보세요...")

    # 6. 질문이 들어오면 처리
    if question:
        # 6-1. 사용자 질문 먼저 화면에 표시
        render_chat_message("user", question)
        add_message("user", question)

        # 6-2. AI 답변 생성 중 표시
        with st.spinner("답변을 생성하는 중이에요..."):
            try:
                # 이전 대화 기록을 문자열로 변환
                chat_history_str = get_history_as_string(max_turns=5)

                # RAG 체인 생성 (이전 대화 기록 포함)
                chain = create_chain(retriever, chat_history=chat_history_str)

                # AI 답변 생성
                answer = chain.invoke(question)

                # 출처 정보 가져오기
                sources = get_sources(retriever, question)

            except Exception as e:
                answer = f"⚠️ 답변 생성 중 오류가 발생했어요: {str(e)}"
                sources = []

        # 6-3. AI 답변 화면에 표시
        render_chat_message("assistant", answer)
        add_message("assistant", answer)

        # 6-4. 출처 카드 표시
        if sources:
            st.markdown("**📎 참고 출처**")
            for source in sources:
                render_source_card(source)

        # 6-5. 새로고침해서 입력창 비우기
        st.rerun()

    # 7. 하단 대화 통계 표시
    if history:
        count = get_message_count()
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            render_badge(f"질문 {count['질문 수']}회", "info")
        with col2:
            render_badge(f"답변 {count['답변 수']}회", "success")
        with col3:
            render_badge(f"전체 메시지 {count['전체 메시지']}개", "warning")


# ─────────────────────────────────────────
# 테스트 코드
# ─────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="chat 테스트", layout="wide")

    from ui.styles import apply_styles
    from ui.sidebar import render_sidebar
    from core.loader import load_pdf
    from core.vectorstore import create_vectorstore, get_retriever

    apply_styles()

    # 사이드바 렌더링
    settings = render_sidebar()

    st.markdown("## 💬 채팅 화면 테스트")

    # 파일 업로드 됐으면 처리
    if settings["uploaded_file"]:
        if "vectorstore" not in st.session_state:
            with st.spinner("문서를 분석하는 중이에요..."):
                split_docs = load_pdf(
                    settings["uploaded_file"],
                    chunk_size=settings["chunk_size"],
                    chunk_overlap=settings["chunk_overlap"]
                )
                st.session_state.vectorstore = create_vectorstore(split_docs)
            st.success("✅ 문서 분석 완료!")

        retriever = get_retriever(
            st.session_state.vectorstore,
            search_type=settings["search_type"],
            k=settings["k"]
        )

        render_chat(retriever, settings)
    else:
        render_empty_state()