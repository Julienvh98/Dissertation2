# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import plotly.graph_objects as go
import plotly.express as px
import plotly.graph_objs as go
import seaborn as s
from plotly.subplots import make_subplots


# SETUP ------------------------------------------------------------------------

# st.title('Comp.Air Dashboard')

st.set_page_config(page_title='Comp.Air Dashboard',
                   page_icon='/Users/Jujuvh/Desktop/Screenshot 2021-05-13 at 20.44.53.png',
                   layout="wide")

col1, mid, col2 = st.beta_columns([1,2,20])
with col1:
    st.image('/Users/Jujuvh/Desktop/compair.png', width=200)
with col2:
    st.title('Comp.Air Dashboard')

option = st.selectbox("Which Dashboard?", ('Overview', 'Detailed Tables', 'FAQ'),0)
st.header(option)

df = pd.read_excel("Monitors_Combined_Keltbray2.xlsx")
df = df.drop(["Unnamed: 0", "Timestamp", "Time (UTC)"], axis=1)


user_input = st.text_input('Input your device name here:')
#
# #F9:5A:3E:AE:39:62
#
#selecting relevant device
df_1 = df[df.Address == user_input]

#concacetting the Date (in datetimeformat) and the Time(min) into one column
df_1["Timestamp"] = pd.to_datetime(df_1["Date"].astype(str)+" "+df_1["Time(min)"].astype(str))

#setting this new column as the index
df_1 = df_1.set_index("Timestamp")

#restricting the time
df_1 = df_1[(df_1.index >= "2020-10-15 00:00:00") & (df_1.index <= "2021-01-09 23:59:59")]
df_1.sort_values("Timestamp", inplace=True)


most_recent_date = df_1.index.max()


#data from the last hour recorded
hour1 = df_1[df_1.index>=(most_recent_date-dt.timedelta(hours=1))]

#data from the last 24 hours
hour24 = df_1[df_1.index>=(most_recent_date-dt.timedelta(hours=24))]

#data from the last 48 hours
hour48 = df_1[df_1.index>=(most_recent_date-dt.timedelta(hours=48))]

#data from the last 48 hours
day7 = df_1[df_1.index>=(most_recent_date-dt.timedelta(days=7))]

#limiting the format to 2 decimal places to make it easier to read for the user
pd.options.display.float_format = "{:.2f}".format

#grabbing the average of all timeframes
m1 = hour1.mean()
m24 =hour24.mean()
m48 = hour48.mean()
mday7 = day7.mean()



#creating a dataframe of all the averages from the different timeframes
d = {'1 Hour':m1 ,'24 Hours':m24 , '48 Hours': m48, '7 Days': mday7}
dfavg = pd.DataFrame(data=d)


#removing unnecessary metrics
dfavg = dfavg.drop(index=['Altitude','Longitude','Latitude'])


#grabbing the max of all timeframes
max1 = hour1.max()
max24 =hour24.max()
max48 = hour48.max()
maxday7 = day7.max()



#creating a dataframe of all the averages from the different timeframes
d = {'1 Hour':max1 ,'24 Hours':max24 , '48 Hours': max48, '7 Days': maxday7}
dfmax = pd.DataFrame(data=d)


#removing unnecessary metrics
dfmax = dfmax.drop(index=['Altitude','Longitude','Latitude','Address','Date','Time(min)'])


#grabbing the min of all timeframes
min1 = hour1.min()
min24 =hour24.min()
min48 = hour48.min()
minday7 = day7.min()



d = {'1 Hour':min1 ,'24 Hours':min24 , '48 Hours': min48, '7 Days': minday7}
dfmin = pd.DataFrame(data=d)


dfmin = dfmin.drop(index=['Altitude','Longitude','Latitude','Address','Date','Time(min)'])

if option == 'Overview':

    #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
    st.write('')

    row1_1, space1, row1_2, space2, row1_3 = st.beta_columns(2.5,0.1,3,0.1,3)

    #TEMPERATURE

    temp = dfavg.loc[dfavg.index == 'Temperature']
    temp2 = temp.T

    temp2['Time'] = temp2.index

    templot = go.Figure(data=[go.Bar(
                x=temp2['Time'] , y=temp2['Temperature'],
                text=temp2['Temperature'],
                textposition='auto',
                texttemplate="%{y:.2f}°C",
    )])

    templot.update_layout(
                autosize=False,
                width=550,
                height=400,
                title = "Average Temperature of Various Time Periods",
                xaxis_title = "Time Periods (Based on current day)",
                yaxis_title = "Average Temperature in °C ",
                font=dict(
                    family="Arial",
                    size=14))
    annotations = []

    annotations.append(dict(xref='paper', yref='paper', x=0.5, y=-0.5,
                            xanchor='center', yanchor='top',
                            text='Comp.Air™',
                            font=dict(family='Arial',
                                      size=12,
                                      color='rgb(150,150,150)'),
                            showarrow=False))

    templot.update_layout(annotations=annotations)


    with row1_1:
        st.plotly_chart(templot)

    #HUMIDITY
    # hum = dfavg.loc[dfavg.index == 'Humdity']
    # hum2 = hum.T
    #
    # hum2['Time'] = hum2.index
    #
    # humplot = go.Figure(data=[go.Bar(
    #     x=hum2['Time'], y=hum2['Humidity'],
    #     text=temp2['Humidity'],
    #     textposition='auto',
    #     texttemplate="%{y:.2f}",
    # )])
    #
    # #AIR PRESSURE
    # air = dfavg.loc[dfavg.index == 'Air Pressure']
    # air2 = air.T
    #
    # air2['Time'] = air2.index

    #LINEPLOTS


    line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['Temperature']))

    line24.update_layout(
                title = "Temperature in the Last 24 hours",
                xaxis_title = "Time",
                yaxis_title = "Average Temperature in °C ",
                font=dict(
                    family="Arial",
                    size=14))

    with row1_2:
        st.plotly_chart(line24)



    line7 = go.Figure(data=go.Scatter(x=day7.index, y=day7['Temperature']))

    line7.update_layout(
        title="Temperature in the Last 7 Days",
        xaxis_title="Time",
        yaxis_title="Average Temperature in °C ",
        font=dict(
            family="Arial",
            size=14))

    with row1_3:
        st.plotly_chart(line7)


    #BOX PLOT

    fig = px.box(day7 , y="Temperature")
    st.plotly_chart(fig)


    #Map

    map = px.density_mapbox(df, lat='Latitude', lon='Longitude', z='Pm25', radius=10,
                            center=dict(lat=55, lon=3.4), zoom=60,
                            mapbox_style="stamen-terrain")

    st.plotly_chart(map)

if option == 'Detailed Tables':
    st.header("Average")
    st.dataframe(dfavg)
    st.header("Minimum")
    st.dataframe(dfmin)
    st.header("Maximum")
    st.dataframe(dfmax)



