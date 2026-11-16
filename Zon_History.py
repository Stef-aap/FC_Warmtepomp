#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 11 08:41:38 2026

@author: stef
"""

import os
import io
import math
import requests
import pandas              as pd
import numpy               as np
import datetime            as dt

import matplotlib.pyplot   as plt
import matplotlib.dates    as mdates

import streamlit           as st


# ********************************************************************"""
# Globals
# ********************************************************************"""
#WeerStations = {}
#WeerStations [ "Arcen"      ] = 391   # Arcen wordt in 2025 vervangen door Horst
#WeerStations [ "De Bilt"    ] = 260
#WeerStations [ "Eindhoven"  ] = 370
#WeerStations [ "Groningen"  ] = 280
#WeerStations [ "Horst"      ] = 392   # geen historische waarden
#WeerStations [ "Schiphol"   ] = 240
#WeerStations [ "Vlissingen" ] = 310
#WeerStations [ "Volkel"     ] = 375

WeerStations = {
    "IJmond": 209,
    "Voorschoten": 215,
    "De Kooy (Den Helder)": 235,
    "Schiphol": 240,
    "Vlieland": 242,
    "Wijdenes": 248,
    "Berkhout": 249,
    "Hoorn Terschelling": 251,
    "Wijk aan Zee": 257,
    "Houtribdijk": 258,
    "De Bilt": 260,
    "Soesterberg": 265,
    "Stavoren": 267,
    "Lelystad": 269,
    "Leeuwarden": 270,
    "Marknesse": 273,
    "Deelen": 275,
    "Lauwersoog": 277,
    "Heino": 278,
    "Hoogeveen": 279,
    "Eelde (Groningen)": 280,
    "Hupsel": 283,
    "Huibertgat": 285,
    "Nieuw Beerta": 286,
    "Twenthe": 290,
    "Cadzand": 308,
    "Vlissingen": 310,
    "Hoofdplaat": 311,
    "Oosterschelde": 312,
    "Vlakte van De Raan": 313,
    "Hansweert": 315,
    "Shaft": 316,
    "Westdorpe": 319,
    "Wilhelminadorp": 323,
    "Stavenisse": 324,
    "Hoek van Holland": 330,
    "Tholen": 331,
    "Woensdrecht": 340,
    "Rotterdam Geulhaven": 343,
    "Rotterdam (The Hague Airport)": 344,
    "Cabauw": 348,
    "Gilze-Rijen": 350,
    "Herwijnen": 356,
    "Eindhoven": 370,
    "Volkel": 375,
    "Ell": 377,
    "Maastricht Aachen Airport": 380,
    "Arcen": 391,
    "Horst": 392
}

# ********************************************************************"""
# Geeft Eerste en Laatste dag van een maand
# in het format   "YYYY-MM-DD"
# ********************************************************************"""
def Get_First_Last_Day_in_Month ( Year, Month ) :
  #jaar, maand = 2024, 2

  First_Day = pd.Timestamp ( Year, Month, 1 )
  Last_Day  = First_Day + pd.offsets.MonthEnd ( 0 )
  
  Start = First_Day.strftime ( "%Y-%m-%d" ) 
  Einde = Last_Day .strftime ( "%Y-%m-%d" ) 

  print ( Start, Einde )
  return Start, Einde



# ********************************************************************"""
# Haalt historische uurgegevens op voor de opgegeven periode 
# (inclusief laatste dag).
# Datums in formaat: 'YYYY-MM-DD'
# ********************************************************************"""
## MOET GEWIJZIGD WORDEN ALS KNMI_Get_QT
def KNMI_Get_Q_T ( Start, Einde, Station = "Volkel" ) :
  """

# Opmerking: door stationsverplaatsingen en veranderingen in waarneemmethodieken zijn deze tijdreeksen van uurwaarden mogelijk inhomogeen! Dat betekent dat deze reeks van gemeten waarden niet geschikt is voor trendanalyse. Voor studies naar klimaatverandering verwijzen we naar de gehomogeniseerde dagreeksen <http://www.knmi.nl/nederland-nu/klimatologie/daggegevens> of de Centraal Nederland Temperatuur <http://www.knmi.nl/kennis-en-datacentrum/achtergrond/centraal-nederland-temperatuur-cnt>.
# 
# SOURCE: ROYAL NETHERLANDS METEOROLOGICAL INSTITUTE (KNMI)
# Comment: These time series are inhomogeneous because of station relocations and changes in observation techniques. As a result these series are not suitable for trend analysis. For climate change studies we refer to the homogenized series of daily data <http://www.knmi.nl/nederland-nu/klimatologie/daggegevens> or the Central Netherlands Temperature <http://www.knmi.nl/kennis-en-datacentrum/achtergrond/centraal-nederland-temperatuur-cnt>.
# 
# STN         LON(east)   LAT(north)  ALT(m)      NAME
# 375         5.707       51.659      22.00       Volkel      
# YYYYMMDD  : datum (YYYY=jaar;MM=maand;DD=dag)
# HH        : tijd (HH=uur; UT.12 UT=13 MET; 14 MEZT. Uurvak 05 loopt van 04.00 UT tot 5.00 UT
# Q         : Globale straling (in J/cm2) per uurvak / Global radiation (in J/cm2) during the hourly division
# T         : Temperatuur (in 0.1 graden Celsius) op 1.50 m hoogte tijdens de waarneming / Temperature (in 0.1 degrees Celsius) at 1.50 m at the time of observation
# STN,YYYYMMDD,HH,    Q,    T
  375,20260501,    1,    0,  108
  375,20260501,    2,    0,   71  
"""
  URL = 'https://www.daggegevens.knmi.nl/klimatologie/uurgegevens'
  
  # Bereken automatisch 1 dag eerder en 1 dag later voor het KNMI
  Format      = "%Y-%m-%d"
  Start_dt    = dt.datetime.strptime ( Start, Format ) - dt.timedelta ( days = 1 )
  Einde_dt    = dt.datetime.strptime ( Einde, Format ) + dt.timedelta ( days = 1 )
  Format_KNMI = "%Y%m%d"

  payload = { 'start' : Start_dt.strftime ( Format_KNMI )
             ,'end'   : Einde_dt.strftime ( Format_KNMI )
             ,'stns'  : WeerStations [ Station ]
             ,'vars'  :'Q:T' }
  response = requests.post ( URL, data = payload )
  
  if response.status_code != 200 :
    raise Exception ( f"KNMI API Fout: Status {response.status_code}" )
      
  regels = response.text.splitlines()
  schone_regels = [ line.strip() for line in regels if line.strip() and not line.startswith('#') ]
  
  df = pd.read_csv ( io.StringIO("\n".join(schone_regels))
                    ,names            = ['STN', 'YYYYMMDD', 'H', 'Q', 'T']
                    ,header           = None
                    ,skipinitialspace = True
                    ,on_bad_lines     = 'skip' )
  KNMI_Raw = df.dropna ( subset = [ 'YYYYMMDD', 'H', 'Q', 'T' ] )
  
  return KNMI_Raw
  


