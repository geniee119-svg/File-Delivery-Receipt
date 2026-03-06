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

    # --- 4. 대화형 채팅 UI 구성 ---
    # 채팅 기록을 저장하는 메모리
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "type": "text", "content": "안녕하세요! 파일 인수증 추출 봇입니다.\n아래 창을 통해 이미지를 올리시거나 텍스트를 입력해 주세요."}
        ]

    # 이전 대화 내용 화면에 그리기
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            elif msg["type"] == "code":
                st.code(msg["content"], language="text")
            elif msg["type"] == "image":
                st.image(msg["content"], caption="업로드된 이미지")

    # --- 5. 이미지 분석 및 결과 출력 함수 ---
    def process_and_reply(img):
        # 1. 유저가 보낸 이미지를 채팅창에 띄움
        st.session_state["messages"].append({"role": "user", "type": "image", "content": img})
        
        # 2. 제미나이 봇의 응답 처리
        try:
            response = model.generate_content([get_prompt(), img])
            st.session_state["messages"].append({"role": "assistant", "type": "code", "content": response.text})
        except Exception as e:
            st.session_state["messages"].append({"role": "assistant", "type": "text", "content": f"오류가 발생했습니다: {e}"})

    # --- 6. 입력 도구 (파일 업로더 + 채팅창 결합) ---
    st.markdown("---")
    
    # 기능 1: 드래그 앤 드롭 / 브라우즈 / 클립보드 붙여넣기 모두 지원하는 업로드 구역
    uploaded_file = st.file_uploader("📂 찾아보기 / 드래그 앤 드롭 / 클릭 후 붙여넣기(Ctrl+V)", type=["png", "jpg", "jpeg"])
    if uploaded_file and st.button("✨ 이 이미지로 파일 인수증 추출하기", use_container_width=True):
        with st.spinner('제미나이가 데이터를 분석하고 있습니다...'):
            img = Image.open(uploaded_file)
            process_and_reply(img)
            st.rerun()

    # 기능 2: 텍스트 채팅창 (하단 고정)
    user_chat = st.chat_input("채팅을 입력하세요...")
    if user_chat:
        # 유저 메시지 화면에 띄움
        st.session_state["messages"].append({"role": "user", "type": "text", "content": user_chat})
        # 봇의 안내 응답
        st.session_state["messages"].append({"role": "assistant", "type": "text", "content": "채팅을 확인했습니다! 영상 목록이 포함된 이미지를 바로 위의 파일 업로더를 통해 올려주시면 표를 추출해 드리겠습니다."})
        st.rerun()
