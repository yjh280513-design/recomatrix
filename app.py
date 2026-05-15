import streamlit as st
import pandas as pd
import requests
import hashlib
import json
import plotly.express as px
from collections import Counter
import random

# --- 1. 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzFQtfn4g5tcK8k2XCX01hNUynOpbMk1usnmHwuRw1-dGa555-igK8YA_9qLKKkh9nFVg/exec"
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

OTT_INFO = {
    "Netflix": {"name": "넷플릭스", "url": "https://www.netflix.com/search?q="},
    "Disney Plus": {"name": "디즈니+", "url": "https://www.disneyplus.com/search?q="},
    "Wavve": {"name": "웨이브", "url": "https://www.wavve.com/search/search?searchKeyword="},
    "Watcha": {"name": "왓챠", "url": "https://watcha.com/search?query="},
    "Coupang Play": {"name": "쿠팡플레이", "url": "https://www.coupangplay.com/search?q="},
    "TVING": {"name": "티빙", "url": "https://www.tving.com/search?keyword="},
    "Laftel": {"name": "라프텔", "url": "https://laftel.net/search?q="}
}

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
        requests.post(WEB_APP_URL, data=json.dumps(data))
        return True
    except: return False

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(SHEET_READ_URL)
        return df.dropna(subset=['user_id'])
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 3. 앱 설정 및 로그인 ---
st.set_page_config(page_title="RecoMatrix Pro v4.2", layout="wide")
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    t1, t2 = st.tabs(["로그인", "회원가입"])
    with t1:
        u = st.text_input("아이디")
        p = st.text_input("비밀번호", type="password")
        if st.button("접속"):
            user_check = df[(df['user_id'].astype(str) == u) & (df['password'].astype(str) == make_hashes(p))]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
    st.stop()

# --- 4. 사이드바 및 메뉴 관리 ---
USER_ID = st.session_state['user_id']
my_df = df[(df['user_id'].astype(str) == USER_ID) & (~df['title'].isin(["SYSTEM", "가입환영"]))]

def on_menu_change():
    if 'view_detail' in st.session_state:
        del st.session_state['view_detail']

st.sidebar.title(f"👤 {USER_ID}님")
page = st.sidebar.radio("메뉴 이동", ["✨ 통합 추천", "📚 내 라이브러리", "🔍 작품 검색"], on_change=on_menu_change)

# --- 5. 상세 페이지 (모든 페이지에서 호출 가능) ---
if 'view_detail' in st.session_state:
    r = st.session_state['view_detail']
    st.button("🔙 목록으로 돌아가기", on_click=lambda: st.session_state.pop('view_detail'))
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
    with c2:
        title = r.get('title', r.get('name'))
        st.title(title)
        st.write(f"📝 **줄거리**: {r.get('overview', '정보 없음')}")
        
        providers = tmdb_api(f"/{r.get('media_type', 'movie')}/{r['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
        if providers:
            st.write("### 📺 바로 시청하기")
            for p in providers:
                for key, info in OTT_INFO.items():
                    if key in p['provider_name'] or info["name"] in p['provider_name']:
                        st.link_button(f"{info['name']} 이동", f"{info['url']}{title}")

        st.divider()
        st.subheader(f"🍿 '{title}'와 비슷한 작품")
        recoms = tmdb_api(f"/{r.get('media_type', 'movie')}/{r['id']}/recommendations")["results"]
        if recoms:
            rec_cols = st.columns(4)
            for idx, rec in enumerate(recoms[:4]):
                with rec_cols[idx]:
                    st.image(f"https://image.tmdb.org/t/p/w500{rec.get('poster_path','')}")
                    st.caption(rec.get('title', rec.get('name')))
                    if st.button("상세보기", key=f"rec_sub_{rec['id']}_{idx}"):
                        st.session_state['view_detail'] = rec
                        st.rerun()
    st.stop() # 상세 페이지가 떠 있을 때는 아래 메인 콘텐츠를 보여주지 않음

# --- 6. 메인 콘텐츠 ---

# (1) 통합 추천
if page == "✨ 통합 추천":
    st.header("✨ 통합 추천")
    high_rated = my_df[my_df['rating'] >= 4.0]
    if not high_rated.empty:
        # 추천 데이터 생성 (캐싱을 위해 session_state 활용 권장하나 여기서는 단순화)
        if 'recom_list' not in st.session_state or st.button("🔄 추천 새로고침"):
            all_recoms = []
            for _, row in high_rated.iterrows():
                res = tmdb_api(f"/{row.media_type}/{int(row.content_id)}/recommendations")["results"]
                for item in res[:5]:
                    item['media_type'] = row.media_type # 타입 보정
                    all_recoms.append(item)
            random.shuffle(all_recoms)
            st.session_state['recom_list'] = all_recoms[:16] # 16개만 유지

        cols = st.columns(4)
        for i, r in enumerate(st.session_state['recom_list']):
            with cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                st.write(f"**{r.get('title', r.get('name'))}**")
                # 핵심 수정: 버튼 클릭 시 즉시 리런(Rerun)하여 상단의 상세 페이지 섹션으로 진입하게 함
                if st.button("상세보기", key=f"btn_recom_{r['id']}_{i}"):
                    st.session_state['view_detail'] = r
                    st.rerun()
    else:
        st.info("평점 4점 이상의 작품을 등록해주세요!")

# (2) 내 라이브러리
elif page == "📚 내 라이브러리":
    st.header("📚 내 라이브러리")
    if not my_df.empty:
        lib_cols = st.columns(4)
        for i, row in enumerate(my_df.itertuples()):
            with lib_cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
                st.write(f"**{row.title}**")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👁️ 정보", key=f"lib_info_{row.content_id}"):
                        detail = tmdb_api(f"/{row.media_type}/{row.content_id}")
                        detail['media_type'] = row.media_type
                        st.session_state['view_detail'] = detail
                        st.rerun()
                with c2:
                    with st.popover("✏️"):
                        new_r = st.slider("평점", 0.5, 5.0, float(row.rating), 0.5, key=f"sl_{row.content_id}")
                        if st.button("저장", key=f"sv_{row.content_id}"):
                            send_to_google({"user_id": USER_ID, "content_id": row.content_id, "rating": new_r, "action": "update"})
                            st.cache_data.clear()
                            st.rerun()

# (3) 작품 검색
elif page == "🔍 작품 검색":
    st.header("🔍 작품 검색")
    q = st.text_input("제목 입력")
    if q:
        res = tmdb_api("/search/multi", {"query": q})["results"]
        for i, r in enumerate(res[:8]):
            if r.get('media_type') in ['movie', 'tv']:
                title = r.get('title', r.get('name'))
                c1, c2 = st.columns([1, 5])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with c2:
                    st.subheader(title)
                    r_val = st.slider("평점", 0.5, 5.0, 4.0, 0.5, key=f"sr_{r['id']}")
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("보관소 저장", key=f"ss_{r['id']}"):
                            send_to_google({"user_id": USER_ID, "title": title, "rating": r_val, "poster_path": r.get('poster_path',''), "media_type": r['media_type'], "content_id": r['id'], "action": "add"})
                            st.success("저장 완료")
                            st.cache_data.clear()
                    with col_btn2:
                        if st.button("상세 정보", key=f"sd_{r['id']}_{i}"):
                            st.session_state['view_detail'] = r
                            st.rerun()
