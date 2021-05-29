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


#uploading logo images that will be used

# st.title('Comp.Air Dashboard')

st.set_page_config(page_title='Comp.Air Dashboard',
                   page_icon='/Users/Jujuvh/Desktop/icon3.png',
                   layout="wide")



col1, mid, col2 = st.beta_columns([10,6,20])
with col1:
    st.title('Comp.Air Dashboard')
with col2:
    st.image('/Users/Jujuvh/Desktop/header.png', width=90)


# with col1:
#     st.title('Comp.Air Dashboard')
# with col2:
#     st.image('/Users/Jujuvh/Desktop/header.png', width=90)

option2 = st.selectbox("Which Metric?", ('Temperature', 'Humidity', 'Air Pressure'),0)

option = st.selectbox("Which Dashboard?", ('Overview', 'Detailed',  'FAQ'),0)

# id = acess_key_id
#
# password = secret_access_key

#allsensorsrecent

user_input = st.text_input('Input your device name here:')
user_input2 = st.text_input('Input additional device name here:')

if option == "Overview":
    st.header(option2 + " " + option)

if option == 'Detailed':
    st.header(option2 + " " + option)

if option == "FAQ":
    st.header(option)



if user_input != "":
    def get_data():
        s3 = boto3.client("s3", \
                          region_name="eu-west-2", \
                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                          aws_secret_access_key="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")

        response = s3.list_objects(Bucket=user_input)

        df_list = []

        for file in response["Contents"]:
            obj = s3.get_object(Bucket=user_input, Key=file["Key"])
            obj_df = pd.read_csv(obj["Body"])
            df_list.append(obj_df)

        df_n = pd.concat(df_list)

        return df_n

    df_n = get_data()

    #getting the data for the additional device

    def get_data2():
        s3 = boto3.client("s3", \
                          region_name="eu-west-2", \
                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                          aws_secret_access_key="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")

        response = s3.list_objects(Bucket=user_input2)

        df_list = []

        for file in response["Contents"]:
            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
            obj_df = pd.read_csv(obj["Body"])
            df_list.append(obj_df)

        df_n2 = pd.concat(df_list)

        return df_n2

    df_n2 = get_data2()

    # getting the data for the all comp.air device's
    def get_data_all():
        s3 = boto3.client("s3", \
                          region_name="eu-west-2", \
                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                          aws_secret_access_key="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")

        response = s3.list_objects(Bucket='allsensorsrecent')

        df_list = []

        for file in response["Contents"]:
            obj = s3.get_object(Bucket='allsensorsrecent', Key=file["Key"])
            obj_df = pd.read_csv(obj["Body"])
            df_list.append(obj_df)

        df_1 = pd.concat(df_list)

        return df_1

    df_1 = get_data_all()



    # F9:5A:3E:AE:39:62

    #transforming the strange Date and Time (UTC) formatting

    def clean(dataf):
        dataf["Date"] = pd.to_datetime(dataf.Date)
        dataf['Time(min)'] = dataf["Time (UTC)"].astype(str).str[:-3]

        dataf = dataf.drop(["Unnamed: 0", "Timestamp", "Time (UTC)"], axis=1)

        #concacetting the Date (in datetimeformat) and the Time(min) into one column
        dataf["Timestamp"] = pd.to_datetime(dataf["Date"].astype(str)+" "+dataf["Time(min)"].astype(str))

        #setting this new column as the index
        dataf = dataf.set_index("Timestamp")
        dataf.sort_values("Timestamp", inplace=True)

        return dataf

    #applying the function to all three datasets
    df_n = clean(df_n)
    df_n2 = clean(df_n2)
    df_1 = clean(df_1)

    most_recent_date = df_n.index.max()

    #data from the last 24 hours
    hour24 = df_n[df_n.index>=(most_recent_date-dt.timedelta(hours=24))]
    hour24_all = df_1[df_1.index>=(most_recent_date-dt.timedelta(hours=24))]

    #data from the last 7 days
    day7 = df_n[df_n.index>=(most_recent_date-dt.timedelta(days=7))]
    day7_all = df_1[df_1.index>=(most_recent_date-dt.timedelta(days=7))]

    #data from the last 30 days
    day30 = df_n[df_n.index>=(most_recent_date-dt.timedelta(days=30))]
    day30_all = df_1[df_1.index>=(most_recent_date-dt.timedelta(days=30))]

    #grabbing the average of all timeframes
    m24 =hour24.mean()
    m24_all = hour24_all.mean()
    mday30 = day30.mean()
    mday30_all = day30_all.mean()
    mday7 = day7.mean()
    mday7_all = day7_all.mean()

    #creating a dataframe of all the averages from the different timeframes
    d = {'24 Hours':m24, '7 Days': mday7, '30 Days': mday30, }
    dfavg = pd.DataFrame(data=d)

    # dfavg['Device'] = 'Your Device'


    d2 = {'24 Hours':m24_all, '7 Days': mday7_all, '30 Days': mday30_all, }
    dfavg2 = pd.DataFrame(data=d2)

    # rouding decimals to 2 places
    dfavg= dfavg.round(decimals=2)

    #removing unnecessary metrics
    #dfavg = dfavg.drop(index=['Altitude','Longitude','Latitude'])

    #calculating the change between past hour and past month
    dif24h = ((m24-mday30)/mday30)

    #creating a dataframe of the change in average from the past hour and the past 30 days
    b = {'1 day Change to 30 days': dif24h}
    dfdif = pd.DataFrame(data=b)

    # rouding decimals to 2 places
    dfdif = dfdif.round(decimals=2)

    # #if negative change = colour is red, if positve change = colour is green

    #removing unnecessary metrics
    dfdif = dfdif.drop(index=['Altitude','Longitude','Latitude'])

    #grabbing the max of all timeframes
    max24 =hour24.max()
    maxday30 = day30.max()
    maxday7 = day7.max()


    #creating a dataframe of all the averages from the different timeframes
    d = {'24 Hours':max24 , '7 Days': maxday7, '30 Days': maxday30 }
    dfmax = pd.DataFrame(data=d)

    #removing unnecessary metrics
    dfmax = dfmax.drop(index=['Altitude','Longitude','Latitude','Address','Date','Time(min)'])


    #grabbing the min of all timeframes
    min24 =hour24.min()
    minday30 = day30.min()
    minday7 = day7.min()

    d = {'24 Hours':min24 , '7 Days': minday7, '30 Days': minday30 }
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

            temp3 = dfavg2.loc[dfavg2.index == 'Temperature']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            # df4 = pd.concat([temp2, temp4], axis=1, ignore_index=False)
            #
            # df4.columns = ['Your Device','All Comp.Air Devices']

            # st.dataframe(df4)

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['Temperature'],
                        marker_color='crimson',
                        text=temp2['Temperature'],
                        textposition='auto',
                        texttemplate="%{y:.2f}°C"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['Temperature'],
                    marker_color='darkblue',
                    text=temp4['Temperature'],
                    textposition='auto',
                    texttemplate="%{y:.2f}°C"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['Temperature'],
                        text=temp2['Temperature'],
                        textposition='auto',
                        texttemplate="%{y:.2f}°C",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title = "Average Temperature of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average Temperature in °C ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_1:
                st.plotly_chart(compareplot)



            # with row1_2:
            #     st.plotly_chart(line24)



            # line7 = go.Figure(data=go.Scatter(x=day7.index, y=day7['Temperature']))
            #
            # line7.update_layout(
            #     title="Temperature in the Last 7 Days",
            #     xaxis_title="Time",
            #     yaxis_title="Temperature in °C ",
            #     font=dict(
            #         family="Arial",
            #         size=14))

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)


            #LINEPLOTS



            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['Temperature']))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "Temperature in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "Temperature in °C ",
                        font=dict(
                            family="Arial",
                            size=14))

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['Temperature']))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="Temperature in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="Temperature in °C ",
                    font=dict(
                        family="Arial",
                        size=14))

            with row2_1:
                st.plotly_chart(line24)


            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map

            st.write('')

            row3_1, row3_2, = st.beta_columns(2)



            map = px.density_mapbox(df1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")


            map.update_layout(
                    autosize=False,
                    width=600,
                    height=600,
                    title="Map of Temperature across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title="Temperature in °C ",
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

    if option == 'Comparison of 2 devices':

        compareline = go.Figure(data=[go.Scatter(
            name='Your Device',
            x=day7.index, y=day7['Temperature'],
            marker_color='crimson'
        ), go.Bar(
            name='All Comp.Air Devices',
            x=day7['Time'], y=temp4['Temperature'],
            marker_color='darkblue',
            text=temp4['Temperature'],
            textposition='auto',
            texttemplate="%{y:.2f}°C"
        )
        ])

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


