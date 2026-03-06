import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 보안 설정: 비밀번호 확인 ---
def check_password():
    if "password_entered" not in st.session_state:
        st.session_state["password_entered"] = False

    if not st.session_state["password_entered"]:
        st.text_input("팀 전용 접속 비밀번호를 입력하세요", type="password", key="pwd")
        if st.session_state["pwd"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_entered"] = True
            st.rerun()
        elif st.session_state["pwd"]:
            st.error("비밀번호가 일치하지 않습니다.")
        return False
    return True

if check_password():
    # --- 2. 사이드바: 신규 프로그램 개별 입력 폼 ---
    st.sidebar.header("⚙️ 신규 프로그램 추가")
    st.sidebar.write("기존 코드표에 없는 새 프로그램을 개별 등록합니다.")
    
    # 세션 상태에 임시 코드 딕셔너리 생성
    if "custom_codes" not in st.session_state:
        st.session_state["custom_codes"] = {}

    # 시각적으로 묶인 입력 폼(Form) 구성
    with st.sidebar.form("new_program_form", clear_on_submit=True):
        new_name = st.text_input("📝 프로그램명 (예: 신농사직설7시즌)")
        new_code = st.text_input("🔠 영문 코드 (예: NBCCH)")
        submitted = st.form_submit_button("➕ 추가하기")
        
        if submitted:
            if new_name and new_code:
                clean_name = new_name.replace(" ", "") # 띄어쓰기 자동 제거
                st.session_state["custom_codes"][clean_name] = new_code
                st.success(f"'{clean_name}' 등록 완료!")
            else:
                st.warning("프로그램명과 코드를 모두 입력해주세요.")
                
    # 등록된 임시 프로그램 목록 실시간 출력
    if st.session_state["custom_codes"]:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**[현재 추가된 프로그램]**")
        for name, code in st.session_state["custom_codes"].items():
            st.sidebar.markdown(f"- **{name}**: `{code}`")
            
        if st.sidebar.button("목록 초기화"):
            st.session_state["custom_codes"] = {}
            st.rerun()

    # --- 3. 메인 화면: 제미나이 봇 세팅 ---
    st.title("📺 방송 편성 데이터 추출 봇")
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')

    # 프롬프트 동적 생성 함수
    def get_prompt():
        custom_section = ""
        if st.session_state["custom_codes"]:
            custom_section = "\n[추가된 신규 프로그램 코드]\n"
            for name, code in st.session_state["custom_codes"].items():
                custom_section += f"- {name}: {code}\n"
                
        return f"""
당신은 방송 편성 데이터 정제 전문가입니다. 
첨부된 이미지(영상 목록 캡처본)를 분석하여 '파일 인수증' 텍스트를 작성해야 합니다.

[작업 규칙]
1. 파일명 맨 앞에 있는 숫자를 '회차'로 최우선 인식합니다. 맨 앞에 숫자가 없다면 파일명 중간에 있는 회차(예: 31회, 40화 등)를 찾아 적용합니다.
2. 프로그램명은 띄어쓰기를 모두 없애고 아래 [코드표]의 공식 명칭으로 통일합니다. (예: 테마기행 길 -> 테마기행길, 시토 -> 시사토론)
3. 아이디 생성 규칙: [영
