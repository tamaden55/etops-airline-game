import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium
import math

# --- Load Data ---
@st.cache_data
def load_data():
    aircraft_df = pd.read_csv("data/aircraft.csv")
    airports_df = pd.read_csv("data/airports.csv").set_index("IATA")
    return aircraft_df, airports_df

aircraft_df, airports_df = load_data()

# --- Scoring and Title System ---
def calculate_game_score(etops_compliant, co2_per_passenger, capacity_utilization, aircraft_sdg_score):
    """
    Calculate comprehensive game score (0-100 points)
    """
    # ETOPS Compliance Score (0-25 points)
    etops_score = 25 if etops_compliant else 0
    
    # Environmental Score (0-25 points) - Lower CO2 per passenger is better
    if co2_per_passenger <= 50:
        env_score = 25
    elif co2_per_passenger <= 100:
        env_score = 20
    elif co2_per_passenger <= 150:
        env_score = 15
    elif co2_per_passenger <= 200:
        env_score = 10
    else:
        env_score = 5
    
    # Efficiency Score (0-25 points) - Based on capacity utilization
    if capacity_utilization >= 90:
        eff_score = 25
    elif capacity_utilization >= 80:
        eff_score = 20
    elif capacity_utilization >= 70:
        eff_score = 15
    elif capacity_utilization >= 60:
        eff_score = 10
    else:
        eff_score = 5
    
    # Aircraft Performance Score (0-25 points) - Based on SDG score
    aircraft_score = (aircraft_sdg_score / 10) * 25
    
    total_score = etops_score + env_score + eff_score + aircraft_score
    
    return {
        'total_score': round(total_score),
        'etops_score': etops_score,
        'environmental_score': env_score,
        'efficiency_score': eff_score,
        'aircraft_score': round(aircraft_score),
        'breakdown': {
            'ETOPS適合性': f"{etops_score}/25",
            '環境性能': f"{env_score}/25", 
            '運航効率': f"{eff_score}/25",
            '機材性能': f"{round(aircraft_score)}/25"
        }
    }

def get_title_and_badge(score):
    """
    Determine title and badge based on score
    """
    if score >= 90:
        return {
            'title': '🏆 エコ航空の達人',
            'badge': '🌟',
            'color': 'success',
            'message': '素晴らしい！持続可能な航空運航のエキスパートです！',
            'tier': 'レジェンド'
        }
    elif score >= 80:
        return {
            'title': '✈️ 優秀な経営者', 
            'badge': '🥇',
            'color': 'success',
            'message': '優秀な運航計画です！環境と効率のバランスが取れています。',
            'tier': 'エキスパート'
        }
    elif score >= 70:
        return {
            'title': '🌱 駆け出し経営者',
            'badge': '🥈', 
            'color': 'warning',
            'message': '良いスタートです！さらなる改善で上位ランクを目指しましょう。',
            'tier': '中級者'
        }
    elif score >= 60:
        return {
            'title': '📚 研修生',
            'badge': '🥉',
            'color': 'warning', 
            'message': '基本はできています。ETOPS適合性と環境性能の向上を目指しましょう。',
            'tier': '初級者'
        }
    else:
        return {
            'title': '🔧 要改善',
            'badge': '⚠️',
            'color': 'error',
            'message': '運航計画の見直しが必要です。機材選択から再検討してみてください。',
            'tier': '見習い'
        }

def display_score_dashboard(score_data, title_data):
    """
    Display scoring dashboard in sidebar
    """
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 ゲームスコア")
    
    # Total Score with progress bar
    st.sidebar.metric(
        "総合スコア", 
        f"{score_data['total_score']}/100", 
        delta=f"目標まで{max(0, 80-score_data['total_score'])}点"
    )
    
    # Progress bar
    progress = min(score_data['total_score'] / 100, 1.0)
    st.sidebar.progress(progress)
    
    # Title and Badge
    st.sidebar.markdown(f"### {title_data['badge']} {title_data['title']}")
    st.sidebar.markdown(f"**ランク**: {title_data['tier']}")
    
    # Score breakdown
    st.sidebar.subheader("📊 スコア内訳")
    for category, points in score_data['breakdown'].items():
        st.sidebar.text(f"{category}: {points}")
    
    # Achievement message
    if title_data['color'] == 'success':
        st.sidebar.success(title_data['message'])
    elif title_data['color'] == 'warning':
        st.sidebar.warning(title_data['message'])
    else:
        st.sidebar.error(title_data['message'])