# ********************************************************************"""
# Haalt historische uurgegevens op voor de opgegeven periode 
# (inclusief laatste dag).
# Datums in formaat: 'YYYY-MM-DD'
# ********************************************************************"""
@st.cache_data # Zorgt ervoor dat Streamlit het bestand onthoudt en niet bij elke klik opnieuw downloadt
def KNMI_Get_QT_Year ( Year, WeerStation = "Volkel" ) :
  Start    = "%i-01-01" % Year
  Einde    = "%i-12-31" % Year
  Filename = "KNMI_QT_%i_%s.csv" % ( Year, WeerStation )
  if os.path.exists ( Filename ) :
    DF = pd.read_csv ( Filename, sep=';'
                      ,index_col   = 0       # Maakt van de eerste kolom (de tijd) de officiële index
                      ,parse_dates = True )  # Zorgt dat pandas snapt dat het om datums en tijden gaat
  else : 
    DF = KNMI_Get_QT ( Start, Einde, Station = WeerStation )
    DF.to_csv ( Filename, sep=';')

  return DF

@st.cache_data # Zorgt ervoor dat Streamlit het bestand onthoudt en niet bij elke klik opnieuw downloadt
def KNMI_Get_QT ( Start, Einde, Station = "Volkel" ) :
  URL = 'https://www.daggegevens.knmi.nl/klimatologie/uurgegevens'
  
  #Start = "2026-01-01"
  #Einde = "2026-01-31"
  
  # NEEEEE  Bereken automatisch 1 dag eerder en 1 dag later voor het KNMI
  Format      = "%Y-%m-%d"
  #Start_dt    = dt.datetime.strptime ( Start, Format ) - dt.timedelta ( days = 1 )
  #Einde_dt    = dt.datetime.strptime ( Einde, Format ) + dt.timedelta ( days = 1 )
  Start_dt    = dt.datetime.strptime ( Start, Format )
  Einde_dt    = dt.datetime.strptime ( Einde, Format )
  Format_KNMI = "%Y%m%d"

  Payload = {
      'start': Start_dt.strftime ( Format_KNMI ),
      'end'  : Einde_dt.strftime ( Format_KNMI ),
      'vars' : "T:Q",
      'stns' : WeerStations [ Station ],
      'fmt'  : "json"
      }
  Response = requests.post ( URL, data = Payload )    
  Data     = pd.DataFrame ( Response.json() )
  # ***********************************************************
  # ***********************************************************
  def Calc_date ( Row ):
    #return Row.date [:10].replace ( '-', '' ) + 
    DateTime = Row.date [:10] + " %02d:00:00" % ( Row.hour - 1 )
    return pd.to_datetime ( DateTime )
  
  Data [ "DateTime" ] = Data.apply ( lambda row: Calc_date ( row ), axis=1 )
  Data.set_index ( "DateTime", inplace = True )
  
  Data [ "T" ] /= 10
  Data [ "Q" ] *= 2.77778   # [J/cm2] * 10000 / 36000 = [W/m2]

  Data.drop ( columns = [ "station_code", "date", "hour" ], inplace = True )
  Data.rename ( columns = { "T": "Temp"
                           ,"Q": "W_hor"
                          }, inplace = True )

  # ***********************************************************
  # Selecteer het gewenste tijdblok
  # ***********************************************************
  #Data = Data [ ( Data.index >= Start ) & ( Data.index < Einde_dt ) ]
  
  return Data



# ********************************************************************"""
# ********************************************************************"""
  

