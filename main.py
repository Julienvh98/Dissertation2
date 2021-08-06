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
from botocore.exceptions import ClientError
import io
import scipy

from scipy import signal

#rounding numbers to 2 decimal places
pd.set_option('precision', 2)

#limiting the format to 2 decimal places to make it easier to read for the user
pd.options.display.float_format = "{:.2f}".format


# SETUP ----------------------------------------------------------------------------------------------------------------

#uploading logo images that will be used & config
st.set_page_config(page_title='Comp.Air Dashboard',
                   page_icon='https://i.ibb.co/rbZyb0N/icon3.png',
                   layout="wide")

#creating space between header and image
col1, mid, col2 = st.beta_columns([10,6,20])

#creating header and image
with col1:
    st.title('Comp.Air Dashboard')
with col2:
    st.image('https://i.ibb.co/PwCKwyp/header.png', width=90)

# creating beta columns to organise the input functions
name_cols = st.beta_columns(3)

#options in alphabetical order
option2 = name_cols[0].selectbox("Which Metric?", ('Air Pressure', 'AQI', 'eC02','Humidity', 'PM1','PM2.5', 'PM10', 'Temperature', 'VOCs' ),6)

option = name_cols[1].selectbox("Which Dashboard?", ('Overview','Comparison', 'FAQ'),0)

user_input = name_cols[2].text_input('Input your device name here:')

#adjusting the padding of the dashboard to enhance the use of space
padding = 3
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)

#removing the developers menu (should not be there for users)
st.markdown(""" <style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style> """, unsafe_allow_html=True)

# GETTING DATA --------------------------------------------------------------------------------------------------------

if user_input != "":

#caching the data, will only run the function if it has not been run before
    def get_data():
        s3 = boto3.client("s3", \
                          region_name="eu-west-2", \
                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                          aws_secret_access_key="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")

        response = s3.list_objects(Bucket= user_input)

        df_list = []

        for file in response["Contents"]:

# error handling to check if any files are missing from the bucket (it will ignore missing files)
            try:
                obj = s3.get_object(Bucket= user_input, Key=file["Key"])
                obj_read = obj["Body"].read()
                obj_df = pd.read_csv(io.BytesIO(obj_read))
                df_list.append(obj_df)

            except ClientError as ex:
                if ex.response['Error']['Code'] == 'NoSuchKey':
                    pass
                else:
                    raise

                obj = s3.get_object(Bucket= user_input, Key=file["Key"])
                obj_df = pd.read_csv(obj["Body"], error_bad_lines = False)
                df_list.append(obj_df)


        df_n = pd.concat(df_list)

        return df_n

    df_n = get_data()


    # getting the data for the all comp.air device's

    @st.cache (allow_output_mutation=True)
    def get_data_all():
        s3 = boto3.client("s3", \
                          region_name="eu-west-2", \
                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                          aws_secret_access_key="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")

        response = s3.list_objects(Bucket='allsensorsrecent')

        df_list_all = []

        for file in response["Contents"]:
            obj = s3.get_object(Bucket='allsensorsrecent', Key=file["Key"])
            obj_df = pd.read_csv(obj["Body"])
            df_list_all.append(obj_df)

        df_1 = pd.concat(df_list_all)

        return df_1

    df_1 = get_data_all()

# CREATING AIR MEASURED COUNTER ----------------------------------------------------------------------------------------

    count = len(df_1.index)

    scount = '{:,}'.format(count)

# CREATING HEADERS FOR DIFFERENT DASHBOARDS ------------------------------------------------------------------------

    if option == "Overview" or option == "Comparison" :
        st.header(option2 + " " + option)

    if option == "FAQ":
        st.header(option)

# CLEANING DATA --------------------------------------------------------------------------------------------------------
    #caching the cleaning process to speed up the cleaning process,
    # getting the data was not cached because when cached streamlit
    # detects that an object returned by the get_data function is mutated outside of the get_data function.

    @st.cache
    def clean(dataf):


        dataf["Date"] = pd.to_datetime(dataf.Date)
        dataf["Date"] = dataf["Date"].astype(str).str[0:10]
        dataf['Time(min)'] = dataf["Time (UTC)"].astype(str).str[:-3]
        dataf['Time(min)'] = dataf['Time(min)'].str[:-2] + "00"

        dataf = dataf.drop(["Unnamed: 0", "Timestamp", "Time (UTC)"], axis=1)

        #concatenating the Date (in datetimeformat) and the Time(min) into one column
        dataf["Timestamp"] = pd.to_datetime(dataf["Date"].astype(str)+" "+dataf["Time(min)"].astype(str))

        #setting this new column as the index
        dataf = dataf.set_index("Timestamp")
        dataf.sort_values("Timestamp", inplace=True)

        #renaming cetain columns to facilitate the use of the input
        dataf.rename(columns={'Pm25': 'PM2.5', 'Pm1': 'PM1','Pm10': 'PM10' }, inplace=True)

        return dataf

    #applying the function to all three datasets

    df_n = clean(df_n)

    df_1 = clean(df_1)



