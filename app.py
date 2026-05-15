import streamlit as st
import pandas as pd
import requests
import hashlib
import json
import plotly.express as px
from collections import Counter
import random

# --- 1. 설정 및 API (주현님이 주신 새 URL 반영) ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
# 보내주신 새로운 URL로 교체했습니다.
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzdhi4I85YhuO3vP4c23MIqEEN8rmVr6Mka2mDOSaO_LaOcN9PSv1XO3tfvQEava8iehw/exec"
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

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
        # 핵심: content_id를 소수점 없는 순수 문자열로 변환 (저장/수정 실패의 주원인 해결)
        if 'content_id' in data:
            data['content_id'] = str(int(float(data['content_id'])))
        
        # POST 요청 전송
        res = requests.post(WEB_APP_URL, data=json.dumps(data))
        return True if "Success" in res.text or res.status_code == 200 else False
    except Exception as e:
        st.error(f"전송 오류: {e}")
        return False

@st.cache_data(ttl=1)
def load_data():
    try:
        # 시트 데이터를 읽을 때 content_id를 문자열로 강제 지정
        df = pd.read_csv(SHEET_READ_URL, dtype={'content_id': str, 'user_id': str})
        return df.dropna(subset=['user_id'])
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 2. 로그인 및 회원가입 ---
st.set_page_config(page_title="RecoMatrix Pro v5.6", layout="wide")
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    t1, t2 = st.tabs(["🔐 로그인", "📝 회원가입"])
    with t1:
        u = st.text_input("아이디", key="l_u")
        p = st.text_input("비밀번호", type="password", key="l_p")
        if st.button("로그인"):
            pw_h = hashlib.sha256(str.encode(p)).hexdigest()
            user_check = df[(df['user_id'] == u) & (df['password'] == pw_h)]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else: st.error("정보가 일치하지 않습니다.")
    with t2:
        nu = st.text_input("새 아이디", key="s_u")
        np = st.text_input("새 비밀번호", type="password", key="s_p")
        if st.button("가입하기"):
            if nu and np:
                pw_h = hashlib.sha256(str.encode(np)).hexdigest()
                # 회원가입 시 시스템 데이터 전송
                if send_to_google({"user_id": nu, "password": pw_h, "title": "SYSTEM", "rating": 0, "poster_path": "", "media_type": "", "content_id": "0", "action": "add"}):
                    st.success("가입 성공! 로그인 해주세요.")
                    st.cache_data.clear()
    st.stop()

# --- 3. 데이터 정리 ---
USER_ID = str(st.session_state['user_id'])
my_df = df[(df['user_id'] == USER_ID) & (~df['title'].str.contains("SYSTEM|가입환영", na=False))]
# content_id 리스트를 깨끗하게 정리 (비교용)
my_content_ids = [str(int(float(cid))) for cid in my_df['content_id'].dropna() if cid != "0"]

def clear_detail():
    if 'view_detail' in st.session_state: del st.session_state['view_detail']

# --- 4. 사이드바 (그래프 & OTT) ---
st.sidebar.title(f"👤 {USER_ID}님")
page = st.sidebar.radio("메뉴 이동", ["✨ 통합 추천", "📚 내 라이브러리", "🔍 작품 검색"], on_change=clear_detail)

st.sidebar.divider()
sel_ott = st.sidebar.multiselect("보유 중인 OTT (추천용)", list(OTT_INFO.keys()), default=list(OTT_INFO.keys()))

if not my_df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("📊 내 장르 취향")
    all_g = []
    for _, row in my_df.iterrows():
        info = tmdb_api(f"/{row.media_type}/{row.content_id}")
        if 'genres' in info: all_g.extend([g['name'] for g in info['genres']])
    if all_g:
        fig = px.pie(names=list(Counter(all_g).keys()), values=list(Counter(all_g).values()), hole=0.5)
        fig.update_layout(showlegend=False, height=220, margin=dict(t=0,b=0,l=0,r=0))
        st.sidebar.plotly_chart(fig, use_container_width=True)