# ********************************************************************"""
# Haalt historische uurgegevens op voor de opgegeven periode (exclusief laatste dag).
# Datums in formaat: 'YYYY-MM-DD'
# liggingen = {"West": 90, "Zuid-West": 45, "Zuid": 0, "Zuid-Oost": -45, "Oost": -90}
# Wat is exact de eenheid die in deze kolommen wordt opgeborgen ?
# ********************************************************************"""
#def Create_Kwartier_Data ( KNMI_Raw, Start, Einde, kWp=1, Helling=35):
def Get_KNMI_KwartierData ( Start, Einde, kWp=1, Helling=35, Station="Volkel" ):
  # einde 1 dag terugzetten
  Einde_dt = dt.datetime.strptime ( Einde, "%Y-%m-%d" ) - dt.timedelta ( days = 1 )
  Einde    = Einde_dt.strftime ( '%Y-%m-%d' )
  
  KNMI_Raw = KNMI_Get_Q_T ( Start, Einde, Station=Station )
  
  """
  Verwerkt een hele periode uur-tot-uur naar gecorrigeerde kwartierwaarden.
  """
  liggingen = {"West": 90, "Zuid-West": 45, "Zuid": 0, "Zuid-Oost": -45, "Oost": -90}
  lat_rad = math.radians(51.7686)
  
  if KNMI_Raw.empty:
    raise ValueError("Het KNMI DataFrame is leeg. Controleer de periode of API-respons.")
  
  uur_data = []
  #print("Astronomische zonnestanden en vermogens per uur berekenen...")
  
  for _, row in KNMI_Raw.iterrows():
    try:
      datum_int     = str ( int ( row [ 'YYYYMMDD' ] ) )
      datum_str    = f"{datum_int[0:4]}-{datum_int[4:6]}-{datum_int[6:8]}"
      dag_van_jaar = pd.to_datetime ( datum_str ).dayofyear
      
      uur            = int   ( row ['H'] )
      straling_j_cm2 = float ( row ['Q'] )
      Temperature    = float ( row ['T'] / 10 )

    except ( ValueError, KeyError ) :
      continue
        
    # Tijdstempel op het midden van het uur zetten
    tijdstempel     = pd.to_datetime(f"{datum_str} {uur-1:02d}:30:00")
    instraling_plat = ( straling_j_cm2 * 10000 ) / 3600 if straling_j_cm2 > 0 else 0
    # ********************************************************************"""

    declinatie = 23.45 * math.sin(math.radians ( 360 / 365 * ( dag_van_jaar - 80 ) ) )
    uur_hoek = math.radians ( ( uur - 12 ) * 15 )
    sin_solar_alt = ( math.sin ( lat_rad ) * math.sin ( math.radians ( declinatie ) ) + 
                      math.cos ( lat_rad ) * math.cos ( math.radians ( declinatie ) ) * math.cos ( uur_hoek ) )
    solar_alt = math.asin ( max ( -1.0, min ( 1.0, sin_solar_alt ) ) )
    
    #res_uur = {"Tijdstempel": tijdstempel}
    res_uur = {"DatumTijd": tijdstempel}
    res_uur [ "Temp" ] = round ( Temperature, 1 )
    
    for naam, az_dak in liggingen.items():
      if solar_alt <= 0 or instraling_plat == 0:
        res_uur[f"W_{naam}"] = 0.0
        continue
          
      cos_solar_az = ((math.sin(math.radians(declinatie)) - math.sin(lat_rad) * math.sin(solar_alt)) / 
                      (math.cos(lat_rad) * math.cos(solar_alt)))
      solar_az = math.acos(max(-1.0, min(1.0, cos_solar_az)))
      if uur > 12: 
        solar_az = 2 * math.pi - solar_az
      solar_az = solar_az - math.pi
      
      cos_invalshoek = ( math.sin ( solar_alt ) * math.cos ( math.radians ( Helling ) ) + 
                         math.cos ( solar_alt ) * math.sin ( math.radians ( Helling ) ) * math.cos ( solar_az - math.radians ( az_dak ) ) )
      
      res_uur[f"W_{naam}"] = kWp * ( instraling_plat / 1000.0 ) * max ( 0.12, cos_invalshoek ) * 0.82 * 1000
      
    uur_data.append ( res_uur )
      
  # 1. Maak het DataFrame aan van de uur-data (deze staan op :30)
  #df_uur = pd.DataFrame(uur_data).set_index('Tijdstempel').sort_index()
  df_uur = pd.DataFrame ( uur_data ).set_index ( 'DatumTijd' ).sort_index()
  df_uur = df_uur.groupby(level=0).mean() # Ontdubbelen indien nodig
  
  # 2. Maak een VOLLEDIGE, strakke kwartierindex aan voor de hele maand
  # Deze index loopt gegarandeerd van exact 00:00:00 tot 23:45:00 voor elke dag
  volledige_kwartier_index = pd.date_range(
      start = f"{Start} 00:00:00", 
      end   = f"{Einde} 23:45:00", 
      freq  = '15min'
  )
  
  #print("Kwartierindex uitlijnen en vloeiend interpoleren...")
  # Reindex voegt de :30 datapunten samen met de strakke kwartierlijst.
  # Alle tussenliggende kwartieren (zoals 00:15:00) worden nu als lege rijen (NaN) aangemaakt.
  df_kwartier = df_uur.reindex(df_uur.index.union(volledige_kwartier_index))
  df_kwartier = df_kwartier.interpolate(method='cubic')
  df_kwartier = df_kwartier.reindex(volledige_kwartier_index).clip(lower=0)

  # Kap negatieve uitschieters in de nacht netjes af naar 0
  df_kwartier = df_kwartier.clip(lower=0)
  
  # 3. Correctie toepassen per uurblok (zoals voorheen)
  df_kwartier['Datum_Uur_Key'] = df_kwartier.index.strftime('%Y%m%d%H')
  df_uur['Datum_Uur_Key'] = df_uur.index.strftime('%Y%m%d%H')
  df_uur_uniek = df_uur.groupby('Datum_Uur_Key').mean()

  for ligging in liggingen.keys():
    col_w = f"W_{ligging}"
    #col_wh = f"Wh_{ligging}" # VERANDERD: Van kWh naar Wh voor compacte opslag
    
    kwartier_sommen = df_kwartier.groupby('Datum_Uur_Key')[col_w].transform('sum') / 4.0
    df_kwartier['Doel_kWh'] = df_kwartier['Datum_Uur_Key'].map(df_uur_uniek[col_w])
    
    schaalfactor = np.where(kwartier_sommen > 0, df_kwartier['Doel_kWh'] / kwartier_sommen, 1.0)
    df_kwartier[col_w] = df_kwartier[col_w] * schaalfactor
    
    # Bereken Wattuur (Wh) in plaats van kWh en converteer beide kolommen naar Integers
    #df_kwartier[col_wh] = (df_kwartier[col_w] / 4.0).round().astype(int)
    df_kwartier[col_w] = df_kwartier[col_w].round().astype(int)

  df_kwartier = df_kwartier.drop(columns=['Datum_Uur_Key', 'Doel_kWh'])
  df_kwartier["Temp"] = round ( df_kwartier["Temp"], 1 )
  return df_kwartier