def display_achievement_banner(title_data, score):
    """
    Display achievement banner in main area
    """
    if score >= 80:
        st.balloons()
    
    # Create achievement banner
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if title_data['color'] == 'success':
            st.success(f"## {title_data['badge']} {title_data['title']} {title_data['badge']}\n### スコア: {score}/100\n{title_data['message']}")
        elif title_data['color'] == 'warning':
            st.warning(f"## {title_data['badge']} {title_data['title']} {title_data['badge']}\n### スコア: {score}/100\n{title_data['message']}")
        else:
            st.error(f"## {title_data['badge']} {title_data['title']} {title_data['badge']}\n### スコア: {score}/100\n{title_data['message']}")

# --- Helper Functions (existing) ---
def calculate_etops_requirement(dep_coord, arr_coord, airports_df):
    """Calculate the ETOPS requirement for a route"""
    max_distance_to_nearest_airport = 0
    
    # Sample points along the great circle route
    for i in range(21):  # 21 points including start and end
        ratio = i / 20
        # Simple linear interpolation for demonstration
        lat = dep_coord[0] + ratio * (arr_coord[0] - dep_coord[0])
        lon = dep_coord[1] + ratio * (arr_coord[1] - dep_coord[1])
        
        # Find distance to nearest airport
        min_distance = float('inf')
        for _, airport in airports_df.iterrows():
            distance = geodesic((lat, lon), (airport['Latitude'], airport['Longitude'])).km
            min_distance = min(min_distance, distance)
        
        max_distance_to_nearest_airport = max(max_distance_to_nearest_airport, min_distance)
    
    return max_distance_to_nearest_airport

def calculate_sdg_impact(aircraft, distance_km, passengers):
    """Calculate SDG impact metrics"""
    total_fuel = distance_km * aircraft['Fuel_L_per_km']
    total_co2 = distance_km * aircraft['CO2_kg_per_km']
    co2_per_passenger = total_co2 / passengers if passengers > 0 else total_co2
    
    # SDG scoring (higher is better)
    efficiency_score = max(0, 10 - (co2_per_passenger / 100))
    capacity_utilization = passengers / aircraft['Capacity']
    utilization_score = capacity_utilization * 10
    
    total_sdg_score = (efficiency_score + utilization_score + aircraft['SDG_Score']) / 3
    
    return {
        'total_fuel': total_fuel,
        'total_co2': total_co2,
        'co2_per_passenger': co2_per_passenger,
        'efficiency_score': efficiency_score,
        'utilization_score': utilization_score,
        'total_sdg_score': total_sdg_score
    }

def create_etops_map(dep_coord, arr_coord, dep_name, arr_name, aircraft_etops, etops_required_min):
    """Create a folium map with ETOPS visualization"""
    # Calculate center point for map
    center_lat = (dep_coord[0] + arr_coord[0]) / 2
    center_lon = (dep_coord[1] + arr_coord[1]) / 2
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=3,
        tiles='OpenStreetMap'
    )
    
    # Add departure airport
    folium.Marker(
        dep_coord,
        popup=f"🛫 出発: {dep_name}",
        tooltip=f"出発地: {dep_name}",
        icon=folium.Icon(color='green', icon='plane', prefix='fa')
    ).add_to(m)
    
    # Add arrival airport
    folium.Marker(
        arr_coord,
        popup=f"🛬 到着: {arr_name}",
        tooltip=f"到着地: {arr_name}",
        icon=folium.Icon(color='red', icon='plane', prefix='fa')
    ).add_to(m)
    
    # Add flight route
    folium.PolyLine(
        [dep_coord, arr_coord],
        color='blue',
        weight=3,
        opacity=0.8,
        popup=f"航路: {dep_name} → {arr_name}"
    ).add_to(m)
    
    # Add ETOPS circles around available airports
    etops_radius_km = (aircraft_etops / 60) * 850  # Assuming average speed of 850 km/h
    
    for iata, airport in airports_df.iterrows():
        airport_coord = [airport['Latitude'], airport['Longitude']]
        
        # ETOPS circle
        folium.Circle(
            location=airport_coord,
            radius=etops_radius_km * 1000,  # Convert to meters
            popup=f"ETOPS範囲: {iata}<br>半径: {etops_radius_km:.0f}km",
            color='orange',
            fillColor='yellow',
            fillOpacity=0.2,
            weight=1
        ).add_to(m)
        
        # Airport marker
        folium.CircleMarker(
            location=airport_coord,
            radius=5,
            popup=f"✈️ {iata}: {airport['Name']}",
            color='black',
            fillColor='white',
            fillOpacity=0.8
        ).add_to(m)
    
    # Add ETOPS status indicator
    etops_status = "適合" if etops_required_min <= aircraft_etops else "不適合"
    status_color = "green" if etops_required_min <= aircraft_etops else "red"
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4>ETOPS Status</h4>
    <p><span style="color:{status_color};">●</span> 状態: {etops_status}</p>
    <p>必要時間: {etops_required_min:.0f}分</p>
    <p>機材性能: {aircraft_etops}分</p>
    <p><span style="color:orange;">○</span> ETOPS範囲</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def create_route_map_plotly(dep_coord, arr_coord, dep_name, arr_name):
    """Create a plotly map showing the route (fallback)"""
    fig = go.Figure()
    
    # Add route line
    fig.add_trace(go.Scattergeo(
        lon=[dep_coord[1], arr_coord[1]],
        lat=[dep_coord[0], arr_coord[0]],
        mode='lines+markers',
        line=dict(width=2, color='red'),
        marker=dict(size=8, color='blue'),
        text=[f'出発: {dep_name}', f'到着: {arr_name}'],
        name='Route'
    ))
    
    fig.update_layout(
        geo=dict(
            projection_type='natural earth',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            coastlinecolor='rgb(204, 204, 204)',
        ),
        height=400,
        title='Flight Route'
    )
    
    return fig

