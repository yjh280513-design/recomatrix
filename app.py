import streamlit as st
import pandas as pd
import requests
import hashlib
import json
import plotly.express as px
from collections import Counter  # <--- 이 줄을 꼭 추가해주세요!

# --- 1. 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwmqdP0R214q6KsssDbj3vZVMsk4iyF61bRO7spNARrMpcoJqqMg_cEhRzib-NV7urYcw/exec"
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# OTT 정보 매핑 (TMDB 제공 기준)
OTT_MAP = {"Netflix": "넷플릭스", "Disney Plus": "디즈니+", "Wavve": "웨이브", "Watcha": "왓챠", "Coupang Play": "쿠팡플레이", "TVING": "티빙"}

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

def send_to_google(data, action="add"):
    # action: add(추가), delete(삭제), update(수정) 기능을 위해 시트 코드 확장이 필요할 수 있습니다.
    # 현재는 추가/로그인 로직 위주로 작동하며 삭제/수정은 시트에서 직접 하는 것을 권장하나, 
    # 아래 코드로 데이터 전송은 동일하게 수행합니다.
    data["action"] = action 
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

# --- 3. 앱 설정 ---
st.set_page_config(page_title="RecoMatrix Pro v3.0", layout="wide")
df = load_data()

# --- 4. 로그인 / 회원가입 ---
if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    t1, t2 = st.tabs(["로그인", "회원가입"])
    with t1:
        u = st.text_input("아이디")
        p = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            user_check = df[(df['user_id'].astype(str) == u) & (df['password'].astype(str) == make_hashes(p))]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else: st.error("정보가 불치합니다.")
    with t2:
        nu, np = st.text_input("아이디 설정"), st.text_input("비번 설정", type="password")
        if st.button("가입"):
            if nu and np:
                send_to_google({"user_id": nu, "password": make_hashes(np), "title": "SYSTEM_JOIN", "rating": 0, "poster_path": "", "media_type": "", "content_id": ""})
                st.success("가입 완료! 로그인하세요.")
    st.stop()

USER_ID = st.session_state['user_id']
my_df = df[(df['user_id'].astype(str) == USER_ID) & (df['title'] != "가입환영") & (df['title'] != "SYSTEM_JOIN")]

# --- 5. 사이드바 (OTT 필터 & 장르 통계) ---
st.sidebar.title(f"👤 {USER_ID}님")
selected_otts = st.sidebar.multiselect("📺 구독 중인 OTT 선택", list(OTT_MAP.values()), default=list(OTT_MAP.values()))

if not my_df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("📊 내 취향 분석")
    # 장르 분석 (간이 장르 매핑)
    genre_list = []
    for _, row in my_df.iterrows():
        # 실제로는 TMDB 상세 호출이 필요하나 성능상 media_type 기반으로 예시 구성
        genre_list.append("애니메이션" if "애니" in row['title'] else "일반/SF") 
    
    fig = px.pie(names=list(Counter(genre_list).keys()), values=list(Counter(genre_list).values()), hole=0.4)
    fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200)
    st.sidebar.plotly_chart(fig, use_container_width=True)

if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 6. 메인 화면 (메뉴 통합) ---
st.title("🚀 RecoMatrix 대시보드")

# 1. 내 라이브러리 (삭제/수정 포함)
st.header("📚 내 라이브러리")
if not my_df.empty:
    cols = st.columns(5)
    for i, row in enumerate(my_df.itertuples()):
        with cols[i % 5]:
            st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
            st.write(f"**{row.title}** (⭐{row.rating})")
            if st.button("삭제/수정", key=f"edit_{row.Index}"):
                st.info("데이터 수정은 현재 구글 시트에서 직접 하시는 것이 가장 안전합니다!")

# 2. 통합 추천 (개별 연관 추천 포함)
st.divider()
st.header("✨ 맞춤형 추천 서비스")
if not my_df.empty:
    # 4점 이상인 모든 작품에 대해 각각 추천 리스트 생성
    top_picks = my_df[my_df['rating'] >= 4.0].tail(3) # 최근 3개 기반
    for _, pick in top_picks.iterrows():
        st.subheader(f"🍿 '{pick['title']}'를 좋아하신 당신에게")
        recom_res = tmdb_api(f"/{pick['media_type']}/{int(pick['content_id'])}/recommendations")["results"]
        
        r_cols = st.columns(5)
        count = 0
        for r in recom_res:
            if count >= 5: break
            title = r.get('title', r.get('name'))
            
            # OTT 정보 가져오기
            provider_res = tmdb_api(f"/{pick['media_type']}/{r['id']}/watch/providers")
            providers = provider_res.get('results', {}).get('KR', {}).get('flatrate', [])
            available_otts = [OTT_MAP[p['provider_name']] for p in providers if p['provider_name'] in OTT_MAP]
            
            # 필터링: 선택한 OTT에 포함된 경우만 표시
            if any(ott in selected_otts for ott in available_otts) or not selected_otts:
                with r_cols[count]:
                    st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path', '')}")
                    st.caption(title)
                    with st.expander("상세 정보"):
                        st.write(f"📝 **줄거리**: {r.get('overview', '정보 없음')[:100]}...")
                        if available_otts:
                            st.write(f"📺 **시청 가능**: {', '.join(available_otts)}")
                            if st.button("지금 보러가기", key=f"link_{r['id']}"):
                                st.write("🔗 해당 OTT 앱/웹으로 이동합니다.")
                count += 1
else:
    st.info("평점을 4점 이상 남겨주시면 정교한 추천이 시작됩니다!")

# 3. 작품 검색 및 추가
st.divider()
st.header("🔍 새로운 작품 찾기")
q = st.text_input("제목을 입력하세요", key="main_search")
if q:
    s_res = tmdb_api("/search/multi", {"query": q})["results"]
    for r in s_res[:3]:
        if r.get('media_type') in ['movie', 'tv']:
            c1, c2 = st.columns([1, 5])
            with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path', '')}", width=100)
            with c2:
                st.subheader(r.get('title', r.get('name')))
                st.write(r.get('overview', ''))
                rate = st.slider("내 평점", 0.5, 5.0, 4.0, 0.5, key=f"rate_{r['id']}")
                if st.button("보관소 저장", key=f"save_{r['id']}"):
                    send_to_google({"user_id": USER_ID, "password": "", "title": r.get('title', r.get('name')), "rating": rate, "poster_path": r.get('poster_path', ''), "media_type": r['media_type'], "content_id": r['id']})
                    st.success("저장 완료!")
                    st.cache_data.clear()
