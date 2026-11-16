#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 17 20:36:32 2026

ToDo
  - als slim WarmtePomp gebruik, dan moet WP_Beta_Hour opnieuw gecalibreerd worden na de slinne struring
  - accu laden en ontladen met verlies
  - accu ontladen tot een bepaald minimum
  - werkt extra PV-panelen wel ?
  - extra cachen voor streamlit ??
  - default values in Case zetten als ze ontbreken ???

Version = 0.3  # 09-11-2026
  - gereed om te testen ij Streamlit
  
Version = 0.2  # 30-10-2026
  - slechts 1 optimalisatie over: base, alfa, stookgrens
  - Version toegevoegd

Version = 0.1  # 13-10-2026, orignal release
"""

Version = 0.3    # 09-11-2026

kWh_from_m3 = 9  # aantal kWh dat equivalent is met 1 m3 gas

import numpy          as     np
import pandas         as     pd
from   scipy.optimize import minimize


# ***********************************************************************
# ***********************************************************************
class Dict_prop ( dict ) :
  def __getattr__ ( self, key ) :
    try :
      return self [ key ]
    except KeyError :
      raise AttributeError ( f"'PropertyDict' object has no attribute '{key}'" )

  def __setattr__ ( self, key, value ) :
    # Voorkom dat we interne Python-attributen per ongeluk in de dict zetten
    if key.startswith ( '_' ) :
      super().__setattr__ ( key, value )
    else :
      self [ key ] = value

  def __delattr__ ( self, key ) :
    if key.startswith ( '_' ) :
      super().__delattr__ ( key )
    else :
      try :
        del self [ key ]
      except KeyError :
        raise AttributeError ( f"'PropertyDict' object has no attribute '{key}'" )

  # NIEUW: Zorgt ervoor dat .copy() een echte PropertyDict teruggeeft
  def copy ( self ) :
    return Dict_prop ( self )


# ***********************************************************************
# ***********************************************************************
def Optimize_Base_Alfa_Stookgrens ( Year
                                   ,Levering_kWh_pj 
                                   ,Terug_kWh_pj
                                   ,*
                                   ,PV_kWh_pj  = 0
                                   ,Dag_ipv_Uur_Temp = True #True lijkt wat beter
                                   ,Do_Print = False
                                  ) :
            
  # **********************************************
  # 3. DE GEAVANCEERDE OPTIMALISATIE-FUNCTIE
  # **********************************************
  def loss_function_3 ( params ) :
    # We optimaliseren de volgende 3 variabelen!
    base_kWh_pd, alpha_kWh_GD, stookgrens = params
    
    # Bereken de graaduren per uur op basis van de vliegende stookgrens
    # Als de buitentemperatuur boven de stookgrens ligt, zijn de graaduren 0
    graaduren_per_uur = np.maximum ( 0, stookgrens - Temperatuur_Hour )
    
    # Verbruik per uur = (Basisverbruik per dag / 24) + (alpha * graaduren van dat uur)
    V_Hour = ( base_kWh_pd / 24 ) + ( alpha_kWh_GD * graaduren_per_uur )
    
    # Netto interactie per uur berekenen
    L_sim = np.maximum ( 0, V_Hour  - PV_Hour )
    T_sim = np.maximum ( 0, PV_Hour - V_Hour  )
    
    # Jaartotalen
    L_sim_totaal = np.sum ( L_sim )
    T_sim_totaal = np.sum ( T_sim )
    
    # Foutfunctie (kwadratisch verschil)
    fout_levering      = ( L_sim_totaal - Levering_kWh_pj ) ** 2
    fout_teruglevering = ( T_sim_totaal - Terug_kWh_pj    ) ** 2
    
    return fout_levering + fout_teruglevering

  # **********************************************
  DF = Prepare_KNMI_Data ( Year )
  Zon_Radiation_Hour = DF [ 'W_hor'    ].to_numpy()
  if Dag_ipv_Uur_Temp :
    Temperatuur_Hour = DF [ 'Temp_Dag' ].to_numpy()
  else :
    Temperatuur_Hour = DF [ 'Temp_Uur' ].to_numpy()
  
  # PV-opbrengst per uur schalen
  Zon_Radiation_Tot = np.sum ( Zon_Radiation_Hour )
  PV_Hour           = ( Zon_Radiation_Hour / Zon_Radiation_Tot ) * PV_kWh_pj

  # **********************************************
  # **********************************************
  # start en grenzen base_kWh_pd    alpha_kWh_GD      stookgrens
  initial_guess = [     7.6          , 0.002          , 14.0       ]
  bounds        = ( (0, None)      , (0, None)       , (8.0, 18.0) )
  
  # Optimalisatie uitvoeren
  result = minimize ( loss_function_3
                     ,initial_guess
                     ,bounds           = bounds
                     ,method           = 'L-BFGS-B'
                    )
  Base_kWh_pd, Alfa_kWh_GD, Stookgrens = result.x

  # 1. Bereken de graaduren correct per uur (stookgrens - buitentemp, met een ondergrens van 0)
  if Dag_ipv_Uur_Temp :
    DF [ "Graaduren" ] = np.maximum ( 0, Stookgrens - DF [ "Temp_Dag" ] )
  else :
    DF [ "Graaduren" ] = np.maximum ( 0, Stookgrens - DF [ "Temp_Uur" ] )
    
  # 2. Bereken het verbruik per uur: ( base / 24 ) + ( alfa * graaduren )
  DF [ "Verbruik"  ] = ( Base_kWh_pd / 24 ) + ( Alfa_kWh_GD * DF [ "Graaduren" ] )

  # ***************************************
  # Bereken PV, Levering en Terug per uur
  # ***************************************
  DF [ "PV"       ] = DF [ "W_hor"] * PV_kWh_pj / DF.W_hor.sum()
  Netto             = DF [ "Verbruik" ] - DF [ "PV" ]
  DF [ "Levering" ] =     Netto  .clip ( lower=0 )
  DF [ "Terug"    ] = ( - Netto ).clip ( lower=0 )
  
  # ==========================================
  # 5. RESULTATEN TONEN
  # ==========================================
  if Do_Print and result.success :
    print("\n==========================================")
    print("--- Uurlijkse Optimalisatie Geslaagd --- Loss_function-3")
    print("==========================================")
    print(f"Optimale Base (basisverbruik per dag) :  {Base_kWh_pd:.3f} kWh/dag")
    print(f"Optimale alpha (per graaduur)         :  {24*Alfa_kWh_GD:.5f} kWh/graadag")
    print(f"Berekende Stookgrens van de woning    : {Stookgrens:.2f} °C")
    print(f"Verhouding Base / Alfa in dit model   :  {Base_kWh_pd / (24*Alfa_kWh_GD):.2f}")
    
    # Controlemeting van de fit
    GraadUren_Hour = np.maximum ( 0, Stookgrens - Temperatuur_Hour )
    v_uur_opt = ( Base_kWh_pd / 24) + ( Alfa_kWh_GD * GraadUren_Hour )
    L_sim_opt = np.sum(np.maximum ( 0, v_uur_opt - PV_Hour ))
    T_sim_opt = np.sum(np.maximum ( 0, PV_Hour - v_uur_opt))
    
    Eigen_Verbruik = 100 * ( PV_kWh_pj - Terug_kWh_pj ) / PV_kWh_pj
    print("\n--- Controle Jaartotalen ---")
    print(f"Levering      -> Werkelijk : {Levering_kWh_pj:.0f} kWh | Gesimuleerd    : {L_sim_opt:.0f} kWh")
    print(f"Teruglevering -> Werkelijk : {Terug_kWh_pj:.0f} kWh | Gesimuleerd    : {T_sim_opt:.0f} kWh")
    print(f"PV            -> Werkelijk : {PV_kWh_pj:.0f} kWh | Eigen Verbruik : {Eigen_Verbruik:.0f} %" )


    print(f"Elektra Jaarverbruik       : {int ( DF [ 'Verbruik' ].sum () )} kWh")
  
  #else:
  #  print("Optimalisatie mislukt:", result.message)
  return DF, Base_kWh_pd, Alfa_kWh_GD, Stookgrens  
 

# ***********************************************************************
# ***********************************************************************
def Prepare_KNMI_Data ( Year ):
  # ==========================================
  # 2. DATA INLADEN
  # ==========================================
  DF = pd.read_csv ( 'KNMI_QT_%i_Volkel.csv' % Year, sep=';' )
  DF [ 'DateTime' ] = pd.to_datetime ( DF [ 'DateTime' ] )
  # Maak een pure datum-kolom om per dag te kunnen groeperen
  ## 3b werkt slecht:  DF  ['Date' ] = DF [ 'DateTime' ].dt.date
  # INDEX ?????????????????????????????
  DF.set_index ( "DateTime", inplace=True )

  # ==========================================
  # Speciaal voor 3 params en daggemiddelde GraadUren
  # ==========================================
  # Bereken de gemiddelde buitentemperatuur PER DAG = Temp_Dag
  # .transform('mean') zorgt ervoor dat de 24 uren van dezelfde dag allemaal dit daggemiddelde krijgen
  ## 3b werkt slecht: DF['T_dag_gemiddeld'] = DF.groupby('Date')['Temp'].transform('mean')
  if True :
    DF [ 'Date'            ] = DF.index.date
    #DF [ 'T_dag_gemiddeld' ] = DF.groupby ( 'Date' )[ 'Temp' ].transform ( 'mean' )
    #DF.rename ( columns = { "Temp": "Torg", "T_dag_gemiddeld": "Temp" }, inplace=True )
    DF [ 'Temp_Dag' ] = DF.groupby ( 'Date' )[ 'Temp' ].transform ( 'mean' )
    DF.rename ( columns = { "Temp": "Temp_Uur" }, inplace=True )
  # Speciaal voor 3 params en daggemiddelde GraadUren
  ## 3b werkt slecht:   t_dag_gemiddeld_uur = DF['T_dag_gemiddeld'].to_numpy() # 8784 waarden, maar constant per dag
  # ==========================================
  # Einde Speciaal voor 3 params et daggemiddelde GraadUren
  # ==========================================
  
  DF [ "Hour" ] = DF.index.hour
  return DF
  

# ***********************************************************************
# Converteert Uurdata naar Maand data
# en als een Filename is opgegeven, (File met echte maanddata)
# dan worden deze kolommen toegevoegd
# Met name bedoeld op berekende resultaten te vergelijken met echte metingen
# ***********************************************************************
def Make_Month_Data ( DF, Filename = None ) :
  # Groepeer per maand en som alle kolommen, resultaat op MS=start, ME=eind
  DF_M = DF.resample ( 'ME' ).sum ( numeric_only=True ).round().astype(int)
  #print ( DF_M )

  if Filename : 
    # ***************************
    # Vergelijk met ECHTE data
    # ***************************
    RM       = pd.read_csv ( Filename )
    RM.set_index ( "DateTime", inplace=True )  
    RM.index = pd.to_datetime ( RM.index )
    #print ( RM )
    #  deze data bevat geen fractie, dus geen afkapping
    #DF_M [ "EL_Lever" ] = RM [ "EL_Lever" ].round().astype(int)
    DF_M [ "EL_Lever" ] = RM [ "EL_Lever" ].astype(int)
    DF_M [ "EL_Terug" ] = -RM [ "EL_Terug" ].astype(int)
    DF_M [ "EL_Gas"   ] = RM [ "EL_Gas"   ].astype(int)
    #print ( DF_M )
    Title = "Lever=%i,  Terug=%i,   PV=%i,  Base=%.2f,  alfa=%.2f,   Stook=%.1f" % (
             Levering_kWh_pj, Terug_kWh_pj, PV_kWh_pj, Base, Alfa, Stookgrens )
    ax = DF_M.plot ( y="Levering,EL_Lever,Terug,EL_Terug".split(','), grid=True, title=Title )
  
  return DF_M


# ***********************************************************************
# ***********************************************************************
def Add_Accu_WP_PV ( Case:Dict_prop, DF, *, Do_Print = False ) :

  Accu_Verlies = Case.Accu_RTE ** 0.5  #verdeel verlies gelijkelijk over laden en ontladen
  N_Hour       = len ( DF )

  Zon_Radiation_Hour = DF [ 'W_hor'    ].to_numpy ()
  Temperatuur_Hour   = DF [ 'Temp_Dag' ].to_numpy ()
  """
  if Dag_ipv_Uur_Temp :
    Temperatuur_Hour   = DF [ 'Temp_Dag'  ].to_numpy ()
  else :
    Temperatuur_Hour   = DF [ 'Temp_Uur'  ].to_numpy ()
  #"""

  # PV-opbrengst per uur schalen
  Zon_Radiation_Tot  = np.sum ( Zon_Radiation_Hour )
  PV_Hour            = ( Zon_Radiation_Hour / Zon_Radiation_Tot) * Case.PV_kWh_pj

  # Bereken de graaduren per uur
  GraadUren_Hour              = np.maximum ( 0, Case.StookGrens - Temperatuur_Hour )
  Elektra_Non_Verwarming_Hour = ( Case.Base_kWh_pd / 24 ) + ( Case.Alfa_kWh_GD * GraadUren_Hour )
  Elektra_Tot_Hour            = Elektra_Non_Verwarming_Hour
  WP_Beta                     = 0
  
  # *********************************************************************
  # Bereken WP-stroomverbruik en resterende GasVerbruik
  # *********************************************************************
  WP_kWh_pj = Case.WP_Hybride * Case.Gas_m3_pj * kWh_from_m3 / Case.WP_SCOP
  Gas_m3    = ( 1- Case.WP_Hybride ) * Case.Gas_m3_pj
  
  
  # *********************************************************************
  # Toevoegen van Warmtepomp die (een deel van) het gas vervangt
  # Base en Alhpa blijven gelijk,
  # extra Warmtepomp verbruik is alleen afhankelijk van graaduren
  # *********************************************************************
  if WP_kWh_pj > 0 :
    # =====================================================================
    # BEREKENING VAN DE NIEUWE VERBRUIKSREEKS
    # =====================================================================
    WP_Beta      = WP_kWh_pj / sum ( GraadUren_Hour )
    # Dynamische Beta bepalen per uur voor de warmtepomp
    WP_Beta_Hour = np.full ( len ( DF ), WP_Beta )
    
    # ************************************************
    # Slim gebruik van de warmtepomp, Levert niet zo veel op
    # ************************************************
    """
    if WP_Slim :
      # SLIMME STRATEGIE: Huis voorverwarmen met zon (bijv. tussen 12:00 en 16:00 uur)
      PRE_HEAT_FACTOR   = 1.3       # Overdag 30% harder draaien (hogere binnentemperatuur)
      NIGHT_DROP_FACTOR = 0.8     # 's Nachts/avond 20% minder hard draaien (uitgezakt huis)

      # Tussen 12:00 en 16:00 (uur 12, 13, 14, 15) draait de WP harder
      #overdag_mask =  ( DF['Hour'] >= 12 ) & ( DF [ 'Hour'] < 16 )
      overdag_mask =  ( DF [ 'Hour'] >= 10 ) & ( DF [ 'Hour' ] < 16 )
      WP_Beta_Hour [ overdag_mask ] = WP_Beta * PRE_HEAT_FACTOR
      #overdag_mask =  ( DF [ 'Hour' ] < 6 )
      #WP_Beta_Hour [ overdag_mask ] = WP_Beta * PRE_HEAT_FACTOR
      
      # In de nacht en vroege ochtend (00:00 - 06:00) en avond (18:00 - 24:00) mag hij lager
      rust_mask = ( DF [ 'Hour' ] < 6 ) | ( DF [ 'Hour' ] >= 18 )
      #rust_mask = ( DF [ 'Hour' ] >= 18 )
      WP_Beta_Hour [ rust_mask ] = WP_Beta * NIGHT_DROP_FACTOR
    #"""
    
    # 3. Het extra verbruik van de warmtepomp per uur
    Elektra_WP_Hour  = WP_Beta_Hour * GraadUren_Hour
    Elektra_Tot_Hour = Elektra_Non_Verwarming_Hour + Elektra_WP_Hour

    #print ( "Warmtepomp Elektra         : %i kWh   (Beta = %.4f)" % (round ( sum ( Elektra_WP_Hour )), WP_Beta ))

  # =====================================================================
  # Uurverwerking van Accu in Nul-Op-De-Meter mode
  # =====================================================================
  E_Lever_met_Accu_Hour = np.zeros ( N_Hour )
  E_Terug_met_Accu_Hour = np.zeros ( N_Hour )
  Accu_Lading      = 0.0
  
  for Hour in range( N_Hour ):
    # Hier vergelijken we continu het TOTALE verbruik (Base + CV + WP) met de PV opwek
    Verbruik = Elektra_Tot_Hour [ Hour ]
    Opwek    = PV_Hour          [ Hour ]
    
    if Opwek > Verbruik:
      # Er is een netto overschot over na HEEL het huishouden
      Overschot = Opwek - Verbruik
      Ruimte_in_Accu = Case.Accu_kWh - Accu_Lading
      Max_te_Laden = min ( Overschot, Case.Accu_max_Laad_kW, Ruimte_in_Accu / Case.Accu_RTE )
      
      Accu_Lading += Max_te_Laden * Case.Accu_RTE  # nu even alle verlies in laden
      E_Terug_met_Accu_Hour [ Hour ] = Overschot - Max_te_Laden
      E_Lever_met_Accu_Hour [ Hour ] = 0.0
    else:
      # Er is een tekort
      Tekort = Verbruik - Opwek
      Max_te_Ontladen = min ( Tekort, Case.Accu_max_Ontlaad_kW, Accu_Lading )
      
      Accu_Lading -= Max_te_Ontladen
      E_Lever_met_Accu_Hour [ Hour ] = Tekort - Max_te_Ontladen
      E_Terug_met_Accu_Hour [ Hour ] = 0.0

  # Jaarsommen na accu-interactie
  E_Lever_met_Accu_Tot = round ( np.sum ( E_Lever_met_Accu_Hour ) )
  E_Terug_met_Accu_Tot = round ( np.sum ( E_Terug_met_Accu_Hour ) )

  # Bereken ook de situatie zonder accu (maar met eventuele extra panelen) voor de vergelijking
  E_Lever_zonder_Accu_Tot = round ( np.sum ( np.maximum ( 0, Elektra_Tot_Hour - PV_Hour )))
  E_Terug_zonder_Accu_Tot = round ( np.sum ( np.maximum ( 0, PV_Hour - Elektra_Tot_Hour )))
  
  # =====================================================================
  # 6. EXCLUSIEVE WARMTEPOMP-ZON STATISTIEKEN BEREKENEN
  # =====================================================================
  # Om te zien hoeveel zon direct in de WP gaat, vergelijken we de totale situatie
  # met de situatie waarin de WP er niet was geweest (de oude CV-situatie)
  direct_eigen_verbruik_totaal = np.minimum(Elektra_Tot_Hour, PV_Hour )
  direct_eigen_verbruik_cv     = np.minimum(Elektra_Non_Verwarming_Hour, PV_Hour )
  zonstroom_direct_naar_wp     = direct_eigen_verbruik_totaal - direct_eigen_verbruik_cv
  
  # =====================================================================
  # 7. FINANCIËLE CONTROLE EN RAPPORTAGE
  # =====================================================================
  Elektra_Prijs_Jaar  = ( E_Lever_met_Accu_Tot * Case.Elektra_Prijs ) - \
                        ( E_Terug_met_Accu_Tot * Case.Terug_Prijs   )
  Elektra_Prijs_Jaar += Case.Elektra_Vastrecht_pj
  
  if Gas_m3 > 0 :
    Gas_Prijs_Jaar = Case.Gas_Vastrecht_pj + Gas_m3 * Case.Gas_Prijs
  else :
    Gas_Prijs_Jaar = 0
  
  Totaal_Prijs_Jaar = Elektra_Prijs_Jaar + Gas_Prijs_Jaar

  # ********************************************************************
  # ********************************************************************
  Case.Lever_Calc_kWh_pj = E_Lever_met_Accu_Tot
  Case.Terug_Calc_kWh_pj = E_Terug_met_Accu_Tot
  Case.Gas_Calc_m3_pj    = Gas_m3

  Case.Eigen_Verbruik = 100 * ( Case.PV_kWh_pj - E_Terug_met_Accu_Tot ) / Case.PV_kWh_pj
  
  # ********************************************************************
  # ********************************************************************
  if Do_Print :
    print("\n=======================================================")
    print("--- Warmtepomp & ThuisAccu & Extra PV ---")
    print("=======================================================")
    if WP_kWh_pj > 0 :
      print ( "Warmtepomp Elektra  : %i kWh   (Hybr=%.1f   SCOP=%.1f   Beta = %.4f)" % (
        round ( sum ( Elektra_WP_Hour )), Case.WP_Hybride, Case.WP_SCOP, WP_Beta ))
      #print(f"Warmtepomp status   : Actief ( {WP_kWh_pj:.0f} kWh/jaar     Beta={WP_Beta:.5f} )" )
      print(f"Slimme WP-sturing   : {'JA' if Case.WP_Slim else 'NEE'}")
    print(f"Thuisbatterij       : {Case.Accu_kWh:.1f} kWh")
    #print(f"Zonnepanelen totaal : {Case.PV_kWh_pj:.0f} kWh/jaar")
    
    #print("\n--- Energetische Balans (kWh/jaar) ---")
    #print(f"Bruto basisverbruik woning : {np.sum(Elektra_Non_Verwarming_Hour):4.0f} kWh/jaar")
    #if WP_kWh_pj > 0 :
    #  print(f"Elektra WP berekend  : { np.sum(Elektra_WP_Hour ):4.0f} kWh/jaar")
    #  print(f"Totaal bruto jaarverbruik  : {np.sum(Elektra_Tot_Hour):4.0f} kWh/jaar")
    
    Zelf_Zonder = round ( 100 * ( Case.PV_kWh_pj - E_Terug_zonder_Accu_Tot ) / Case.PV_kWh_pj )
    Zelf_Met    = round ( 100 * ( Case.PV_kWh_pj - E_Terug_met_Accu_Tot    ) / Case.PV_kWh_pj )
  
    print( "\n--- Verbruik  Zonder   |  MET Accu    | ZelfGebruik")
    print( "Elektra   : %4i kWh   |  %4i kWh    |   %i %%" % ( 
      E_Lever_zonder_Accu_Tot, E_Lever_met_Accu_Tot, Zelf_Zonder ))
    print( "Terug     : %4i kWh   |  %4i kWh    |   %i %%" % ( 
      E_Terug_zonder_Accu_Tot, E_Terug_met_Accu_Tot, Zelf_Met ))
    
    print("\n--- Warmtepomp & Zon-integratie Analayse ---")
    print(f"WP stroom direct gedekt door dak-zon  : {np.sum(zonstroom_direct_naar_wp):.0f} kWh")
    if WP_kWh_pj > 0 :
      WP_sum = np.sum(Elektra_WP_Hour) 
      print(f"Percentage WP gedekt door directe zon : {(np.sum(zonstroom_direct_naar_wp)/WP_sum)*100:.1f} %")
    
    print ("\n--- Kosten   Jaar    |    Maand")
    print ( "Elektra   : € %4.0f   |   € %4.0f" % ( Elektra_Prijs_Jaar, Elektra_Prijs_Jaar / 12 ) )
    print ( "Gas       : € %4.0f   |   € %4.0f" % ( Gas_Prijs_Jaar    , Gas_Prijs_Jaar     / 12 ) )
    print ( "Totaal    : € %4.0f   |   € %4.0f" % ( Totaal_Prijs_Jaar , Totaal_Prijs_Jaar  / 12 ) )
  
    print("=======================================================")
  
  return Case.Lever_Calc_kWh_pj, Case.Terug_Calc_kWh_pj, Case.Gas_Calc_m3_pj

  