# --- Session State Init ---
if "game_mode" not in st.session_state:
    st.session_state.game_mode = "route_planning"
    st.session_state.selected_aircraft = None
    st.session_state.departure = None
    st.session_state.arrival = None
    st.session_state.passengers = 200
    st.session_state.map_type = "folium"

# --- Page Config ---
st.set_page_config(
    page_title="ETOPS Airline Strategy",
    page_icon="✈️",
    layout="wide"
)

# --- Title ---
st.title("✈️ ETOPS Airline Strategy Game")
st.markdown("**目標: 80点以上で航空会社経営成功！最高得点100点を目指そう！**")

# --- ETOPS Explanation ---
with st.expander("🤔 ETOPSとは？（初回プレイの方は必読）", expanded=False):
    st.markdown("""
    ### ✈️ ETOPS（イートップス）とは？
    
    **ETOPS** = **E**xtended-range **T**win-engine **O**perational **P**erformance **S**tandards
    
    双発機（エンジンが2つの飛行機）が海洋上などの長距離路線を飛行する際の**安全基準**です。
    
    #### 🔍 なぜETOPSが必要？
    - 双発機は4発機より燃費が良いが、エンジン故障時のリスクが高い
    - 海洋上でエンジンが1つ故障した場合、**最寄りの空港まで飛行できる能力**が必要
    - 例：ETOPS 180分 = エンジン1つで180分間飛行可能
    
    #### 🎯 このゲームでは...
    - 各機材のETOPS性能を確認
    - 飛行ルートが安全基準を満たすかチェック
    - 環境性能も考慮した最適な運航を目指します
    """)

# --- How to Play ---
with st.expander("🎮 ゲームの遊び方", expanded=False):
    st.markdown("""
    ### 🕹️ 3ステップで簡単！
    
    #### ステップ1: 機材選択
    - B787-9、A350-900、B737MAX等から選択
    - **ETOPS性能**、**燃費**、**環境性能**を比較
    
    #### ステップ2: ルート計画  
    - 出発地・到着地を選択
    - 搭乗予定人数を設定
    
    #### ステップ3: 結果確認
    - 地図でETOPS制限エリアを確認
    - **総合スコア100点満点**で評価
    - **80点以上**で航空会社経営成功！🎉
    
    ### 📊 スコア構成（各25点満点）
    - 🛡️ **ETOPS適合性**: 安全基準をクリア
    - 🌱 **環境性能**: CO₂排出量の少なさ  
    - 📈 **運航効率**: 座席利用率の高さ
    - ⭐ **機材性能**: 選択した機材のSDGスコア
    
    ### 🏆 称号システム
    - 90点以上: 🌟 **エコ航空の達人**
    - 80-89点: 🥇 **優秀な経営者**
    - 70-79点: 🥈 **駆け出し経営者** 
    - 60-69点: 🥉 **研修生**
    - 60点未満: ⚠️ **要改善**
    """)

# --- Sidebar for Game Controls ---
st.sidebar.header("🎮 Game Controls")
game_mode = st.sidebar.selectbox(
    "モードを選択",
    ["route_planning", "challenge_mode"],
    format_func=lambda x: "ルート計画モード" if x == "route_planning" else "チャレンジモード"
)
st.session_state.game_mode = game_mode

# Map type selection
map_type = st.sidebar.selectbox(
    "地図表示タイプ",
    ["folium", "plotly"],
    format_func=lambda x: "詳細地図 (Folium)" if x == "folium" else "シンプル地図 (Plotly)"
)
st.session_state.map_type = map_type

# Initialize variables
departure = None
arrival = None
passengers = None
aircraft = None

