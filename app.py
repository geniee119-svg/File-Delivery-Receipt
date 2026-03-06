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
    # --- 2. 메인 타이틀 ---
    st.title("📺 파일 인수증 생성기")
    
    # --- 3. 신규 프로그램 개별 입력 폼 ---
    if "custom_codes" not in st.session_state:
        st.session_state["custom_codes"] = {}

    with st.container(border=True):
        st.markdown("#### ⚙️ 신규 프로그램 추가")
        st.write("기존 코드표에 없는 새 프로그램을 임시로 등록합니다.")
        with st.form("new_program_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("📝 프로그램명 (예: 신농사직설7시즌)")
            with col2:
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
            st.markdown("**[현재 추가된 프로그램]**")
            for name, code in st.session_state["custom_codes"].items():
                st.markdown(f"- **{name}**: `{code}`")
                
            if st.button("목록 초기화"):
                st.session_state["custom_codes"] = {}
                st.rerun()

    # --- 제미나이 API 세팅 ---
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
3. 아이디 생성 규칙: [영문 코드 5자리] + [회차 4자리 숫자(빈자리는 0으로 채움)]. 예: 82회 -> 0082
4. 출력 포맷: 엑셀에 바로 붙여넣을 수 있게 각 항목을 '탭(Tab)'으로만 구분합니다. 마크다운 표 형태(|)는 절대 사용하지 마세요.
5. 열 구성: [아이디] (탭) [영상 길이(예: 00:45:00)] (탭) [본방]프로그램명+회차 (탭) [비고(빈칸)]

[기존 프로그램 코드표]
- 어영차바다야: NBOBA
- 로컬판타지: NBFCF
- 인생내컷: NBJCB
- 테마기행길: NBDHA
- 보통의존재: NBRBB
- 시사토론: NBFKB
- 제주엔: NBKBH
- 톡톡동해인: NBTBA
- 문화콘서트난장: NBDEA
- 맛나면좋은친구: NBNCA
- 인생굿샷: NBIFA
- 문화요: NBCCE
- 어서와한국은처음이지: NCVJA
- 취미로운생활: NAABJ
- 팔도맛지도: NAABI
- 어린왕자원정대: NBQCC
- 소통의고수3시즌: NBKGF
- 여기이슈강원: NBIKA
- 신농사직설6시즌: NBCCH
- 시민의품격: NBCCG
- 다정다감: NBFCG
- 이슈잇다: NBKKA
{custom_section}

위 규칙과 코드표를 엄격하게 적용하여 탭으로 구분된 텍스트 결과물만 출력하세요. 다른 부연 설명이나 인사말은 절대 하지 마세요.
"""

    # --- 4. 대화 기록 출력 구역 ---
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            elif msg["type"] == "code":
                st.code(msg["content"], language="text")
            elif msg["type"] == "image":
                st.image(msg["content"], caption="업로드된 이미지", width=400)

    # --- 5. 스마트 채팅창 (이미지 붙여넣기 및 엔터 실행 완벽 지원) ---
    prompt_input = st.chat_input("궁금한점을 타이핑하고 엔터를 누르세요", accept_file=True, file_type=["png", "jpg", "jpeg"])

    if prompt_input:
        if isinstance(prompt_input, str):
            # Streamlit 구버전 예외 처리
            st.session_state["messages"].append({"role": "user", "type": "text", "content": prompt_input})
            st.session_state["messages"].append({"role": "assistant", "type": "text", "content": "현재 앱 구동 환경이 이미지 붙여넣기를 지원하지 않습니다. 스트림릿 서버를 재부팅(Reboot) 해주세요."})
            st.rerun()
        else:
            user_text = prompt_input.text
            user_files = prompt_input.files
            
            # 텍스트가 있다면 출력
            if user_text:
                st.session_state["messages"].append({"role": "user", "type": "text", "content": user_text})
                
            # 이미지 첨부(붙여넣기)가 감지되었을 때 메인 프로세스 실행
            if user_files:
                img = Image.open(user_files[0])
                st.session_state["messages"].append({"role": "user", "type": "image", "content": img})
                
                with st.spinner('제미나이가 데이터를 분석하고 있습니다...'):
                    try:
                        response = model.generate_content([get_prompt(), img])
                        st.session_state["messages"].append({"role": "assistant", "type": "code", "content": response.text})
                    except Exception as e:
                        st.session_state["messages"].append({"role": "assistant", "type": "text", "content": f"오류가 발생했습니다: {e}"})
            else:
                # 텍스트만 치고 이미지를 안 올렸을 때의 안내문
                if user_text:
                    st.session_state["messages"].append({"role": "assistant", "type": "text", "content": "이미지가 확인되지 않았습니다. 추출하시려는 캡처본을 채팅창에 붙여넣기(Ctrl+V) 하거나 왼쪽 아이콘으로 첨부한 뒤 엔터를 눌러주세요."})
            
            st.rerun()
