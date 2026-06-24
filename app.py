import streamlit as st
from ui.styles import apply_styles, render_header, render_empty_state
from ui.sidebar import render_sidebar
from ui.chat import render_chat
from core.loader import load_pdf
from core.vectorstore import create_vectorstore, get_retriever


# 페이지 설정
st.set_page_config(
    page_title="DocuMind AI",
    page_icon="🧠",
    layout="wide"
)

# 1. 스타일 적용
apply_styles()

# 2. 헤더
render_header()

# 3. 사이드바 렌더링 → 설정값 받기
settings = render_sidebar()

# 4. 파일 업로드 됐으면 처리
if settings["uploaded_file"]:

    # 파일이 새로 업로드됐거나 처음이면 처리
    file_key = settings["uploaded_file"].name + str(settings["uploaded_file"].size)

    if "file_key" not in st.session_state or st.session_state.file_key != file_key:
        with st.spinner("📄 문서를 분석하는 중이에요... 잠시만 기다려주세요!"):
            try:
                # PDF 읽기 + 분할
                split_docs = load_pdf(
                    settings["uploaded_file"],
                    chunk_size=settings["chunk_size"],
                    chunk_overlap=settings["chunk_overlap"]
                )

                # 임베딩 + 벡터저장소 생성
                vectorstore = create_vectorstore(split_docs)

                # session_state 에 저장
                st.session_state.vectorstore = vectorstore
                st.session_state.split_docs = split_docs  # ← 추가!
                st.session_state.file_key = file_key
                st.session_state.chat_history = []

                st.success(f"✅ {settings['uploaded_file'].name} 분석 완료! ({len(split_docs)}개 조각)")

            except Exception as e:
                st.error(f"❌ 문서 처리 중 오류 발생 : {str(e)}")
                st.stop()

    # 5. 검색기 생성
    retriever = get_retriever(
        st.session_state.vectorstore,
        split_docs=st.session_state.split_docs,
        search_type=settings["search_type"],
        k=settings["k"]
    )

    # 6. 채팅 화면 렌더링
    render_chat(retriever, settings)

else:
    # 파일 없으면 빈 화면
    render_empty_state()