# ********************************************************************"""
# Plot van 1 dag, de PV-Opbrengst van West, Zuid, Oost, in 1 grafiek
# ********************************************************************"""
def Dag_Grafiek_WZO ( df
                     ,datum_str
                     ,station_naam = "Volkel (KNMI 375)"
                     ,kwp          = 3.6
                     ,helling      = 35 ) :
  
  # Sla de gekozen kwartierdata op als CSV
  #df.to_csv(f"pv_kwartierwaarden_{datum_str}.csv", sep=';')
  #print(f"✅ Kwartierdata opgeslagen: pv_kwartierwaarden_{datum_str}.csv")
  
  # Bereken de exacte dagsommen voor de legenda
  W_Oost = df['W_Oost'].sum()
  W_Zuid = df['W_Zuid'].sum()
  W_West = df['W_West'].sum()
  
  # Console-output ter controle
  print("\n--- CONTROLE DAGSOMMEN (kWh) ---")
  print(f"Oost : {W_Oost:.2f} kWh")
  print(f"Zuid : {W_Zuid:.2f} kWh")
  print(f"West : {W_West:.2f} kWh")
          
  # Grafiek genereren
  plt.figure(figsize=(12, 6.5), facecolor='white')
  
  # 1. Oost plotten (inclusief dagsom in het label voor de legenda)
  #plt.plot(df.index, df['W_Oost'], label=f'Oost-opstelling ({W_oost:.2f} kWh)', color='#0077BB', linewidth=2.5)
  plt.plot(df.index, df['W_Oost'], label=f'Oost-opstelling ({W_Oost:.2f} kWh)', color='#0077BB', linewidth=2.5)
  plt.fill_between(df.index, df['W_Oost'], color='#0077BB', alpha=0.04)
  
  # 2. Zuid plotten
  plt.plot(df.index, df['W_Zuid'], label='fZuid-opstelling ({W_Zuid:.2f} kWh)', color='#009988', linewidth=3)
  plt.fill_between(df.index, df['W_Zuid'], color='#009988', alpha=0.04)
  
  # 3. West plotten
  plt.plot(df.index, df['W_West'], label='fWest-opstelling ({W_West:.2f} kWh)', color='#EE7733', linewidth=2.5)
  plt.fill_between(df.index, df['W_West'], color='#EE7733', alpha=0.04)
  
  # Hoofdtitel en dynamic subtitel met alle gevraagde configuraties
  plt.suptitle(f"Vergelijking PV-opbrengstcurves ({datum_str})", fontsize=15, fontweight='bold', y=0.96)
  plt.title(f"Systeem: {kwp} kWp | Hellingshoek: {helling}° | Locatie: Molenhoek via Weerstation {station_naam}", 
            fontsize=10.5, color='#444444', pad=15)
  
  """ plot bargraph
  df["Test"]=df["W_Oost"]+100
  # We verschuiven de X-as voor de verschillende windrichtingen zodat ze naast elkaar staan
  #x_num = mdates.date2num(df.index) # Converteer tijdstempels naar getallen voor de wiskunde
  # HET GEHEIM VOOR DE BARGRAPH:
  # We berekenen de breedte van de staafjes in dagen (omdat matplotlib tijd zo opslaat).
  # Een kwartier is 1 / (24 * 4) van een dag. We maken elk staafje iets minder dan 1/3e daarvan.
  breedte = 0.004
  plt.bar ( df.index, df['Test'], width=breedte, 
            label=f'West-opstelling ({W_West:.2f} kWh)'
           ,color='#EE7733', alpha=0.85)
  #"""
  
  # Assen labels
  plt.xlabel("Tijd van de dag (Uur)", labelpad=10, fontsize=11)
  plt.ylabel("Gegenereerd Vermogen (Watt)", labelpad=10, fontsize=11)
  plt.grid(True, linestyle='--', alpha=0.45)
  
  # Grenzen van de X-as strakzetten op de dagranden
  plt.xlim(df.index.min(), df.index.max())
  
  # HET GEHEIM VOOR DE 2-UURS TICKS:
  plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=2)) # Ticks om de 2 uur
  plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) # Formaat HH:MM
  
  # Prachtige legenda rechtsbovenin met de berekende kWh-totalen
  plt.legend(loc='upper right', frameon=True, shadow=False, facecolor='white', edgecolor='#CCCCCC', fontsize=10.5)
  
  plt.tight_layout()
  
  # Grafiek opslaan
  grafiek_naam = f"pv_vergelijking_compleet_{datum_str}.png"
  plt.savefig(grafiek_naam, dpi=150)
  print(f"✅ Uitgebreide vergelijkingsgrafiek opgeslagen als: {grafiek_naam}")
  plt.show()

