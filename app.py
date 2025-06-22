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

# --- Helper Functions ---
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
st.markdown("**持続可能な航空運航を目指すシミュレーションゲーム**")

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
    st.header("3. ルート分析")
    
    # Get coordinates
    dep_coord = (airports_df.loc[departure, 'Latitude'], airports_df.loc[departure, 'Longitude'])
    arr_coord = (airports_df.loc[arrival, 'Latitude'], airports_df.loc[arrival, 'Longitude'])
    
    # Calculate route metrics
    route_distance = geodesic(dep_coord, arr_coord).km
    etops_required_km = calculate_etops_requirement(dep_coord, arr_coord, airports_df)
    etops_required_min = (etops_required_km / aircraft['Speed']) * 60
    
    # SDG Impact Analysis
    sdg_metrics = calculate_sdg_impact(aircraft, route_distance, passengers)
    
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
    
    # Recommendations
    st.subheader("💡 改善提案")
    recommendations = []
    
    if capacity_utilization < 70:
        recommendations.append("座席利用率が低いです。需要予測を見直すか、より小型の機材を検討してください")
    
    if sdg_metrics['co2_per_passenger'] > 150:
        recommendations.append("乗客1人当たりのCO₂排出量が高いです。より燃費の良い機材を検討してください")
    
    if etops_required_min > aircraft['ETOPS']:
        recommendations.append("ETOPS要求を満たしていません。経由地の設定や機材変更を検討してください")
    
    if sdg_metrics['total_sdg_score'] < 6:
        recommendations.append("SDGスコアが低いです。環境負荷軽減と運航効率の改善が必要です")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.warning(f"{i}. {rec}")
    else:
        st.success("✅ 優秀な運航計画です！環境負荷とETOPS要求の両方を満たしています")

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
st.markdown("**ETOPS**: Extended-range Twin-engine Operational Performance Standards")
st.markdown("💡 **ヒント**: 詳細地図では各空港周辺のETOPS範囲（オレンジ円）が表示されます。飛行ルートがこの範囲から外れないよう計画してください。")
