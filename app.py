import streamlit as st
import google.generativeai as genai
from PIL import Image
import base64

# --- 앱 기본 설정 ---
st.set_page_config(page_title="MBC NET 파일 인수증", layout="centered")

# --- 사내 전용 폰트(MBC NEW L.ttf) 로드 및 CSS 적용 ---
font_file = "MBC NEW L.ttf"

try:
    with open(font_file, "rb") as f:
        font_data = f.read()
        font_b64 = base64.b64encode(font_data).decode("utf-8")

    st.markdown(f"""
        <style>
        @font-face {{
            font-family: 'MBC_NEW_L';
            src: url(data:font/ttf;charset=utf-8;base64,{font_b64}) format('truetype');
        }}
        
        /* 1. 앱 전체 폰트 적용 */
        html, body, p, div, span, input, button, textarea, label, li {{
            font-family: 'MBC_NEW_L', sans-serif !important;
        }}
        
        /* 2. 상단 쨍한 형광 보라색 포인트 띠 */
        [data-testid="stHeader"] {{
            background-color: transparent;
            border-top: 8px solid #684CDB;
        }}
        
        /* 3. 메인 텍스트 입력창 포커스 시 테두리 색상 강제 지정 */
        div[data-baseweb="input"] > div {{
            border-color: #684CDB !important;
        }}

        /* 4. 사이드바 여닫기 버튼 (텍스트 찌꺼기 완벽 제거 및 보라색 삼각형 고정) */
        button[data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapseButton"] {{
            color: transparent !important; /* double_arrow_right 글자 숨김 */
        }}
        button[data-testid="collapsedControl"] *,
        button[data-testid="stSidebarCollapseButton"] * {{
            display: none !important; /* 내부 svg, span 등 요소 강제 삭제 */
        }}
        
        /* 접혀있을 때 (▶) */
        button[data-testid="collapsedControl"]::after {{
            content: "▶" !important;
            color: #684CDB !important;
            font-size: 20px !important;
            display: block !important;
            visibility: visible !important;
        }}
        /* 펼쳐져있을 때 (◀) */
        button[data-testid="stSidebarCollapseButton"]::after {{
            content: "◀" !important;
            color: #684CDB !important;
            font-size: 20px !important;
            display: block !important;
            visibility: visible !important;
        }}

        /* 5. 채팅창 이모티콘(아바타) 영역 및 텍스트(face, art_) 강제 완전 삭제 */
        div[data-testid="stChatMessageAvatar"],
        div[data-testid="chatAvatarIcon-user"],
        div[data-testid="chatAvatarIcon-assistant"] {{
            display: none !important;
        }}
        /* 머티리얼 아이콘 텍스트 누수 방지 */
        .stChatMessage span[class*="material"] {{
            display: none !important;
            color: transparent !important;
        }}
        
        /* 6. 추출 데이터(코드 블록) 폰트 굵기/크기 완벽 통일 */
        .stCodeBlock, .stCodeBlock code, .stCodeBlock pre, .stCodeBlock span {{
            font-family: 'MBC_NEW_L', monospace !important;
            font-size: 15px !important;
            font-weight: normal !important;
            line-height: 1.6 !important;
            color: #262730 !important;
        }}
        </style>
    """, unsafe_allow_html=True)