# ***********************************************************************
# ***********************************************************************
def Get_Uur_QT_Bestand ( Year, Month
                        ,*  # all following parameters must be...
                        ,Station       = "Volkel" 
                        ,Force_Rebuild = False
                       ) :
  Filename = "PV_Uurdata_%s_%i_%i" % ( Station, Year, Month )
  if not os.path.isfile ( Filename ) or Force_Rebuild :
    Start, Einde = Get_First_Last_Day_in_Month ( Year, Month )
    DF = KNMI_Get_QT ( Start, Einde, Station=Station )
    
    DF.to_csv ( Filename, float_format='%.1f', sep=';' )
    
    print ( "\n" + "="*60 )
    print ( f"Bestand opgeslagen als: {Filename}" )
    dir = os.path.dirname ( os.path.abspath ( __file__ ) )
    print ( "in: %s" % dir )
    
  return Filename    

# ***********************************************************************
# ***********************************************************************
def Add_Uur_PV ( df, PV_Wp, Orientatie, Helling ) :
  """
  Berekent de PV-opbrengst pe  df = pd.read_csv ( Filename, sep=';'
                      ,index_col   = 0       # Maakt van de eerste kolom (de tijd) de officiële index
                      ,parse_dates = True )  # Zorgt dat pandas snapt dat het om datums en tijden gaat
   
r uur op basis van richting, helling en totaal Wattpiek.
  Richting opties: 'Oost', 'Zuid-Oost', 'Zuid', 'Zuid-West', 'West'
  Helling opties: 15, 35, 45
  """
  # Officiële correctiematrix (Richting vs Helling) voor Nederland
  # Waarde 1.00 betekent dat de opbrengst gelijk is aan de horizontale meting
  correctie_matrix = {
      "Oost":      {15: 0.87, 35: 0.79, 45: 0.72},
      "Zuid-Oost": {15: 0.94, 35: 0.96, 45: 0.93},
      "Zuid":      {15: 0.97, 35: 1.02, 45: 1.01}, # Zuid 35 graden is optimaal (> 1.00)
      "Zuid-West": {15: 0.94, 35: 0.95, 45: 0.92},
      "West":      {15: 0.86, 35: 0.77, 45: 0.71}
  }
  
  # Pak de juiste factor, fallback naar Zuid 35 graden als de invoer afwijkt
  factor = correctie_matrix.get ( Orientatie, {}).get ( Helling, 1.02 )

  # Systeemrendement (omvormer-verliezen, warmteverlies panelen, ca. 85%)
  systeem_rendement = 0.85

  #print ( "Factor = %.2f    Rendement = %i%%    Orientatie = %s    Helling = %i" 
  #       % ( factor, 100*systeem_rendement, Orientatie, Helling ) )
  df [ 'PV_kWh' ] = ( df ['W_hor' ] * PV_Wp * factor * systeem_rendement / 1000000 )

                        
# ***********************************************************************
# Afname + PV - Terug = Verbruik
# We hebben deze gegevens per jaar, maar willen ze ook per maand weten.
# We veronderstellen in eerste instantie dat het verbruik over de dag constant is
# Verbruik_Dag = Verbruik_Maand / 30.5
# Vervolgens kunnen we over alle dagen in iedere maand:
# Per dag de PV vergelijken met het constante Verbruik
#  - PV sommeren 
#  - als PV > Verbruik, meetellen als Terug
# we weten dan ook de Afname = Verbruik + Terug - PV
# Vervolgens dagggevens van Afname, Terug, PV sommeren over de gehele maand
# ***********************************************************************
def Get_Month_PV_Uur_part ( Year, Month, Verbruik, PV_Wp
                           ,*
                           ,Orientatie    = "Zuid"
                           ,Helling       = 35
                           ,Force_Rebuild = False
                          ) :
  Filename = Get_Uur_QT_Bestand ( Year, Month, Force_Rebuild=Force_Rebuild )  
  df = pd.read_csv ( Filename, sep=';'
                    ,index_col   = 0       # Maakt van de eerste kolom (de tijd) de officiële index
                    ,parse_dates = True )  # Zorgt dat pandas snapt dat het om datums en tijden gaat
 
  Add_Uur_PV ( df, PV_Wp, Orientatie, Helling )

  df [ "Verbruik_kWh" ] = Verbruik / len ( df )
  #df [ "Verbruik_kWh" ] = 0.95 * Verbruik / len ( df )
  
  
  # ==========================================
  # 4. TERUGLEVERING & AFNAME BEPALEN PER UUR
  # ==========================================
  # Teruglevering vindt plaats als de PV opbrengst groter is dan het verbruik
  df [ "Teruglevering_kWh" ] = np.where (
    df [ "PV_kWh" ] > df [ "Verbruik_kWh" ],
    df [ "PV_kWh" ] - df [ "Verbruik_kWh" ],
    0.0,
  )
  
  # Net-afname vindt plaats als het verbruik groter is dan de PV opbrengst
  df [ "Net_afname_kWh" ] = np.where (
    df [ "Verbruik_kWh" ] > df [ "PV_kWh" ],
    df [ "Verbruik_kWh" ] - df [ "PV_kWh" ],
    0.0,
  )
  
  #print ( df )  

  totale_pv_opbrengst  = df [ "PV_kWh"            ].sum()
  totale_teruglevering = df [ "Teruglevering_kWh" ].sum()
  totale_net_afname    = df [ "Net_afname_kWh"    ].sum()

  return ( df, totale_pv_opbrengst, totale_teruglevering, totale_net_afname )


