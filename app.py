import streamlit as st
import pandas as pd
import requests
import hashlib
import json
from collections import Counter

# --- 1. 설정 및 연결 정보 ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwmqdP0R214q6KsssDbj3vZVMsk4iyF61bRO7spNARrMpcoJqqMg_cEhRzib-NV7urYcw/exec"
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# --- 2. 유틸리티 함수 ---
def tmdb_api(endpoint, params={}):
    params['api_key'] = API_KEY
    params['language'] = 'ko-KR'
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", params=params)
        return res.json()
    except: return {}

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_to_google(data):
    try:
        response = requests.post(WEB_APP_URL, data=json.dumps(data))
        return response.text == "Success"
    except: return False

@st.cache_data(ttl=5)
def load_data():
    try:
        return pd.read_csv(SHEET_READ_URL)
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 3. 앱 화면 설정 ---
st.set_page_config(page_title="RecoMatrix Pro v2.0", layout="wide")
df = load_data()

# --- 4. 로그인 및 회원가입 ---
if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    with tab1:
        u = st.text_input("아이디")
        p = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            user_check = df[(df['user_id'].astype(str) == u) & (df['password'].astype(str) == make_hashes(p))]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else: st.error("정보가 일치하지 않습니다.")
    with tab2:
        new_u = st.text_input("새 아이디")
        new_p = st.text_input("새 비밀번호", type="password")
        if st.button("회원가입"):
            if new_u and new_p:
                if send_to_google({"user_id": new_u, "password": make_hashes(new_p), "title": "SYSTEM", "rating": 0, "poster_path": "", "media_type": "", "content_id": ""}):
                    st.success("가입 성공! 로그인해 주세요.")
    st.stop()

# --- 5. 메인 메뉴 (사이드바) ---
USER_ID = st.session_state['user_id']
menu = st.sidebar.selectbox("메뉴 선택", ["🔍 작품 검색 및 평점", "📚 내 라이브러리", "✨ 통합 추천 서비스"])
if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 6. 메뉴별 기능 ---

# (1) 검색 및 저장
if menu == "🔍 작품 검색 및 평점":
    st.title("🔍 작품 검색")
    q = st.text_input("제목을 입력하세요")
    if q:
        results = tmdb_api("/search/multi", {"query": q})["results"]
        for r in results[:5]:
            if r.get('media_type') in ['movie', 'tv']:
                title = r.get('title', r.get('name'))
                col1, col2 = st.columns([1, 4])
                with col1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path', '')}", width=120)
                with col2:
                    st.subheader(title)
                    score = st.slider(f"평점", 0.5, 5.0, 4.0, 0.5, key=f"s_{r['id']}")
                    if st.button("평점 저장", key=f"b_{r['id']}"):
                        if send_to_google({"user_id": USER_ID, "password": "", "title": title, "rating": score, "poster_path": r.get('poster_path', ''), "media_type": r['media_type'], "content_id": r['id']}):
                            st.success(f"'{title}' 저장 완료!")
                            st.cache_data.clear()

# (2) 내 라이브러리 (보관소)
elif menu == "📚 내 라이브러리":
    st.title("📚 내 라이브러리")
    my_df = df[(df['user_id'].astype(str) == USER_ID) & (df['title'] != "SYSTEM")]
    if not my_df.empty:
        cols = st.columns(4)
        for i, row in enumerate(my_df.itertuples()):
            with cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
                st.write(f"**{row.title}**")
                st.write(f"⭐ {row.rating}")
    else: st.info("아직 저장된 작품이 없습니다.")

# (3) 통합 추천 서비스
elif menu == "✨ 통합 추천 서비스":
    st.title("✨ 주현님을 위한 추천")
    my_df = df[(df['user_id'].astype(str) == USER_ID) & (df['rating'] >= 4.0)]
    if not my_df.empty:
        # 가장 최근에 높게 평가한 작품 기반 추천
        target = my_df.iloc[-1]
        st.write(f"✅ 최근에 좋아하신 **'{target.title}'**과 비슷한 작품들입니다.")
        recoms = tmdb_api(f"/{target.media_type}/{int(target.content_id)}/recommendations")["results"]
        
        cols = st.columns(5)
        for i, r in enumerate(recoms[:10]):
            with cols[i % 5]:
                st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path', '')}")
                st.caption(r.get('title', r.get('name')))
    else: st.warning("추천을 받으려면 평점 4점 이상의 작품이 1개 이상 필요합니다.")
