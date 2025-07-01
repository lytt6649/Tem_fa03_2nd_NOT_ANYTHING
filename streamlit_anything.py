import os
import sys
import streamlit as st
import folium
import requests
from streamlit_folium import st_folium
import urllib.request
import re
import json
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 가운데 오는 컨텐츠 영역(라운드) 꽉차게 변경
st.set_page_config(layout="wide")

# CSS를 활용한 사이드바 크기 조절
st.markdown(
    """
    <style>
        /* 사이드바 크기 조절 */
        [data-testid="stSidebar"] {
            width: 450px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# 사이드바 요소 추가
with st.sidebar:
    st.title("맛 형용사 입력으로 검색하기")
    st.markdown("검색어를 입력하세요.<br><small>검색어 앞에 #을 꼭 붙여주세요!</small><br><small>예시) #매운, #달콤한, #고소한, #바삭한, #칼칼한 등</small>", unsafe_allow_html=True)
    search_query = st.text_input("", placeholder="#검색어 입력")

# 검색어 나누기
search_query = search_query.split(',')
search_query = [q.strip() for q in search_query] # 검색어 앞뒤 공백 제거

if len(search_query) == 1:
    x = search_query[0]
    st.session_state.x = x
elif len(search_query) == 2:
    x = search_query[0]
    y = search_query[1]
    st.session_state.x = x
    st.session_state.y = y
elif len(search_query) == 3:
    x = search_query[0]
    y = search_query[1]
    z = search_query[2]
    st.session_state.x = x
    st.session_state.y = y
    st.session_state.z = z
else:
    st.sidebar.markdown("이 버전에서는 맛형용사는 3개까지만 입력할 수 있습니다.")

# 데이터 불러오기
# 파일 불러오기
data_list = []
for x in range(1, 27):
    data = pd.read_csv(f'맛형용사/맛형용사 ({x}).csv', encoding="utf-8")
    data_list.append(data)

# 비율과 맛도리 알고리즘 식 계산 열 추가
for x in range(0, 26):
    data_list[x]['비율'] = 0.0
    for y in range(len(data_list[x]['맛형용사'])):
        data_list[x].loc[y, '비율'] = data_list[x].loc[y, '개수'] / data_list[x]['개수'].sum()
        data_list[x].loc[y, '알고리즘'] = data_list[x].loc[y, '개수'] * data_list[x].loc[y, '비율']

# 하나의 파일로 합치기
df = pd.concat([data_list[0], data_list[1]], axis=0)
for x in range(2, 26):
    df = pd.concat([df, data_list[x]], axis=0)
df.reset_index(drop=True, inplace=True)

# 3. Multi Select 기능을 통한 형태소 사전 내 선택 기능 추가
st.sidebar.title('키워드 선택으로 검색하기')
keyword_display = st.sidebar.empty()  # 먼저 빈 markdown을 만들어 둠
# multiselect를 통해 키워드 선택
options = st.sidebar.multiselect('작성하기 어렵다면 선택해보세요!', 
                                 ['#달콤한', '#새콤한', '#짭짤한', '#쌉쌀한', '#감칠맛',  
                                  '#매운', '#얼얼한', '#칼칼한', '#얼큰한', '#고소한', 
                                  '#구수한', '#불맛', '#싱거운', '#담백한', '#맑은',
                                  '#진한', '#연한', '#쫄깃한', '#바삭한', '#부드러운', 
                                  '#느끼한', '#걸죽한', '#꾸덕한'])
st.session_state.options = options                                  
if len(options) <= 3: 
    selected_keywords = ', '.join(options) 
elif len(options) > 3:
    selected_keywords = '이 버전에서는 맛형용사는 3개까지만 입력할 수 있습니다.'
else:  # options 리스트가 비어 있는 경우
    selected_keywords = '없음'  # '없음'이라는 문자열을 사용
keyword_display.markdown(f"현재 선택된 키워드: {selected_keywords}")

# 함수 모음집
# 맛도리알고리즘 사용 함수
def 맛도리알고리즘(x, y, z):
    if (type(x) == str) & (y==1) & (z==1):
        df_taste = df.loc[df['맛형용사']==x]
    elif (type(x) == str) & (type(y) == str) & (z==1):
        df_taste = df.loc[(df['맛형용사']==x) | (df['맛형용사']==y)]
        restaurant_counts = df_taste['식당이름'].value_counts()
        selected_restaurants = restaurant_counts[restaurant_counts >= 2].index
        df_taste = df[df['식당이름'].isin(selected_restaurants)]
        df_taste = df_taste.loc[(df['맛형용사']==x) | (df_taste['맛형용사']==y)]
    elif (type(x) == str) & (type(y) == str) & (type(z) == str):
        df_taste = df.loc[(df['맛형용사']==x) | (df['맛형용사']==y) | (df['맛형용사']==z)]
        restaurant_counts = df_taste['식당이름'].value_counts()
        selected_restaurants = restaurant_counts[restaurant_counts >= 3].index
        df_taste = df[df['식당이름'].isin(selected_restaurants)]
        df_taste = df_taste.loc[(df['맛형용사']==x) | (df_taste['맛형용사']==y) | (df_taste['맛형용사']==z)]
    df_taste = df_taste[['식당이름', '알고리즘', '비율', '개수', '맛형용사']]
    df_taste = df_taste.groupby(by='식당이름', as_index=False)[['알고리즘']].sum()
    df_taste = df_taste.sort_values(by='알고리즘', ascending=False, ignore_index=True)
    return df_taste

# 메인 화면을 업데이트할 placeholder 생성
content_placeholder = st.empty()

# 메인화면
def main():
    with content_placeholder.container(): # 컨테이너를 사용해 내부 내용을 변경 가능하도록 
        empty, con = st.columns([0.05, 3])    
        with empty:
            st.write(" ")

        with con:        
            st.title("아무거나!")
            st.subheader("키워드 기반의 원하는 맛 형용사 필터링 API, \"!아무거나\"")
            st.markdown("<h1 style='font-size:20px;'>사용자가 희망하는 맛과 부합하는 키워드(맛 형용사)를 기반으로 음식점을 필터링하여</h1>", unsafe_allow_html=True)
            st.markdown("<h1 style='font-size:20px;'>메뉴 결정을 위한 소요 시간과 스트레스는 감소하고, 식사 만족도는 높게!</h1>", unsafe_allow_html=True)
            video = 'C:/Users/Admin/workspace/project(2)/Anything 홍보영상_KPMG_3기_3팀.mp4'
            st.video(video)

# 검색할 시 변경되는 화면
def main2():
    with content_placeholder.container():    
        empty1, con1, empty2, con2, empty3, con3, empty4 = st.columns([0.05, 0.5, 0.1, 1.0, 0.1, 1.4, 0.05])
        
        with empty1:
            st.write(" ")

        with con1:
            x = st.session_state["x"]
            options = st.session_state["options"]

            if x != "":
                st.title("목록")
                st.write(f"입력된 검색어  \n{search_query}")
                x = ""
                y = 1
                z = 1
                # 검색어 변수 불러오기
                if len(search_query) == 1:
                    x = st.session_state["x"]              
                elif len(search_query) == 2:
                    x = st.session_state["x"]   
                    y = st.session_state["y"] 
                elif len(search_query) == 3:
                    x = st.session_state["x"]   
                    y = st.session_state["y"]
                    z = st.session_state["z"]

                # 예제 식당 리스트 (실제로는 검색 결과를 기반으로 변경 가능)
                df_good = 맛도리알고리즘(x, y, z)

                restaurant_list = list(df_good['식당이름'])

                # 3. 식당 리스트를 선택할 수 있게 해주기            
                for s in restaurant_list:
                    if st.button(s):  
                        restaurant = s
                        st.session_state.restaurant = restaurant

                        # 4. 네이버 API를 통해 해당 식당의 주소를 가져오기
                        client_id = "uRvRYNCvOGdRsAbvhqfw"
                        client_secret = "6wFBSCn4Il"

                        encText = urllib.parse.quote(restaurant)
                        url = "https://openapi.naver.com/v1/search/local?query=" + encText + \
                            "&display=1" + "&start=1" + '&sort=comment'

                        request = urllib.request.Request(url)
                        request.add_header("X-Naver-Client-Id",client_id)
                        request.add_header("X-Naver-Client-Secret",client_secret)
                        response = urllib.request.urlopen(request)
                        rescode = response.getcode()
                        if(rescode==200):
                            response_body = response.read()
                            print(response_body.decode('utf-8'))
                        else:
                            print("Error Code:" + rescode)

                        if rescode == 200:
                            text_data = response_body.decode('utf-8')
                            json_data = json.loads(text_data)
                            print(json_data)

                        # HTML 태그 제거 함수
                        def remove_html_tags(text):
                            if text:
                                clean_text = re.sub(r'<.*?>', '', text)  # 정규표현식으로 HTML 태그 제거
                                return clean_text
                            return text

                        # json_data 적용
                        cleaned_store_results = []
                        for store in json_data['items']:
                            clean_store = {
                                'title': remove_html_tags(store['title']),
                                'roadAddress':store['roadAddress']
                            }

                            # 중복 데이터 방지
                            if clean_store not in cleaned_store_results:
                                cleaned_store_results.append(clean_store)
                        
                        address = store['roadAddress']
                        st.session_state.address = address

                        client_id = "uRvRYNCvOGdRsAbvhqfw"
                        client_secret = "6wFBSCn4Il"

                        url = f"https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query={address}"
                        headers = {
                            "X-NCP-APIGW-API-KEY-ID": 'cse5mt5oai',
                            "X-NCP-APIGW-API-KEY": '2naVTMdx2Ls50VYimgbA7fe1JEbM3MyxQutG30Um'
                        }
                        response = requests.get(url, headers=headers)
                        data = response.json()

                        if data.get('addresses'):
                            longitude = float(data['addresses'][0].get('x'))  # x 좌표 (경도)
                            latitude = float(data['addresses'][0].get('y'))   # y 좌표 (위도)


                        restaurant_coordinates = (latitude, longitude)
                        st.session_state.restaurant_coordinates = restaurant_coordinates

            elif len(options) > 0:
                st.title("목록")
                st.write(f"입력된 검색어  \n{options}")
                x = ""
                y = 1
                z = 1
                if len(options) == 1:
                    x = options[0]
                elif len(options) == 2:
                    x = options[0]
                    y = options[1]
                elif len(options) == 3:
                    x = options[0]
                    y = options[1]
                    z = options[2]

                # 예제 식당 리스트 (실제로는 검색 결과를 기반으로 변경 가능)
                df_good = 맛도리알고리즘(x, y, z)         

                restaurant_list = list(df_good['식당이름'])

                # 3. 식당 리스트를 선택할 수 있게 해주기            
                for s in restaurant_list:
                    if st.button(s):  
                        restaurant = s
                        st.session_state.restaurant = restaurant

                        # 4. 네이버 API를 통해 해당 식당의 주소를 가져오기
                        client_id = "uRvRYNCvOGdRsAbvhqfw"
                        client_secret = "6wFBSCn4Il"

                        encText = urllib.parse.quote(restaurant)
                        url = "https://openapi.naver.com/v1/search/local?query=" + encText + \
                            "&display=1" + "&start=1" + '&sort=comment'

                        request = urllib.request.Request(url)
                        request.add_header("X-Naver-Client-Id",client_id)
                        request.add_header("X-Naver-Client-Secret",client_secret)
                        response = urllib.request.urlopen(request)
                        rescode = response.getcode()
                        if(rescode==200):
                            response_body = response.read()
                            print(response_body.decode('utf-8'))
                        else:
                            print("Error Code:" + rescode)

                        if rescode == 200:
                            text_data = response_body.decode('utf-8')
                            json_data = json.loads(text_data)
                            print(json_data)

                        # HTML 태그 제거 함수
                        def remove_html_tags(text):
                            if text:
                                clean_text = re.sub(r'<.*?>', '', text)  # 정규표현식으로 HTML 태그 제거
                                return clean_text
                            return text

                        # json_data 적용
                        cleaned_store_results = []
                        for store in json_data['items']:
                            clean_store = {
                                'title': remove_html_tags(store['title']),
                                'roadAddress':store['roadAddress']
                            }

                            # 중복 데이터 방지
                            if clean_store not in cleaned_store_results:
                                cleaned_store_results.append(clean_store)
                        
                        address = store['roadAddress']
                        st.session_state.address = address

                        client_id = "uRvRYNCvOGdRsAbvhqfw"
                        client_secret = "6wFBSCn4Il"

                        url = f"https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query={address}"
                        headers = {
                            "X-NCP-APIGW-API-KEY-ID": 'cse5mt5oai',
                            "X-NCP-APIGW-API-KEY": '2naVTMdx2Ls50VYimgbA7fe1JEbM3MyxQutG30Um'
                        }
                        response = requests.get(url, headers=headers)
                        data = response.json()

                        if data.get('addresses'):
                            longitude = float(data['addresses'][0].get('x'))  # x 좌표 (경도)
                            latitude = float(data['addresses'][0].get('y'))   # y 좌표 (위도)


                        restaurant_coordinates = (latitude, longitude)
                        st.session_state.restaurant_coordinates = restaurant_coordinates

        with empty2:
            st.write(" ")    

        with con2:
            if "restaurant_coordinates" in st.session_state:
                restaurant = st.session_state["restaurant"]
                st.title("맛형용사 분석")

                # 데이터 불러오기
                df_review = df.loc[df['식당이름'] == restaurant]
                df_review = df_review.reset_index(drop=True)
                df_review = df_review[['맛형용사', '개수', '비율', '알고리즘']]                   

                # 데이터 전처리
                df_pie = df_review[['맛형용사', '개수']] # 맛형용사, 개수 열만 사용
                df_pie.loc[df_pie['개수'] <= 10, '맛형용사'] = '#기타'
                df_pie = df_pie.groupby(by='맛형용사', as_index=False).sum() # 맛형용사 중 중복행으로 있는 '#기타'를 묶기
                df_pie = df_pie.sort_values(by='개수', ascending=False, ignore_index=True) # 내림차순
                # '#기타' 행을 분리 후 가장 아래로 이동
                df_etc = df_pie[df_pie['맛형용사'] == '#기타']  # '#기타' 행 따로 저장
                df_main = df_pie[df_pie['맛형용사'] != '#기타']  # 나머지 데이터
                df_pie = pd.concat([df_main, df_etc], ignore_index=True) # 다시 합치기 (기본 데이터 + '#기타' 행)

                # 파이차트 그리기
                fig = go.Figure()
                # 차트 제목 지정
                fig.update_layout(
                    title={
                            'text': f"<b style='display:block; text-align:center;'>{restaurant}의 손맛</b>",
                            'font': dict(size=30),
                            'x': 0.5,
                            'xanchor': 'center'
                        },
                    template='plotly_white',
                    width=600,  # 그래프 너비
                    height=600,  # 그래프 높이
                    margin=dict(l=50, r=50, t=100, b=100),
                    legend=dict(
                        x=0.5,  # 가로 위치
                        y=-0.05,  # 세로 위치
                        xanchor="center",  # 범례 박스 기준점 (left, center, right)
                        yanchor="top",  # 범례 박스 기준점 (top, middle, bottom)
                        font=dict(size=20),  # 범례 글씨 크기
                        orientation="h", # 범례 항목을 가로로 배치
                        itemwidth=30,  # 각 범례 항목의 너비 조정
                    )
                )

                # 특정 라벨 찾기 (평균 이상인 값들만 글씨 키우기)
                mean_value = df_pie['개수'][:5].sum() / len(df_pie['개수'][:5])  # 상위 탑 5 맛형용사에 대한 평균
                highlight_labels = [label for label, count in zip(df_pie['맛형용사'], df_pie['개수']) if count >= mean_value]

                # HTML 스타일 적용 (평균 이상이면 크기 키우기)
                highlight_size = 25  # 강조할 글씨 크기
                default_size = 20  # 기본 글씨 크기

                custom_labels = [
                    f"<span style='font-size:{highlight_size}px'><b>{label}</b></span>"
                    if label in highlight_labels and label != '#기타' else f"<span style='font-size:{default_size}px'>{label}</span>"
                    for label in df_pie['맛형용사']
                ]

                # 전체 개수 합산하여 백분율 계산
                total = sum(df_pie['개수'])
                percentages = [(v / total) * 100 for v in df_pie['개수']]

                # 비율에 따른 동적 폰트 크기 설정
                min_size, max_size = 15, 25  # 최소, 최대 글씨 크기
                scaled_sizes = np.interp(percentages, (min(percentages), max(percentages)), (min_size, max_size))

                # HTML 스타일 적용 (각 비율에 따라 크기 조정)
                custom_percentages = [
                    f"<span style='font-size:{size}px'><b>{p:.1f}%</b></span>"
                    for p, size in zip(percentages, scaled_sizes)
                ]


                fig.add_trace(go.Pie(
                    labels=df_pie['맛형용사'],
                    values=df_pie['개수'],
                    hole=0.4,  
                    direction='clockwise',
                    textinfo="label",  # 라벨만 표시
                    textposition="outside",  # 바깥쪽 배치
                    texttemplate="%{customdata}",  # HTML 스타일 적용
                    customdata=custom_labels,  # HTML이 적용된 백분율 전달
                    sort=False,
                    domain={'x': [0, 1], 'y': [0, 1]}  # 크기 균일하게 맞춤
                ))

                fig.add_trace(go.Pie(
                    labels=df_pie['맛형용사'],
                    values=df_pie['개수'],
                    hole=0.4,
                    direction='clockwise',  
                    textinfo="percent",  # 백분율만 표시
                    textposition="inside",  # 안쪽 배치
                    hoverinfo="none",  # 마우스 오버 시 중복 방지
                    showlegend=False,  # 범례 중복 방지
                    texttemplate="%{customdata}",  # HTML 스타일 적용
                    customdata=custom_percentages,  # HTML이 적용된 백분율 전달
                    sort=False,
                    domain={'x': [0, 1], 'y': [0, 1]}  # 크기 균일하게 맞춤
                ))

                # 파이차트 보기
                st.plotly_chart(fig)

                # 데이터 프레임 보기
                if (len(df_review['맛형용사'])) <= 5: 
                    st.dataframe(df_review, width=600, height=200)
                elif 5 < (len(df_review['맛형용사'])) <= 10 :
                    st.dataframe(df_review, width=600, height=400)
                elif 10 < (len(df_review['맛형용사'])) <= 15 :
                    st.dataframe(df_review, width=600, height=600)
                elif 15 < (len(df_review['맛형용사'])) <= 20 :
                    st.dataframe(df_review, width=600, height=800)
                elif 20 < (len(df_review['맛형용사'])) <= 25 :
                    st.dataframe(df_review, width=600, height=1000)
                elif 25 < (len(df_review['맛형용사'])):
                    st.dataframe(df_review, width=600, height=1200) 

        with empty3:
            st.write(" ")    

        with con3:
            if "restaurant_coordinates" in st.session_state:
                restaurant_coordinates = st.session_state["restaurant_coordinates"]
                coordi_list = list(restaurant_coordinates)
                restaurant = st.session_state["restaurant"]
                address = st.session_state["address"]

                st.title("지도")
                st.header(f"**📍 선택된 식당:** {restaurant}")
                st.write(f"**🗺️ 주소:** {address}")

                # 지도 생성
                zoom_level = 17
                locations = [coordi_list[0], coordi_list[1]]

                # 지도 표시
                f = folium.Figure(width=1200, height=500)
                m = folium.Map(location=locations, zoom_start=zoom_level).add_to(f)

                location_name = restaurant

                # 선택된 위치에 마커 추가
                folium.Marker(
                    locations,
                    popup=f"{location_name}",
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)

                st_folium(m, width=700, height=500)
        with empty4:
            st.write(" ")

# search_query 값에 따라 화면 변경
if len(options) > 0:  # options 리스트가 비어 있지 않은 경우
    main2()
elif len(search_query) > 0 and all(q != "" for q in search_query):  # search_query가 비어 있지 않고 모든 요소가 빈 문자열이 아닐 경우
    main2()
else:
    main()  # 위 조건을 만족하지 않으면 main() 실행