# ***********************************************************************
# ***********************************************************************
def Calc_Month_Elektra ( DF_Year 
                        ,Year, Month
                        ,*
                        ,Verbruik       = 0
                        ,PV_Wp          = 0
                        ,Warmtepomp_kWh = 0
                        ,Accu_kWh       = 0
                        ,Accu_RTE       = 0.9
                        ,Orientatie     = "Zuid"
                        ,Helling        = 35
                        ,Force_Rebuild  = False
                       ) :
  
  Month_str = "%i-%02i" % ( Year, Month )
  df        = DF_Year.loc [ Month_str ]

  
  Add_Uur_PV ( df, PV_Wp, Orientatie, Helling )
  
  #df [ "WPomp" ] = Warmtepomp_kWh / len ( df )
  #print ( "Warmtepomp per uur %i W"   % ( 1000 * Warmtepomp_kWh / len ( df ) ) ) 
  #print ( "Warmtepomp per uur %i kWh" %  Warmtepomp_kWh  ) 

  df [ "Verbruik_kWh" ] = ( Verbruik + Warmtepomp_kWh ) / len ( df )
  #df [ "Verbruik_kWh" ] = 0.95 * Verbruik / len ( df )
  
  """
  # ==========================================
  # 4. TERUGLEVERING & AFNAME BEPALEN PER UUR
  # ==========================================
  # Teruglevering vindt plaats als de PV opbrengst groter is dan het verbruik
  df [ "Teruglevering_kWh" ] = np.where (
    df [ "PV_kWh" ] > df [ "Verbruik_kWh" ],
    df [ "PV_kWh" ] - df [ "Verbruik_kWh" ],
    0.0,
  )
  
  # Net-afname vindt plaats als het verbruik groter is dan de PV opbrengst
  df [ "Net_afname_kWh" ] = np.where (
    df [ "Verbruik_kWh" ] > df [ "PV_kWh" ],
    df [ "Verbruik_kWh" ] - df [ "PV_kWh" ],
    0.0,
  )
"""  
  
  # ==========================================
  # 4. THUISACCU SIMULATIE PER UUR
  # ==========================================
  accu_capaciteit_kwh = Accu_kWh   # Maximale opslagcapaciteit van de accu in kWh
  #laad_efficientie    = 0.95  # 5% verlies tijdens zowel laden als ontladen
  laad_efficientie    = Accu_RTE ** 0.5
  
  accu_status   = []  # Hoe vol zit de accu aan het EINDE van het uur
  teruglevering = []
  net_afname    = []
  
  # We beginnen het jaar met een lege accu
  huidige_acculading = accu_capaciteit_kwh / 2
  
  # Loop chronologisch door alle uren van het jaar heen
  # We gebruiken zip() omdat dit vele malen sneller is dan .iterrows()
  for pv, verbruik in zip ( df["PV_kWh"], df["Verbruik_kWh"] ) :
    netto_uur = pv - verbruik  # Positief = overschot, Negatief = tekort
    
    if netto_uur > 0:
      # --- ER IS OVERSCHOT (Laden) ---
      beschikbare_ruimte = accu_capaciteit_kwh - huidige_acculading
      # Hoeveel van het overschot kan daadwerkelijk in de accu?
      stroom_naar_accu = min ( netto_uur, beschikbare_ruimte / laad_efficientie )
      
      # Update de acculading
      huidige_acculading += stroom_naar_accu * laad_efficientie
      
      # Wat overblijft na het laden gaat naar het net
      uur_teruglevering = netto_uur - stroom_naar_accu
      uur_net_afname = 0.0
        
    else:
      # --- ER IS TEKORT (Ontladen) ---
      tekort = abs ( netto_uur )
      # Hoeveel kan de accu maximaal leveren om het tekort te dekken?
      stroom_uit_accu = min ( tekort, huidige_acculading * laad_efficientie )
      
      # Update de acculading
      huidige_acculading -= stroom_uit_accu / laad_efficientie
      
      # Wat nog overblijft van het tekort moet van het net komen
      uur_teruglevering = 0.0
      uur_net_afname = tekort - stroom_uit_accu
        
    # Sla de resultaten van dit specifieke uur op
    accu_status  .append ( huidige_acculading )
    teruglevering.append ( uur_teruglevering  )
    net_afname   .append ( uur_net_afname     )

  # Voeg de berekende arrays in één keer toe aan de DataFrame
  df [ "Accu_Status_kWh"   ] = accu_status
  df [ "Teruglevering_kWh" ] = teruglevering
  df [ "Net_afname_kWh"    ] = net_afname
  
  totale_pv_opbrengst  = df [ "PV_kWh"            ].sum()
  totale_teruglevering = df [ "Teruglevering_kWh" ].sum()
  totale_net_afname    = df [ "Net_afname_kWh"    ].sum()

  return ( df, totale_pv_opbrengst, totale_teruglevering, totale_net_afname )