# DATAFRAME TRANSFORMATION -----------------------------------------------------------------------------------

    df_nu = df_n.groupby([df_n.index.values.astype('<M8[h]')]).mean()

    most_recent_date = df_nu.index.max()

    @st.cache
    def transform():
        # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)

        #data from the last 24 hours
        hour24 = df_nu[df_nu.index>=(most_recent_date-dt.timedelta(hours=24))]
        hour24_all = df_1[df_1.index>=(most_recent_date-dt.timedelta(hours=24))]

        #data from the last 7 days
        day7 = df_nu[df_nu.index>=(most_recent_date-dt.timedelta(days=7))]
        day7_all = df_1[df_1.index>=(most_recent_date-dt.timedelta(days=7))]

        #data from the last 30 days
        day30 = df_nu[df_nu.index>=(most_recent_date-dt.timedelta(days=30))]
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

        all = {'24 Hours':m24_all, '7 Days': mday7_all, '30 Days': mday30_all, }
        dfavg2 = pd.DataFrame(data=all)

        # rouding decimals to 2 places
        dfavg= dfavg.round(decimals=2)
        dfavg2 = dfavg2.round(decimals=2)

        return dfavg, dfavg2, day30, day30_all, hour24, hour24_all, day7, day7_all

    dfavg, dfavg2, day30, day30_all, hour24, hour24_all, day7, day7_all = transform()