# --- Game Mode Specific Logic ---
if game_mode == "challenge_10_routes":
    # 10 Routes Challenge Mode
    st.header("🏆 10路線チャレンジモード")
    
    col1, col2 = st.columns(2)
    with col1:
        difficulty = st.selectbox(
            "難易度を選択",
            ["easy", "medium", "hard"],
            format_func=lambda x: {"easy": "😊 Easy", "medium": "😐 Medium", "hard": "😤 Hard"}[x]
        )
    
    with col2:
        if st.button("🎲 新しいチャレンジを開始"):
            st.session_state.challenge_routes = generate_challenge_routes(10, difficulty)
            st.session_state.current_route_index = 0
            st.session_state.challenge_total_score = 0
            st.rerun()
    
    # Display challenge progress
    if st.session_state.challenge_routes:
        progress = sum(1 for r in st.session_state.challenge_routes if r['completed']) / len(st.session_state.challenge_routes)
        st.progress(progress)
        st.write(f"進捗: {sum(1 for r in st.session_state.challenge_routes if r['completed'])}/10 路線完了")
        
        # Display current route
        if st.session_state.current_route_index < len(st.session_state.challenge_routes):
            current_route = st.session_state.challenge_routes[st.session_state.current_route_index]
            st.subheader(f"路線 {current_route['route_num']}: {current_route['departure']} → {current_route['arrival']}")
            st.write(f"距離: {current_route['distance_km']:,} km | 乗客数: {current_route['passengers']}人")
            
            # Aircraft selection for challenge
            available_aircraft = aircraft_df.copy()
            selected_model = st.selectbox(
                "機材を選択してください",
                available_aircraft["Model"],
                key="challenge_aircraft",
                help="チャレンジモード用機材選択"
            )
            
            aircraft = available_aircraft[available_aircraft["Model"] == selected_model].iloc[0]
            
            # Set route variables for analysis
            departure = current_route['departure']
            arrival = current_route['arrival']
            passengers = current_route['passengers']

elif game_mode == "budget_constraint":
    # Budget Constraint Mode
    st.header("💰 制限モード")
    
    col1, col2 = st.columns(2)
    with col1:
        constraint_type = st.selectbox(
            "制限タイプ",
            ["budget", "category"],
            format_func=lambda x: "💰 予算制限" if x == "budget" else "✈️ 機材カテゴリ制限"
        )
    
    if constraint_type == "budget":
        with col2:
            budget_limit = st.slider("予算上限 (百万USD)", 50, 500, 200, 25)
        
        available_aircraft = calculate_budget_constraints(budget_limit, aircraft_df)
        
        if len(available_aircraft) == 0:
            st.error("予算内で利用可能な機材がありません。予算を増やしてください。")
        else:
            st.info(f"予算 ${budget_limit}M以内で利用可能な機材: {len(available_aircraft)}機種")
            
            # Display available aircraft with prices
            display_df = available_aircraft[['Model', 'Category', 'ETOPS', 'Capacity', 'Price_Million_USD', 'SDG_Score']].copy()
            st.dataframe(display_df)
    
    else:  # category constraint
        with col2:
            allowed_category = st.selectbox(
                "使用可能機材カテゴリ",
                ["Regional", "Narrow-body", "Wide-body", "Turboprop"],
                format_func=lambda x: {
                    "Regional": "🛩️ リージョナル機",
                    "Narrow-body": "✈️ ナローボディ機", 
                    "Wide-body": "🛫 ワイドボディ機",
                    "Turboprop": "🚁 ターボプロップ機"
                }[x]
            )
        
        available_aircraft = aircraft_df[aircraft_df['Category'] == allowed_category].copy()
        st.info(f"{allowed_category}カテゴリ機材: {len(available_aircraft)}機種")
        
        # Display available aircraft
        display_df = available_aircraft[['Model', 'ETOPS', 'Capacity', 'Range', 'SDG_Score']].copy()
        st.dataframe(display_df)
    
    # If aircraft available, proceed with route planning
    if len(available_aircraft) > 0:
        st.subheader("機材選択 & ルート計画")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_model = st.selectbox(
                "機材を選択",
                available_aircraft["Model"],
                help="制限モードで利用可能な機材から選択"
            )
            aircraft = available_aircraft[available_aircraft["Model"] == selected_model].iloc[0]
        
        with col2:
            if constraint_type == "budget":
                remaining_budget = budget_limit - aircraft['Price_Million_USD']
                st.metric("選択機材価格", f"${aircraft['Price_Million_USD']:.0f}M")
                st.metric("残予算", f"${remaining_budget:.0f}M")
            st.metric("機材カテゴリ", aircraft['Category'])
        
        # Route planning
        col1, col2, col3 = st.columns(3)
        with col1:
            departure = st.selectbox("出発地", airports_df.index, 
                                   format_func=lambda x: f"{x} - {airports_df.loc[x, 'Name']}")
        with col2:
            arrival_options = [code for code in airports_df.index if code != departure]
            arrival = st.selectbox("到着地", arrival_options,
                                 format_func=lambda x: f"{x} - {airports_df.loc[x, 'Name']}")
        with col3:
            passengers = st.number_input("搭乗予定人数", 1, int(aircraft['Capacity']), 
                                       min(200, int(aircraft['Capacity'])))