# ***********************************************************************
# ***********************************************************************
def Get_Kwartier_PV_Bestand ( Year, Month
                             ,kWp     = 1
                             ,Helling = 35
                             ,Station = "Volkel" ) :

  Filename = "pv_%i_kwartierdata_%i_%i.csv" % ( Helling, Year, Month )

  if not os.path.isfile ( Filename ) :
    Start    = "%i-%02i-%02i" % ( Year, Month, 1 )
    if Month == 12 :
      Einde    = "%i-%02i-%02i" % ( Year+1, 1, 1)
    else :
      Einde    = "%i-%02i-%02i" % ( Year, Month + 1, 1)
    
    DF = Get_KNMI_KwartierData ( Start, Einde, kWp=kWp, Helling=Helling, Station = "Volkel" )
    DF.to_csv ( Filename, float_format='%.1f', sep=';' )
    
    print ( "\n" + "="*60 )
    print ( f"Bestand opgeslagen als: {Filename}" )
    
    # Toon de totale maandopbrengst per oriëntatie ter controle
    #"""
    #print("--- TOTALE MAANDOPBRENGST PER ORIËNTATIE (kWh) ---")
    for Col in DF.columns :
      if Col != "Temp" :
        kWh = int(round(DF[Col].sum()/1000))
        print ( "%5i kWh = %s" % ( kWh, Col ) )
        
  return Filename    

# ***********************************************************************
# Afname + PV - Terug = Verbruik
# We hebben deze gegevens per jaar, maar willen ze ook per maand weten.
# We veronderstellen in eerste instantie dat het verbruik over de dag constant is
# Verbruik_Dag = Verbruik_Maand / 30.5
# Vervolgens kunnen we over alle dagen in iedere maand:
# Per dag de PV vergeljken met het constante Verbruik
#  - PV sommeren 
#  - als PV > Verbruik, meetellen als Terug
# we weten dan ook de Afname = Verbruik + Terug - PV
# Vervolgens dagggevens van Afname, Terug, PV sommeren over de gehele maand
# ***********************************************************************
def Get_Month_PV_part ( Year, Month, Verbruik, PV_Wp ) :
  Filename = Get_Kwartier_PV_Bestand ( Year, Month )  
  df = pd.read_csv ( Filename, sep=';'
                    ,index_col   = 0       # Maakt van de eerste kolom (de tijd) de officiële index
                    ,parse_dates = True )  # Zorgt dat pandas snapt dat het om datums en tijden gaat
  #print ( df )  



  # ==========================================
  # 1. INSTELLINGEN & INPUTS
  # ==========================================
  #csv_bestand = "PV_kwartier_data.csv"  # Pas aan naar jouw bestandsnaam
  totale_consumptie_maand_kwh = Verbruik
  
  # Geef hier de gewenste windrichting en het vermogen van jouw panelen op:
  gekozen_richting = "W_Zuid"  # Opties: 'W_West', 'W_Zuid-West', 'W_Zuid', 'W_Zuid-Oost', 'W_Oost'
  gekozen_wpeak = PV_Wp  # Voorbeeld: 4000 Wp (4 kWp) aan zonnepanelen
  
  # ==========================================
  # 2. DATA INLEZEN EN VOORBEREIDEN
  # ==========================================
  # We lezen de CSV in, gebruiken de eerste kolom als index en gebruiken de puntkomma als scheidingsteken
  #df = pd.read_csv(csv_bestand, sep=";", parse_dates=[0], index_col=0)
  
  # Bereken het totaal aantal kwartieren in deze specifieke maand (dynamisch op basis van de data)
  totaal_kwartieren = len(df)
  
  # Bereken het constante verbruik per kwartier in kWh
  verbruik_per_kwartier_kwh = totale_consumptie_maand_kwh / totaal_kwartieren
  
  # ==========================================
  # 3. PV OPBRENGST BEREKENEN
  # ==========================================
  # De basisdata is voor 1 kWp (1000 Wp). We schalen dit naar de gekozen Wpeak.
  # Formule: (Watt_basis * (Gekozen_Wp / 1000 Wp)) * 0.25 uur / 1000 (naar kWh)
  schaal_factor = gekozen_wpeak / 1000.0
  
  df["PV_opbrengst_kWh"] = (
      df[gekozen_richting] * schaal_factor * 0.25 / 1000.0
  )
  
  # Voeg de constante lijn voor het verbruik toe aan het DataFrame
  df["Verbruik_kWh"] = verbruik_per_kwartier_kwh
  
  # ==========================================
  # 4. TERUGLEVERING & AFNAME BEPALEN PER KWARTIER
  # ==========================================
  # Teruglevering vindt plaats als de PV opbrengst groter is dan het verbruik
  df["Teruglevering_kWh"] = np.where(
      df["PV_opbrengst_kWh"] > df["Verbruik_kWh"],
      df["PV_opbrengst_kWh"] - df["Verbruik_kWh"],
      0.0,
  )
  
  # Net-afname vindt plaats als het verbruik groter is dan de PV opbrengst
  df["Net_afname_kWh"] = np.where(
      df["Verbruik_kWh"] > df["PV_opbrengst_kWh"],
      df["Verbruik_kWh"] - df["PV_opbrengst_kWh"],
      0.0,
  )
  
  # ==========================================
  # 5. RESULTATEN BEREKENEN EN TONEN
  # ==========================================
  totale_pv_opbrengst = df["PV_opbrengst_kWh"].sum()
  totale_teruglevering = df["Teruglevering_kWh"].sum()
  totale_net_afname = df["Net_afname_kWh"].sum()
  
  """
  eigen_verbruik = totale_pv_opbrengst - totale_teruglevering
  print(f"--- Resultaten voor {gekozen_richting} met {gekozen_wpeak} Wp ---")
  print(f"Totale PV opbrengst deze maand:      {totale_pv_opbrengst:.2f} kWh")
  print(f"Totale Teruglevering aan het net:    {totale_teruglevering:.2f} kWh")
  print(f"Totale Afname elektriciteit van net: {totale_net_afname:.2f} kWh")
  print(f"Direct eigen verbruik van PV-stroom: {eigen_verbruik:.2f} kWh")
  #"""
  
  return ( totale_pv_opbrengst, totale_teruglevering, totale_net_afname )



