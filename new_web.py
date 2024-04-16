import io
import streamlit as st
import matplotlib.pyplot as plt
from pyproj import Transformer
from lib.pll_rtk_lib import NMEA
from lib.stroke_lib import Stroke
import geopandas as gp
from lib.stroke_lib import Stroke
import matplotlib as mpl
import mpld3
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import datetime
#import mediapipe as mp
#from mediapipe.tasks import python
#from mediapipe.tasks.python import vision

#_lock = RendererAgg.lock
nmea = NMEA()
stroke = Stroke()
HEIGHT = 150

def data_load(file):
    lines = file.readlines()
    dict = {}
    for line in lines:
        r = nmea.parse_GGA(line)
        if r is not None:
            t,lat,lon,mode,alt = r
            if t not in dict:
                dict[t] = {}
            dict[t]['lat'] = lat
            dict[t]['lon'] = lon
            dict[t]['mode'] = mode
            dict[t]['alt'] = alt
            continue
        r = nmea.parse_RMC(line)
        if r is not None:
            t,lat,lon,vel,theta = r
            if t not in dict:
                dict[t] = {}
            dict[t]['lat'] = lat
            dict[t]['lon'] = lon 
            dict[t]['vel'] = vel
            dict[t]['theta'] = theta
            continue
    
    return dict

@st.cache_data
def data_get3d(dict=dict,t1=-1,t2=-1):
    dict = dict
    ts = sorted(dict.keys())
    xs,ys,zs,vs,modes,ts2,thetas = [],[],[],[],[],[],[]
    lats,lons = [],[]
    mode, alt, vel, theta = 0,0,0,0
    total_distance = 0
    previous_lat = None
    previous_lon = None

    transformer = Transformer.from_crs('epsg:4612', 'epsg:2451')
    for t in ts:
        d = dict[t]
        lat = [d['lat']]
        lon = [d['lon']]
        alt = d['alt'] if 'alt' in d else alt
        vel = d['vel'] if 'vel' in d else vel
        mode = d['mode'] if 'mode' in d else mode
        theta = d['theta'] if 'theta' in d else theta

        if t1 == -1 or t1 <= t - ts[0] <= t2:
            lats.append(lat)
            lons.append(lon)
            y, x = transformer.transform(lat, lon)
            xs.append(x)
            ys.append(y)
            zs.append(alt)
            vs.append(vel)
            modes.append(mode)
            ts2.append(t - ts[0])
            thetas.append(theta)
            
            if previous_lat is not None and previous_lon is not None:
                distance = nmea.haversine_distance(previous_lat, previous_lon, lat[0], lon[0])
                total_distance += distance

            previous_lat = lat[0]
            previous_lon = lon[0]

    #print(f'xs min:{min(xs)} max:{max(xs)} ys min:{min(ys)} ys max:{max(ys)}')
    #print(f"移動した距離は {total_distance:.4f} kmです。")
    return xs, ys, zs, vs, modes, ts2, thetas, total_distance, lats, lons

def vel_plot(vs,ts):
    fig,ax = plt.subplots()
    ax.clear()

    #_, _, _, vs, _, ts, _, _,_,_ = data_get3d(data,t1,t2)
    ax.plot(ts,vs)
    ax.grid(":")
    ax.set_xlabel("time[s]")
    ax.set_ylabel("velocity[m/s]")
    fig_html = mpld3.fig_to_html(fig)
    components.html(fig_html,height=800)

def pitch_plot(zs,ts):
    fig,ax = plt.subplots()
    ax.clear()
    #_, _, zs, _, _, ts, _, _, _, _ = data_get3d(data,t1,t2)
    
    ax.plot(ts,zs)
    ax.grid(":")
    ax.set_xlabel("time[s]")
    ax.set_ylabel("pitch[m]")
    fig_html = mpld3.fig_to_html(fig)
    components.html(fig_html,height=800)

def map_plot(lat,lon):
    #_, _, _, _, _, _, _,_, lat, lon = data_get3d(data,-1,-1)
    lats = []
    lons = []
    for sublists in lat:
        if isinstance(sublists,list):
            for item in sublists:
                lats.append(item)
        else:
            lats.append(sublists)
    
    for sublists in lon:
        if isinstance(sublists,list):
            for item in sublists:
                lons.append(item)
        else:
            lons.append(sublists)

    df = pd.DataFrame({
        "lat":lats,
        "lon":lons
    })

    #print(df)
    st.map(df,size=0.1)