# ***********************************************************************
# ***********************************************************************
def Calc_Energie ( Case: Dict_prop, Do_Print = False ) :
  DF, Base_kWh_pd, Alfa_kWh_GD, StookGrens = \
    Optimize_Base_Alfa_Stookgrens ( 
       Year            = Case.Year
      ,Levering_kWh_pj = Case.Afname_kWh_pj
      ,Terug_kWh_pj    = Case.Terug_kWh_pj
      ,PV_kWh_pj       = Case.PV_kWh_pj
      ,Do_Print        = Do_Print
    )

  Case.WP_kWh          = Case.WP_Hybride * Case.Gas_m3_pj * kWh_from_m3  / Case.WP_SCOP
  Case.Base_kWh_pd     = Base_kWh_pd
  Case.Alfa_kWh_GD     = Alfa_kWh_GD
  Case.StookGrens      = StookGrens

  Lever, Terug, Gas = Add_Accu_WP_PV ( Case, DF, Do_Print = Do_Print )
  if Do_Print :
    print ( "Lever = %i kWh    Terug = %i kWh    Gas = %i m3" % (
             Lever, Terug, Gas ))
  return Lever, Terug, Gas


def Main_Start () :  pass
""" *********************************************************************
# ***********************************************************************
# Main program
# ***********************************************************************
# ********************************************************************"""
if __name__ == "__main__" :
  Tests = [1]

  # ********************************************************************
  # Optimalisatie loss function 3
  # zou zo bruikbaar moeten zijn in streamlit
  # misschien nog wat cahen toevoegen
  # ********************************************************************
  if 1 in Tests :
    # *****************************************
    Energie_Case = Dict_prop ()
    # *****************************************
    Energie_Case.Year                 = 2024        # 2024
    
    Energie_Case.Afname_kWh_pj        = 1900        # 1900 kWh
    Energie_Case.Terug_kWh_pj         = 1700        # 1700 kWh
    
    Energie_Case.PV_kWh_pj            = 2600        # 2600 kWh
    Energie_Case.PV_kWh_Extra_pj      = 0           #    0 kWh
    
    Energie_Case.WP_Hybride           = 0.5         # 0=CV_ketel, 1=Full_Electric
    Energie_Case.WP_SCOP              = 4.0         # 4.0
    Energie_Case.WP_Slim              = False       # False
    
    Energie_Case.Accu_kWh             = 0           # 5.0 kWh
    Energie_Case.Accu_RTE             = 0.92 ** 2   # 0.85
    Energie_Case.Accu_max_Laad_kW     = 2.5         # 2.5 kW
    Energie_Case.Accu_max_Ontlaad_kW  = 0.8         # 0.8 kW
    Energie_Case.Accu_min_SOC         = 12          # 12%
    
    Energie_Case.Gas_m3_pj            = 1200        # 1200 m3
    
    Energie_Case.Elektra_Vastrecht_pj = 480         # € 490 = Leverancier + Netkosten
    Energie_Case.Gas_Vastrecht_pj     = 270         # € 270 = Leverancier + Netkosten
    Energie_Case.Elektra_Prijs        = 0.40        # € 0.40 all in prijs      per kWh
    Energie_Case.Terug_Prijs          = 0.02        # € 0.02 all in vergoeding per kWh
    Energie_Case.Gas_Prijs            = 2.00        # € 2.00 per m3

    for Energie_Case.WP_Hybride in [ 0, 0.5, 1 ] :
      Lever, Terug, Gas = Calc_Energie ( Energie_Case, Do_Print = True ) 
 