# Air Pressure DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'Air Pressure':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: the pressure within the atmosphere of Earth measured in hectopascals (hPa).''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)


            #specifying the layout of the page
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            #reformating the dataframe to be able to plot
            temp = dfavg.loc[dfavg.index == 'Air Pressure']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            st.dataframe(temp)
            st.dataframe(temp2)

            temp3 = dfavg2.loc[dfavg2.index == 'Air Pressure']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            #creating the bar plot
            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['Air Pressure'],
                        marker_color='crimson',
                        text=temp2['Air Pressure'],
                        textposition='auto',
                        texttemplate="%{y:.2f}hPa"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['Air Pressure'],
                    marker_color='darkblue',
                    text=temp4['Air Pressure'],
                    textposition='auto',
                    texttemplate="%{y:.2f}hPa"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['Air Pressure'],
                        text=temp2['Air Pressure'],
                        textposition='auto',
                        texttemplate="%{y:.2f} hPa",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average Air Pressure of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average Air Pressure in hPa ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)

            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['Air Pressure']))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "Air Pressure in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "Air Pressure in hPa ",
                        font=dict(
                            family="Arial",
                            size=14))

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['Air Pressure']))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="Air Pressure in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="Air Pressure in hPa",
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

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")
            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " hPa Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4','5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')


            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2

                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                            name= user_input ,
                            x=day30.index, y=day30['Air Pressure'],
                            marker_color='crimson'
                        ), go.Scatter(
                            name= user_input2,
                            x=day30_2.index, y=day30_2['Air Pressure'],
                            marker_color='darkblue',
                        )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Air Pressure" ,
                        xaxis_title="Time",
                        yaxis_title="Air Pressure in hPa ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Air Pressure'],
                        marker_color='crimson'
                        ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Air Pressure'],
                        marker_color='darkblue'
                        ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Air Pressure'],
                        marker_color='darkslategrey'
                        )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Air Pressure",
                        xaxis_title="Time",
                        yaxis_title="Air Pressure in hPa ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')


                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)


            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4

                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Air Pressure'],
                        marker_color='crimson'
                        ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Air Pressure'],
                        marker_color='darkblue'
                        ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Air Pressure'],
                        marker_color='gold'
                        ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['Air Pressure'],
                        marker_color='forestgreen'
                        )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Air Pressure",
                        xaxis_title="Time",
                        yaxis_title="Air Pressure in hPa ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)


            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5

                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Air Pressure'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Air Pressure'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Air Pressure'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['Air Pressure'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['Air Pressure'],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                            autosize=False,
                            width=800,
                            height=520,
                            title="Comparing Air Pressure",
                            xaxis_title="Time",
                            yaxis_title="Air Pressure in hPa ",
                            font=dict(
                                family="Arial",
                                size=14)
                        )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)


    # AQI DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'AQI':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: an air quality index used by government agencies, the higher the AQI value, the greater the level of air pollution.''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')
            with about:
                '''
                - Keep  rugs and carpet clean 
                - Get indoor plants
                - Clean your bathroom/kitchwn ducts,vents and filters.
                
                _Refer to FAQ for sources_
                '''

            st.image('https://i.ibb.co/jLdDjTN/AQI.png')
            st.markdown(''' _Source: https://www.airnow.gov/_ ''')

            #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            #AQI

            temp = dfavg.loc[dfavg.index == 'AQI']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'AQI']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['AQI'],
                        marker_color='crimson',
                        text=temp2['AQI'],
                        textposition='auto',
                        texttemplate="%{y:.2f}"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['AQI'],
                    marker_color='darkblue',
                    text=temp4['AQI'],
                    textposition='auto',
                    texttemplate="%{y:.2f}"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['AQI'],
                        text=temp2['AQI'],
                        textposition='auto',
                        texttemplate="%{y:.2f}",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average AQI of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average AQI",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)

            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['AQI']))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "AQI in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "AQI",
                        font=dict(
                            family="Arial",
                            size=14))

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['AQI'], name = user_input))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="AQI in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="AQI ",
                    font=dict(
                        family="Arial",
                        size=14))

            line30.add_trace(go.Scatter(
                x=day30.index,
                y=signal.savgol_filter(day30['AQI'],
                                       121,  # window size used for filtering (24 points per day - 31 * 24 = 744/6 = 124 +1
                                       3), # order of fitted polynomial

                name='SG Smoothing'
            ))

            with row2_1:
                st.plotly_chart(line24)

            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map
            st.write('')

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " AQI Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['AQI'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['AQI'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing AQI",
                        xaxis_title="Time",
                        yaxis_title="AQI ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['AQI'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['AQI'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['AQI'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing AQI",
                        xaxis_title="Time",
                        yaxis_title="AQI ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['AQI'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['AQI'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['AQI'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['AQI'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing AQI",
                        xaxis_title="Time",
                        yaxis_title="AQI",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['AQI'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['AQI'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['AQI'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['AQI'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['AQI'],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing AQI",
                        xaxis_title="Time",
                        yaxis_title="AQI",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

# eC02 DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'eC02':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: carbon dioxide measured electronically in parts per million (ppm).''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')

            with about:
                '''
                - 1400 ppm will ensure good indoor air quality in most situations
                - Above 1600 ppm indicates poor air quality
                - Open windows 
                - Limit open flames (fireplaces, candles)
                - Incorporate plants
                - Invest in an air purifier
                - Increase airflow while cooking

                _Refer to FAQ for sources_
                '''

            #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            temp = dfavg.loc[dfavg.index == 'eC02']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'eC02']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['eC02'],
                        marker_color='crimson',
                        text=temp2['eC02'],
                        textposition='auto',
                        texttemplate="%{y:.1f}ppm"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['eC02'],
                    marker_color='darkblue',
                    text=temp4['eC02'],
                    textposition='auto',
                    texttemplate="%{y:.1f}ppm"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['eC02'],
                        text=temp2['eC02'],
                        textposition='auto',
                        texttemplate="%{y:.1f}ppm",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average eC02 of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average eC02 ppm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)


            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['eC02'], name = user_input))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "eC02 in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "eC02 ppm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['eC02'], name = user_input))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="eC02 in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="eC02 ppm ",
                    font=dict(
                        family="Arial",
                        size=14))

            line30.add_trace(go.Scatter(
                x=day30.index,
                y=signal.savgol_filter(day30['eC02'],
                                       121,  # window size used for filtering (24 points per day - 31 * 24 = 744/6 = 124 +1
                                       3), # order of fitted polynomial

                name='SG Smoothing'
            ))

            with row2_1:
                st.plotly_chart(line24)


            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map

            st.write('')

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['eC02'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['eC02'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing eC02",
                        xaxis_title="Time",
                        yaxis_title="eC02 ppm ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['eC02'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['eC02'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['eC02'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing eC02",
                    xaxis_title = "Time",
                                  yaxis_title = "eC02 ppm ",
                                                font = dict(
                        family="Arial",
                        size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['eC02'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['eC02'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['eC02'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['eC02'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing eC02",
                        xaxis_title="Time",
                        yaxis_title="eC02 ppm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['eC02'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['eC02'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['eC02'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['eC02'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['eC02'],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing eC02",
                        xaxis_title="Time",
                        yaxis_title="eC02 ppm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

# TEMPERATURE DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'Temperature':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: temperature measured in degree Celcius °C.''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')

            with about:
                '''
                - High temperatures can cause insufficient humidity
                - High temperature and humidity levels can also increase concentrations of some pollutants
                - A temperature of 19°C to 24°C helps you to prevent the drying of your nasal passage = less susceptible to viruses 
                
                _Refer to FAQ for sources_
                '''

            #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            #TEMPERATURE

            temp = dfavg.loc[dfavg.index == 'Temperature']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'Temperature']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

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
                        width=850,
                        height=520,
                        title = "Average Temperature of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average Temperature in °C ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

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

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " °C Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Temperature'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Temperature'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Temperature",
                        xaxis_title="Time",
                        yaxis_title="Temperature in °C  ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Temperature'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Temperature'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Temperature'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Temperature",
                    xaxis_title = "Time",
                                  yaxis_title = "Temperature in °C ",
                                                font = dict(
                        family="Arial",
                        size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Temperature'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Temperature'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Temperature'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['Temperature'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Temperature",
                        xaxis_title="Time",
                        yaxis_title="Temperature in °C ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Temperature'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Temperature'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Temperature'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['Temperature'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['Temperature'],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Temperature",
                        xaxis_title="Time",
                        yaxis_title="Temperature in °C ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)



# Humidity DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'Humidity':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: the concentration of water vapour present in the air.''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')

            with about:
                '''
                - Humidity above 60% can lead to mould growth
                - High temperature and humidity levels can also increase concentrations of some pollutants
                - Mold spores, dust mites and other allergens survive best in high humidity environments
                - Bacteria and viruses that cause respiratory infections thrive in extremely high and extremely low humidity
                - To decrease humidity: use A/C, check for water leaks, get a Dehumidifier, open a window
                - To increase humidity: warm showers, hang laundry inside
               
               _Refer to FAQ for sources_
                '''


            #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            temp = dfavg.loc[dfavg.index == 'Humidity']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'Humidity']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['Humidity'],
                        marker_color='crimson',
                        text=temp2['Humidity'],
                        textposition='auto',
                        texttemplate="%{y:.2f}%"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['Humidity'],
                    marker_color='darkblue',
                    text=temp4['Humidity'],
                    textposition='auto',
                    texttemplate="%{y:.2f}%"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['Humidity'],
                        text=temp2['Humidity'],
                        textposition='auto',
                        texttemplate="%{y:.2f}%",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average Humidity of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average Humidity  ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)


            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['Humidity'], name = user_input))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "Humidity in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "Humidity",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['Humidity'], name = user_input))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="Humidity in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="Humidity",
                    font=dict(
                        family="Arial",
                        size=14))

            line30.add_trace(go.Scatter(
                x=day30.index,
                y=signal.savgol_filter(day30['Humidity'],
                                       121,  # window size used for filtering (24 points per day - 31 * 24 = 744/6 = 124 +1
                                       3), # order of fitted polynomial

                name='SG Smoothing'
            ))

            with row2_1:
                st.plotly_chart(line24)


            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map

            st.write('')

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Humidity'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Humidity'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Humidity",
                        xaxis_title="Time",
                        yaxis_title="Humidity in % ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Humidity'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Humidity'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Humidity'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Humidity",
                    xaxis_title = "Time",
                                  yaxis_title = "Humidity in % ",
                                                font = dict(
                        family="Arial",
                        size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Humidity'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Humidity'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Humidity'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['Humidity'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Humidity",
                        xaxis_title="Time",
                        yaxis_title="Humidity in % ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['Humidity'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['Humidity'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['Humidity'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['Humidity'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['Humidity'],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing Humidity",
                        xaxis_title="Time",
                        yaxis_title="Humidity in % ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

# PM2.5 DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'PM2.5':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: atmospheric particulate matter (PM) that have a diameter of less than 2.5 micrometers (μm) .''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')

            with about:
                '''
                - Particulate Matter levels are mostly dependent on outdoor air quality
                - Particulate Matter sources: engine combustion, industrial processes
                - Monitor outdoor PM levels and open/close windows accordingly
                - Purchase a air cleaner to reduce PM
                - Avoid using anything that burns, such as wood fireplaces, gas logs and even candles or incense
                - Avoid smoking indoors
               
               _Refer to FAQ for sources_
                '''


            #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            temp = dfavg.loc[dfavg.index == 'PM2.5']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'PM2.5']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['PM2.5'],
                        marker_color='crimson',
                        text=temp2['PM2.5'],
                        textposition='auto',
                        texttemplate="%{y:.2f} μm"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['PM2.5'],
                    marker_color='darkblue',
                    text=temp4['PM2.5'],
                    textposition='auto',
                    texttemplate="%{y:.2f} μm"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['PM2.5'],
                        text=temp2['PM2.5'],
                        textposition='auto',
                        texttemplate="%{y:.2f} μm",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average PM2.5 of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average PM2.5 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)


            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['PM2.5'], name = user_input))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "PM2.5 in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "PM2.5 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['PM2.5'], name = user_input))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="PM2.5 in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="PM2.5 μm ",
                    font=dict(
                        family="Arial",
                        size=14))

            line30.add_trace(go.Scatter(
                x=day30.index,
                y=signal.savgol_filter(day30['PM2.5'],
                                       121,  # window size used for filtering (24 points per day - 31 * 24 = 744/6 = 124 +1
                                       3), # order of fitted polynomial

                name='SG Smoothing'
            ))

            with row2_1:
                st.plotly_chart(line24)


            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map

            st.write('')

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM2.5'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM2.5'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM2.5",
                        xaxis_title="Time",
                        yaxis_title="PM2.5 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM2.5'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM2.5'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM2.5'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM2.5",
                    xaxis_title = "Time",
                                  yaxis_title = "PM2.5 μm ",
                                                font = dict(
                        family="Arial",
                        size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM2.5'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM2.5'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM2.5'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['PM2.5'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM2.5",
                        xaxis_title="Time",
                        yaxis_title="PM2.5 in μm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM2.5 '],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM2.5 '],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM2.5 '],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['PM2.5 '],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['PM2.5 '],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM2.5 ",
                        xaxis_title="Time",
                        yaxis_title="PM2.5  in μm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

# PM1 DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'PM1':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''' :books: * Definition *: atmospheric particulate matter (PM) that have a diameter of less than 1 micrometers (μm) . ''')


            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')

            with about:
                '''
                - Particulate Matter levels are mostly dependent on outdoor air quality
                - Particulate Matter sources: engine combustion, industrial processes
                - Monitor outdoor PM levels and open/close windows accordingly
                - Purchase a air cleaner to reduce PM
                - Avoid using anything that burns, such as wood fireplaces, gas logs and even candles or incense
                - Avoid smoking indoors
               
               _Refer to FAQ for sources_
                '''


            #reformating the dataframe to be able to plot
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            temp = dfavg.loc[dfavg.index == 'PM1']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'PM1']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['PM1'],
                        marker_color='crimson',
                        text=temp2['PM1'],
                        textposition='auto',
                        texttemplate="%{y:.2f} μm"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['PM1'],
                    marker_color='darkblue',
                    text=temp4['PM1'],
                    textposition='auto',
                    texttemplate="%{y:.2f} μm"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['PM1'],
                        text=temp2['PM1'],
                        textposition='auto',
                        texttemplate="%{y:.2f} μm",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average PM1 of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average PM2.5 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)


            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['PM1'], name = user_input))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "PM1 in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "PM1 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['PM1'], name = user_input))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="PM1 in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="PM1 μm ",
                    font=dict(
                        family="Arial",
                        size=14))

            line30.add_trace(go.Scatter(
                x=day30.index,
                y=signal.savgol_filter(day30['PM1'],
                                       121,  # window size used for filtering
                                       3), # order of fitted polynomial

                name='SG Smoothing'
            ))

            with row2_1:
                st.plotly_chart(line24)


            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map

            st.write('')

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM1'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM1'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM1",
                        xaxis_title="Time",
                        yaxis_title="PM1 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM1'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM1'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM1'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM1",
                    xaxis_title = "Time",
                                  yaxis_title = "PM1 μm ",
                                                font = dict(
                        family="Arial",
                        size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM1'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM1'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM1'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['PM1'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM1",
                        xaxis_title="Time",
                        yaxis_title="PM1 in μm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM1'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM1'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM1'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['PM1'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['PM1'],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM1 ",
                        xaxis_title="Time",
                        yaxis_title="PM1  in μm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)


# PM10 DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'PM10':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: atmospheric particulate matter (PM) that have a diameter of less than 10 micrometers (μm) .''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')

            with about:
                '''
                - Particulate Matter levels are mostly dependent on outdoor air quality
                - Particulate Matter sources: engine combustion, industrial processes
                - Monitor outdoor PM levels and open/close windows accordingly
                - Purchase a air cleaner to reduce PM
                - Avoid using anything that burns, such as wood fireplaces, gas logs and even candles or incense
                - Avoid smoking indoors
                
                _Refer to FAQ for sources_
                '''

            #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            temp = dfavg.loc[dfavg.index == 'PM10']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'PM10']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['PM10'],
                        marker_color='crimson',
                        text=temp2['PM10'],
                        textposition='auto',
                        texttemplate="%{y:.2f} μm"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['PM10'],
                    marker_color='darkblue',
                    text=temp4['PM10'],
                    textposition='auto',
                    texttemplate="%{y:.2f} μm"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['PM10'],
                        text=temp2['PM10'],
                        textposition='auto',
                        texttemplate="%{y:.2f} μm",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average PM10 of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average PM10 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)


            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['PM10'], name = user_input))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "PM10 in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "PM10 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['PM10'], name = user_input))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="PM10 in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="PM10 μm ",
                    font=dict(
                        family="Arial",
                        size=14))

            line30.add_trace(go.Scatter(
                x=day30.index,
                y=signal.savgol_filter(day30['PM10'],
                                       121,  # window size used for filtering (24 points per day - 31 * 24 = 744/6 = 124 +1
                                       3), # order of fitted polynomial

                name='SG Smoothing'
            ))

            with row2_1:
                st.plotly_chart(line24)


            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map

            st.write('')

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM10'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM10'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM10",
                        xaxis_title="Time",
                        yaxis_title="PM10 μm ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM10'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM10'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM10'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM10",
                    xaxis_title = "Time",
                                  yaxis_title = "PM10 μm ",
                                                font = dict(
                        family="Arial",
                        size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM10'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM10'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM10'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['PM10'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM10",
                        xaxis_title="Time",
                        yaxis_title="PM10 in μm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['PM10'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['PM10'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['PM10'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['PM10'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['PM1 '],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing PM10 ",
                        xaxis_title="Time",
                        yaxis_title="PM10  in ppm",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)
