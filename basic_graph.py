from __future__ import print_function
import pandas as pd
import requests, json

from ipywidgets import interact
import ipywidgets as widgets

from plotly import graph_objects as go

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
    for country in df.country:
        fig.add_trace(go.Scatter(x=df.columns, 
                                 y=df.loc[df.country==country,:].values[0],
                                 mode='lines',
                                 name=country))
    fig.show()

def get_graph(key,continent):
    df = get_df(webpage_json,key)
    plot_df_covid(df,continent)



# csv obtenido de Kaggle https://www.kaggle.com/statchaitya/country-to-continent/data#
df_continents = pd.read_csv("countryContinent.csv",encoding = "ISO-8859-1")\
                  .loc[:,["country","code_2","continent","sub_region"]]
df_continents.columns=["country","country_code","continent","sub_region"]

# Keys: "confirmed","deaths","recovered"
webpage_str = requests.get("https://coronavirus-tracker-api.herokuapp.com/all")\
                     .content\
                     .decode('utf8')
webpage_json = json.loads(webpage_str)

interact(get_graph,
         key=widgets.Dropdown(options=["confirmed", "deaths", "recovered"], value="confirmed"),
         continent=widgets.Dropdown(options=["Africa","Americas","Asia","Europe","Oceania","All"], value="Europe"))
