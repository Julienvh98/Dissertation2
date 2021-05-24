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
import boto3


# SETUP ------------------------------------------------------------------------

#rounding numbers to 2 decimal places
pd.set_option('precision', 2)

#limiting the format to 2 decimal places to make it easier to read for the user
pd.options.display.float_format = "{:.2f}".format

# st.title('Comp.Air Dashboard')

st.set_page_config(page_title='Comp.Air Dashboard',
                   page_icon='/Users/Jujuvh/Desktop/icon3.png',
                   layout="wide")

col1, mid, col2 = st.beta_columns([10,6,20])
with col1:
    st.title('Comp.Air Dashboard')
with col2:
    st.image('/Users/Jujuvh/Desktop/header.png', width=90)

option2 = st.selectbox("Which Metric?", ('Temperature', 'Humidity', 'Air Pressure'),0)

option = st.selectbox("Which Dashboard?", ('Overview', 'Detailed',  'FAQ'),0)

# id = acess_key_id
#
# password = secret_access_key

user_input = st.text_input('Input your device name here:')

if option == "Overview":
    st.header(option2 + " " + option)

if option == 'Detailed':
    st.header(option2 + " " + option)

if option == "FAQ":
    st.header(option)

def get_data():
    s3 = boto3.client("s3", \
                      region_name="eu-west-2", \
                      aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                      aws_secret_access_key="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")

    response = s3.list_objects(Bucket="compair5c26")

    df_list = []

    for file in response["Contents"]:
        obj = s3.get_object(Bucket="compair5c26", Key=file["Key"])
        obj_df = pd.read_csv(obj["Body"])
        df_list.append(obj_df)

    df1 = pd.concat(df_list)

    return df1


def get_data2():
    s3 = boto3.client("s3", \
                      region_name="eu-west-2", \
                      aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                      aws_secret_access_key="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")

    response = s3.list_objects(Bucket="allsensorsrecent")

    df2_list = []

    for file in response["Contents"]:
        obj = s3.get_object(Bucket="allsensorsrecent", Key=file["Key"])
        obj_df = pd.read_csv(obj["Body"])
        df2_list.append(obj_df)

    df2 = pd.concat(df2_list)

    return df2


df2 = get_data2()


# @st.cache(allow_output_mutation=True)
# def get_data():
#     data = pd.read_excel("Monitors_Combined_Keltbray2.xlsx")
#     data = data.drop(["Unnamed: 0", "Timestamp", "Time (UTC)"], axis=1)
#
#     return data

df_1 = get_data()

# F9:5A:3E:AE:39:62

#selecting relevant device
#df_1 = df[df.Address == user_input]

#transforming the strange Date and Time (UTC) formatting
df_1["Date"] = pd.to_datetime(df_1.Date)
df_1['Time(min)'] = df_1["Time (UTC)"].astype(str).str[:-3]

#concacetting the Date (in datetimeformat) and the Time(min) into one column
df_1["Timestamp"] = pd.to_datetime(df_1["Date"].astype(str)+" "+df_1["Time(min)"].astype(str))

#setting this new column as the index
df_1 = df_1.set_index("Timestamp")
df_1.sort_values("Timestamp", inplace=True)


most_recent_date = df_1.index.max()


#data from the last hour recorded
hour1 = df_1[df_1.index>=(most_recent_date-dt.timedelta(hours=1))]

#data from the last 24 hours
hour24 = df_1[df_1.index>=(most_recent_date-dt.timedelta(hours=24))]

#data from the last 30 days
day30 = df_1[df_1.index>=(most_recent_date-dt.timedelta(days=30))]

#data from the last 7 days
day7 = df_1[df_1.index>=(most_recent_date-dt.timedelta(days=7))]

#grabbing the average of all timeframes
m1 = hour1.mean()
m24 =hour24.mean()
mday30 = day30.mean()
mday7 = day7.mean()

#creating a dataframe of all the averages from the different timeframes
d = {'1 Hour':m1 ,'24 Hours':m24 , '7 Days': mday7, '30 Days': mday30 }
dfavg = pd.DataFrame(data=d)

# rouding decimals to 2 places
dfavg= dfavg.round(decimals=2)

#removing unnecessary metrics
dfavg = dfavg.drop(index=['Altitude','Longitude','Latitude'])

#calculating the change between past hour and past month
dif30 = ((m1-mday30)/mday30)
dif24h = ((m24-mday30)/mday30)

#creating a dataframe of the change in average from the past hour and the past 30 days
b = {'1 hour change to 30 days':dif30 ,'1 day Change to 30 days': dif24h}
dfdif = pd.DataFrame(data=b)

# rouding decimals to 2 places
dfdif = dfdif.round(decimals=2)

# #if negative change = colour is red, if positve change = colour is green

#removing unnecessary metrics
dfdif = dfdif.drop(index=['Altitude','Longitude','Latitude'])

#grabbing the max of all timeframes
max1 = hour1.max()
max24 =hour24.max()
maxday30 = day30.max()
maxday7 = day7.max()