else:
    # Normal Route Planning Mode
    st.header("🎯 ルート計画モード")
    
    # Aircraft category filter
    category_filter = st.selectbox(
        "機材カテゴリでフィルター",
        ["All"] + list(aircraft_df['Category'].unique()),
        format_func=lambda x: "全カテゴリ" if x == "All" else x
    )
    
    if category_filter == "All":
        available_aircraft = aircraft_df.copy()
    else:
        available_aircraft = aircraft_df[aircraft_df['Category'] == category_filter].copy()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_model = st.selectbox(
            "使用する機材を選択してください",
            available_aircraft["Model"],
            help="カテゴリフィルターで絞り込まれた機材から選択してください"
        )
        aircraft = available_aircraft[available_aircraft["Model"] == selected_model].iloc[0]
    
    with col2:
        st.metric("ETOPS性能", f"{aircraft['ETOPS']}分")
        st.metric("航続距離", f"{aircraft['Range']:,}km")
        st.metric("価格", f"${aircraft['Price_Million_USD']:.0f}M")
    
    # Display aircraft details
    st.subheader("選択した機材の詳細")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("製造会社", aircraft['Manufacturer'])
    with col2:
        st.metric("カテゴリ", aircraft['Category'])
    with col3:
        st.metric("座席数", f"{aircraft['Capacity']}席")
    with col4:
        st.metric("巡航速度", f"{aircraft['Speed']}km/h")
    with col5:
        st.metric("SDGスコア", f"{aircraft['SDG_Score']}/10")
    
    # Route planning
    st.subheader("ルート計画")
    col1, col2, col3 = st.columns(3)
    with col1:
        departure = st.selectbox("出発地", airports_df.index,
                               format_func=lambda x: f"{x} - {airports_df.loc[x, 'Name']}")
    with col2:
        arrival_options = [code for code in airports_df.index if code != departure]
        arrival = st.selectbox("到着地", arrival_options,
                             format_func=lambda x: f"{x} - {airports_df.loc[x, 'Name']}")
    with col3:
        passengers = st.number_input("搭乗予定人数", 1, int(aircraft['Capacity']), 
                                   min(200, int(aircraft['Capacity'])),
                                   help=f"最大搭乗可能人数: {aircraft['Capacity']}人")

