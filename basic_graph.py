from __future__ import print_function

import ipywidgets as widgets
import numpy as np, pandas as pd
import requests, json, os, zipfile

from io import BytesIO
from ipywidgets import interact
from plotly import graph_objects as go, express as px
from sklearn.preprocessing import QuantileTransformer


""" Estos gráficos están basados en los datos de la universidad de
    JOHNS HOPKINS, que disponibiliza a diario en su Github 
    github.com/CSSEGISandData

    No es la fuente de la que parto. Mi fuente es el GitHub de ExpDev07,
    que ha montado un proyecto más avanzado que el mío, en donde utiliza
    entre otras cosas, Flask, para mostrar los datos.

    Mi pequeño proyecto no es tan avanzado. Es tan solo un poco de codigo
    para poder disponibilizar los datos de una manera rápida y sencilla, 
    usando un programa, Jupyter-Notebook, fácilmente instalable tanto en 
    Windows como en Linux, en donde será tan sencillo ejecutar este programa
    como:

    Paso 1) Abrir un notebook de Jupyter. 
    Paso 2) Ejecutar 'from basic_graph import *'   

    NOTA: Importante, para que sea sencillo, abrir Jupyter-notebook. La
          alternativa (común) es Jupyter-lab, que está basado en otra cosa
          (Node.js) y hay algunos problemas para mostrar los gráficos bien.

"""

def get_population():
    file = [file for file in os.listdir() if "Metadada" not in file and "POP.TOTL" in file]
    if len(file)==0:
        zip_file_url = "http://api.worldbank.org/v2/en/indicator/SP.POP.TOTL?downloadformat=csv"
        r = requests.get(zip_file_url)
        z = zipfile.ZipFile(BytesIO(r.content),"r")
        z.extractall()
        file = [file for file in os.listdir() if "Metadada" not in file and "POP.TOTL" in file]
    file = file[0]

    df = pd.read_csv(file,skiprows=4)\
           .drop(["Country Name","Indicator Name","Indicator Code"],axis=1)
    for col in df.columns[-4:]:
        if len(df.loc[pd.isna(df[col])==False])<df.shape[0]/2:
            df.drop(col,axis=1,inplace=True)
    max_value = df.columns[-1]

    for col in df.columns[1:-1]:
        if col<max_value:
            df.drop(col,axis=1,inplace=True)
        elif col>max_value: max_value = col
    df.columns = ['country_code_3','Latest_pop']
    return df

def add_percentage_population(df,mode):
    
    df_population = get_population()
    if mode == 'Absolute': df_aux = df.loc[:,df.columns[-6:-2]]
    else: df_aux = df.loc[:,df.columns[-7:-2]]

    df_aux.columns = ["Latest"]+[str(name) for name in df_aux.columns[1:]]
    df_aux = df_aux.merge(df_population,on="country_code_3")
    df_aux['%']= df_aux.Latest*(10**2)/df_aux[df_population.columns[-1]]

    scaler = QuantileTransformer(random_state=0)
    df_aux["Modified"] = scaler.fit_transform(df_aux[["%"]])
    
    return df_aux

def sort_columns(df,date):
    df = df.reset_index(drop=False)\
           .groupby(by=["index"])\
           .sum()
    df = df.loc[df[date] != 0, :]
    
    df_aux = df.T.reset_index(drop=False)
    df_aux['index'] = pd.to_datetime(df_aux["index"])
    df_aux = df_aux.sort_values(by="index")\
                   .set_index("index")
    return df_aux.T

def get_country_code(data,key='confirmed'):
    return pd.DataFrame([x.get("country_code") \
                                     for x in data],
                                 index=[x.get("country") for x in data],
                                 columns=['country_code'])\
             .drop_duplicates()

def resize_data(df):
    columns_to_change = df.columns[:-5]
    df_population = get_population()
    df_aux=df.merge(df_population,on="country_code_3")
    for col in columns_to_change:
        if type(col) != str:
            df_aux[col] = df_aux[col]*(10**2)/df_aux["Latest_pop"]
    return df_aux

