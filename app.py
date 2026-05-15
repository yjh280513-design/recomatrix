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
st.set_page_config(page_title="RecoMatrix Pro v4.0", layout="wide")
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
    with t2:
        nu, np = st.text_input("새 아이디"), st.text_input("새 비번", type="password")
        if st.button("가입 완료"):
            if nu and np:
                send_to_google({"user_id": nu, "password": make_hashes(np), "title": "SYSTEM", "rating": 0, "poster_path": "", "media_type": "", "content_id": "", "action": "add"})
                st.success("가입 성공!")
    st.stop()

# --- 4. 사이드바 (순서 변경 및 분석) ---
USER_ID = st.session_state['user_id']
my_df = df[(df['user_id'].astype(str) == USER_ID) & (~df['title'].isin(["SYSTEM", "가입환영"]))]

st.sidebar.title(f"👤 {USER_ID}님")
# 요청 1번: 순서 변경 (통합 추천 -> 내 라이브러리 -> 작품 검색)
page = st.sidebar.radio("메뉴 이동", ["✨ 통합 추천", "📚 내 라이브러리", "🔍 작품 검색"])
selected_otts = st.sidebar.multiselect("📺 내 OTT", [v["name"] for v in OTT_INFO.values()], default=[v["name"] for v in OTT_INFO.values()])

if not my_df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("📊 장르 취향")
    genre_data = ["애니메이션" if "애니" in str(t) else "영화/기타" for t in my_df['title']]
    fig = px.pie(names=list(Counter(genre_data).keys()), values=list(Counter(genre_data).values()), hole=0.5)
    fig.update_layout(showlegend=False, height=200, margin=dict(t=0, b=0, l=0, r=0))
    st.sidebar.plotly_chart(fig, use_container_width=True)

if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 5. 상세 페이지 (개별 연관 추천 포함) ---
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
        
        # OTT 버튼
        providers = tmdb_api(f"/{r.get('media_type', 'movie')}/{r['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
        if providers:
            st.write("### 📺 바로 시청하기")
            for p in providers:
                for key, info in OTT_INFO.items():
                    if key in p['provider_name'] or info["name"] in p['provider_name']:
                        st.link_button(f"{info['name']} 이동", f"{info['url']}{title}")

        # 요청 2번: 콘텐츠 클릭 시 개별 추천 노출
        st.divider()
        st.subheader(f"🍿 '{title}'와 비슷한 작품")
        recoms = tmdb_api(f"/{r.get('media_type', 'movie')}/{r['id']}/recommendations")["results"]
        if recoms:
            rec_cols = st.columns(4)
            for idx, rec in enumerate(recoms[:4]):
                with rec_cols[idx]:
                    st.image(f"https://image.tmdb.org/t/p/w500{rec.get('poster_path','')}")
                    st.caption(rec.get('title', rec.get('name')))
    st.stop()

# --- 6. 페이지별 메인 콘텐츠 ---

# (1) 통합 추천 페이지
if page == "✨ 통합 추천":
    st.header("✨ 모든 시청 기록 기반 통합 추천")
    # 요청 2번: 모든 고평점 콘텐츠 종합 추천
    high_rated = my_df[my_df['rating'] >= 4.0]
    if not high_rated.empty:
        all_recoms = []
        for _, row in high_rated.iterrows():
            res = tmdb_api(f"/{row.media_type}/{int(row.content_id)}/recommendations")["results"]
            all_recoms.extend(res[:5])
        
        random.shuffle(all_recoms) # 다양하게 섞기
        
        cols = st.columns(4)
        for i, r in enumerate(all_recoms[:12]):
            with cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                st.write(f"**{r.get('title', r.get('name'))}**")
                if st.button("상세보기", key=f"recom_all_{r['id']}_{i}"):
                    st.session_state['view_detail'] = r
                    st.rerun()
    else:
        st.info("평점 4점 이상의 작품이 보관함에 있어야 통합 추천이 가능합니다.")

# (2) 내 라이브러리 페이지
elif page == "📚 내 라이브러리":
    st.header("📚 내 라이브러리")
    # 요청 3번: 한 줄에 포스터 4개씩 시각화
    if not my_df.empty:
        lib_cols = st.columns(4)
        for i, row in enumerate(my_df.itertuples()):
            with lib_cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
                st.write(f"**{row.title}**")
                
                # 요청 4번: 평점 수정/삭제 작게 배치
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👁️ 정보", key=f"lib_view_{row.content_id}"):
                        # row 객체를 TMDB 형태의 딕셔너리로 변환하여 상세 보기 지원
                        st.session_state['view_detail'] = {'id': row.content_id, 'title': row.title, 'poster_path': row.poster_path, 'media_type': row.media_type, 'overview': '라이브러리에서 상세보기 버튼을 눌러 확인하세요.'}
                        st.rerun()
                with c2:
                    with st.popover("✏️ 수정"):
                        new_r = st.slider("평점", 0.5, 5.0, float(row.rating), 0.5, key=f"slider_{row.content_id}")
                        if st.button("확인", key=f"upd_{row.content_id}"):
                            send_to_google({"user_id": USER_ID, "content_id": row.content_id, "rating": new_r, "action": "update"})
                            st.success("수정됨")
                            st.cache_data.clear()
    else: st.info("보관함이 비어있습니다.")

# (3) 작품 검색 페이지
elif page == "🔍 작품 검색":
    st.header("🔍 작품 검색")
    q = st.text_input("제목 입력")
    if q:
        res = tmdb_api("/search/multi", {"query": q})["results"]
        for r in res[:5]:
            if r.get('media_type') in ['movie', 'tv']:
                c1, c2 = st.columns([1, 5])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with c2:
                    st.subheader(r.get('title', r.get('name')))
                    if st.button("상세 정보 보기", key=f"src_main_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
