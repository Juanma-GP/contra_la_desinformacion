from __future__ import print_function

import pandas as pd
import os,requests, json
from datetime import datetime
from sklearn.preprocessing import QuantileTransformer

from ipywidgets import interact,Dropdown
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
    # -------------------------------------------------------------------------------------
    if len(file)==0:
        zip_file_url = "http://api.worldbank.org/v2/en/indicator/SP.POP.TOTL?downloadformat=csv"
        r = requests.get(zip_file_url)
        z = zipfile.ZipFile(BytesIO(r.content),"r")
        z.extractall()
        file = [file for file in os.listdir() if "Metadada" not in file and "POP.TOTL" in file]
    # -------------------------------------------------------------------------------------
    file = file[0]

    df = pd.read_csv(file,skiprows=4)\
           .drop(["Country Name","Indicator Name","Indicator Code"],axis=1)
    shape0_5 = df.shape[0]/2
    
    for col in df.columns[-4:]:
        if len(df.loc[pd.isna(df[col])]) > shape0_5:
            df.drop(col,axis=1,inplace=True)
    
    # -------------------------------------------------------------------------------------
    to_drop = list(df.columns[1:])
    to_drop.remove(max(to_drop))
    df.drop(to_drop,axis=1,inplace=True)
    df.columns = ['country_code_3','Latest_pop']
    df = df.loc[df.Latest_pop.isna()==False]
    df.Latest_pop = df.Latest_pop.astype(int)
    return df


def get_basic_df(key='confirmed'):
    # Continents
    df_continents = pd.read_csv("countryContinent.csv",encoding = "ISO-8859-1")\
                      .loc[:,["country","code_2","code_3","continent","sub_region"]]
    df_continents.columns=["country","country_code","country_code_3","continent","sub_region"]
    # -------------------------------------------------------------------------------------
    
    # Population per country
    df_pop = get_population()
    # -------------------------------------------------------------------------------------
    
    # Basic data
    webpage_str = requests.get("https://coronavirus-tracker-api.herokuapp.com/all")\
                          .content\
                          .decode('utf8')
    relevant_data = json.loads(webpage_str).get(key)
    year,month,day = relevant_data.get("last_updated")\
                                  .split("T")[0]\
                                  .split("-")
    
    data = relevant_data.get("locations")
    
    df_countries = pd.DataFrame([x.get("country_code") \
                                     for x in data],
                                 index=[x.get("country") for x in data],
                                 columns=['country_code'])\
                     .drop_duplicates()
    
    df_basic = pd.DataFrame([x.get("history") \
                                     for x in data],
                                 index=[x.get("country") for x in data])
    df_basic.columns = [datetime.strptime(col,"%m/%d/%y").date() for col in df_basic.columns]
    df_basic = df_basic.groupby(df_basic.index)\
                       .sum()
    df_basic = df_basic.T\
                       .sort_index()\
                       .T
    # -------------------------------------------------------------------------------------
    
    # Merge data
    df_complex = df_basic.merge(df_countries, left_index=True, right_index=True)\
                         .merge(df_continents,on="country_code")\
                         .merge(df_pop,on="country_code_3")
    
    return df_complex,df_basic.columns

def get_relative_df(df,datecolumns):
    df_aux = df.copy()
    for col in datecolumns:
        df_aux[col] = df_aux[col]*100/df_aux["Latest_pop"]
    return df,df_aux,datecolumns

def quantiles(df):
    scaler = QuantileTransformer(random_state=0)
    df["Modified"] = scaler.fit_transform(df[[df.columns[-7]]])
    return df

def get_first_values(records):
    return [round(float(record),3) for record in list(records) \
                                    if (float(record)>0)]

def based_on_first_positive_case(df):
    countries = {}
    for i in range(df.shape[0]):
        country = df.iloc[i].country
        countries[country]=get_first_values(df.iloc[i][datecolumns].values)
    return countries

def dict_based_on_first_positive_case(cases):
    dict_fpc = {}
    for key in cases:
        values = based_on_first_positive_case(cases[key])
        df = pd.DataFrame.from_dict(values,orient="index")
        df_aux = cases[key].loc[:,["country","continent","country_code_3","Latest_pop"]]\
                           .set_index("country") 
        dict_fpc[key] = df.merge(df_aux, left_index=True, 
                                         right_index=True)
    return dict_fpc

