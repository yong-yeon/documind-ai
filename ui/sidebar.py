import os   # 모듈 경로 처리용
import sys  # 모듈 경로 추가용
import streamlit as st

try:
    from config import (
        DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
        DEFAULT_SEARCH_TYPE, DEFAULT_K, SUPPORTED_EXTENSIONS
    )
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 루트 경로 추가
    from config import (
        DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
        DEFAULT_SEARCH_TYPE, DEFAULT_K, SUPPORTED_EXTENSIONS
    )


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("## DocuMind AI")
        st.caption("다중 문서 통합 분석 시스템")
        st.divider()

        # 파일 업로드
        st.markdown("#### 문서 업로드")
        uploaded_file = st.file_uploader(
            "파일을 선택해주세요",
            type=[ext.replace(".", "") for ext in SUPPORTED_EXTENSIONS],  # [".pdf"] → ["pdf"] 형식으로 변환
            help="PDF, DOCX, XLSX, PPTX 파일을 지원합니다."
        )
        if uploaded_file:
            file_size_mb = uploaded_file.size / (1024 * 1024)  # bytes → MB 변환
            st.success(f"{uploaded_file.name} ({file_size_mb:.1f}MB)")

        st.divider()

        # 답변 모드
        st.markdown("#### 답변 모드")
        answer_mode = st.radio(
            "답변 방식 선택",
            options=["hybrid", "document"],
            format_func=lambda x: "혼합 모드 (문서 + AI)" if x == "hybrid" else "문서 전용 모드",  # 옵션 레이블 한글화
            help="혼합: 문서에 없으면 AI 지식으로 보완 / 문서 전용: 문서 내용만 사용"
        )

        st.divider()

        # 고급 설정: 청크/검색 파라미터 조정 (변경 시 문서 자동 재처리)
        with st.expander("고급 설정", expanded=False):
            st.markdown("**텍스트 분할 설정**")
            chunk_size = st.slider(
                "청크 크기",
                min_value=200, max_value=1500,
                value=DEFAULT_CHUNK_SIZE, step=100,
                help="텍스트를 몇 글자씩 분할할지 설정합니다. 변경 시 문서를 자동으로 재처리합니다."
            )
            chunk_overlap = st.slider(
                "청크 겹침",
                min_value=0, max_value=chunk_size // 2,             # chunk_size 절반 이상은 설정 불가
                value=min(DEFAULT_CHUNK_OVERLAP, chunk_size // 2),  # chunk_size 변경 시 초과 방지
                step=50,
                help="조각 간 겹치는 글자 수입니다. 문맥 연결에 도움이 됩니다."
            )

            st.markdown("**검색 설정**")
            search_type = st.radio(
                "검색 방식",
                options=["mmr", "similarity"],
                index=0 if DEFAULT_SEARCH_TYPE == "mmr" else 1,  # 기본값에 맞춰 선택 항목 초기화
                format_func=lambda x: "MMR (다양한 결과)" if x == "mmr" else "Similarity (정확한 결과)",
                help="MMR은 중복을 줄인 다양한 결과, Similarity는 가장 유사한 결과만 반환합니다."
            )
            k = st.slider(
                "검색 조각 수",
                min_value=3, max_value=10,
                value=DEFAULT_K, step=1,
                help="답변 생성에 참고할 문서 조각 개수입니다."
            )

        st.divider()

        # 대화 관리
        st.markdown("#### 대화 관리")
        col1, col2 = st.columns(2)
        with col1:
            save_clicked  = st.button("저장",  use_container_width=True)  # 대화 기록 JSON 저장
        with col2:
            clear_clicked = st.button("초기화", use_container_width=True)  # 대화 기록 전체 삭제

        st.divider()
        st.caption("기술 스택")
        st.caption("LangChain · Groq · FAISS · Streamlit")

    return {                              # 모든 설정값을 딕셔너리로 반환해 app.py에서 사용
        "uploaded_file": uploaded_file,
        "chunk_size":    chunk_size,
        "chunk_overlap": chunk_overlap,
        "search_type":   search_type,
        "k":             k,
        "answer_mode":   answer_mode,
        "save_clicked":  save_clicked,
        "clear_clicked": clear_clicked,
    }