except FileNotFoundError:
    st.error(f"사내 폰트 파일을 찾을 수 없습니다: '{font_file}'. 깃허브에 파일이름이 정확히 일치하는지 확인해주세요.")


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
    # --- 2. 왼쪽 서랍 (사이드바 - 프로그램 관리 폼) ---
    with st.sidebar:
        st.markdown("### 프로그램 관리")
        st.write("기존 코드표에 없는 새 프로그램을 임시 등록합니다.")
        
        if "custom_codes" not in st.session_state:
            st.session_state["custom_codes"] = {}

        with st.form("new_program_form", clear_on_submit=True):
            new_name = st.text_input("프로그램명 (예: 신농사직설)")
            new_code = st.text_input("영문 코드 (예: NBCCH)")
            
            submitted = st.form_submit_button("추가하기", type="primary", use_container_width=True)
            
            if submitted:
                if new_name and new_code:
                    clean_name = new_name.replace(" ", "")
                    st.session_state["custom_codes"][clean_name] = new_code
                    st.success(f"'{clean_name}' 등록 완료")
                else:
                    st.warning("프로그램명과 코드를 모두 입력해주세요.")
        
        if st.session_state["custom_codes"]:
            st.markdown("---")
            st.markdown("**[현재 추가된 프로그램]**")
            for name, code in st.session_state["custom_codes"].items():
                st.markdown(f"- **{name}**: `{code}`")
                
            if st.button("목록 초기화", use_container_width=True):
                st.session_state["custom_codes"] = {}
                st.rerun()

    # --- 제미나이 API 세팅 ---
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')

    def get_prompt():
        custom_section = ""
        if st.session_state["custom_codes"]:
            custom_section = "\n[추가된 신규 프로그램 코드]\n"
            for name, code in st.session_state["custom_codes"].items():
                custom_section += f"- {name}: {code}\n"
                
        return f"""
당신은 방송 편성 데이터 정제 전문가입니다. 
첨부된 이미지(영상 목록 캡처본)를 분석하여 '파일 인수증' 텍스트를 작성해야 합니다.
데이터 처리는 반드시 Python(Code Interpreter)을 사용해서 수행해 주세요.

[작업 규칙]
1. 회차 추출 (매우 중요): 파일명 문자열을 왼쪽부터 읽었을 때 **가장 먼저 등장하는 숫자(숫자+회/화)**를 무조건 최종 회차로 확정합니다. 파일명 중간이나 프로그램명 뒤쪽에 다른 회차가 적혀 있더라도 절대 무시하세요. 
   - 예시: '39회_260125일_시토_40회' -> 39회 추출 (40회 무시)
2. 프로그램명은 띄어쓰기를 모두 없애고 아래 [코드표]의 공식 명칭으로 통일합니다.
3. 아이디 생성 규칙: [영문 코드 5자리] + [회차 4자리 숫자(빈자리는 0으로 채움)]. 예: 82회 -> 0082
4. 출력 포맷: 엑셀에 바로 붙여넣을 수 있게 각 항목을 '탭(Tab)'으로만 구분하며, 각 영상 목록은 반드시 줄바꿈(Enter)으로 구분하여 한 줄에 하나씩 작성하세요. 마크다운 표 형태(|)는 절대 사용하지 마세요.
5. 열 구성: [아이디] (탭) [영상 길이(예: 00:45:00)] (탭) [프로그램명+회차] (탭) [비고(빈칸)]
6. 재방/본방 표기: 기본적으로 프로그램명 앞에 본방/재방 여부를 표기하지 않습니다. 단, 아래 [본방 시간대 지정 프로그램]에 해당하는 경우에만 프로그램명 앞에 '[본방]'을 붙이세요.

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

[본방 시간대 지정 프로그램]
(여기에 전달해주실 본방 프로그램 목록과 시간대 규칙이 적용됩니다.)

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
                st.image(msg["content"], caption="업로드된 캡처본", width=400)

    # --- 5. 스마트 채팅창 ---
    prompt_input = st.chat_input(" ", accept_file=True, file_type=["png", "jpg", "jpeg"])

    if prompt_input:
        if isinstance(prompt_input, str):
            st.session_state["messages"].append({"role": "assistant", "type": "text", "content": "현재 스트림릿 구버전이 작동 중이라 이미지 직접 첨부가 제한될 수 있습니다. 서버를 재부팅해주세요."})
            st.rerun()
        else:
            user_text = prompt_input.text
            user_files = prompt_input.files
            
            if user_text:
                st.session_state["messages"].append({"role": "user", "type": "text", "content": user_text})
                
            if user_files:
                img = Image.open(user_files[0])
                st.session_state["messages"].append({"role": "user", "type": "image", "content": img})
                
                with st.spinner('데이터를 분석하고 있습니다...'):
                    try:
                        response = model.generate_content([get_prompt(), img])
                        st.session_state["messages"].append({"role": "assistant", "type": "code", "content": response.text})
                    except Exception as e:
                        st.session_state["messages"].append({"role": "assistant", "type": "text", "content": f"오류가 발생했습니다: {e}"})
            else:
                if user_text:
                    st.session_state["messages"].append({"role": "assistant", "type": "text", "content": "이미지가 확인되지 않았습니다. 파일 첨부 아이콘을 눌러 이미지를 올려주세요."})
            
            st.rerun()
