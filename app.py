import streamlit as st
import pandas as pd
import requests
import hashlib
import json
import plotly.express as px
from collections import Counter
import random
import time

# --- 1. 설정 ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbTeG_23IIXkpwV_aYFvIyrVbLcQYMtyPG4bWcfl-PkFemL66uscFaLdrTWZYDxABjjmw/exec"
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

def tmdb_api(endpoint, params={}):
    params['api_key'] = API_KEY
    params['language'] = 'ko-KR'
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", params=params)
        return res.json()
    except: return {}

def send_to_google(data):
    try:
        requests.post(WEB_APP_URL, data=json.dumps(data))
        return True
    except: return False

@st.cache_data(ttl=2)
def load_data():
    try:
        df = pd.read_csv(SHEET_READ_URL, dtype={'content_id': str, 'user_id': str})
        return df.dropna(subset=['user_id'])
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 2. 앱 시작 및 로그인 ---
st.set_page_config(page_title="RecoMatrix Pro v4.7", layout="wide")
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    u = st.text_input("아이디")
    p = st.text_input("비밀번호", type="password")
    if st.button("접속"):
        pw_hash = hashlib.sha256(str.encode(p)).hexdigest()
        user_check = df[(df['user_id'] == u) & (df['password'] == pw_hash)]
        if not user_check.empty:
            st.session_state['user_id'] = u
            st.rerun()
    st.stop()

# --- 3. 공통 데이터 준비 ---
USER_ID = str(st.session_state['user_id'])
my_df = df[(df['user_id'] == USER_ID) & (~df['title'].isin(["SYSTEM", "가입환영"]))]
# ID 비교 시 오류 방지를 위해 소수점 제거 및 문자열화
my_content_ids = [str(int(float(cid))) for cid in my_df['content_id'].dropna() if cid != ""]

# --- 4. 사이드바 (그래프 복구) ---
st.sidebar.title(f"👤 {USER_ID}님")
def on_menu_change():
    if 'view_detail' in st.session_state: del st.session_state['view_detail']

page = st.sidebar.radio("메뉴 이동", ["✨ 통합 추천", "📚 내 라이브러리", "🔍 작품 검색"], on_change=on_menu_change)

if not my_df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("📊 장르 취향")
    # 제목에 '애니'가 포함된 경우를 분류 (간단 버전)
    genre_labels = ["애니메이션" if "애니" in str(t) else "영화/기타" for t in my_df['title']]
    counts = Counter(genre_labels)
    fig = px.pie(names=list(counts.keys()), values=list(counts.values()), hole=0.5)
    fig.update_layout(showlegend=False, height=200, margin=dict(t=0, b=0, l=0, r=0))
    st.sidebar.plotly_chart(fig, use_container_width=True)

