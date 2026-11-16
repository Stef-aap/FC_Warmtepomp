#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
self.Results    bevat de resulaten die worden afgebeeld in tabel onder grafiek

BELANGRIJK:
Vastrecht (VR) en EnergieBelastingTeruggave (EBT) worden pas bij het eindresultaat toegevoegd.
Kosten in tussenberekeningen zijn daarom altijd zonder VR en EBT.
  
Version = 1.6
  - CV, WP1 en WP3 helemaal nageplozen
  - Elektrakosten houden nu rekening met extra eigen gebruik van PV door WP

Version = 1.5
  - implementering van uurscan, PV en Accu
  - print pdf problem via global variable opgelost
  
Version = 1.4   # 12-10-2025
  - correct gebruik van session_state

Version = 1.3   # 12-10-2025
Version = 1.2   # 10-10-2025     saved: St_Warmtepomp_27_v1.2.py
Version = 1.1   # 10-10-2026    saved: St_Warmtepomp_26_v1.1.py
  - Lay out, alle componenten aanwezig
  - getest op streamlit cloud
  
Version = 0.9   # - DEEL 1 - Fix voor printen, tabel-zichtbaarheid en balk-nulpunt
"""
Version = 1.6

import os
from   datetime          import datetime, timedelta
import streamlit         as st
import pandas            as pd
import plotly.express    as px
import requests

# *****************************************************************************
# MOET ANDERS
# *****************************************************************************
from   model_optimization  import kWh_from_m3, Dict_prop, Calc_Energie
from   Zon_History         import KNMI_Get_QT_Year
# *****************************************************************************
# *****************************************************************************


# *****************************************************************************
# *****************************************************************************

Stations = "Volkel,Arcen,Horst,De Bilt,Eindhoven,Groningen,Schiphol,Vlissingen".split(',')
Datum    = datetime.now().strftime("%d-%m-%Y")
   


# 1. INITIALISEER DE CONFIGURATIE EN DWING LICHT THEMA AF VOOR STABIELE PRINTS
st.set_page_config (
  layout                = "wide", 
  page_title            = "Energie Dashboard", 
  page_icon             = "⚡",
  initial_sidebar_state = "collapsed"
)

# Basisdata in session state laden
if "init_verbruik" not in st.session_state :
  st.session_state.init_verbruik = {
    "Gas [m3]"                   : 1200, 
    "Elektra Afname [kWh]"       : 1900, 
    "TerugLevering [kWh]"        : 1700,
    "PV Opbrengst [kWh]"         : 2600, 
    "Capaciteit ThuisAccu [kWh]" : 5,
  }

if "init_vast" not in st.session_state :
  st.session_state.init_vast = {
    "Leen Rente [%]"                 : 5.2, 
    "Spaar Rente [%]"                : 2.1, 
    "Vastrecht Elektra [€]"          : 480, 
    "Vastrecht Gas [€]"              : 270, 
    "Teruggave EnergieBelasting [€]" : 635
  }

if "init_wp" not in st.session_state :
  st.session_state.init_wp = {
    "Installatie": [
       "Aanschaf Prijs [€]", 
       "OnderhoudsKosten [€]", 
       "Aanschaf Jaar", 
       "Levensduur [jaren]", 
       "SCOP (factor)", 
       "Aandeel Verwarming [%]" ],
    "CV" : [  2000, 100, 2024, 15, 1.0,   0 ],   
    "WP1": [ 12000, 100, 2024, 15, 4.0, 100 ], 
    "WP2": [  6000, 100, 2024, 15, 4.0,  75 ],  
    "WP3": [  4500, 100, 2024, 15, 4.0,  50 ],  
  }

# ****************************************************************************
# **************************************************************************** @st.cache_data
def Print_Iets () :
  print ( "Dit is een gecachte procedure" )
  
# ****************************************************************************
# Berekent Cumulatieve rente
# 5% (berekend vanaf jaar 1) over 10 jaar levbert dus 12.58
# ****************************************************************************
@st.cache_data
def Cum_Rente ( Delta, N_Jaren ) :
  if Delta == 0 : Factor = N_Jaren
  else          : Factor = ( ( 1 + Delta ) ** N_Jaren - 1 ) / Delta
  return Factor
      
  
# ****************************************************************************
# ****************************************************************************
class EnergieModel :
  def __init__ ( self ) :
    pass
      
  # ************************************************************
  # ************************************************************
  def get_value_verbruik ( self, item ) :
    if "editor_verbruik" in st.session_state and\
       "edited_rows"     in st.session_state.editor_verbruik :
      edited = st.session_state.editor_verbruik [ "edited_rows" ]
      keys = list(st.session_state.init_verbruik.keys () )
      for idx, changes in edited.items () :
        if keys [ idx ] == item and "Waarde" in changes :
          return changes [ "Waarde" ]
    return st.session_state.init_verbruik [ item ]

  # ************************************************************
  # ************************************************************
  def create_sliders ( self ) :
    col_1, col_2 = st.columns ( 2 )
    
    # Check of er zojuist een JSON-bestand is ingeladen, anders pakken we de standaardwaarden
    sl_load = st.session_state.get ( "load_sliders", {} )
    
    with col_1 :
      self.sl_elek_prijs  = st.slider ( "Elektra Prijs (ct)"             ,10, 50, int ( sl_load.get ( "elek_prijs" , 40 ))) / 100
      self.sl_elek_delta  = st.slider ( "Elektra Jaarlijkse Stijging (%)", 0, 10, int ( sl_load.get ( "elek_delta" ,  5 ))) / 100  
      self.sl_terug_prijs = st.slider ( "Terug Prijs (ct)"               ,10, 50, int ( sl_load.get ( "terug_prijs",  2 ))) / 100
    with col_2 :
      self.sl_gas_prijs = st.slider ( "Gas Prijs (ct)"            , 50, 300, int ( sl_load.get ( "gas_prijs", 200 ))) / 100
      self.sl_gas_delta = st.slider ( "Gas Jaarlijkse Stijging (%)", 0,  10, int ( sl_load.get ( "gas_delta",   5 ))) / 100      
      self.sl_jaren     = st.slider ( "EvaluatiePeriode (Jaren)"   , 1,  30, int ( sl_load.get ( "jaren"    ,  10 )))


  # ************************************************************
  # ************************************************************
  def get_value_vast ( self, item ) :
    if "editor_vast" in st.session_state and \
       "edited_rows" in st.session_state.editor_vast :
      edited = st.session_state.editor_vast [ "edited_rows" ]
      keys   = list ( st.session_state.init_vast.keys () )
      for idx, changes in edited.items () :
        if keys [ idx ] == item and "Waarde" in changes :
          return changes [ "Waarde" ]
    return st.session_state.init_vast [ item ]

  # ************************************************************
  # ************************************************************
  def get_value_wp ( self, rij, Sys ) :
    if "editor_wp"   in st.session_state and \
       "edited_rows" in st.session_state.editor_wp :
      edited = st.session_state.editor_wp [ "edited_rows" ]
      rijen = st.session_state.init_wp [ "Installatie" ]
      for idx, col_changes in edited.items() :
        if rijen [ idx ] == rij and Sys in col_changes :
          return col_changes [ Sys ]
    rijen = st.session_state.init_wp [ "Installatie" ]
    row_idx = rijen.index ( rij )
    return st.session_state.init_wp [ Sys ][ row_idx ]

  # ************************************************************
  # ************************************************************
  def create_table_energie_verbruik ( self ) :
    df                 = pd.DataFrame ( { "Waarde": st.session_state.init_verbruik } )
    df.index.name      = "Energie Verbruik"
    kolom_instellingen = { "Waarde": st.column_config.NumberColumn(alignment="center" ) }
    st.data_editor ( df, 
                     width         = "stretch", 
                     num_rows      = "fixed", 
                     disabled      = ["_index"], # Zorgt dat de eerste kolom (de index) NIET editable is
                     column_config = kolom_instellingen, 
                     key           = "editor_verbruik")    
       
  # ************************************************************
  # ************************************************************
  def create_table_vaste_kosten ( self ) :    
    df                 = pd.DataFrame ( { "Waarde": st.session_state.init_vast } )
    df.index.name      = "Vaste Kosten"
    kolom_instellingen = { "Waarde": st.column_config.NumberColumn(alignment = "center" ) }
    st.data_editor ( df, 
                     width         ="stretch", 
                     num_rows      ="fixed", 
                     disabled      = ["_index"],
                     column_config = kolom_instellingen, 
                     key           = "editor_vast" )    

  # ************************************************************
  # ************************************************************
  def create_table_output ( self ) :
    data_items = [ "VerwarmingsKosten per Maand", 
                   "VerwarmingsKosten per Jaar", 
                   "EnergieKosten (eerste jaar)",
                   "Gas (per jaar)",
                   "Afname (per jaar)",
                   "Terug (per jaar)",
                   "PV Eigen Verbruik" 
                 ]
    df_output = pd.DataFrame ( {
      "Resultaat": data_items,
      "CV":  [
        "€ %i" % ( round ( self.Results [ "CV" ][ "Totaal" ] / self.sl_jaren / 12 ) ),
        "€ %i" % ( self.Results [ "CV" ][ "Totaal" ] / self.sl_jaren ),
        "€ %i" %   self.Results [ "CV" ][ "EnergieKosten" ],
        self.Results [ "CV" ][ "Gas"            ],
        self.Results [ "CV" ][ "Afname"         ],
        self.Results [ "CV" ][ "Terug"          ],
        self.Results [ "CV" ][ "Eigen_Verbruik" ],
      ],
      "WP1": [
        "€ %i" % ( round ( self.Results [ "WP1" ][ "Totaal" ] / self.sl_jaren / 12 ) ),
        "€ %i" % ( self.Results [ "WP1" ][ "Totaal" ] / self.sl_jaren ),
        "€ %i" %   self.Results [ "WP1" ][ "EnergieKosten" ],
        self.Results [ "WP1" ][ "Gas"            ],
        self.Results [ "WP1" ][ "Afname"         ],
        self.Results [ "WP1" ][ "Terug"          ],
        self.Results [ "WP1" ][ "Eigen_Verbruik" ],
      ],
      "WP2": [
        "€ %i" % ( round ( self.Results [ "WP2" ][ "Totaal" ] / self.sl_jaren / 12 ) ),
        "€ %i" % ( self.Results [ "WP2" ][ "Totaal" ] / self.sl_jaren ),
        "€ %i" %   self.Results [ "WP2" ][ "EnergieKosten" ],
        self.Results [ "WP2" ][ "Gas"            ],
        self.Results [ "WP2" ][ "Afname"         ],
        self.Results [ "WP2" ][ "Terug"          ],
        self.Results [ "WP2" ][ "Eigen_Verbruik" ],
      ],
      "WP3": [
        "€ %i" % ( round ( self.Results [ "WP3" ][ "Totaal" ] / self.sl_jaren / 12 ) ), 
        "€ %i" % ( self.Results [ "WP3" ][ "Totaal" ] / self.sl_jaren ),
        "€ %i" %   self.Results [ "WP3" ][ "EnergieKosten" ],
        self.Results [ "WP3" ][ "Gas"            ],
        self.Results [ "WP3" ][ "Afname"         ],
        self.Results [ "WP3" ][ "Terug"          ],
        self.Results [ "WP3" ][ "Eigen_Verbruik" ],
      ],
    })    
    # TextColumn voorkomt dat er rode accenten in de hoeken van een string cell komen
    #kolom_instellingen = { col : st.column_config.NumberColumn ( alignment="center", width=100 ) \
    kolom_instellingen = { col : st.column_config.TextColumn ( alignment="center", width=100 ) \
                          for col in [ "CV", "WP1", "WP2", "WP3" ] }

    kolom_instellingen["Resultaat"] = st.column_config.Column ( width = 160 )

    # Om te voorkomen dat we foutmeldingen in de console ontstaan
    df_output['CV']  = df_output['CV' ].astype(str)
    df_output['WP1'] = df_output['WP1'].astype(str)
    df_output['WP2'] = df_output['WP2'].astype(str)
    df_output['WP3'] = df_output['WP3'].astype(str)

    st.dataframe ( df_output
                  ,width         = "stretch"
                  #,use_container_width = True  # Vervang "stretch" (is verouderd) door True
                  ,row_height    = 25
                  ,hide_index    = True
                  ,column_config = kolom_instellingen )


  # ************************************************************
  # ************************************************************
  def create_table_installatie ( self ) :
    df                 = pd.DataFrame ( st.session_state.init_wp ).set_index ( "Installatie" )
    #kolom_instellingen = { Sys: st.column_config.NumberColumn ( alignment="center" ) \
    #                       for Sys in [ "CV", "WP1", "WP2", "WP3" ]}
    # 1. Zet de systeemkolommen op gecentreerd én op een vaste breedte van 100 pixels
    kolom_instellingen = { Sys: st.column_config.NumberColumn ( alignment="center", width=100 ) \
                           for Sys in [ "CV", "WP1", "WP2", "WP3" ]}
    
    # 2. Voeg de eerste kolom (de index-kolom) handmatig toe met een vaste breedte van 250 pixels
    kolom_instellingen["Installatie"] = st.column_config.Column ( width = 180 )
          
    st.data_editor ( df 
                    ,width         = "stretch"
                    ,row_height    = 25
                    ,num_rows      = "fixed"
                    ,disabled      = ["_index"]
                    ,column_config = kolom_instellingen
                    ,key           = "editor_wp" )
    
  # ************************************************************
  # ************************************************************
  def create_PV_Opwek ( self ) :
    # 1. Initialiseer de lijst éénmalig in de session_state als deze nog niet bestaat
    if "knmi_stations_lijst" not in st.session_state :
      st.session_state.knmi_stations_lijst = "Volkel,Arcen,Horst,De Bilt,Eindhoven,Groningen,Schiphol,Vlissingen".split(',')

    # 2. Gebruik de lijst uit de session_state voor de selectbox
    self.KNMI_Station = st.selectbox (
        "Kies een KNMI Weerstation of type een nieuwe" 
        ,st.session_state.knmi_stations_lijst
        ,index              = 0
        ,accept_new_options = True
      )
    
    # Print de onthouden lijst naar je terminal ter controle
    print(st.session_state.knmi_stations_lijst)
    
    if self.KNMI_Station:
      # 3. Controleer tegen de onthouden lijst in session_state
      if self.KNMI_Station not in st.session_state.knmi_stations_lijst:
        st.session_state.knmi_stations_lijst.append(self.KNMI_Station)
        st.rerun() # Deze herlaadbeurt stopt nu wél de loop, omdat het station nu wél onthouden is!

      # 4. Data ophalen en tonen
      KNMI_Get_QT_Year ( 2024, WeerStation = self.KNMI_Station )
      st.write(f"Geselecteerd station: **{self.KNMI_Station}**")


  # ************************************************************
  # ************************************************************
  def create_chart ( self ) :
    chart_rows = []
    for Sys, posten in self.Results.items () :
      for kosten_type in [ "Aanschaf", "Vaste Kosten", "Verbruik" ] :
        chart_rows.append ( {
          "Installatie" : Sys,
          "Type Kosten" : kosten_type,
          "Bedrag (€)"  : posten [ kosten_type ]
        } )
    self.df_grafiek_laatste = pd.DataFrame ( chart_rows ) # Onthoud de data voor de PDF
  
    fig = px.bar (
      self.df_grafiek_laatste, x = "Installatie", y = "Bedrag (€)", color = "Type Kosten", 
      text_auto = '.2s', height = 400,
      color_discrete_map = { "Aanschaf": "#94a3b8", "Vaste Kosten": "#38bdf8", "Verbruik": "#f43f5e" } 
    )
    
    fig.update_layout(
      legend        = dict ( orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1 ),
      margin        = dict ( l=40, r=10, t=10, b=30 ),
      paper_bgcolor = "rgba(0,0,0,0)",
      plot_bgcolor  = "rgba(0,0,0,0)",
      font          = dict ( color = "#000000" )
    )
    
    fig.update_xaxes ( title = None, showgrid = True, gridcolor = "#e2e8f0", tickfont = dict ( color ="#000000" ) )
    fig.update_yaxes ( title = None, showgrid = True, gridcolor = "#e2e8f0", tickfont = dict ( color ="#000000" ) )
    
    #st.plotly_chart ( fig, 
    #                  width = "stretch",
    #                  #use_container_width = True, 
    #                  config = {"displayModeBar": False }
    #                )
    
    # 1. Blokkeer zoomen en slepen op de assen in de layout van de figuur
    fig.update_layout (
      xaxis    = dict ( fixedrange = True ), # Voorkomt zoomen/slepen op de X-as
      yaxis    = dict ( fixedrange = True ), # Voorkomt zoomen/slepen op de Y-as
      dragmode = False               # Schakelt de sleep-modus volledig uit
    )
    
    # 2. Toon de grafiek zonder menubalk en zet de interactie op 'fixed'
    st.plotly_chart (
      fig, 
      #use_container_width = True,
      width  = "stretch",             
      config = {
          "displayModeBar" : False, # Verbergt het menu rechtsboven
          "scrollZoom"     : False      # Voorkomt zoomen met het muiswiel
      }
    )

  

    
  # ************************************************************
  # ************************************************************
  def run_calculations ( self ) :
    Gas_Verbruik        = self.get_value_verbruik ( "Gas [m3]" )
    Gas_Vastrecht       = self.get_value_vast     ( "Vastrecht Gas [€]" )
    Teruggave_Belasting = self.get_value_vast     ( "Teruggave EnergieBelasting [€]" )
    Kosten_Aanschaf_CV  = self.get_value_wp       ( "Aanschaf Prijs [€]", "CV" )
    Levensduur_CV       = self.get_value_wp       ( "Levensduur [jaren]", "CV" )
    Onderhoud_CV        = self.get_value_wp       ( "OnderhoudsKosten [€]", "CV" )
    
    Elektra_Vastrecht   = self.get_value_vast     ( "Vastrecht Elektra [€]" )
    Elektra_Afname      = self.get_value_verbruik ( "Elektra Afname [kWh]" )
    Elektra_Terug       = self.get_value_verbruik ( "TerugLevering [kWh]" )
    PV_Opbrengst        = self.get_value_verbruik ( "PV Opbrengst [kWh]" )
    Accu_kWh            = self.get_value_verbruik ( "Capaciteit ThuisAccu [kWh]" )
    
    # *****************************************
    Energie_Case = Dict_prop ()
    # *****************************************
    Energie_Case.Year                 = 2024                # 2024
    
    Energie_Case.Afname_kWh_pj        = Elektra_Afname      # 1900 kWh
    Energie_Case.Terug_kWh_pj         = Elektra_Terug       # 1700 kWh
    
    Energie_Case.PV_kWh_pj            = PV_Opbrengst        # 2600 kWh
    Energie_Case.PV_kWh_Extra_pj      = 0                   #    0 kWh
    
    #Energie_Case.WP_Hybride           = Aandeel_Verw        # 0=CV_ketel, 1=Full_Electric
    #Energie_Case.WP_SCOP              = SCOP                # 4.0
    Energie_Case.WP_Slim              = False               # False
    
    Energie_Case.Accu_kWh             = Accu_kWh            # 5.0 kWh
    Energie_Case.Accu_RTE             = 0.92 ** 2           # 0.85
    Energie_Case.Accu_max_Laad_kW     = 2.5                 # 2.5 kW
    Energie_Case.Accu_max_Ontlaad_kW  = 0.8                 # 0.8 kW
    Energie_Case.Accu_min_SOC         = 12                  # 12%
    
    Energie_Case.Gas_m3_pj            = Gas_Verbruik        # 1200 m3
    
    Energie_Case.Elektra_Vastrecht_pj = Elektra_Vastrecht                 # € 490 = Leverancier + Netkosten
    Energie_Case.Gas_Vastrecht_pj     = Gas_Vastrecht       # € 270 = Leverancier + Netkosten
    Energie_Case.Elektra_Prijs        = self.sl_elek_prijs  # € 0.40 all in prijs      per kWh
    Energie_Case.Terug_Prijs          = self.sl_terug_prijs # € 0.02 all in vergoeding per kWh
    Energie_Case.Gas_Prijs            = self.sl_gas_prijs   # € 2.00 per m3

    # ************************************************************
    # ************************************************************
    self.Results = {}
    CL      = ''   # Controle regel die een hele hoop kan printen    
    Systems = [ "CV", "WP1", "WP2", "WP3" ]
    for Sys in Systems :
      Aanschaf_sys   = self.get_value_wp ( "Aanschaf Prijs [€]"    , Sys )
      Levensduur     = self.get_value_wp ( "Levensduur [jaren]"    , Sys )
      Onderhoud_sys  = self.get_value_wp ( "OnderhoudsKosten [€]"  , Sys )
      SCOP           = self.get_value_wp ( "SCOP (factor)"         , Sys )
      Aandeel_Verw   = self.get_value_wp ( "Aandeel Verwarming [%]", Sys ) / 100 
      
      # *************************
      # Aanschaf Kosten
      # *************************
      Kosten_Aanschaf_pj = Aanschaf_sys / Levensduur
      if Aandeel_Verw < 1.0 and Sys != "CV":
        Kosten_Aanschaf_pj += ( Kosten_Aanschaf_CV / Levensduur_CV )
      Kosten_Aanschaf = Kosten_Aanschaf_pj * self.sl_jaren
      
      # *************************
      # Vaste Kosten
      # *************************
      Kosten_Vast_pj = Onderhoud_sys
      if Aandeel_Verw < 1.0 and Sys != "CV":
        Kosten_Vast_pj += ( Onderhoud_CV + Gas_Vastrecht )
      elif Sys == "CV":
        Kosten_Vast_pj += Gas_Vastrecht
      Kosten_Vast = Kosten_Vast_pj * self.sl_jaren

      # OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO
      #          MODEL OPTIMIZATION
      # OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO
      Energie_Case.WP_Hybride       = Aandeel_Verw        # 0=CV_ketel, 1=Full_Electric
      Energie_Case.WP_SCOP          = SCOP                # 4.0
      Afname_kWh, Terug_kWh, Gas_m3 = Calc_Energie ( Energie_Case, Do_Print = False ) 
      # OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO
      # OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO

      # *************************
      # Verbruikskosten, doorloop alle jaren, want prijzen stijgen
      # *************************
      Factor_G = Cum_Rente ( self.sl_gas_delta , self.sl_jaren )
      Factor_E = Cum_Rente ( self.sl_elek_delta, self.sl_jaren )

      Kosten_Gas_Verwarming     = Factor_G * ( 1 - Aandeel_Verw ) * Gas_Verbruik               * self.sl_gas_prijs
      Kosten_Elektra_Verwarming = Factor_E *  Aandeel_Verw        * Gas_Verbruik * kWh_from_m3 * self.sl_elek_prijs / SCOP
      

      # *************************
      # Bewaar de CV situatie, want dan kun je verschillen berekenen
      # *************************
      if Sys == "CV" :
        #Energie_Case_CV      = Energie_Case.copy ()
        #Afname_kWh_CV        = Afname_kWh
        #Terug_kWh_CV         = Terug_kWh
        Kosten_Verbruik_Flex = Kosten_Gas_Verwarming + Kosten_Elektra_Verwarming
        
        # **********************
        # Hier vastleggen wat de kosten voor elektra zijn
        # om bij de andere systemen af te trekken
        # **********************
        Kosten_Verbruik_Flex_CV  = Factor_E * Afname_kWh * self.sl_elek_prijs
        Kosten_Verbruik_Flex_CV -= Factor_E * Terug_kWh  * self.sl_terug_prijs
        
      else :
        Kosten_Elektra_Totaal  = Factor_E * Afname_kWh * self.sl_elek_prijs
        Kosten_Elektra_Totaal -= Factor_E * Terug_kWh  * self.sl_terug_prijs

        Kosten_Verbruik_Flex   = Kosten_Elektra_Totaal - Kosten_Verbruik_Flex_CV
        Kosten_Verbruik_Flex  += Kosten_Gas_Verwarming
        #CL += '\n\nnot SYS: %i   %i   %i' % ( Afname_kWh, Kosten_Elektra_Totaal, Kosten_Verbruik_Flex_CV )
      
      
      #CL += '\n  Afname=%i    Flex_CV=€%i' % ( Afname_kWh, Kosten_Verbruik_Flex_CV )
      
      
      # *************************************************************
      # Bereken tiotalen en berg deze op
      # *************************************************************
      bruto_totaal = Kosten_Aanschaf + Kosten_Vast + Kosten_Verbruik_Flex

      Afname_Kosten = Elektra_Vastrecht + Afname_kWh * self.sl_elek_prijs
      Terug_Kosten  =                   - Terug_kWh  * self.sl_terug_prijs
      Gas_Kosten    = Gas_Vastrecht     + Gas_m3     * self.sl_gas_prijs
      if Gas_m3 == 0 : Gas_Kosten = 0
      Kosten = Afname_Kosten + Terug_Kosten + Gas_Kosten - Teruggave_Belasting

      self.Results [ Sys ] = {
        "Totaal"            : bruto_totaal,

        "EnergieKosten"     : Kosten,

        "Gas"               : "%i m3  |  €%i"  % ( round(Gas_m3    ), round(Gas_Kosten    )),
        "Afname"            : "%i kWh  |  €%i" % ( round(Afname_kWh), round(Afname_Kosten )),
        "Terug"             : "%i kWh  |  €%i" % ( round(Terug_kWh ), round(Terug_Kosten  )),
 
        "Eigen_Verbruik"    : "%i %%" % round ( Energie_Case.Eigen_Verbruik ),
        
        "Aanschaf"          : Kosten_Aanschaf,
        "Vaste Kosten"      : Kosten_Vast,
        "Verbruik"          : Kosten_Verbruik_Flex,
      }

      # *****************************************************************
      # *****************************************************************
      Verbruik     = Afname_kWh + PV_Opbrengst - Terug_kWh 
      Euro_per_kWh = ( Afname_kWh * self.sl_elek_prijs + Terug_Kosten ) \
                    / ( Afname_kWh + Energie_Case.PV_kWh_pj - Terug_kWh )

      CL += '\n'
      CL += '\nAanschaf = €%i' % Kosten_Aanschaf
      CL += '\nVast     = €%i' % Kosten_Vast
      CL += '\nFlex_Sys = €%i' % Kosten_Verbruik_Flex
      #CL += '\nAfname   =  %i kWh' % Afname_kWh
      #CL += '\nTerug    =  %i kWh' % Terug_kWh
      #CL += '\nVerbruikE=  %i kWh' % Verbruik
      #CL += '\nGas      =  %i m3' % Gas_m3
      #CL += '\nGasKosten= €%i' % Gas_Kosten
      CL += '\nFlex CV  = €%i' % Kosten_Verbruik_Flex_CV
     
      CL += '\nAccu= %i    Hybr= %0.2f     SCOP= %.1f' % (
        Accu_kWh, Aandeel_Verw, SCOP )
      CL += '\nCV: Verbruik A+PV-T= %i kWh    Afname= %i kWh    PV= %i kWh    Terug= %i kWh' % (
        Verbruik, Afname_kWh, PV_Opbrengst ,Terug_kWh )
      CL += '\nPrijs per kWh= €%0.2f' % ( Euro_per_kWh )

      if Sys == "CV" :
        Verbruik_CV = Verbruik
      else :
        Verbruik_WP = Verbruik - Verbruik_CV
        CL += '\n%s Kosten WP verbruik= %i' % ( Sys, Verbruik_WP * Euro_per_kWh )

      CL += '\n================'
      CL += '\nKosten_Gas      = %i' % Kosten_Gas_Verwarming
      #CL += '\nKosten_Elektra  = %i' % Kosten_Elektra_Verwarming
      CL += '\nKosten_Aanschaf = %i' % Kosten_Aanschaf
      CL += '\nKosten_Vast     = %i' % Kosten_Vast
      CL += '\nKosten_Verbruik = %i' % Kosten_Verbruik_Flex
      CL += '\nStookgrens      = %.1f °C' % Energie_Case.StookGrens

    print ( CL )


  # ************************************************************
  # ************************************************************
  def export_to_json ( self ) :
    """Pakt alle actuele waarden van tabellen en sliders samen in een JSON string"""
    import json
    
    # Verzamel de live waarden uit de data_editors via de helpers
    live_verbruik = { k: self.get_value_verbruik ( k ) \
                     for k in st.session_state.init_verbruik.keys () }
    live_vast = { k: self.get_value_vast ( k ) \
                 for k in st.session_state.init_vast.keys () }
    
    live_wp = { "Installatie" : st.session_state.init_wp [ "Installatie" ] }
    for Sys in [ "CV", "WP1", "WP2", "WP3" ] :
      live_wp [ Sys ] = [ self.get_value_wp ( rij, Sys ) \
                         for rij in st.session_state.init_wp [ "Installatie" ] ]

    # Voeg alles samen in één groot instellingen-pakket
    instellingen = {
      "verbruik" : live_verbruik,
      "vast"     : live_vast,
      "wp"       : live_wp,
      "sliders"  : {
        "elek_prijs"  : self.sl_elek_prijs  * 100, # Terug naar centen voor de sliders
        "elek_delta"  : self.sl_elek_delta  * 100,
        "terug_prijs" : self.sl_terug_prijs * 100,
        "gas_prijs"   : self.sl_gas_prijs   * 100,
        "gas_delta"   : self.sl_gas_delta   * 100,
        "jaren"       : self.sl_jaren
      }
    }
    # Zet om naar nette JSON tekst met inspringing
    return json.dumps ( instellingen, indent = 4 )

  # ************************************************************
  # ************************************************************
  def import_from_json ( self, json_bestand ) :
    """Laadt een geüpload JSON bestand en overschrijft de session state"""
    import json
    try:
      data = json.load ( json_bestand )
      
      # Overschrijf de basis data in session state
      st.session_state.init_verbruik = data [ "verbruik" ]
      st.session_state.init_vast     = data [ "vast" ]
      st.session_state.init_wp       = data [ "wp" ]
      
      # Sla de slider-waarden op in session state zodat de sliders deze overnemen
      st.session_state.load_sliders = data [ "sliders" ]
      
      # Forceer Streamlit om de pagina direct te vernieuwen met de nieuwe data
      st.rerun ()
    except Exception as e:
      st.error ( f"Fout bij het laden van het JSON-bestand: {e}" )
    

  # ************************************************************
  # ************************************************************
  def export_to_pdf ( self, pdf_verbruik, pdf_vast, pdf_wp, df_grafiek ) :
    import io
    from   reportlab.lib.pagesizes import A4
    from   reportlab.platypus      import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from   reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
    from   reportlab.lib           import colors
    from   matplotlib.figure       import Figure

    # ************************************************************
    # 2. Matplotlib Grafiek Genereren voor de PDF (Thread-safe & Async-proof)
    # ************************************************************
    try:
      # GEBRUIK NU HIER DE MEEGEGEVEN df_grafiek VARIABELE:
      df_pivot = df_grafiek.groupby ( [ 'Installatie', 'Type Kosten' ] 
                                    ) [ 'Bedrag (€)' ].sum ().unstack ().fillna ( 0 )
      
      # Zorg dat de kolommen in de juiste volgorde staan
      gewenste_kolommen = [ col for col in [ "Aanschaf", "Vaste Kosten", "Verbruik" ] \
                            if col in df_pivot.columns ]
      df_pivot = df_pivot [ gewenste_kolommen ]
      
      # Exact dezelfde kleurenmatchen met je originele Plotly schermgrafiek
      color_map   = { "Aanschaf" : "#94a3b8", "Vaste Kosten" : "#38bdf8", "Verbruik" : "#f43f5e" }
      colors_list = [ color_map.get ( col, "#000000" ) for col in df_pivot.columns ]
      
      fig = Figure ( figsize = ( 6, 3.5 ), dpi = 200 )
      ax  = fig.subplots ()
      
      # TEKEN DE GESTAPELDE GRAFIEK
      df_pivot.plot ( kind = 'bar', stacked = True, ax = ax, color = colors_list, width = 0.6 )
      
      # Strakke styling (aslijnen verbergen, grids aanzetten)
      ax.spines [ 'top'    ].set_visible ( False )
      ax.spines [ 'right'  ].set_visible ( False )
      ax.spines [ 'left'   ].set_visible ( False )
      ax.spines [ 'bottom' ].set_color   ( '#e2e8f0' )
      ax.grid ( axis = 'y', linestyle = '-', linewidth = 0.5, color = '#e2e8f0' )
      ax.set_axisbelow ( True )
      ax.set_xlabel ( "" )
      ax.set_ylabel ( "" )
      
      for tick in ax.get_xticklabels () :
        tick.set_rotation ( 0 )
      
      ax.legend ( loc = 'lower right', bbox_to_anchor = ( 1.0, 1.02 ), 
                 ncol = 3, frameon = False, fontsize = 8 )
      
      img_buf = io.BytesIO ()
      fig.savefig ( img_buf, format = 'png', bbox_inches = 'tight', transparent = True )
      img_buf.seek ( 0 )
      chart_img_bytes = img_buf.read ()
        
    except :
      chart_img_bytes = None

    # ************************************************************
    # 3. Document Setup (A4 breedte = 595pt. Marges 25+25=50pt. Beschikbare breedte = 545pt)
    # Linkerkolom (200) + Tussenruimte (25) + Rechterkolom (320) = exact 545pt.
    # ************************************************************
    buffer = io.BytesIO ()
    doc    = SimpleDocTemplate ( buffer,           pagesize     = A4, 
                                 rightMargin = 25, leftMargin   = 25, 
                                 topMargin   = 25, bottomMargin = 25 )
    story  = []
    
    # 4. Typografie & Stijlen
    styles        = getSampleStyleSheet ()
    title_style   = ParagraphStyle ( 'Title'  , parent=styles [ 'Heading1' ], fontSize = 18,                   spaceAfter = 5, textColor = colors.HexColor ( "#0f172a" ))
    section_style = ParagraphStyle ( 'Section', parent=styles [ 'Heading2' ], fontSize = 11, spaceBefore =  8, spaceAfter = 4, textColor = colors.HexColor ( "#1e293b" ))
    normal_style  = ParagraphStyle ( 'Normal' , parent=styles [ 'Normal'   ], fontSize =  9, leading     = 11,                 textColor = colors.HexColor ( "#334155" ))
    
    # Stijl voor tekst IN de tabellen (voorkomt tekst overlap bij lange zinnen)
    table_body_style  = ParagraphStyle ( 'TableBody'      , parent = styles [ 'Normal' ], fontSize = 9, leading = 11, textColor = colors.HexColor ( "#1e293b" ))
    table_body_center = ParagraphStyle  ('TableBodyCenter', parent = table_body_style, alignment = 1 ) # 1 = gecentreerd

    # NIEUW: Stijl voor het tekstblok over de volle breedte aan het einde
    footer_block_style = ParagraphStyle ('FooterBlock',
      parent        = styles [ 'Normal' ],
      fontSize      = 9,
      leading       = 13,
      textColor     = colors.HexColor ( "#1e293b" ),
      backColor     = colors.HexColor ( "#f8fafc" ),  # Lichtgrijze achtergrond
      borderColor   = colors.HexColor ( "#cbd5e1" ),  # Dunne rand
      borderWidth   = 0.5,
      borderPadding = 10,                             # Ruimte binnen het blok
      spaceBefore   = 15,                             # Ruimte boven het blok
      spaceAfter    = 10
    )

    # ************************************************************
    # 1. LOGO & HEADER TOEVOEGEN
    # ************************************************************
    logo_pad = "logo.png" # Zorg dat dit logo in de root van je GitHub staat
    
    header_tekst = [
      Paragraph ( "FC Warmtepomp Calculator (v%.1f)  %s" % ( Version, Datum ), title_style ),
      Paragraph ( f"<b>EvaluatiePeriode:</b> {self.sl_jaren} jaar  |  <b>Gasprijs:</b> € {self.sl_gas_prijs:.2f}/m³  |  <b>Elektraprijs:</b> € {self.sl_elek_prijs:.2f}/kWh", normal_style)
    ]

    # Controleer of het logo bestaat (voorkomt crashes als het bestand ontbreekt)
    if os.path.exists ( logo_pad ) :
      # Logo breedte 100pt, hoogte automatisch schalen (pas aan naar wens)
      logo_img = Image ( logo_pad, width=100, height=40 ) 
      # Tabel met 2 kolommen: Titel (425pt) en Logo (120pt) = 545pt breed
      header_tabel = Table ( [ [ header_tekst, logo_img ] ], colWidths = [ 425, 120 ] )
      header_tabel.setStyle ( TableStyle ( [
        ( 'VALIGN', ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
        ( 'ALIGN' , ( 1, 0 ), (  1 , 0 ), 'RIGHT'  ), # Logo rechts uitlijnen
      ]))
      story.append ( header_tabel )
    else:
      # Fallback als logo niet wordt gevonden
      story.append ( header_tekst [ 0 ] )
      story.append ( header_tekst [ 1 ] )

    story.append ( Spacer ( 1, 15 ))

    # ************************************************************
    # Standaard tabelstijl voor een strakke look
    # ************************************************************
    base_table_style = TableStyle ( [
        ( 'BACKGROUND'    , (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ( 'TEXTCOLOR'     , (0, 0), (-1, 0), colors.whitesmoke),
        ( 'ALIGN'         , (0, 0), (-1, 0), 'LEFT'),
        ( 'FONTNAME'      , (0, 0), (-1, 0), 'Helvetica-Bold'),
        ( 'FONTSIZE'      , (0, 0), (-1, 0), 9),
        ( 'BOTTOMPADDING' , (0, 0), (-1, 0), 5),
        ( 'TOPPADDING'    , (0, 0), (-1, 0), 5),
        ( 'FONTNAME'      , (0, 1), (-1, -1), 'Helvetica'),
        ( 'FONTSIZE'      , (0, 1), (-1, -1), 9),
        ( 'VALIGN'        , (0, 0), (-1, -1), 'MIDDLE'),
        ( 'ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
        ( 'LINEBELOW'     , (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ])

    # --- LINKS: VERBRUIK & VASTE KOSTEN & SLIDERS ---
    left_flowables = []
    
    # ************************************************************
    # 1. Energie Verbruik
    # ************************************************************
    left_flowables.append ( Paragraph ( "Energie Verbruik", section_style ))
    verbruik_data = [[ "Energie Item", "Waarde" ]]
    for k, v in pdf_verbruik.items () :
      verbruik_data.append ( [Paragraph ( k, table_body_style ), Paragraph ( str ( v ), table_body_style ) ])
    t_verbruik = Table ( verbruik_data, colWidths = [ 140, 50 ])
    t_verbruik.setStyle ( base_table_style )
    left_flowables.append ( t_verbruik )
    left_flowables.append ( Spacer ( 1, 15 ) )

    # ************************************************************
    # 2. Vaste Kosten
    # ************************************************************
    left_flowables.append ( Paragraph("Vaste Kosten", section_style ))
    vast_data = [[ "Kosten Item", "Waarde" ]]
    for k, v in pdf_vast.items () :
      vast_data.append ( [ Paragraph ( k        , table_body_style ), 
                           Paragraph ( str ( v ), table_body_style ) ])
    t_vast = Table ( vast_data, colWidths = [ 140, 50 ])
    t_vast.setStyle ( base_table_style )
    #t_vast.setStyle ( table_body_center )   # GEEFT FOUTMELDING
    left_flowables.append ( t_vast )
    left_flowables.append ( Spacer ( 1, 15 ))

    # ************************************************************
    # --- RECHTS: GRAFIEK, RESULTATEN & EIGENSCHAPPEN ---
    # ************************************************************
    right_flowables = []
    
    # ************************************************************
    # Grafiek
    # ************************************************************
    if chart_img_bytes:
      right_flowables.append ( Paragraph ( "Kosten Evaluatie Grafiek", section_style ))
      #right_flowables.append ( Image ( io.BytesIO ( chart_img_bytes ), width=320, height=186 ))
      right_flowables.append ( Image ( io.BytesIO ( chart_img_bytes ), width=350, height=186 ))
      right_flowables.append ( Spacer ( 1, 10 ) )

    # ************************************************************
    # Gemiddelde Resultaten
    # ************************************************************
    right_flowables.append ( Paragraph ( "Gemiddelde Resultaten (Netto)", section_style ))
    output_data = [
      [ "Resultaat indicator", "CV", "WP1", "WP2", "WP3"],
      [ "Kosten / Maand avg", f"€ {int(self.Results['CV']['Totaal']/self.sl_jaren/12)}", f"€ {int(self.Results['WP1']['Totaal']/self.sl_jaren/12)}", f"€ {int(self.Results['WP2']['Totaal']/self.sl_jaren/12)}", f"€ {int(self.Results['WP3']['Totaal']/self.sl_jaren/12)}"],
      [ "Kosten / Jaar avg", f"€ {int(self.Results['CV']['Totaal']/self.sl_jaren)}", f"€ {int(self.Results['WP1']['Totaal']/self.sl_jaren)}", f"€ {int(self.Results['WP2']['Totaal']/self.sl_jaren)}", f"€ {int(self.Results['WP3']['Totaal']/self.sl_jaren)}"],
      [ "Netto Totaal Evaluatie", f"€ {int(self.Results['CV']['Totaal'])}", f"€ {int(self.Results['WP1']['Totaal'])}", f"€ {int(self.Results['WP2']['Totaal'])}", f"€ {int(self.Results['WP3']['Totaal'])}"]
    ]
    
    # ************************************************************
    # Omzetten naar Paragraphs voor automatische uitlijning en wrapping
    # ************************************************************
    formatted_output_data = []
    for r_idx, row in enumerate ( output_data ) :
      formatted_row = []
      for c_idx, cell in enumerate ( row ) :
        if r_idx == 0:
          formatted_row.append ( cell ) # Headers blijven platte tekst voor de TableStyle
        else:
          # Allign iedere row, de volgende regel: col0=Left, andere columns=Center
          #style = table_body_style if c_idx == 0 else table_body_center
          style = table_body_style
          formatted_row.append ( Paragraph ( cell, style ))
      formatted_output_data.append ( formatted_row )

    t_output = Table ( formatted_output_data, colWidths = [ 120, 55, 55, 55, 55 ] )
    t_output.setStyle ( base_table_style )
    right_flowables.append ( t_output )

    right_flowables.append ( Spacer ( 1, 15 ))
    
    # ************************************************************
    # Installatie Eigenschappen (pdf_wp)
    # ************************************************************
    right_flowables.append ( Paragraph ( "Installatie Eigenschappen", section_style ))
    wp_data = [[ "Eigenschap", "CV", "WP1", "WP2", "WP3" ]]
    
    rijen = pdf_wp [ "Installatie" ]
    for idx, rij in enumerate ( rijen ) :
      wp_data.append ( [
        Paragraph ( rij, table_body_style ), 
        Paragraph ( str ( pdf_wp [ "CV"  ][idx]), table_body_style ), #table_body_center ), 
        Paragraph ( str ( pdf_wp [ "WP1" ][idx]), table_body_style ), 
        Paragraph ( str ( pdf_wp [ "WP2" ][idx]), table_body_style ), 
        Paragraph ( str ( pdf_wp [ "WP3" ][idx]), table_body_style )
      ])
    
    t_wp = Table ( wp_data, colWidths= [ 120, 55, 55, 55, 55 ])
    t_wp.setStyle ( base_table_style )
    right_flowables.append ( t_wp )
 
    # --- MASTER LAYOUT (2 KOLOMMEN) ---
    master_data  =  [ [ left_flowables, "", right_flowables ] ]
    master_table = Table ( master_data, colWidths = [ 180, 25, 350 ] )
    master_table.setStyle ( TableStyle ( [
        ( 'VALIGN'       , (0,0), (-1,-1), 'TOP' ),
        ( 'LEFTPADDING'  , (0,0), (-1,-1), 0 ),
        ( 'RIGHTPADDING' , (0,0), (-1,-1), 0 ),
        ( 'BOTTOMPADDING', (0,0), (-1,-1), 0 ),
        ( 'TOPPADDING'   , (0,0), (-1,-1), 0 ),
    ]))
    story.append(master_table)
    
    # ************************************************************
    # 2. TEKSTBLOK OVER VOLLE BREEDTE AAN HET EINDE
    # ************************************************************
    story.append ( Spacer ( 1, 10 ) )
    
    conclusie_tekst = (
      "<b>Disclaimer & Notitie:</b> Deze berekening is een schatting op basis van de door u "
      "ingevoerde verbruiksgegevens en huidige energietarieven. Rendementen van warmtepompen (SCOP) "
      "kunnen in de praktijk variëren afhankelijk van de isolatiewaarde van uw woning en het type "
      "afgiftesysteem (bijv. vloerverwarming versus radiatoren). Er kunnen geen rechten aan deze "
      "calculatie worden ontleend."
    )
    # Omdat dit direct in de main story staat (buiten de kolommen), 
    # neemt het automatisch de volledige breedte van 545pt in beslag.
    story.append ( Paragraph ( conclusie_tekst, footer_block_style ) )
    
    # Bouw PDF document
    doc.build ( story )
    buffer.seek ( 0 )
    return buffer
  
# ****************************************************************************
# ****************************************************************************
def main () :        

  # Dashboard schermlay-out hersteld naar stabiele weergave
  st.markdown ( """
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h3 {margin-top: 0rem; margin-bottom: 0.5rem;}
    </style>
  """, unsafe_allow_html = True )
  
  st.title ( "⚡ FC Warmtepomp Calculator (v%.1f)  %s" % ( Version, Datum ) )
  
  # **************************************************
  # Model in session_state
  # **************************************************
  #model = EnergieModel ()
  # Initialiseer de klasse EENMALIG per unieke gebruiker in zijn eigen session_state
  if "model" not in st.session_state:
    st.session_state.model = EnergieModel()
  # Roep vanaf nu alle functies aan via het session_state object
  #st.session_state.model.create_sliders()
  
  # Als je ergens anders in je code (buiten de class) de prijs nodig hebt, 
  # lees je die zo uit:
  # prijs = st.session_state.model.sl_elek_prijs
  # **************************************************
  # **************************************************
  
  Col_Left, Col_Right = st.columns ( [ 1, 1.8 ] )
  
  with Col_Left:
    st.session_state.model.create_table_energie_verbruik ()
    st.session_state.model.create_sliders ()
    st.session_state.model.create_PV_Opwek ()
    st.session_state.model.create_table_vaste_kosten ()
      
  #********************************************************************
  #********************************************************************
  st.session_state.model.run_calculations ()
  #********************************************************************
  #********************************************************************
    
  with Col_Right :
    st.session_state.model.create_chart ()
    
    # *************************************************************
    # Het werken met een key werkt veel beter 
    # dan het resultaat in ee variable st.session_state.Incl_Elektra op te slaan
    # *************************************************************
    st.toggle ( "Dit knopje heeft nog geen betekenis"
      ,help = "Kosten Inclusief alle Elektra, anders enkel verwarmingskosten, vaste Elektra kosten worden nooit meegenomen"
      ,key  ="Incl_Elektra"
      )

    st.session_state.model.create_table_output ()
    st.session_state.model.create_table_installatie ()

    # FIX: Haal de benodigde dictionaries VEILIG op uit de state VOORDAT de achtergrond-thread start
    state_verbruik = dict ( st.session_state.init_verbruik )
    state_vast     = dict ( st.session_state.init_vast )
    state_wp       = dict ( st.session_state.init_wp )

    # Maak de JSON data live aan voor de downloadknop
    json_data_string = st.session_state.model.export_to_json ()

    # Geef de veilige data mee via een argumentloze lambda naar de export_to_pdf
    col_json_0, col_json1, col_json2 = st.columns ( 3 )
    #col_json_0, col_json1, col_json2 = st.columns ( [1,1,2] )

    # *************************************************************
    # We moeten ook de klasse-instantie zelf (het model) loskoppelen van de 
    # st.session_state voordat we de lambda-knop inladen. 
    # Door de variabele direct aan een lokale Python-variabele Safe_Model 
    # toe te wijzen in je hoofdprogramma, 
    # kan de achtergrond-thread er direct bij zonder de state te hoeven raadplegen.
    # *************************************************************
    Safe_Model = st.session_state.model
    with col_json_0 :
      st.download_button ( 
        label     = "📥 PDF Rapport",
        #data      = lambda: st.session_state.model.export_to_pdf(state_verbruik, state_vast, state_wp)
        # Verander dit bij de st.download_button aanroep:
        #data = lambda: st.session_state.model.export_to_pdf ( state_verbruik, 
        data = lambda: Safe_Model.export_to_pdf ( state_verbruik, 
                                           state_vast, 
                                           state_wp, 
                                           #st.session_state.model.df_grafiek_laatste )
                                           Safe_Model.df_grafiek_laatste )
                                           #st.session_state.df_grafiek_laatste)
        # (Of als de dataframe buiten session_state leeft, vul hier de variabele in die je voor het scherm gebruikt, bijv: self.df_grafiek_laatste)
       ,file_name = "Warmtepomp_Berekening_Rapport.pdf"
       ,mime      ="application/pdf"
       ,type      ="primary"
       ,width     = "stretch"
    )

    with col_json1 :
      st.download_button (
        label     = "📤 Exporteer Data",
        data      = json_data_string,
        file_name = "warmtepomp_model_instellingen.json",
        mime      = "application/json",
        width     = "stretch"
      )
        
    with col_json2 :
      # Een compacte file uploader die alleen naar .json bestanden zoekt
      geupload_bestand = st.file_uploader (
        "Importeer Data (JSON)", 
        type             = [ "json" ], 
        width            = "stretch",
        label_visibility = "collapsed" #"visible" 
      )
      if geupload_bestand is not None :
        st.session_state.model.import_from_json ( geupload_bestand )

  #********************************************************************
  #********************************************************************
  # DIT MAG NIET HIER STAAN, 
  # WANT DE self.Results MOET ER AL ZIJN
  #st.session_state.model.run_calculations ()
  #********************************************************************
  #********************************************************************

  # nog wat tekst / toelichting
  line  = ''
  line += 'Overweeg een lening met goede voorwaarden en tegen lage rente (zelfs 0% voor lage inkomens) <a href="https://www.warmtefonds.nl/" target="a">Warmtefonds</a>. '
  line += '<br>Free BSD license(c) 2026, designed by <a href="mailto:Frans.Cremers@RadboudUMC.nl">Frans Cremers</a>'
  line += ', created by <a href="mailto:Stef.Mientki@gmail.com">Stef Mientki</a>'
  
  line += '<br>Verwarmingskosten per jaar/maand'
  line += ', Gas : Vastrecht + Verbruikskosten'
  line += ', Elektra: Verbruikskosten'
  line += '<br>Dit zijn steeds de gemiddelde kosten over 1 jaar (dus het eerste jaar zijn die kosten lager)'
  line += ', zie verder <a href="https://stef-aap.github.io/EnergieContract/">Help Info</a>'
  
  line += '<br><br>Rente, Weerstation worden nog niet meegenomen.'
  line += '<br>rapport moet nog gecontroleerd worden.'
  line += ' Import tolt rond.'
  st.html ( line )

# ****************************************************************************
# ****************************************************************************
# Main program
# ****************************************************************************
# ****************************************************************************
if __name__ == "__main__":
  
  Tests = []
  
  if 1 in Tests :
    Year = 2024
    
    DF = Get_KNMI_Uur_QT ( Year, Station = 375 )
    print ( DF.sum() )
  
    from Zon_History import KNMI_Get_QT_Year
    DF2 = KNMI_Get_QT_Year ( Year, Station = "Volkel" )
    print ( DF2.sum() )
  
    This_Is_The_End
    
  
  main()
       

# ****************************************************************************
# ****************************************************************************
#  - Save File
#  - run hier in spyder (dan staat de omgeving goed)
#  - voer dan hier het volgende commando uit
#      !streamlit run St_Warmtepomp.py
# ****************************************************************************
# ****************************************************************************