# --- Route Analysis (Common for all modes) ---
if departure and arrival and departure != arrival and aircraft is not None:
    st.header("ルート分析 & ゲーム結果")
    
    # Get coordinates
    dep_coord = (airports_df.loc[departure, 'Latitude'], airports_df.loc[departure, 'Longitude'])
    arr_coord = (airports_df.loc[arrival, 'Latitude'], airports_df.loc[arrival, 'Longitude'])
    
    # Calculate route metrics
    route_distance = geodesic(dep_coord, arr_coord).km
    etops_required_km = calculate_etops_requirement(dep_coord, arr_coord, airports_df)
    etops_required_min = (etops_required_km / aircraft['Speed']) * 60
    
    # SDG Impact Analysis
    sdg_metrics = calculate_sdg_impact(aircraft, route_distance, passengers)
    
    # Calculate Game Score
    etops_compliant = etops_required_min <= aircraft['ETOPS']
    capacity_utilization = (passengers / aircraft['Capacity']) * 100
    
    if game_mode == "challenge_10_routes":
        score_data = calculate_route_score_detailed(
            etops_compliant, sdg_metrics['co2_per_passenger'], 
            capacity_utilization, aircraft['SDG_Score'], route_distance
        )
    else:
        score_data = calculate_game_score(
            etops_compliant, sdg_metrics['co2_per_passenger'], 
            capacity_utilization, aircraft['SDG_Score']
        )
    
    title_data = get_title_and_badge(score_data['total_score'])
    
    # Display scoring dashboard in sidebar (for non-challenge modes)
    if game_mode != "challenge_10_routes":
        display_score_dashboard(score_data, title_data)
        display_achievement_banner(title_data, score_data['total_score'])
    
    # Challenge mode specific handling
    if game_mode == "challenge_10_routes" and st.session_state.current_route_index < len(st.session_state.challenge_routes):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ETOPS適合", "✅" if etops_compliant else "❌")
        with col2:
            st.metric("CO₂/人", f"{sdg_metrics['co2_per_passenger']:.1f} kg")
        with col3:
            st.metric("搭乗率", f"{capacity_utilization:.1f}%")
        with col4:
            st.metric("路線スコア", f"{score_data['total_score']}/105")
        
        if st.button("この路線を完了", key="complete_route"):
            # Mark route as completed
            st.session_state.challenge_routes[st.session_state.current_route_index]['completed'] = True
            st.session_state.challenge_routes[st.session_state.current_route_index]['score'] = score_data['total_score']
            st.session_state.challenge_total_score += score_data['total_score']
            st.session_state.current_route_index += 1
            
            if st.session_state.current_route_index >= len(st.session_state.challenge_routes):
                # Challenge completed
                st.balloons()
                avg_score = st.session_state.challenge_total_score / 10
                st.success(f"🎉 チャレンジ完了！ 総合スコア: {st.session_state.challenge_total_score}/1050")
                st.success(f"平均スコア: {avg_score:.1f}/105")
                
                if avg_score >= 90:
                    st.success("🌟 レジェンド級の経営者！")
                elif avg_score >= 80:
                    st.success("🥇 優秀な経営者！")
                elif avg_score >= 70:
                    st.warning("🥈 中級レベル！もう少しで上級者！")
                else:
                    st.info("🥉 練習を重ねて上達しましょう！")
            
            st.rerun()
    
    # Display route map
    st.subheader("ルートマップ & ETOPS可視化")
    
    if st.session_state.map_type == "folium":
        try:
            etops_map = create_etops_map(
                dep_coord, arr_coord,
                f"{departure} ({airports_df.loc[departure, 'Name']})",
                f"{arrival} ({airports_df.loc[arrival, 'Name']})",
                aircraft['ETOPS'], etops_required_min
            )
            map_data = st_folium(etops_map, width=700, height=500)
            st.info("🗺️ **地図の見方**: オレンジの円はETOPS範囲を示しています。青い線が飛行ルートで、全区間がETOPS範囲内にある必要があります。")
        except Exception as e:
            st.warning(f"詳細地図の表示に失敗しました。シンプル地図を表示します。")
            route_map = create_route_map_plotly(dep_coord, arr_coord, 
                                             f"{departure} ({airports_df.loc[departure, 'Name']})",
                                             f"{arrival} ({airports_df.loc[arrival, 'Name']})")
            st.plotly_chart(route_map, use_container_width=True)
    else:
        route_map = create_route_map_plotly(dep_coord, arr_coord, 
                                         f"{departure} ({airports_df.loc[departure, 'Name']})",
                                         f"{arrival} ({airports_df.loc[arrival, 'Name']})")
        st.plotly_chart(route_map, use_container_width=True)
    
    # Route metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("飛行距離", f"{route_distance:,.0f} km")
    with col2:
        etops_status = "✅ 適合" if etops_required_min <= aircraft['ETOPS'] else "❌ 不適合"
        st.metric("ETOPS要求", f"{etops_required_min:.0f}分", delta=etops_status)
    with col3:
        st.metric("総CO₂排出量", f"{sdg_metrics['total_co2']:,.0f} kg")
    with col4:
        st.metric("乗客1人当たりCO₂", f"{sdg_metrics['co2_per_passenger']:.1f} kg")
    
    # Score breakdown for enhanced modes
    if game_mode == "challenge_10_routes" and 'distance_bonus' in score_data:
        st.subheader("スコア詳細 (チャレンジモード)")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("ETOPS", f"{score_data['etops_score']}/25")
        with col2:
            st.metric("環境性能", f"{score_data['environmental_score']}/25")
        with col3:
            st.metric("運航効率", f"{score_data['efficiency_score']}/25")
        with col4:
            st.metric("機材性能", f"{score_data['aircraft_score']}/25")
        with col5:
            st.metric("距離ボーナス", f"+{score_data['distance_bonus']}")

# Display completed routes summary for challenge mode
if game_mode == "challenge_10_routes" and st.session_state.challenge_routes:
    completed_routes = [r for r in st.session_state.challenge_routes if r['completed']]
    if completed_routes:
        st.subheader("完了済み路線")
        summary_df = pd.DataFrame(completed_routes)
        st.dataframe(summary_df[['route_num', 'departure', 'arrival', 'distance_km', 'passengers', 'score']])

# --- Footer ---
st.markdown("---")
st.markdown("**ETOPS Airline Strategy Game** - 持続可能な航空運航を学ぶシミュレーションゲーム")
st.markdown("**🎯 ゲーム目標**: 80点以上で航空会社経営成功！")
st.markdown("**✈️ 新機能**: 21機種の航空機 | 10路線チャレンジ | 予算・機材制限モード")
st.markdown("**ETOPS**: Extended-range Twin-engine Operational Performance Standards"))
st.session_state.map_type = map_type

