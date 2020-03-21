from __future__ import print_function

import ipywidgets as widgets
import numpy as np, pandas as pd
import requests, json, os, zipfile

from io import BytesIO
from ipywidgets import interact
from plotly import graph_objects as go, express as px
from sklearn.preprocessing import MinMaxScaler,PowerTransformer,QuantileTransformer


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

def get_file_of_population():
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
    return df

def add_percentage_population(df):
    
    df_population = get_file_of_population()
    
    df_population.columns=["country_code_3",df_population.columns[-1]]
    
    df_aux = df.loc[:,df.columns[-6:]]
    df_aux.columns = ["Latest"]+[str(name) for name in df_aux.columns[1:]]
    df_aux = df_aux.merge(df_population,on="country_code_3")
    df_aux['%']= df_aux.Latest*(10**3)/df_aux[df_population.columns[-1]]
    scaler = QuantileTransformer(random_state=0)
    df_aux["% scaled"] = scaler.fit_transform(df_aux[["%"]])
    return df_aux

def get_country_code(data,key='confirmed'):
    return pd.DataFrame([x.get("country_code") \
                                     for x in data],
                                 index=[x.get("country") for x in data],
                                 columns=['country_code'])\
             .drop_duplicates()

def get_df(webpage_json,key='confirmed'):
    relevant_data = webpage_json.get(key)
    year,month,day = relevant_data.get("last_updated")\
                                  .split("T")[0]\
                                  .split("-")
    
    date = str(int(month))+'/'+str(int(day))+'/'+year
    
    data = relevant_data.get("locations")

    df = pd.DataFrame([x.get("history") \
                                     for x in data],
                                 index=[x.get("country") for x in data])
    df[date]=[x.get("latest") for x in data]
    
    df = df.reset_index(drop=False)\
           .groupby(by=["index"])\
           .sum()
    df = df.loc[df[date] != 0, :]
    df2 = df.T.reset_index(drop=False)
    df2['index'] = pd.to_datetime(df2["index"])
    df2 = df2.sort_values(by="index").set_index("index")
    df = df2.T
    
    df_countries = get_country_code(data,key)
    df = df.merge(df_countries, left_index=True, right_index=True)\
           .merge(df_continents,on="country_code")
    
    return df


def plot_df_covid(df,continente=None):
    if continente in ["Americas","Africa","Asia","Europe","Oceania"]:
        df = df.loc[df.continent==continente].reset_index(drop=True)
    df = df.drop(["country_code","continent","sub_region"],axis=1)
    fig = go.Figure()
    if continente != 'All': fig.update_layout(showlegend=True)
    else: fig.update_layout(showlegend=False)
    for country in df.country:
        fig.add_trace(go.Scatter(x=df.columns, 
                                 y=df.loc[df.country==country,:].values[0],
                                 mode='lines',
                                 name=country))
    
    fig.show()

def plot_maps(df):
    fig = px.choropleth(df, locations="country_code_3",
                        color="% scaled", # lifeExp is a column of gapminder
                        hover_name="country", # column to add to hover information
                        hover_data=["Latest","%"],
                        color_continuous_scale=px.colors.sequential.Plasma,
                        scope="world",
                        title="<b>Map with data scaled to appreciate the order of the countries by contagion rate</b>")
    fig.update_layout(title_x=0.5)
    fig.show()
    
    fig = px.choropleth(df, locations="country_code_3",
                        color="%", # lifeExp is a column of gapminder
                        hover_name="country", # column to add to hover information
                        hover_data=["continent","sub_region","Latest"],
                        color_continuous_scale=px.colors.sequential.Plasma,
                        title="<b>Map with contagion rate, real percentage</b>")
    fig.update_layout(title_x=0.5)
    fig.show()

def get_graph(key,continent):
    df = get_df(webpage_json,key)
    plot_df_covid(df,continent)
    df_aux = add_percentage_population(df)
    plot_maps(df_aux)




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
         key=widgets.Dropdown(options=["confirmed", "deaths", "recovered"], value="confirmed"),
         continent=widgets.Dropdown(options=["Africa","Americas","Asia","Europe","Oceania","All"], value="Europe"))