if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 5. 상세보기 페이지 (비슷한 작품 추천 복구) ---
if 'view_detail' in st.session_state:
    r = st.session_state['view_detail']
    st.button("🔙 돌아가기", on_click=lambda: st.session_state.pop('view_detail'))
    
    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
    with c2:
        title = r.get('title', r.get('name'))
        m_type = r.get('media_type', 'movie')
        st.title(title)
        st.write(f"📝 **줄거리**: {r.get('overview', '정보 없음')}")
        
        # OTT 정보
        providers = tmdb_api(f"/{m_type}/{r['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
        st.write("### 📺 시청 가능 OTT")
        if providers:
            for p in providers:
                for key, info in OTT_INFO.items():
                    if key in p['provider_name'] or info["name"] in p['provider_name']:
                        st.link_button(f"{info['name']} 이동", f"{info['url']}{title}")
        else: st.info("한국 스트리밍 정보가 없습니다.")

        st.divider()
        # 중복 저장 방지 및 평점 저장
        if str(r['id']) in my_content_ids:
            st.warning("✅ 이미 보관함에 있습니다.")
        else:
            score = st.slider("평점 주기", 0.5, 5.0, 4.0, 0.5)
            if st.button("내 보관소 저장"):
                if send_to_google({"user_id": USER_ID, "title": title, "rating": score, "poster_path": r.get('poster_path',''), "media_type": m_type, "content_id": str(r['id']), "action": "add"}):
                    st.success("저장 완료!")
                    st.cache_data.clear()
                    st.rerun()

        # 비슷한 작품 추천 (복구됨)
        st.divider()
        st.subheader("🍿 이 작품과 비슷한 추천")
        recom_data = tmdb_api(f"/{m_type}/{r['id']}/recommendations")["results"]
        if recom_data:
            rec_cols = st.columns(4)
            for idx, rec in enumerate(recom_data[:4]):
                with rec_cols[idx]:
                    st.image(f"https://image.tmdb.org/t/p/w500{rec.get('poster_path','')}")
                    st.caption(rec.get('title', rec.get('name')))
                    if st.button("보기", key=f"rec_detail_{rec['id']}"):
                        rec['media_type'] = m_type # 타입 전파
                        st.session_state['view_detail'] = rec
                        st.rerun()
    st.stop()

# --- 6. 메인 콘텐츠 ---

if page == "✨ 통합 추천":
    st.header("✨ 통합 취향 추천")
    high_rated = my_df[my_df['rating'].astype(float) >= 4.0]
    if not high_rated.empty:
        if 'recom_list' not in st.session_state or st.button("🔄 새로고침"):
            all_recoms = []
            for _, row in high_rated.iterrows():
                res = tmdb_api(f"/{row.media_type}/{int(float(row.content_id))}/recommendations")["results"]
                for item in res[:5]:
                    item['media_type'] = row.media_type
                    all_recoms.append(item)
            random.shuffle(all_recoms)
            st.session_state['recom_list'] = all_recoms[:12]

        cols = st.columns(4)
        for i, r in enumerate(st.session_state['recom_list']):
            with cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                st.write(f"**{r.get('title', r.get('name'))}**")
                if st.button("상세보기", key=f"tr_btn_{r['id']}_{i}"):
                    st.session_state['view_detail'] = r
                    st.rerun()
    else: st.info("평점 4점 이상의 작품을 등록해주세요!")

elif page == "📚 내 라이브러리":
    st.header("📚 내 라이브러리")
    if not my_df.empty:
        lib_cols = st.columns(4)
        for i, row in enumerate(my_df.itertuples()):
            with lib_cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
                st.write(f"**{row.title}**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("👁️", key=f"lib_v_{row.content_id}"):
                        detail = tmdb_api(f"/{row.media_type}/{int(float(row.content_id))}")
                        detail['media_type'] = row.media_type
                        st.session_state['view_detail'] = detail
                        st.rerun()
                with c2:
                    with st.popover("✏️"):
                        new_r = st.slider("수정", 0.5, 5.0, float(row.rating), 0.5, key=f"s_{row.content_id}")
                        if st.button("OK", key=f"up_{row.content_id}"):
                            send_to_google({"user_id": USER_ID, "content_id": str(int(float(row.content_id))), "rating": new_r, "action": "update"})
                            st.cache_data.clear()
                            st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_{row.content_id}"):
                        send_to_google({"user_id": USER_ID, "content_id": str(int(float(row.content_id))), "action": "delete"})
                        st.cache_data.clear()
                        st.rerun()
    else: st.info("라이브러리가 비어있습니다.")

elif page == "🔍 작품 검색":
    st.header("🔍 작품 검색")
    q = st.text_input("제목 검색")
    if q:
        res = tmdb_api("/search/multi", {"query": q})["results"]
        for i, r in enumerate(res[:8]):
            if r.get('media_type') in ['movie', 'tv']:
                title = r.get('title', r.get('name'))
                c1, c2 = st.columns([1, 5])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with c2:
                    st.subheader(title)
                    if str(r['id']) in my_content_ids:
                        st.success("✅ 이미 보관함에 있습니다.")
                    else:
                        r_val = st.slider("평점", 0.5, 5.0, 4.0, 0.5, key=f"sr_{r['id']}")
                        if st.button("보관소 저장", key=f"save_{r['id']}"):
                            send_to_google({"user_id": USER_ID, "title": title, "rating": r_val, "poster_path": r.get('poster_path',''), "media_type": r['media_type'], "content_id": str(r['id']), "action": "add"})
                            st.cache_data.clear()
                            st.rerun()
                    if st.button("상세 정보", key=f"src_dt_{r['id']}_{i}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
