import streamlit as st
import pandas as pd
import requests
import hashlib
import json

# --- 1. 설정 및 연결 정보 ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"

# 주현님이 방금 만든 '비밀 통로' 주소
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwmqdP0R214q6KsssDbj3vZVMsk4iyF61bRO7spNARrMpcoJqqMg_cEhRzib-NV7urYcw/exec"

# 구글 시트 데이터 읽기용 주소 (CSV)
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# --- 2. 주요 기능 함수 ---
def tmdb_api(endpoint, params={}):
    params['api_key'] = API_KEY
    params['language'] = 'ko-KR'
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", params=params)
        return res.json()
    except: return {}

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# 구글 시트에 데이터를 전송(쓰기)하는 함수
def send_to_google(data):
    try:
        response = requests.post(WEB_APP_URL, data=json.dumps(data))
        return response.text == "Success"
    except:
        return False

# 구글 시트에서 데이터를 가져오는(읽기) 함수
@st.cache_data(ttl=5)
def load_data():
    try:
        return pd.read_csv(SHEET_READ_URL)
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 3. 앱 화면 구성 ---
st.set_page_config(page_title="RecoMatrix Pro", layout="wide")
df = load_data()

# 로그인 세션 관리
if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        u = st.text_input("아이디")
        p = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            # 시트에서 아이디와 비번(해시) 대조
            user_check = df[(df['user_id'].astype(str) == u) & (df['password'].astype(str) == make_hashes(p))]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")

    with tab2:
        new_u = st.text_input("새 아이디")
        new_p = st.text_input("새 비밀번호", type="password")
        if st.button("회원가입"):
            if new_u in df['user_id'].astype(str).values:
                st.warning("이미 사용 중인 아이디입니다.")
            elif new_u and new_p:
                register_data = {
                    "user_id": new_u,
                    "password": make_hashes(new_p),
                    "title": "가입환영", "rating": 5, "poster_path": "", "media_type": "", "content_id": ""
                }
                if send_to_google(register_data):
                    st.success("회원가입 성공! 이제 로그인 탭에서 접속하세요.")
                    st.cache_data.clear() # 데이터 새로고침
                else:
                    st.error("전송 오류가 발생했습니다.")
    st.stop()

# --- 4. 로그인 성공 후 메인 화면 ---
USER_ID = st.session_state['user_id']
st.sidebar.subheader(f"👋 반가워요, {USER_ID}님!")
if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

st.title("🔍 작품을 검색하고 평점을 남겨보세요")

q = st.text_input("영화/애니메이션 제목 입력")
if q:
    results = tmdb_api("/search/multi", {"query": q})["results"]
    for r in results[:5]:
        if r.get('media_type') in ['movie', 'tv']:
            title = r.get('title', r.get('name'))
            poster = r.get('poster_path', '')
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(f"https://image.tmdb.org/t/p/w500{poster}", width=120)
            with col2:
                st.subheader(title)
                score = st.slider(f"'{title}'의 평점", 0.5, 5.0, 4.0, 0.5, key=f"s_{r['id']}")
                if st.button("내 보관소에 저장", key=f"b_{r['id']}"):
                    save_data = {
                        "user_id": USER_ID,
                        "password": "", # 평점 저장 시엔 비번 불필요
                        "title": title,
                        "rating": score,
                        "poster_path": poster,
                        "media_type": r['media_type'],
                        "content_id": r['id']
                    }
                    if send_to_google(save_data):
                        st.success(f"'{title}' 저장 완료!")
                        st.cache_data.clear()
                    else:
                        st.error("저장 실패. 네트워크를 확인하세요.")

st.divider()
st.subheader("📋 내 평점 목록 (실시간 시트 데이터)")
my_ratings = df[df['user_id'].astype(str) == USER_ID]
if not my_ratings.empty:
    st.dataframe(my_ratings[['title', 'rating', 'media_type']], use_container_width=True)
else:
    st.info("아직 저장된 데이터가 없습니다.")
