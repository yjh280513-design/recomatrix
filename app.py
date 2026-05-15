import streamlit as st
import pandas as pd
import requests
import hashlib
import json
import plotly.express as px
from collections import Counter
import random
import time

# --- 1. 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbTeG_23IIXkpwV_aYFvIyrVbLcQYMtyPG4bWcfl-PkFemL66uscFaLdrTWZYDxABjjmw/exec"
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# OTT 로고 및 정보 설정 (11번 반영)
OTT_INFO = {
    "Netflix": {"name": "넷플릭스", "url": "https://www.netflix.com/search?q=", "logo": "https://www.edigitalagency.com.au/wp-content/uploads/Netflix-logo-red-black-png.png"},
    "Disney Plus": {"name": "디즈니+", "url": "https://www.disneyplus.com/search?q=", "logo": "https://cnbl-cdn.bamgrid.com/assets/7fa24ec18a09bc08183181827448377759d5a7d78018e6e5a07204781467554c/original"},
    "Wavve": {"name": "웨이브", "url": "https://www.wavve.com/search/search?searchKeyword=", "logo": "https://upload.wikimedia.org/wikipedia/commons/2/25/Wavve_logo.png"},
    "Watcha": {"name": "왓챠", "url": "https://watcha.com/search?query=", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Watcha_logo.png/640px-Watcha_logo.png"},
    "TVING": {"name": "티빙", "url": "https://www.tving.com/search?keyword=", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Tving_logo.svg/1200px-Tving_logo.svg.png"},
    "Coupang Play": {"name": "쿠팡플레이", "url": "https://www.coupangplay.com/search?q=", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Coupang_Play_Logo.svg/1024px-Coupang_Play_Logo.svg.png"}
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
        data['content_id'] = str(data.get('content_id', ''))
        data['user_id'] = str(data.get('user_id', ''))
        res = requests.post(WEB_APP_URL, data=json.dumps(data))
        return True if res.status_code == 200 else False
    except: return False

@st.cache_data(ttl=1)
def load_data():
    try:
        df = pd.read_csv(SHEET_READ_URL, dtype={'content_id': str, 'user_id': str})
        return df.dropna(subset=['user_id'])
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 2. 로그인 및 회원가입 (10번 반영) ---
st.set_page_config(page_title="RecoMatrix Pro v5.5", layout="wide")
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    tab1, tab2 = st.tabs(["🔐 로그인", "📝 회원가입"])
    with tab1:
        u = st.text_input("아이디")
        p = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            pw_hash = hashlib.sha256(str.encode(p)).hexdigest()
            user_check = df[(df['user_id'] == u) & (df['password'] == pw_hash)]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else: st.error("정보가 올치 않습니다.")
    with tab2:
        nu = st.text_input("새 아이디")
        np = st.text_input("새 비밀번호", type="password")
        if st.button("회원가입"):
            if nu and np:
                pw_h = hashlib.sha256(str.encode(np)).hexdigest()
                send_to_google({"user_id": nu, "password": pw_h, "title": "SYSTEM", "rating": 0, "poster_path": "", "media_type": "", "content_id": "0", "action": "add"})
                st.success("회원가입 성공! 로그인 해주세요.")
    st.stop()

# --- 3. 공통 데이터 정리 (가입환영 숨기기) ---
USER_ID = str(st.session_state['user_id'])
my_df = df[(df['user_id'] == USER_ID) & (~df['title'].str.contains("SYSTEM|가입환영", na=False))]
my_content_ids = my_df['content_id'].tolist()

def clear_detail():
    if 'view_detail' in st.session_state: del st.session_state['view_detail']

# --- 4. 사이드바 (취향 분석 원그래프 및 OTT 선택 - 5, 6번 반영) ---
st.sidebar.title(f"👤 {USER_ID}님")
page = st.sidebar.radio("메뉴 이동", ["✨ 통합 추천", "📚 내 라이브러리", "🔍 작품 검색"], on_change=clear_detail)

# OTT 선택 (통합 추천용)
st.sidebar.divider()
st.sidebar.subheader("🍿 추천용 OTT 선택")
sel_ott = st.sidebar.multiselect("보유 중인 OTT", list(OTT_INFO.keys()), default=list(OTT_INFO.keys()))

# 취향 분석 그래프
if not my_df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("📊 장르 취향 분석")
    all_genres = []
    for _, row in my_df.iterrows():
        m_info = tmdb_api(f"/{row.media_type}/{row.content_id}")
        if 'genres' in m_info: all_genres.extend([g['name'] for g in m_info['genres']])
    if all_genres:
        counts = Counter(all_genres)
        fig = px.pie(names=list(counts.keys()), values=list(counts.values()), hole=0.5)
        fig.update_layout(showlegend=False, height=250, margin=dict(t=0, b=0, l=0, r=0))
        st.sidebar.plotly_chart(fig, use_container_width=True)

if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 5. 상세정보 표시 레이어 (3, 7, 8, 12번 반영) ---
if 'view_detail' in st.session_state:
    r = st.session_state['view_detail']
    st.button("🔙 목록으로", on_click=clear_detail)
    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
    with c2:
        title = r.get('title', r.get('name'))
        m_type = r.get('media_type', 'movie')
        st.title(title)
        st.write(f"📝 **줄거리**: {r.get('overview', '정보 없음')}")
        
        # OTT 로고 및 클릭 이동 (8, 11번 반영)
        st.write("### 📺 시청 가능한 OTT")
        provs = tmdb_api(f"/{m_type}/{r['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
        if provs:
            ocols = st.columns(len(provs) if len(provs) < 6 else 6)
            for idx, p in enumerate(provs[:6]):
                p_name = p['provider_name']
                for ott_key, info in OTT_INFO.items():
                    if ott_key.lower() in p_name.lower() or info['name'] in p_name:
                        with ocols[idx % 6]:
                            st.markdown(f'<a href="{info["url"]}{title}" target="_blank"><img src="{info["logo"]}" width="60"></a>', unsafe_allow_html=True)
                            st.caption(info['name'])
        else: st.info("정보를 찾을 수 없습니다.")

        # 비슷한 추천작 (3번 반영)
        st.divider()
        st.subheader("🍿 비슷한 작품 추천")
        recs = tmdb_api(f"/{m_type}/{r['id']}/recommendations")["results"]
        if recs:
            rcols = st.columns(4)
            for i, rec in enumerate(recs[:4]):
                with rcols[i]:
                    st.image(f"https://image.tmdb.org/t/p/w500{rec.get('poster_path','')}")
                    if st.button("보기", key=f"rec_v_{rec['id']}"):
                        rec['media_type'] = m_type
                        st.session_state['view_detail'] = rec
                        st.rerun()
    st.stop()

# --- 6. 메인 콘텐츠 ---

# (1) 통합 추천
if page == "✨ 통합 추천":
    st.header("✨ 내 취향 맞춤 추천")
    high_rated = my_df[my_df['rating'] >= 4.0]
    if not high_rated.empty:
        if 'recom_list' not in st.session_state or st.button("🔄 새로고침"):
            all_list = []
            for _, row in high_rated.sample(min(len(high_rated), 5)).iterrows():
                res = tmdb_api(f"/{row.media_type}/{row.content_id}/recommendations")["results"]
                for item in res[:15]:
                    item['media_type'] = row.media_type
                    # OTT 필터링 적용
                    p_info = tmdb_api(f"/{item['media_type']}/{item['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
                    if any(any(ott.lower() in p['provider_name'].lower() for ott in sel_ott) for p in p_info):
                        all_list.append(item)
            st.session_state['recom_list'] = all_list[:12]
        
        if st.session_state['recom_list']:
            cols = st.columns(4)
            for i, r in enumerate(st.session_state['recom_list']):
                with cols[i % 4]:
                    st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                    st.write(f"**{r.get('title', r.get('name'))}**")
                    if st.button("상세보기", key=f"tr_d_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
    else: st.info("평점 4점 이상 작품을 등록해주세요.")

# (2) 내 라이브러리 (2, 4번 반영)
elif page == "📚 내 라이브러리":
    st.header("📚 내 라이브러리")
    if not my_df.empty:
        lcols = st.columns(4) # 한 줄당 4개씩 (4번 반영)
        for i, row in enumerate(my_df.itertuples()):
            with lcols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
                st.write(f"**{row.title}** (⭐{row.rating})")
                # 상세/수정 칸 (4번 반영)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👁️ 정보", key=f"lib_v_{row.content_id}"):
                        detail = tmdb_api(f"/{row.media_type}/{row.content_id}")
                        detail['media_type'] = row.media_type
                        st.session_state['view_detail'] = detail
                        st.rerun()
                with c2:
                    with st.popover("✏️ 수정"): # (2번 반영)
                        new_r = st.slider("평점", 0.5, 5.0, float(row.rating), 0.5, key=f"ed_{row.content_id}")
                        if st.button("OK", key=f"up_{row.content_id}"):
                            send_to_google({"user_id": USER_ID, "content_id": str(row.content_id), "rating": new_r, "action": "update"})
                            st.cache_data.clear()
                            st.rerun()
    else: st.info("라이브러리가 비어있습니다.")

# (3) 작품 검색 (1, 9번 반영)
elif page == "🔍 작품 검색":
    st.header("🔍 작품 검색")
    q = st.text_input("제목을 입력하세요")
    if q:
        res = tmdb_api("/search/multi", {"query": q})["results"]
        for r in res[:8]:
            if r.get('media_type') in ['movie', 'tv']:
                c1, c2 = st.columns([1, 5])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with c2:
                    title = r.get('title', r.get('name'))
                    st.subheader(title)
                    cid = str(r['id'])
                    # 중복 등록 방지 (9번 반영)
                    if cid in my_content_ids:
                        st.success("✅ 이미 라이브러리에 있는 작품입니다.")
                    else:
                        # 평점 내리면(슬라이더 조작) 저장 유도 (1번 반영)
                        r_val = st.slider("평점 매기기", 0.5, 5.0, 4.0, 0.5, key=f"s_{r['id']}")
                        if st.button("보관소 저장", key=f"save_{r['id']}"):
                            if send_to_google({"user_id": USER_ID, "title": title, "rating": r_val, "poster_path": r.get('poster_path',''), "media_type": r['media_type'], "content_id": cid, "action": "add"}):
                                st.success("라이브러리에 저장되었습니다!")
                                st.cache_data.clear()
                                st.rerun()
                    if st.button("상세보기", key=f"dt_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