def Main_Start () :  pass
""" *********************************************************************
# ***********************************************************************
# Main program
# ***********************************************************************
# ********************************************************************"""
if __name__ == "__main__":
  
  Tests = [5]
  
  # =========================================================================
  if 1 in Tests :
  # =========================================================================
    Year     = 2024
    Month    = 3
    Verbruik = 278  # kWh over de gehele maand
    PV_Wp    = 3000
    
    
    DF, PV, Terug, Afname = Get_Month_PV_Uur_part ( Year, Month, Verbruik, PV_Wp )
    print ( DF.sum() )
    print ( "PV = %i    Afname = %i    Terug = %i" % ( PV, Afname, Terug ) ) 
    print ()
    
    # *****************************************
    # Gas-2-Elektra  hybr * Gas_m3 * G2E / SCOP
    # *****************************************
    Warmtepomp_kWh = 0.60 * 1200   * 10  / 4
    GraadDagen_pm_Volkel_2024_18_15 = np.array ([ 498, 318, 281, 164, 40, 46, 12, 0, 55, 174, 375, 428 ])
    GraadDagen_pm                   = np.array ([ 498, 318, 281, 164, 40, 46, 12, 0, 55, 174, 375, 428 ])

    GD_MaandDeel = GraadDagen_pm [ Month - 1 ] / GraadDagen_pm.sum()

    DF_Year   = KNMI_Get_QT_Year ( Year, WeerStation='Volkel' )
    DF, PV2, Terug2, Afname2 = Calc_Month_Elektra ( DF_Year, Year, Month
                                                   ,Verbruik       = Verbruik 
                                                   ,PV_Wp          = PV_Wp
                                                   ,Warmtepomp_kWh = GD_MaandDeel * Warmtepomp_kWh )
    print ( DF.sum() )
    print ( "PV = %i    Afname = %i    Terug = %i" % ( PV2, Afname2, Terug2 ) ) 
    print ()
    print ( "Delta_Afname = %i    Delta_Terug = %i" % ( Afname2-Afname, Terug2-Terug ) ) 
  
  
  
  # =========================================================================
  if 2 in Tests :
  # =========================================================================
    Year     = 2024
    for Month in range ( 1, 3 ) :
      Filename = Get_Uur_QT_Bestand ( Year, Month, Force_Rebuild=True )
      df = pd.read_csv ( Filename, sep=';'
                        ,index_col   = 0      
                        ,parse_dates = True ) 
      Filename = Get_Uur_QT_Bestand ( Year, Month, Force_Rebuild=True )
      print ( Filename )
  
  
  # =========================================================================
  # Lees MaandFile, filter 1 dag em plot deze
  # =========================================================================
  if 4 in Tests :
    kWp          = 3.0
    Year         = 2026
    Month        = 5
    Day          = 28
    Day_Selected = "%i-%02i-%02i" % ( Year, Month, Day )
    Filename     = Get_Kwartier_PV_Bestand ( Year, Month )  
    
    
    DF = pd.read_csv ( Filename, sep=';'
                      ,index_col   = 0       # Maakt van de eerste kolom (de tijd) de officiële index
                      ,parse_dates = True )  # Zorgt dat pandas snapt dat het om datums en tijden gaat
    
    een_dag_df  = DF.loc [ Day_Selected ]
    
    print("\n" + "="*60)
    print(f"📊 DAGDATA GEFILTERD VOOR: {Day_Selected}")
    print(f"Aantal kwartier-records voor deze dag: {len(een_dag_df)}")
    print("="*60)
    
    Dag_Grafiek_WZO ( een_dag_df
                     ,datum_str = Day_Selected
                     ,kwp       = kWp )
             
  # =========================================================================
  # Geneeer alle KNMI QT-bestanden van 2017 t/m 2025
  # =========================================================================
  if 5 in Tests :
    for Year in range ( 2017, 2026 ) :
      DF = KNMI_Get_QT_Year ( Year, WeerStation = "Volkel" )
      print ( DF.sum(), Year )