def plot_lines_covid(df_abs,df_rel,mode,continent):
    
    fig = go.Figure()
    # -------------------------------------------------------------------------------------
    if continent != 'All': fig.update_layout(showlegend=True)
    else: fig.update_layout(showlegend=False)
    # -------------------------------------------------------------------------------------
    if mode=='Relative': df = df_rel
    else: df = df_abs
    # -------------------------------------------------------------------------------------
    datecolumns = df.columns[:-7]
    
    # -------------------------------------------------------------------------------------
    for country in df.country:
        # ---------------------------------------------------------------------------------
        if mode=='Relative':
            text = [country+'<br>Total:'+str(int(value)) \
                    for value in df_abs.loc[df_abs.country==country,datecolumns].values[0]\
                   ]
        else: 
            text = country
        # ---------------------------------------------------------------------------------
        fig.add_trace(go.Scatter(x=df.columns[:-3], 
                                 y=df.loc[df.country==country,datecolumns].values[0],
                                 mode='lines',
                                 name=df.loc[df.country==country,["country_code_3"]].values[0][0],
                                 hovertext = text
                                )
                     )
    # -------------------------------------------------------------------------------------
    fig.show()

def plot_lines_covid_fpc(df,continent):
    fig = go.Figure()
    columns = [col for col in df.columns if col not in ['country','continent',"country_code_3",'Latest_pop']]
    for country in df.index:
        fig.add_trace(go.Scatter(x=df.columns,
                                 y=df.loc[df.index==country,columns].values[0],
                                 mode='lines',
                                 name=df.loc[df.index==country,["country_code_3"]].values[0][0]))
    if continent != 'All': fig.update_layout(showlegend=True)
    else: fig.update_layout(showlegend=False)
    fig.show()

def plot_maps(df,mode):
    
    df.columns = [str(col) for col in df.columns]
    
    if mode == "Absolute":
        color_column=df.columns[0]
        title = "<b>Map with contagion rate sorted</b>"
        hover_columns = [df.columns[-8]]
    else:
        color_column="Modified"
        df["Latest"] = df[df.columns[-8]]*df["Latest_pop"]/100
        title = "<b>Map with data modified for appreciate the order of the countries by contagion rate</b>"
        hover_columns = ["Latest"]
    
    
    fig = px.choropleth(df, 
                        locations="country_code_3",
                        color=color_column, # lifeExp is a column of gapminder
                        hover_name="country", # column to add to hover information
                        hover_data=hover_columns,
                        color_continuous_scale=px.colors.sequential.Plasma,
                        scope="world",
                        title=title)
    fig.update_layout(title_x=0.5)
    fig.show()

def get_continent(df,continent):
    return df.loc[df.continent==continent]

def get_graph(mode,key,continent):
    df_abs = absolute[key]
    df_rel = relative[key]
    df_abs_fpc = absolute_fpc[key]
    df_rel_fpc = relative_fpc[key]

    if continent != 'All':
        df_abs = get_continent(df_abs,continent)
        df_rel = get_continent(df_rel,continent)
        if mode=="Absolute": 
            df_fpc = get_continent(df_abs_fpc,continent)
        else: 
            df_fpc = get_continent(df_rel_fpc,continent)
    else:
        if mode=="Absolute": df_fpc = df_abs_fpc
        else: df_fpc = df_rel_fpc
    
    if mode=="Absolute": df = df_abs
    else: df = df_rel
    
    df = df.loc[:,df.columns[-8:]]
    
    plot_lines_covid(df_abs,df_rel,mode,continent)
    plot_lines_covid_fpc(df_fpc,continent)
    plot_maps(df,mode)


# csv obtenido de Kaggle https://www.kaggle.com/statchaitya/country-to-continent/data#

absolute,relative = {},{}
for key in ['confirmed','deaths','recovered']:
    df,df_relative,datecolumns = get_relative_df(*get_basic_df(key))
    absolute[key]=quantiles(df)
    relative[key]=quantiles(df_relative)
#     print("key",key,"ready")

absolute_fpc = dict_based_on_first_positive_case(absolute)
relative_fpc = dict_based_on_first_positive_case(relative)

interact(get_graph,
         mode= Dropdown(options=["Absolute","Relative"], value="Absolute"),
         key = Dropdown(options=["confirmed", "deaths", "recovered"], value="confirmed"),
         continent=Dropdown(options=["Africa","Americas","Asia","Europe","Oceania","All"], value="Europe"))