if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 5. 상세 페이지 (OTT 로고/추천작 포함) ---
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
        st.write(f"📝 **줄거리**: {r.get('overview', '줄거리 정보가 없습니다.')}")
        
        st.write("### 📺 시청 가능한 OTT")
        provs = tmdb_api(f"/{m_type}/{r['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
        if provs:
            ocols = st.columns(6)
            for i, p in enumerate(provs[:6]):
                for k, info in OTT_INFO.items():
                    if k.lower() in p['provider_name'].lower() or info['name'] in p['provider_name']:
                        with ocols[i]:
                            st.markdown(f'[![Logo]({info["logo"]})]({info["url"]}{title})', unsafe_allow_html=True)
                            st.caption(info['name'])
        else: st.info("한국 스트리밍 정보가 없습니다.")

        st.divider()
        st.subheader("🍿 비슷한 작품 추천")
        recs = tmdb_api(f"/{m_type}/{r['id']}/recommendations")["results"]
        if recs:
            rcols = st.columns(4)
            for i, rec in enumerate(recs[:4]):
                with rcols[i]:
                    st.image(f"https://image.tmdb.org/t/p/w500{rec.get('poster_path','')}")
                    if st.button("보기", key=f"rec_{rec['id']}"):
                        rec['media_type'] = m_type
                        st.session_state['view_detail'] = rec
                        st.rerun()
    st.stop()

# --- 6. 메인 콘텐츠 ---

if page == "✨ 통합 추천":
    st.header("✨ 내 취향 기반 추천")
    high_rated = my_df[my_df['rating'] >= 4.0]
    if not high_rated.empty:
        if 'recom_list' not in st.session_state or st.button("🔄 새로고침"):
            all_list = []
            for _, row in high_rated.sample(min(len(high_rated), 5)).iterrows():
                res = tmdb_api(f"/{row.media_type}/{row.content_id}/recommendations")["results"]
                for item in res[:10]:
                    item['media_type'] = row.media_type
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
                    if st.button("상세보기", key=f"tr_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
    else: st.info("평점 4점 이상 작품을 등록해주세요.")

elif page == "📚 내 라이브러리":
    st.header("📚 내 라이브러리")
    if not my_df.empty:
        lcols = st.columns(4)
        for i, row in enumerate(my_df.itertuples()):
            with lcols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
                st.write(f"**{row.title}** (⭐{row.rating})")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👁️ 정보", key=f"lv_{row.content_id}"):
                        dt = tmdb_api(f"/{row.media_type}/{row.content_id}")
                        dt['media_type'] = row.media_type
                        st.session_state['view_detail'] = dt
                        st.rerun()
                with c2:
                    with st.popover("✏️ 수정"):
                        new_r = st.slider("평점", 0.5, 5.0, float(row.rating), 0.5, key=f"ed_{row.content_id}")
                        if st.button("확인", key=f"ok_{row.content_id}"):
                            # 'update' 액션 전송
                            if send_to_google({"user_id": USER_ID, "content_id": str(row.content_id), "rating": new_r, "action": "update"}):
                                st.success("수정 완료")
                                st.cache_data.clear()
                                st.rerun()
    else: st.info("보관함이 비어있습니다.")

elif page == "🔍 작품 검색":
    st.header("🔍 작품 검색")
    query = st.text_input("제목을 입력하세요")
    if query:
        res = tmdb_api("/search/multi", {"query": query})["results"]
        for r in res[:8]:
            if r.get('media_type') in ['movie', 'tv']:
                c1, c2 = st.columns([1, 5])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with c2:
                    title = r.get('title', r.get('name'))
                    st.subheader(title)
                    cid = str(r['id'])
                    if cid in my_content_ids:
                        st.success("✅ 이미 보관함에 있습니다.")
                    else:
                        r_val = st.slider("평점 선택", 0.5, 5.0, 4.0, 0.5, key=f"sr_{r['id']}")
                        if st.button("보관소 저장", key=f"sv_{r['id']}"):
                            # 'add' 액션 전송
                            if send_to_google({"user_id": USER_ID, "title": title, "rating": r_val, "poster_path": r.get('poster_path',''), "media_type": r['media_type'], "content_id": cid, "action": "add"}):
                                st.success("저장되었습니다!")
                                st.cache_data.clear()
                                st.rerun()
                    if st.button("상세보기", key=f"dt_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