# VOCs DASHBOARD -------------------------------------------------------------------------------------------------

    if option2 == 'VOCs':

        if option == 'Overview':

            st.write('')

            row1_1,space, row1_2, row1_3 = st.beta_columns((1.5,1,0.2,1))

            with row1_1:
                st.markdown(''':books: * Definition *: Volatile organic compounds (VOC) are organic chemicals that have a high vapour pressure at room temperature.''')

            with row1_2:
                st.image('https://i.ibb.co/T8887H7/air.png', width=35)

            with row1_3:
                st.markdown('''Comp.Air samples taken of all devices in the last month: ''' + scount)

            about = st.beta_expander(
                'Recommendations/Contextual Info')

            with about:
                '''
                To reduce levels:
                
                - Limit paints, paint strippers and other solvents
                - Limit wood preservatives
                - Limit aerosol sprays
                - Limit cleansers and disinfectants
                - Limit moth repellents and air fresheners
                - Limit stored fuels and automotive products
                - Limit dry-cleaned clothing
                - Limit pesticide    
                - Limit personal care products (moisturisers, foundation etc.)
                - Meet or exceed any label precautions
                - Do not store opened containers of unused paints and similar materials
                - Make sure you provide plenty of fresh air when using these the above products
    
                _Refer to FAQ for sources_
                '''

            #specifying the layout of the page each row is working as a container with spaces. The sizes of the containers and spaces are specified.
            st.write('')

            row1_1, row1_2, row1_3 = st.beta_columns((0.75,3,0.75))

            temp = dfavg.loc[dfavg.index == 'VOCs']
            temp2 = temp.T

            temp2['Time'] = temp2.index

            temp3 = dfavg2.loc[dfavg2.index == 'VOCs']
            temp4 = temp3.T

            temp4['Time'] = temp4.index

            compareplot = go.Figure(data=[go.Bar(
                        name= user_input,
                        x=temp2['Time'] , y=temp2['VOCs'],
                        marker_color='crimson',
                        text=temp2['VOCs'],
                        textposition='auto',
                        texttemplate="%{y:.2f}"
                    ), go.Bar (
                    name = 'All Comp.Air Devices',
                    x=temp4['Time'], y=temp4['VOCs'],
                    marker_color='darkblue',
                    text=temp4['VOCs'],
                    textposition='auto',
                    texttemplate="%{y:.2f}"
            )
                ])


            templot = go.Figure(data=[go.Bar(
                        x=temp2['Time'] , y=temp2['VOCs'],
                        text=temp2['VOCs'],
                        textposition='auto',
                        texttemplate="%{y:.2f}",
            )])

            compareplot.update_layout(
                        autosize=False,
                        width=850,
                        height=520,
                        title = "Average VOCs of Various Time Periods",
                        xaxis_title = "Time Periods (Based on current day)",
                        yaxis_title = "Average VOCs ppm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            with row1_2:
                st.plotly_chart(compareplot)

            #ROW 2
            st.write('')

            row2_1, row2_2, = st.beta_columns(2)


            #LINEPLOTS
            line24 = go.Figure(data=go.Scatter(x=hour24.index, y=hour24['VOCs'], name = user_input))

            line24.update_layout(
                        autosize=False,
                        width=600,
                        height=450,
                        title = "VOCs in the Last 24 hours",
                        xaxis_title = "Time",
                        yaxis_title = "VOCs ppm ",
                        font=dict(
                            family="Arial",
                            size=14)
            )

            line30 = go.Figure(data=go.Scatter(x=day30.index, y=day30['VOCs'], name = user_input))

            line30.update_layout(
                    autosize=False,
                    width=600,
                    height=450,
                    title="VOCs in the Last 30 Days",
                    xaxis_title="Time",
                    yaxis_title="VOCs ppm ",
                    font=dict(
                        family="Arial",
                        size=14))

            line30.add_trace(go.Scatter(
                x=day30.index,
                y=signal.savgol_filter(day30['VOCs'],
                                       121,  # window size used for filtering (24 points per day - 31 * 24 = 744/6 = 124 +1
                                       3), # order of fitted polynomial

                name='SG Smoothing'
            ))

            with row2_1:
                st.plotly_chart(line24)


            with row2_2:
                st.plotly_chart(line30)

            #ROW 3

            #Map

            st.write('')

            space1, row3_1, space2 = st.beta_columns((0.5,3,0.75))

            map = px.density_mapbox(df_1, lat='Latitude', lon='Longitude', z=option2, radius=4,
                                    center=dict(lat=54.5, lon=-4), zoom=4.3,
                                    mapbox_style="stamen-terrain")

            map.update_layout(
                    autosize=False,
                    width=850,
                    height=600,
                    title="Map of " + option2 + " Across All Comp.Air Devices",
                    xaxis_title="Time",
                    yaxis_title= option2,
                    font=dict(
                        family="Arial",
                        size=14))
            with row3_1:
                st.plotly_chart(map)

        if option == 'Comparison':

            st.write('')

            name_cols = st.beta_columns(5)

            number = name_cols[0].selectbox("How many Devices?", ('2', '3', '4', '5'), 3)

            user_input2 = name_cols[1].text_input('Input additional device name here:')

            if number == '3':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')

            if number == '4':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')

            if number == '5':
                user_input3 = name_cols[2].text_input('Input 3rd device name here:')
                user_input4 = name_cols[3].text_input('Input 4th device name here:')
                user_input5 = name_cols[4].text_input('Input 5th device name here:')

            # getting the data for the additional device if the input is not blank (makes sure no error is displayed)
            if number == '2':
                if user_input2 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['VOCs'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['VOCs'],
                        marker_color='darkblue',
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing VOCs",
                        xaxis_title="Time",
                        yaxis_title="VOCs ",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '3':
                if user_input3 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['VOCs'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['VOCs'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['VOCs'],
                        marker_color='darkslategrey'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing VOCs",
                    xaxis_title = "Time",
                                  yaxis_title = "VOCs ",
                                                font = dict(
                        family="Arial",
                        size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '4':
                if user_input4 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['VOCs'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['VOCs'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['VOCs'],
                        marker_color='gold'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['VOCs'],
                        marker_color='forestgreen'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing VOCs",
                        xaxis_title="Time",
                        yaxis_title="VOC",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)

            if number == '5':
                if user_input5 != "":
                    def get_data2():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input2)

                        df_list2 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input2, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list2.append(obj_df)

                        df_n2 = pd.concat(df_list2)

                        return df_n2


                    df_n2 = get_data2()
                    df_n2 = clean(df_n2)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n2 = df_n2.groupby([df_n2.index.values.astype('<M8[h]')]).mean()

                    day30_2 = df_n2[df_n2.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data3():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input3)

                        df_list3 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input3, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list3.append(obj_df)

                        df_n3 = pd.concat(df_list3)

                        return df_n3


                    df_n3 = get_data3()
                    df_n3 = clean(df_n3)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n3 = df_n3.groupby([df_n3.index.values.astype('<M8[h]')]).mean()

                    day30_3 = df_n3[df_n3.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data4():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input4)

                        df_list4 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input4, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list4.append(obj_df)

                        df_n4 = pd.concat(df_list4)

                        return df_n4


                    df_n4 = get_data4()
                    df_n4 = clean(df_n4)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n4 = df_n4.groupby([df_n4.index.values.astype('<M8[h]')]).mean()

                    day30_4 = df_n4[df_n4.index >= (most_recent_date - dt.timedelta(days=30))]


                    def get_data5():
                        s3 = boto3.client("s3", \
                                          region_name="eu-west-2", \
                                          aws_access_key_id="AKIA3C5IQYEMH7773L7F", \
                                          aws_secret_access_key="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")

                        response = s3.list_objects(Bucket=user_input5)

                        df_list5 = []

                        for file in response["Contents"]:
                            obj = s3.get_object(Bucket=user_input5, Key=file["Key"])
                            obj_df = pd.read_csv(obj["Body"])
                            df_list5.append(obj_df)

                        df_n5 = pd.concat(df_list5)

                        return df_n5


                    df_n5 = get_data5()
                    df_n5 = clean(df_n5)

                    # changing from a frequency of data point per minute to the hourly average to enhance the user experience in the lineplots (individual devices only as there are no aggregate line plots)
                    df_n5 = df_n5.groupby([df_n5.index.values.astype('<M8[h]')]).mean()

                    day30_5 = df_n5[df_n5.index >= (most_recent_date - dt.timedelta(days=30))]

                    compareline = go.Figure(data=[go.Scatter(
                        name=user_input,
                        x=day30.index, y=day30['VOCs'],
                        marker_color='crimson'
                    ), go.Scatter(
                        name=user_input2,
                        x=day30_2.index, y=day30_2['VOCs'],
                        marker_color='darkblue'
                    ), go.Scatter(
                        name=user_input3,
                        x=day30_3.index, y=day30_3['VOCs'],
                        marker_color='yellow'
                    ), go.Scatter(
                        name=user_input4,
                        x=day30_4.index, y=day30_4['VOCs'],
                        marker_color='forestgreen'
                    ), go.Scatter(
                        name=user_input5,
                        x=day30_5.index, y=day30_5['VOCs'],
                        marker_color='violet'
                    )])

                    compareline.update_layout(
                        autosize=False,
                        width=800,
                        height=520,
                        title="Comparing VOCs ",
                        xaxis_title="Time",
                        yaxis_title="VOCs",
                        font=dict(
                            family="Arial",
                            size=14)
                    )

                    st.write('')

                    row1_1, row1_2, row1_3 = st.beta_columns((0.75, 3, 0.75))

                    with row1_2:
                        st.plotly_chart(compareline)
if option == "FAQ":

    st.markdown('___')
    about = st.beta_expander('About & Metrics Info')
    with about:
            '''
            Thanks for checking out our Dashboard ! It was built entirely using Comp.Air (https://www.compair.earth/) data. 
            
            This app is a dashboard that runs an analysis on any desired metric captured by Comp.Air devices. 
             
            They are briefly described below:
            
            **Air pressure**: also known as barometric pressure (after the barometer), is the pressure within the atmosphere of Earth. 
            
            **AQI**: an air quality index used by government agencies, the higher the AQI value, the greater the level of air pollution.

            **Humidity**: a quantity representing the amount of water vapour in the atmosphere or in a gas.

            **PM1**: atmospheric particulate matter (PM) that have a diameter of less than 1 micrometers (μm) .
            
            **PM2.5**: atmospheric particulate matter (PM) that have a diameter of less than 2.5 micrometers (μm) .
            
            **PM10**: atmospheric particulate matter (PM) that have a diameter of less than 10 micrometers (μm) .
            
            **Temperature**: measured in degree Celcius °C.
            
            **VOCs**: Volatile organic compounds (VOC) are organic chemicals that have a high vapour pressure at room temperature.

            
            *Disclaimer - Some of the data might not be perfectly correct, due to environmental factors and/or mispositioning of the device. 
            Try to avoid placing the device close to any hobs, ovens, radiators. *
            
            '''

    st.markdown('___')
    about = st.beta_expander('Is My Data Protected ?')
    with about:
        '''
        
        The data is collected and used only for the purpose of analysis for its users. You are protected under GDPR law.

        '''

    st.markdown('___')
    about = st.beta_expander('What is SG Smoothing ?')
    with about:
        '''

        A Savitzky–Golay filter is a digital filter that can be applied to a set of digital data points for the purpose of smoothing the data, that is, to increase the precision of the data without distorting the signal tendency.
        
        Source: https://en.wikipedia.org/wiki/Savitzky%E2%80%93Golay_filter

        '''

    st.markdown('___')
    about = st.beta_expander('What are the stress levels and recommended operating conditions for the Comp.Air Device?')
    with about:
        '''
        **Recommended Operating Conditions**
        
        The sensor shows best performance when operated within recommended normal temperature and humidity range of 10 to 40 °C and 20 to 80 % RH, respectively.
        
        
        **Stress Levels**
        
        Operating temperature range: -10 to 60°C
        
        Operating humdity range: 0 to 95 % RH
        
        Supply voltage VDD: -0.3 to 5.5 V
        
        '''

    st.markdown('___')
    about = st.beta_expander(
        'What are the sources for the recommendations in the Overview Dashboards?')
    with about:
        '''
            **AQI**: 
            - https://timesofindia.indiatimes.com/life-style/health-fitness/health-news/6-ways-to-improve-indoor-air-quality/photostory/79477493.cms
            
            **Humidity**: 
            - https://www.epa.gov/mold/mold-course-chapter-2
            - http://penoil.com/blog/indoor-air-quality-humidity/#:~:text=Bacteria%20and%20viruses%20that%20cause,may%20include%20ozone%20and%20formaldehyde.
            - https://www.huskyair.com/blog/reducing-indoor-humidity/



            **PM1, PM2.5 & PM10 **:
            - https://www.airnow.gov/aqi/aqi-basics/extremely-high-levels-of-pm25/
            - https://molekule.science/what-is-pm-2-5-and-how-can-you-reduce-your-exposure/

            
            **Temperature**:
            - https://www.epa.gov/indoor-air-quality-iaq/introduction-indoor-air-quality
            - https://www.advsolned.com/why-temperature-is-important-for-indoor-air-quality/
            
            **VOCs**:
            - https://www.epa.gov/indoor-air-quality-iaq/volatile-organic-compounds-impact-indoor-air-quality

        '''