#creating a dataframe of all the averages from the different timeframes
d = {'1 Hour':max1 ,'24 Hours':max24 , '7 Days': maxday7, '30 Days': maxday30 }
dfmax = pd.DataFrame(data=d)

#removing unnecessary metrics
dfmax = dfmax.drop(index=['Altitude','Longitude','Latitude','Address','Date','Time(min)'])


#grabbing the min of all timeframes
min1 = hour1.min()
min24 =hour24.min()
minday30 = day30.min()
minday7 = day7.min()



d = {'1 Hour':min1 ,'24 Hours':min24 , '7 Days': minday7, '30 Days': minday30 }
dfmin = pd.DataFrame(data=d)


dfmin = dfmin.drop(index=['Altitude','Longitude','Latitude','Address','Date','Time(min)'])



if option2 == 'Temperature':

    if option == 'Overview':

        #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
        st.write('')

        row1_1, row1_2 = st.beta_columns(2)

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
                    height=450,
                    title = "Average Temperature of Various Time Periods",
                    xaxis_title = "Time Periods (Based on current day)",
                    yaxis_title = "Average Temperature in °C ",
                    font=dict(
                        family="Arial",
                        size=14)
        )

        with row1_1:
            st.plotly_chart(templot)

        #LINEPLOTS
        line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['Temperature']))

        line24.update_layout(
                    title = "Temperature in the Last 24 hours",
                    xaxis_title = "Time",
                    yaxis_title = "Temperature in °C ",
                    font=dict(
                        family="Arial",
                        size=14))

        with row1_2:
            st.plotly_chart(line24)



        line7 = go.Figure(data=go.Scatter(x=day7.index, y=day7['Temperature']))

        line7.update_layout(
            title="Temperature in the Last 7 Days",
            xaxis_title="Time",
            yaxis_title="Temperature in °C ",
            font=dict(
                family="Arial",
                size=14))

        #ROW 2
        st.write('')

        row2_1, row2_2, = st.beta_columns(2)

        line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['Temperature']))

        line30.update_layout(
                title="Temperature in the Last 30 Days",
                xaxis_title="Time",
                yaxis_title="Temperature in °C ",
                font=dict(
                    family="Arial",
                    size=14))

        with row2_1:
            st.plotly_chart(line30)

        #BOX PLOT

        box = px.box(day7 , y="Temperature")
        box.update_layout(
            autosize=False,
            width=550,
            height=450,
            title="Boxplot of Temperature in the last 7 days",
            xaxis_title="Time",
            yaxis_title="Average Temperature in °C ",
            font=dict(
                family="Arial",
                size=14))

        with row2_2:
            st.plotly_chart(box)



        #Map



        map = px.density_mapbox(df2, lat='Latitude', lon='Longitude', z='Pm25', radius=10,
                                center=dict(lat=51.7, lon=-5.9), zoom=3.2,
                                mapbox_style="stamen-terrain")

        st.plotly_chart(map)



if option == 'Detailed':
        # @st.cache
        # def detailed()

        all = go.Figure(data=go.Scatter(x=df_1.index, y=df_1['Temperature']))

        all.update_layout(
                title="Temperature Recorded Since Device Activation",
                xaxis_title="Time",
                yaxis_title="Temperature in °C ",
                font=dict(
                    family="Arial",
                    size=14))

        st.plotly_chart(all)

        # st.write(df.style.format("{:.2}"))
        st.write('')

        row2_1, row2_2 = st.beta_columns(2)

        with row2_1:
            st.header("Average")
            st.dataframe(dfavg)

        with row2_2:
            st.header("% Change")
            st.dataframe(dfdif)

        #add rows
        st.write('')

        row3_1, row3_2 = st.beta_columns(2)

        with row3_1:
            st.header("Maximum")
            st.dataframe(dfmax)

        with row3_2:
            st.header("Minimum")
            st.dataframe(dfmin)

        row2_1, row2_2 = st.beta_columns(2)


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

if option == "FAQ":

    st.markdown('___')
    about = st.beta_expander('About & Metrics Info')
    with about:
            '''
            Thanks for checking out our Dashboard ! It was built entirely using Comp.Air (https://www.compair.earth/) data. 
            
            This app is a dashboard that runs an analysis on any desired metric captured by Comp.Air devices. 
             
            They are briefly described below:
            
            **Temperature** - measured in degree Celcius °C.
            
            **Humidity** - a quantity representing the amount of water vapour in the atmosphere or in a gas.
            
            **Air pressure** - also known as barometric pressure (after the barometer), is the pressure within the atmosphere of Earth. 
            
            
            *Disclaimer - Some of the data might not be perfectly correct, due to environmental factors and/or mispositioning of the device. 
            Try to avoid placing the device close to any hobs, ovens, radiators. etc. etc. *
            
            '''

    st.markdown('___')
    about = st.beta_expander('Is My Data Protected ?')
    with about:
        '''
        
        The data is collected and used only for the purpose of analysis for its users. You are protected under GDPR law.

        '''