# --- Aircraft Selection ---
st.header("1. 機材選択")
col1, col2 = st.columns([2, 1])

with col1:
    selected_model = st.selectbox(
        "使用する機材を選択してください",
        aircraft_df["Model"],
        help="各機材のETOPS性能、燃費、環境性能を考慮して選択してください"
    )
    
    aircraft = aircraft_df[aircraft_df["Model"] == selected_model].iloc[0]
    st.session_state.selected_aircraft = aircraft

with col2:
    st.metric("ETOPS性能", f"{aircraft['ETOPS']}分")
    st.metric("航続距離", f"{aircraft['Range']:,}km")
    st.metric("CO₂排出量", f"{aircraft['CO2_kg_per_km']}kg/km")

# Display aircraft details
st.subheader("選択した機材の詳細")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("製造会社", aircraft['Manufacturer'])
with col2:
    st.metric("座席数", f"{aircraft['Capacity']}席")
with col3:
    st.metric("巡航速度", f"{aircraft['Speed']}km/h")
with col4:
    st.metric("SDGスコア", f"{aircraft['SDG_Score']}/10")

# --- Route Planning ---
st.header("2. ルート計画")

col1, col2, col3 = st.columns(3)

with col1:
    departure = st.selectbox(
        "出発地",
        airports_df.index,
        format_func=lambda x: f"{x} - {airports_df.loc[x, 'Name']}"
    )
    st.session_state.departure = departure

with col2:
    arrival_options = [code for code in airports_df.index if code != departure]
    arrival = st.selectbox(
        "到着地",
        arrival_options,
        format_func=lambda x: f"{x} - {airports_df.loc[x, 'Name']}"
    )
    st.session_state.arrival = arrival

with col3:
    passengers = st.number_input(
        "搭乗予定人数",
        min_value=1,
        max_value=int(aircraft['Capacity']),
        value=min(200, int(aircraft['Capacity'])),
        help=f"最大搭乗可能人数: {aircraft['Capacity']}人"
    )
    st.session_state.passengers = passengers