def get_df(webpage_json,key='confirmed',continent='All',mode='Absolute'):
    relevant_data = webpage_json.get(key)
    year,month,day = relevant_data.get("last_updated")\
                                  .split("T")[0]\
                                  .split("-")
    
    date = str(int(month))+'/'+str(int(day))+'/'+year
    
    data = relevant_data.get("locations")
    
    df_countries = get_country_code(data,key)
    
    df = pd.DataFrame([x.get("history") \
                                     for x in data],
                                 index=[x.get("country") for x in data])
    df[date]=[x.get("latest") for x in data]
    
    df = sort_columns(df,date)
    
    df = df.merge(df_countries, left_index=True, right_index=True)\
           .merge(df_continents,on="country_code")
    
    if mode != 'Absolute': df = resize_data(df)
    
    if continent != 'All':
        return df.loc[df.continent==continent]\
                 .reset_index(drop=True)
    return df


def plot_lines_covid(df,mode,continente=None):

    columns_to_drop = ["country_code","continent","sub_region"]
    #if "Latest_pop" in df.columns: 
    #    columns_to_drop.extend(["Latest_pop"])
    
    fig = go.Figure()
    
    df = df.drop(columns_to_drop,axis=1)
    
    if continente != 'All': fig.update_layout(showlegend=True)
    else: fig.update_layout(showlegend=False)
    
    for country in df.country:
        if mode=='Relative':
            text = [country+'<br>Total:'+str(int(float(value)*float(df.loc[df.country==country,["Latest_pop"]].values[0][0])//100)) \
                    for value in df.loc[df.country==country,df.columns[:-3]].values[0]\
                   ]
        else: text= country    
        fig.add_trace(go.Scatter(x=df.columns[:-3], 
                                 y=df.loc[df.country==country,df.columns[:-3]].values[0],
                                 mode='lines',
                                 name=df.loc[df.country==country,["country_code_3"]].values[0][0],
                                 hovertext = text
                                )
                     )
    
    fig.show()

def plot_maps(df,mode):

    if mode == "Absolute":
        color_column="%"
        title = "<b>Map with contagion rate, real percentage</b>"
        hover_columns = ["Latest"]
    else:
        color_column="Modified"
        df["Latest"] = df["Latest"]*df["Latest_pop"]/100
        title = "<b>Map with data modified for appreciate the order of the countries by contagion rate</b>"
        hover_columns = ["Latest"]
    
    fig = px.choropleth(df, locations="country_code_3",
                        color=color_column, # lifeExp is a column of gapminder
                        hover_name="country", # column to add to hover information
                        hover_data=hover_columns,
                        color_continuous_scale=px.colors.sequential.Plasma,
                        scope="world",
                        title=title)
    fig.update_layout(title_x=0.5)
    fig.show()


def get_graph(mode,key,continent):
    df = get_df(webpage_json,key,continent,mode)
    plot_lines_covid(df,mode,continent)
    df_aux = add_percentage_population(df,mode)
    plot_maps(df_aux,mode)
        




# csv obtenido de Kaggle https://www.kaggle.com/statchaitya/country-to-continent/data#

df_continents = pd.read_csv("countryContinent.csv",encoding = "ISO-8859-1")\
                  .loc[:,["country","code_2","code_3","continent","sub_region"]]
df_continents.columns=["country","country_code","country_code_3","continent","sub_region"]

# Keys: "confirmed","deaths","recovered"
webpage_str = requests.get("https://coronavirus-tracker-api.herokuapp.com/all")\
                     .content\
                     .decode('utf8')
webpage_json = json.loads(webpage_str)

interact(get_graph,
         mode= widgets.Dropdown(options=["Absolute","Relative"], value="Absolute"),
         key = widgets.Dropdown(options=["confirmed", "deaths", "recovered"], value="confirmed"),
         continent=widgets.Dropdown(options=["Africa","Americas","Asia","Europe","Oceania","All"], value="Europe"))
