import pandas as pd
from datetime import datetime as dt, timedelta as td

def fecha_csv(fecha):
    fecha_str = str(fecha).split("-")
    return fecha_str[1]+'-'+fecha_str[-1]+'-'+fecha_str[0]

def limpieza_variables(df):
    df.drop(labels=['FIPS',"Admin2"],axis='columns',inplace=True)
    df.Country_Region = df.Country_Region.str.replace("^Mainland ","")
    df.Confirmed = df.Confirmed.astype(int)
    df.Deaths = df.Deaths.astype(int)
    df.Recovered = df.Recovered.astype(int)
    df.Lat = df.Lat.values[-1]
    df.Long_ = df.Long_.values[-1]
    df.Active = df.Confirmed-df.Deaths-df.Recovered
    df.loc[pd.isna(df.Combined_Key) & df.Province_State != ' ',"Combined_Key"] = \
    df.loc[pd.isna(df.Combined_Key) & df.Province_State != ' ',['Province_State',"Country_Region"]]\
      .agg(", ".join,axis=1)
    df.loc[pd.isna(df.Combined_Key) & df.Province_State == ' ',"Combined_Key"] = \
    df.loc[pd.isna(df.Combined_Key) & df.Province_State == ' ',['Country_Region']]
    return df

def get_data():
    ruta_git = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/"
    fecha = dt(2020,1,22).date()
    df = pd.DataFrame()

    while (fecha <= dt.now().date()):
        try:
            df_aux = pd.read_csv(ruta_git+fecha_csv(fecha)+'.csv')\
                       .rename({"Last Update":"Last_Update"},axis="columns")
            df_aux.loc[:,['Last_Update']] = fecha
            df_aux.rename({'Province/State':'Province_State','Country/Region':"Country_Region",
                           "Latitude":"Lat","Longitude":"Long_"},
                          axis="columns",inplace=True)
            df = pd.concat([df,df_aux.fillna({"Province_State":" ","Confirmed":0,"Deaths":0,"Recovered":0})])
            fecha = fecha + td(days=1)
        except:
            if not fecha == dt.now().date(): print("\nFecha "+fecha_csv(fecha),"no disponible")
            fecha = fecha + td(days=1)
    df = limpieza_variables(df)
    
    df.to_csv("data.csv",index=False)
    return df