def data_plot(upload_file):
    if upload_file != None:
        file = io.StringIO(upload_file.getvalue().decode("utf-8"))
        data = data_load(file)
        xs, ys, zs, vs, modes, ts, thetas, total_distance, lat, lon = data_get3d(data)

        with tab1:
            data_container(ts,vs,zs,total_distance,modes)
        with tab2:
            st.write("## Velocity[m/s]")
            vel_plot(vs,ts)
        with tab3:
            st.write("## Pitching[m]")
            pitch_plot(zs,ts)
        with tab4:
            map_plot(lat,lon)

def data_container(ts,vs,zs,total_distance,modes):
    row1 = st.columns(3)
    row2 = st.columns(3)

    container1 = row1[0].container(height=HEIGHT)
    container1.subheader("最高速度[m/s]",divider="blue")
    container1.subheader('{:.2f}'.format(max(vs)))

    container2 = row1[1].container(height=HEIGHT)
    container2.subheader("運動時間:clock9:",divider="blue")
    time = max(ts)-min(ts)
    td = datetime.timedelta(seconds=time)
    container2.subheader(str(td))

    container3 = row1[2].container(height=HEIGHT)
    container3.subheader("距離[km]",divider="blue")
    container3.subheader('{:.2f}'.format(total_distance))

    container4 = row2[0].container(height=HEIGHT)
    container4.subheader("平均高度[m]",divider="blue")
    container4.subheader(f'{sum(zs) / len(zs):.2f}')

    container5 = row2[1].container(height=HEIGHT)
    container5.subheader("測位精度",divider="blue")
    container5.subheader(f'{(sum(modes) / len(modes)):.2f}')

    container6 = row2[2].container(height=HEIGHT)
    container6.title(":balloon:")

def stroke_analysis(file,t1,t2,tw):
    if upload_file != None:
        file = io.StringIO(upload_file.getvalue().decode("utf-8"))
        data = data_load(file)

    xs, ys, zs, vs, mode, ts, theta, total_distance, lat, lon = data_get3d(data,t1,t2)
    fig,ax = plt.subplots()
    strokes = Stroke.extract_strokes(vs,ts,tw)
    for vel,time in strokes:
        time = [t - time[0] for t in time]
        ax.plot(time,vel)
    ax.set_xlabel("time[s]")
    ax.set_ylabel("velocity[m/s]")
    ax.grid(":")
    fig_html = mpld3.fig_to_html(fig)
    components.html(fig_html,height=800)


apptitle = "RowRTK"

st.set_page_config(page_title=apptitle,page_icon="🚣🏼‍♀️")

st.title("RowRTK 🚣🏼‍♀️")
st.markdown("""
            * RTK測位によって得られる情報を可視化したサイトです。
            * 速度グラフ/高度グラフ/地図の軌跡表示を行います。
            """)

tab1,tab2,tab3,tab4,tab5 = st.tabs(["解析データ一覧","📈 速度グラフ",":mountain: 高度グラフ","🗺️地図","ストローク分析"])



with st.sidebar:
    st.sidebar.write("## Upload and download :gear:")
 
    upload_file = st.sidebar.file_uploader("Upload file",type=["txt","nmea"])
    click = st.sidebar.button("UpdateGraph:bar_chart:",type="primary")

    if upload_file:
        st.success("File Loaded!",icon='✅')
        data_plot(upload_file)
    
# data load
        
with tab5:
   with st.expander("See explanation"):
       st.write("The chart above shows some numbers I picked for you.\
        I rolled actual dice for these, so they're *guaranteed* to\
        be random.")
      # st.image("../data/picture/velocity_exp.jpg")
   
   stime = st.number_input("Start Time",0,step=10)
   etime = st.number_input("End Time",0,step=10)
   menu = st.radio("UT or RR",
                   ["UT","RR"])
   
   tw = 0
   if menu == "UT":
       tw = 50
   else:
       tw = 30
   button = st.button("Stroke Analysis",type="primary")
   
   st.write("### velocity[m/s]")
   if button:
       if stime is not None and etime is not None:
           stroke_analysis(upload_file,stime,etime,tw)
   
        