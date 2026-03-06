import streamlit as st
from streamlit_paste_button import paste_image_button
from PIL import Image
import io

# 1. 페이지 레이아웃 설정
st.set_page_config(page_title="AI 데이터 정제 도구", layout="centered")
st.title("💜 이미지 데이터 정제 툴")
st.write("편성표나 리스트를 캡처한 후 아래 버튼을 눌러주세요.")

# 2. 대화 기록 저장용 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. 기존 대화 내용 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.write(msg["content"])
        else:
            st.image(msg["content"])

# 4. 이미지 붙여넣기 버튼 배치 (이게 핵심!)
# 사용자가 캡처(Ctrl+C)한 상태에서 이 버튼을 누르면 이미지가 로드됩니다.
pasted_image = paste_image_button(
    label="📋 여기에 이미지를 붙여넣으세요 (클릭)",
    text="이미지가 감지되었습니다! 클릭하여 업로드",
    color="primary",
)

# 5. 이미지가 감지되었을 때의 처리 로직
if pasted_image and pasted_image.image_data is not None:
    # 사용자 화면에 이미지 표시
    with st.chat_message("user"):
        st.image(pasted_image.image_data)
        st.session_state.messages.append({
            "role": "user", 
            "type": "image", 
            "content": pasted_image.image_data
        })

    # --- 6. 여기서부터 '작업 규칙'에 따른 데이터 정제 로직 시작 ---
    with st.chat_message("assistant"):
        with st.spinner("이미지에서 데이터를 추출하고 규칙에 맞춰 정제 중입니다..."):
            # [참고] 실제 구현 시에는 여기서 Gemini API나 OCR 기능을 호출합니다.
            # 예시 출력:
            extracted_data = """
            | 프로그램명 | 방송시간 | 코드번호 | 구분 |
            | :--- | :--- | :--- | :--- |
            | 9시 뉴스 | 09:00 | 9051 | 본방 |
            | 특집 다큐 | 10:30 | 9052 | 재방 |
            """
            st.markdown("### ✅ 데이터 정제 완료")
            st.markdown(extracted_data)
            
            # 대화 기록에 저장
            st.session_state.messages.append({
                "role": "assistant", 
                "type": "text", 
                "content": extracted_data
            })
            
            # 복사가 편하도록 코드 블록으로 한 번 더 제공
            st.code(extracted_data, language="text")

# 7. 추가 텍스트 입력창 (필요한 경우)
if prompt := st.chat_input("추가 요청 사항이 있으면 입력하세요..."):
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