# --- Route Analysis ---
if departure and arrival and departure != arrival:
    st.header("3. ルート分析 & ゲーム結果")
    
    # Get coordinates
    dep_coord = (airports_df.loc[departure, 'Latitude'], airports_df.loc[departure, 'Longitude'])
    arr_coord = (airports_df.loc[arrival, 'Latitude'], airports_df.loc[arrival, 'Longitude'])
    
    # Calculate route metrics
    route_distance = geodesic(dep_coord, arr_coord).km
    etops_required_km = calculate_etops_requirement(dep_coord, arr_coord, airports_df)
    etops_required_min = (etops_required_km / aircraft['Speed']) * 60
    
    # SDG Impact Analysis
    sdg_metrics = calculate_sdg_impact(aircraft, route_distance, passengers)
    
    # Calculate Game Score
    etops_compliant = etops_required_min <= aircraft['ETOPS']
    capacity_utilization = (passengers / aircraft['Capacity']) * 100
    
    score_data = calculate_game_score(
        etops_compliant, 
        sdg_metrics['co2_per_passenger'], 
        capacity_utilization, 
        aircraft['SDG_Score']
    )
    
    title_data = get_title_and_badge(score_data['total_score'])
    
    # Display scoring dashboard in sidebar
    display_score_dashboard(score_data, title_data)
    
    # Display achievement banner
    display_achievement_banner(title_data, score_data['total_score'])
    
    # Display route map based on selection
    st.subheader("ルートマップ & ETOPS可視化")
    
    if st.session_state.map_type == "folium":
        try:
            # Create enhanced folium map with ETOPS visualization
            etops_map = create_etops_map(
                dep_coord, arr_coord,
                f"{departure} ({airports_df.loc[departure, 'Name']})",
                f"{arrival} ({airports_df.loc[arrival, 'Name']})",
                aircraft['ETOPS'],
                etops_required_min
            )
            
            # Display the map
            map_data = st_folium(etops_map, width=700, height=500)
            
            st.info("🗺️ **地図の見方**: オレンジの円はETOPS範囲を示しています。青い線が飛行ルートで、全区間がETOPS範囲内にある必要があります。")
            
        except Exception as e:
            st.warning(f"詳細地図の表示に失敗しました。シンプル地図を表示します。エラー: {str(e)}")
            # Fallback to plotly
            route_map = create_route_map_plotly(dep_coord, arr_coord, 
                                   f"{departure} ({airports_df.loc[departure, 'Name']})",
                                   f"{arrival} ({airports_df.loc[arrival, 'Name']})")
            st.plotly_chart(route_map, use_container_width=True)
    else:
        # Use plotly map
        route_map = create_route_map_plotly(dep_coord, arr_coord, 
                               f"{departure} ({airports_df.loc[departure, 'Name']})",
                               f"{arrival} ({airports_df.loc[arrival, 'Name']})")
        st.plotly_chart(route_map, use_container_width=True)
    
    # Route metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("飛行距離", f"{route_distance:,.0f} km")
    
    with col2:
        etops_status = "✅ 適合" if etops_required_min <= aircraft['ETOPS'] else "❌ 不適合"
        st.metric("ETOPS要求", f"{etops_required_min:.0f}分", delta=etops_status)
    
    with col3:
        st.metric("総CO₂排出量", f"{sdg_metrics['total_co2']:,.0f} kg")
    
    with col4:
        st.metric("乗客1人当たりCO₂", f"{sdg_metrics['co2_per_passenger']:.1f} kg")
    
    # Detailed Analysis
    st.subheader("詳細分析")
    
    # ETOPS Analysis
    st.write("**ETOPS分析**")
    if etops_required_min <= aircraft['ETOPS']:
        st.success(f"✅ この機材（ETOPS {aircraft['ETOPS']}分）でこのルートを安全に飛行できます")
    else:
        st.error(f"❌ この機材のETOPS性能（{aircraft['ETOPS']}分）では不十分です。必要性能: {etops_required_min:.0f}分")
        st.info("💡 より高いETOPS性能を持つ機材を選択するか、経由地を設定してください")
    
    # SDG Impact Analysis
    st.write("**SDGs影響分析**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**環境負荷指標**")
        st.metric("燃料消費量", f"{sdg_metrics['total_fuel']:,.0f} L")
        st.metric("CO₂効率スコア", f"{sdg_metrics['efficiency_score']:.1f}/10")
        
        # CO2 comparison with other transport
        car_co2 = route_distance * 0.12 * passengers
        st.write(f"🚗 同距離を自動車で移動した場合のCO₂: {car_co2:,.0f} kg")
        co2_reduction = ((car_co2 - sdg_metrics['total_co2']) / car_co2) * 100
        if co2_reduction > 0:
            st.success(f"✅ 自動車比 {co2_reduction:.1f}% CO₂削減")
        else:
            st.warning(f"⚠️ 自動車比 {abs(co2_reduction):.1f}% CO₂増加")
    
    with col2:
        st.write("**運航効率指標**")
        capacity_utilization = (passengers / aircraft['Capacity']) * 100
        st.metric("座席利用率", f"{capacity_utilization:.1f}%")
        st.metric("利用効率スコア", f"{sdg_metrics['utilization_score']:.1f}/10")
        st.metric("総合SDGスコア", f"{sdg_metrics['total_sdg_score']:.1f}/10")
    
    # Recommendations for improvement
    st.subheader("💡 スコアアップのコツ")
    improvements = []
    
    if not etops_compliant:
        improvements.append("🎯 **ETOPS適合で+25点**: より高性能な機材(A350-900等)を選択しましょう")
    
    if sdg_metrics['co2_per_passenger'] > 150:
        improvements.append("🌱 **環境スコアアップ**: 燃費の良い機材選択で環境スコア向上")
    
    if capacity_utilization < 80:
        improvements.append("📈 **効率スコアアップ**: 搭乗率を80%以上に上げると高得点")
    
    if aircraft['SDG_Score'] < 8:
        improvements.append("⭐ **機材スコアアップ**: SDGスコアの高い機材(A350-900等)がおすすめ")
    
    if improvements:
        for improvement in improvements:
            st.info(improvement)
    else:
        st.success("🎉 パーフェクト！全ての要素で高得点を獲得しています！")

# --- Challenge Mode ---
if st.session_state.game_mode == "challenge_mode":
    st.header("🏆 チャレンジモード")
    st.info("複数のルートでスコアを競うモードです（開発中）")
    
    if st.button("チャレンジを開始"):
        st.balloons()
        st.success("チャレンジモードは今後のアップデートで実装予定です！")

# --- Footer ---
st.markdown("---")
st.markdown("**ETOPS Airline Strategy Game** - 持続可能な航空運航を学ぶシミュレーションゲーム")
st.markdown("**🎯 ゲーム目標**: 80点以上で航空会社経営成功！")
st.markdown("**ETOPS**: Extended-range Twin-engine Operational Performance Standards")
st.markdown("💡 **ヒント**: 詳細地図では各空港周辺のETOPS範囲（オレンジ円）が表示されます。高得点を目指して機材・ルート・搭乗率を最適化しましょう！")
