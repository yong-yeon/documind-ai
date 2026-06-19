import os
import streamlit as st

try:
    from config import (
        DEFAULT_CHUNK_SIZE,
        DEFAULT_CHUNK_OVERLAP,
        DEFAULT_SEARCH_TYPE,
        DEFAULT_K,
        SUPPORTED_EXTENSIONS
    )
except ModuleNotFoundError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import (
        DEFAULT_CHUNK_SIZE,
        DEFAULT_CHUNK_OVERLAP,
        DEFAULT_SEARCH_TYPE,
        DEFAULT_K,
        SUPPORTED_EXTENSIONS
    )


def render_sidebar() -> dict:
    """
    사이드바 전체 렌더링 함수

    Returns:
        settings : 사이드바에서 설정한 값들을 담은 딕셔너리
        {
            "uploaded_file": 업로드된 파일 객체 (없으면 None),
            "chunk_size": int,
            "chunk_overlap": int,
            "search_type": str,
            "k": int,
            "save_clicked": bool,
            "clear_clicked": bool
        }
    """
    with st.sidebar:
        # ─────────────────────────────────────────
        # 1. 로고 + 타이틀
        # ─────────────────────────────────────────
        st.markdown("## 🧠 DocuMind AI")
        st.caption("다중 문서 통합 분석 시스템")
        st.divider()

        # ─────────────────────────────────────────
        # 2. 파일 업로드
        # ─────────────────────────────────────────
        st.markdown("#### 📂 문서 업로드")
        uploaded_file = st.file_uploader(
            "파일을 선택해주세요",
            type=[ext.replace(".", "") for ext in SUPPORTED_EXTENSIONS],
            help="PDF, DOCX, XLSX, PPTX 파일을 지원해요"
        )

        if uploaded_file:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.success(f"✅ {uploaded_file.name} ({file_size_mb:.1f}MB)")

        st.divider()

        # ─────────────────────────────────────────
        # 3. 고급 설정 (접기/펼치기)
        # ─────────────────────────────────────────
        with st.expander("⚙️ 고급 설정", expanded=False):

            st.markdown("**텍스트 분할 설정**")
            chunk_size = st.slider(
                "청크 크기",
                min_value=200,
                max_value=1000,
                value=DEFAULT_CHUNK_SIZE,
                step=50,
                help="텍스트를 몇 글자씩 자를지 설정해요"
            )

            chunk_overlap = st.slider(
                "청크 겹침",
                min_value=0,
                max_value=200,
                value=DEFAULT_CHUNK_OVERLAP,
                step=10,
                help="조각 간 겹치는 글자 수예요. 문맥 유지에 도움돼요"
            )

            st.markdown("**검색 설정**")
            search_type = st.radio(
                "검색 방식",
                options=["mmr", "similarity"],
                index=0 if DEFAULT_SEARCH_TYPE == "mmr" else 1,
                format_func=lambda x: "MMR (다양한 결과)" if x == "mmr" else "Similarity (정확한 결과)",
                help="MMR은 다양하고 중복 적은 결과, Similarity는 가장 비슷한 결과만 찾아요"
            )

            k = st.slider(
                "검색 조각 수",
                min_value=3,
                max_value=10,
                value=DEFAULT_K,
                step=1,
                help="질문 답변에 참고할 문서 조각 개수예요"
            )

        st.divider()

        # ─────────────────────────────────────────
        # 4. 대화 관리
        # ─────────────────────────────────────────
        st.markdown("#### 💬 대화 관리")

        col1, col2 = st.columns(2)
        with col1:
            save_clicked = st.button("💾 저장", use_container_width=True)
        with col2:
            clear_clicked = st.button("🗑 초기화", use_container_width=True)

        st.divider()

        # ─────────────────────────────────────────
        # 5. 정보
        # ─────────────────────────────────────────
        st.caption("🛠 기술 스택")
        st.caption("LangChain · Groq · FAISS · Streamlit")

    # 사이드바에서 설정한 값들을 딕셔너리로 반환
    return {
        "uploaded_file": uploaded_file,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "search_type": search_type,
        "k": k,
        "save_clicked": save_clicked,
        "clear_clicked": clear_clicked
    }


# ─────────────────────────────────────────
# 테스트 코드
# ─────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="sidebar 테스트", layout="wide")

    try:
        from ui.styles import apply_styles
    except ModuleNotFoundError:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ui.styles import apply_styles

    apply_styles()

    settings = render_sidebar()

    st.write("### 사이드바에서 받은 값")
    st.json({
        "파일명": settings["uploaded_file"].name if settings["uploaded_file"] else None,
        "chunk_size": settings["chunk_size"],
        "chunk_overlap": settings["chunk_overlap"],
        "search_type": settings["search_type"],
        "k": settings["k"],
        "save_clicked": settings["save_clicked"],
        "clear_clicked": settings["clear_clicked"]
    })