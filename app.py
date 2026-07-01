import streamlit as st                                          # 웹 앱 프레임워크
from ui.styles import apply_styles, render_header, render_empty_state  # 스타일, 헤더, 빈 화면
from ui.sidebar import render_sidebar                           # 사이드바 UI
from ui.chat import render_chat                                 # 채팅 화면 UI
from core.loader import load_file                               # 파일 읽기 및 청크 분할
from core.vectorstore import create_vectorstore, get_retriever  # 벡터 저장소 생성 및 검색기

st.set_page_config(page_title="DocuMind AI", page_icon="🧠", layout="wide")  # 브라우저 탭 설정

apply_styles()   # 전체 CSS 스타일 적용
render_header()  # 상단 헤더 렌더링

settings = render_sidebar()  # 사이드바 렌더링 후 설정값 딕셔너리로 반환

if settings["uploaded_file"]:  # 파일이 업로드된 경우에만 처리
    # 파일명, 용량, 청크 설정이 모두 동일하면 재처리 생략
    file_key = (
        settings["uploaded_file"].name          # 파일명
        + str(settings["uploaded_file"].size)   # 파일 용량
        + str(settings["chunk_size"])           # 청크 크기
        + str(settings["chunk_overlap"])        # 청크 겹침
    )

    if "file_key" not in st.session_state or st.session_state.file_key != file_key:  # 새 파일이거나 설정이 바뀐 경우
        with st.spinner("문서를 분석하는 중입니다. 잠시만 기다려주세요."):  # 로딩 스피너 표시
            try:
                split_docs = load_file(                   # 파일을 읽어 청크로 분할
                    settings["uploaded_file"],
                    chunk_size=settings["chunk_size"],
                    chunk_overlap=settings["chunk_overlap"]
                )
                vectorstore = create_vectorstore(split_docs)  # 청크를 임베딩해 FAISS 벡터 저장소 생성

                st.session_state.vectorstore  = vectorstore   # 벡터 저장소를 세션에 저장
                st.session_state.split_docs   = split_docs    # BM25 검색기 생성에 필요해 세션에 저장
                st.session_state.file_key     = file_key      # 현재 파일 키 저장 (재처리 판별용)
                st.session_state.chat_history = []            # 새 파일이므로 대화 기록 초기화
                st.session_state.retriever    = None          # 파일 바뀌면 캐시된 retriever 초기화

                st.success(f"{settings['uploaded_file'].name} 분석 완료 ({len(split_docs)}개 조각)")  # 완료 메시지

            except Exception as e:
                st.error(f"문서 처리 중 오류가 발생했습니다: {str(e)}")  # 오류 메시지 출력
                st.stop()                                                 # 이후 코드 실행 중단

    # retriever_key: 검색 설정이 바뀌었는지 판별
    retriever_key = settings["search_type"] + str(settings["k"])

    if st.session_state.get("retriever") is None or st.session_state.get("retriever_key") != retriever_key:
        # 파일이 바뀌거나 검색 설정이 바뀐 경우에만 retriever 재생성 (BM25 포함)
        st.session_state.retriever     = get_retriever(
            st.session_state.vectorstore,
            split_docs=st.session_state.split_docs,
            search_type=settings["search_type"],
            k=settings["k"]
        )
        st.session_state.retriever_key = retriever_key  # 현재 검색 설정 저장

    render_chat(st.session_state.retriever, settings)  # 채팅 화면 렌더링

else:
    render_empty_state()  # 파일 미업로드 상태의 안내 화면 렌더링
