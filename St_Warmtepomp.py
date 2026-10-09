#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version 1.1   6-10-2026
  - Lay out, alle componenten aanqwezig
  
Version 0.9 - DEEL 1 - Fix voor printen, tabel-zichtbaarheid en balk-nulpunt
"""
version = 1.1

from   datetime          import datetime, timedelta
import streamlit         as st
import pandas            as pd
import plotly.express    as px
import requests


# 1. INITIALISEER DE CONFIGURATIE EN DWING LICHT THEMA AF VOOR STABIELE PRINTS
st.set_page_config(
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
    "PV Opbrengst [kWh]"         : 2800, 
    "Capaciteit ThuisAccu [kWh]" : 0,
    "Zonneboiler [kWh]"          : 0, 
    "Elektrische Auto [kWh]"     : 0
  }

if "init_vast" not in st.session_state :
  st.session_state.init_vast = {
    "Leen Rente"                 : 5.2, 
    "Spaar Rente"                : 2.1, 
    "Vastrecht Elektra"          : 456, 
    "Vastrecht_Gas"              : 200, 
    "Teruggave EnergieBelasting" : 635
  }

if "init_wp" not in st.session_state :
  st.session_state.init_wp = {
    "Installatie": [
       "Aanschaf Prijs [€]", 
       "OnderhoudsKosten [€]", 
       "Aanschaf Jaar", 
       "Levensduur [jaren]", 
       "SCOP", 
       "Aandeel Verwarming [%]" ],
    "CV" : [  2000, 100, 2024, 15, 1.0,   0 ],   
    "WP1": [  4500, 100, 2024, 15, 4.5,  60 ],  
    "WP2": [  6000, 100, 2024, 15, 4.0,  80 ],  
    "WP3": [ 12000, 100, 2024, 15, 5.0, 100 ], 
  }


# *****************************************************************************
# Haalt uurgegevens Temperatuur en Zon-Instraling 
# over de geselecteerde periode bij het KNMI
#   (simpele versie afgeleid van Get_KNMI_Uur_Data)
# *****************************************************************************
@st.cache_data # Zorgt ervoor dat Streamlit het bestand onthoudt en niet bij elke klik opnieuw downloadt
def Get_KNMI_Uur_QT ( Jaar, Station = 375 ) :
  URL   = 'https://www.daggegevens.knmi.nl/klimatologie/uurgegevens'
  Start = f"{Jaar}0101"
  End   = f"{Jaar+1}0101"
  Pars  = { 'start': Start,
            'end'  : End,
            'vars' : "T:Q",
            'stns' : Station,
            'fmt'  : "json"
          }
  Response = requests.post ( URL, data = Pars )    
  Data     = pd.DataFrame ( Response.json() )
  
  # ***********************************************************
  # Strip timezone information from datetime
  # ***********************************************************
  def Calc_date ( Row ):
    return Row.date [:10].replace ( '-', '' )
  Data [ "date" ] = Data.apply ( lambda row: Calc_date ( row ), axis=1 )

  Data = Data.rename ( columns = { "date" : "YYYYMMDD",
                                   "T"    : "Temp",
                                   "Q"    : "Zon_Wh",
                                 } )
  Data.drop ( columns = [ "station_code" ], inplace=True )

  # ***********************************************************
  # Set index
  # ***********************************************************
  def Calc_DateTime ( Row ) :
    Result = datetime.strptime ( str( int ( Row.YYYYMMDD ) ), "%Y%m%d")
    return Result + timedelta ( hours = Row.hour-1 )
  # ***********************************************************
  Data [ "DateTime" ] = Data.apply ( lambda row: Calc_DateTime ( row ), axis=1 )
  Data.set_index ( "DateTime", inplace=True )
  Data.drop ( columns = "YYYYMMDD,hour".split(','), inplace=True )

  # ***********************************************************
  # Selecteer het gewenste tijdblok
  # ***********************************************************
  Data = Data [ ( Data.index >= Start ) & ( Data.index < End ) ]
 
  # ***********************************************************
  # Converteer Values
  # ***********************************************************
  Data [ "Zon_Wh" ] =       Data [ "Zon_Wh" ] / 0.360
  Data [ "Temp"   ] = 0.1 * Data [ "Temp"   ]

  return Data


# ****************************************************************************
# ****************************************************************************
class EnergieModel:
  def __init__(self):
      pass
      
  # **************************************************************************
  # **************************************************************************
  def get_value_verbruik(self, item):
      if "editor_verbruik" in st.session_state and "edited_rows" in st.session_state.editor_verbruik:
          edited = st.session_state.editor_verbruik["edited_rows"]
          keys = list(st.session_state.init_verbruik.keys())
          for idx, changes in edited.items():
              if keys[idx] == item and "Waarde" in changes:
                  return changes["Waarde"]
      return st.session_state.init_verbruik[item]

  # **************************************************************************
  # **************************************************************************
  def create_sliders(self):
      col_1, col_2 = st.columns(2)
      
      # Check of er zojuist een JSON-bestand is ingeladen, anders pakken we de standaardwaarden
      sl_load = st.session_state.get("load_sliders", {})
      
      with col_1:
          self.sl_elek_prijs = st.slider("Elektra Prijs (ct)", 10, 50, int(sl_load.get("elek_prijs", 31))) / 100
          self.sl_elek_delta = st.slider("Elektra Jaarlijkse Stijging (%)", 0, 10, int(sl_load.get("elek_delta", 2))) / 100  
          self.sl_terug_prijs = st.slider("Terug Prijs (ct)", 10, 50, int(sl_load.get("terug_prijs", 30))) / 100
      with col_2:
          self.sl_gas_prijs = st.slider("Gas Prijs (ct)", 50, 300, int(sl_load.get("gas_prijs", 168))) / 100
          self.sl_gas_delta = st.slider("Gas Jaarlijkse Stijging (%)", 0, 10, int(sl_load.get("gas_delta", 3))) / 100      
          self.sl_jaren     = st.slider("EvaluatiePeriode (Jaren)", 1, 30, int(sl_load.get("jaren", 10)))


  # **************************************************************************
  # **************************************************************************
  def get_value_vast(self, item):
      if "editor_vast" in st.session_state and "edited_rows" in st.session_state.editor_vast:
          edited = st.session_state.editor_vast["edited_rows"]
          keys = list(st.session_state.init_vast.keys())
          for idx, changes in edited.items():
              if keys[idx] == item and "Waarde" in changes:
                  return changes["Waarde"]
      return st.session_state.init_vast[item]

  # **************************************************************************
  # **************************************************************************
  def get_value_wp(self, rij, sys):
      if "editor_wp" in st.session_state and "edited_rows" in st.session_state.editor_wp:
          edited = st.session_state.editor_wp["edited_rows"]
          rijen = st.session_state.init_wp["Installatie"]
          for idx, col_changes in edited.items():
              if rijen[idx] == rij and sys in col_changes:
                  return col_changes[sys]
      rijen = st.session_state.init_wp["Installatie"]
      row_idx = rijen.index(rij)
      return st.session_state.init_wp[sys][row_idx]

  # **************************************************************************
  # **************************************************************************
  def create_table_energie_verbruik(self):
      df = pd.DataFrame({"Waarde": st.session_state.init_verbruik})
      df.index.name = "Energie Verbruik"
      kolom_instellingen = {"Waarde": st.column_config.NumberColumn(alignment="center")}
      st.data_editor(df, width="stretch", num_rows="dynamic", column_config=kolom_instellingen, key="editor_verbruik")    
      
  # **************************************************************************
  # **************************************************************************
  def create_table_vaste_kosten(self):    
      df = pd.DataFrame({"Waarde": st.session_state.init_vast})
      df.index.name = "Vaste Kosten"
      kolom_instellingen = {"Waarde": st.column_config.NumberColumn(alignment="center")}
      st.data_editor(df, width="stretch", num_rows="dynamic", column_config=kolom_instellingen, key="editor_vast")    

  # **************************************************************************
  # **************************************************************************
  def create_table_installatie(self):
      df = pd.DataFrame(st.session_state.init_wp).set_index("Installatie")
      kolom_instellingen = {col: st.column_config.NumberColumn(alignment="center") for col in ["CV", "WP1", "WP2", "WP3"]}
      st.data_editor(df, width="stretch", num_rows="dynamic", column_config=kolom_instellingen, key="editor_wp")
    
  # **************************************************************************
  # **************************************************************************
  def create_PV_Opwek ( self ) :
    # --- VOORBEELD HOE JE DIT TOEPAST ---
    #st.title("☀️ Zon Wh")
    
    #station_opties = {"De Bilt": 260, "Schiphol": 240, "Eindhoven": 370, "Groningen": 280, "Vlissingen": 310}
    station_opties = { "Volkel"     : 375 
                      ,"Arcen"      : 391  # mist historische data
                      ,"Horst"      : 392  # mist historische data
                      ,"De Bilt"    : 260
                      ,"Schiphol"   : 240
                      ,"Eindhoven"  : 370
                      ,"Groningen"  : 280
                      ,"Vlissingen" : 310 
                     }
    gekozen_station = st.selectbox("Kies een KNMI Weerstation", list(station_opties.keys()))
    
    with st.spinner("KNMI data over 8760 uren wordt opgehaald..."):
        #df_weer = download_knmi_uurgegevens_json(jaar=2025, station=station_opties[gekozen_station])
        df_weer = Get_KNMI_Uur_QT ( 2025, Station=station_opties [ gekozen_station ] )

    #st.success(f"Succesvol {len(df_weer)} uren aan data ingeladen!")
    #st.dataframe(df_weer.head(10), width="stretch")

  # **************************************************************************
  # **************************************************************************
  def run_calculations ( self ) :
    gas_verbruik        = self.get_value_verbruik("Gas [m3]")
    vastrecht_gas       = self.get_value_vast("Vastrecht_Gas")
    teruggave_belasting = self.get_value_vast("Teruggave EnergieBelasting")
    
    aanschaf_prijs_cv   = self.get_value_wp("Aanschaf Prijs [€]", "CV")
    levensduur_cv       = self.get_value_wp("Levensduur [jaren]", "CV")
    onderhoud_cv        = self.get_value_wp("OnderhoudsKosten [€]", "CV")
    
    self.kosten_overzicht = {}
    systemen = [ "CV", "WP1", "WP2", "WP3" ]
    
    for sys in systemen :
      aanschaf_prijs = self.get_value_wp("Aanschaf Prijs [€]", sys)
      levensduur     = self.get_value_wp("Levensduur [jaren]", sys)
      onderhoud      = self.get_value_wp("OnderhoudsKosten [€]", sys)
      scop           = self.get_value_wp("SCOP", sys)
      aandeel        = self.get_value_wp("Aandeel Verwarming [%]", sys) / 100 
      
      # Bruto aanschafkosten (altijd positief vanaf 0)
      aanschaf_jaarlijks = aanschaf_prijs / levensduur
      if aandeel < 1.0 and sys != "CV":
        aanschaf_jaarlijks += (aanschaf_prijs_cv / levensduur_cv)
      totaal_aanschaf = aanschaf_jaarlijks * self.sl_jaren
      
      # Bruto vaste kosten (altijd positief vanaf 0)
      vaste_kosten_jaarlijks = onderhoud
      if aandeel < 1.0 and sys != "CV":
        vaste_kosten_jaarlijks += (onderhoud_cv + vastrecht_gas)
      elif sys == "CV":
        vaste_kosten_jaarlijks += vastrecht_gas
      totaal_vaste_kosten = vaste_kosten_jaarlijks * self.sl_jaren
      
      # Bruto verbruikskosten
      totaal_verbruik = 0.0
      for j in range(self.sl_jaren):
        actuele_gasprijs = self.sl_gas_prijs * ((1 + self.sl_gas_delta) ** j)
        actuele_elekprijs = self.sl_elek_prijs * ((1 + self.sl_elek_delta) ** j)
        
        gas_deel = (1 - aandeel) * gas_verbruik * actuele_gasprijs
        if scop > 0:
          elek_deel = aandeel * gas_verbruik * 10 * actuele_elekprijs / scop
        else:
          elek_deel = 0
        totaal_verbruik += (gas_deel + elek_deel)
      
      # Bereken de totale korting van de Energiebelasting over de hele periode
      totaal_korting_belasting = teruggave_belasting * self.sl_jaren
      
      # Eindtotaal = Bruto som minus de belastingteruggave
      bruto_totaal = totaal_aanschaf + totaal_vaste_kosten + totaal_verbruik
      netto_totaal = bruto_totaal - totaal_korting_belasting
      netto_totaal = bruto_totaal
      
      self.kosten_overzicht[sys] = {
        "Aanschaf": totaal_aanschaf,
        "Vaste Kosten": totaal_vaste_kosten,
        "Verbruik": totaal_verbruik,
        "Korting Belasting": totaal_korting_belasting,
        "Totaal": netto_totaal
      }
      #print ( "Gas=%i  GasDeel=%i   EDeel=%i" % ( 
      #  gas_verbruik, gas_deel, elek_deel ) )
      
    #print ( "Calculations ran" )
      
      
      

  # **************************************************************************
  # **************************************************************************
  def create_table_output ( self ) :
    data_items = [ "Kosten per Maand avg [€]", 
                   "Kosten per Jaar avg [€]", 
                   "Kosten over EvaluatiePeriode [€]"]
    df_output = pd.DataFrame({
      "Resultaat": data_items,
      "CV":  [
        int(self.kosten_overzicht["CV"]["Totaal"] / self.sl_jaren / 12),
        int(self.kosten_overzicht["CV"]["Totaal"] / self.sl_jaren),
        int(self.kosten_overzicht["CV"]["Totaal"])
      ],
      "WP1": [
        int(self.kosten_overzicht["WP1"]["Totaal"] / self.sl_jaren / 12),
        int(self.kosten_overzicht["WP1"]["Totaal"] / self.sl_jaren),
        int(self.kosten_overzicht["WP1"]["Totaal"])
      ],
      "WP2": [
        int(self.kosten_overzicht["WP2"]["Totaal"] / self.sl_jaren / 12),
        int(self.kosten_overzicht["WP2"]["Totaal"] / self.sl_jaren),
        int(self.kosten_overzicht["WP2"]["Totaal"])
      ],
      "WP3": [
        int(self.kosten_overzicht["WP3"]["Totaal"] / self.sl_jaren / 12),
        int(self.kosten_overzicht["WP3"]["Totaal"] / self.sl_jaren),
        int(self.kosten_overzicht["WP3"]["Totaal"])
      ],
    })    
    kolom_instellingen = {col: st.column_config.NumberColumn(alignment="center") for col in ["CV", "WP1", "WP2", "WP3"]}
    st.dataframe(df_output, width="stretch", hide_index=True, column_config=kolom_instellingen)

  # **************************************************************************
  # **************************************************************************
  def create_chart(self):
      chart_rows = []
      for sys, posten in self.kosten_overzicht.items():
          for kosten_type in ["Aanschaf", "Vaste Kosten", "Verbruik"]:
              chart_rows.append({
                  "Installatie": sys,
                  "Type Kosten": kosten_type,
                  "Bedrag (€)": posten[kosten_type]
              })
      self.df_grafiek_laatste = pd.DataFrame(chart_rows) # Onthoud de data voor de PDF
    
      fig = px.bar(
          self.df_grafiek_laatste, x="Installatie", y="Bedrag (€)", color="Type Kosten", 
          text_auto='.2s', height=400,
          color_discrete_map={"Aanschaf": "#94a3b8", "Vaste Kosten": "#38bdf8", "Verbruik": "#f43f5e"} 
      )
      
      fig.update_layout(
          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
          margin=dict(l=40, r=10, t=10, b=30),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#000000")
      )
      
      fig.update_xaxes(title=None, showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#000000"))
      fig.update_yaxes(title=None, showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#000000"))
      
      st.plotly_chart(fig, width="stretch")
      
  # **************************************************************************
  # **************************************************************************
  def export_to_json(self):
      """Pakt alle actuele waarden van tabellen en sliders samen in een JSON string"""
      import json
      
      # Verzamel de live waarden uit de data_editors via de helpers
      live_verbruik = {k: self.get_value_verbruik(k) for k in st.session_state.init_verbruik.keys()}
      live_vast = {k: self.get_value_vast(k) for k in st.session_state.init_vast.keys()}
      
      live_wp = {"Installatie": st.session_state.init_wp["Installatie"]}
      for sys in ["CV", "WP1", "WP2", "WP3"]:
          live_wp[sys] = [self.get_value_wp(rij, sys) for rij in st.session_state.init_wp["Installatie"]]

      # Voeg alles samen in één groot instellingen-pakket
      instellingen = {
          "verbruik": live_verbruik,
          "vast": live_vast,
          "wp": live_wp,
          "sliders": {
              "elek_prijs": self.sl_elek_prijs * 100, # Terug naar centen voor de sliders
              "elek_delta": self.sl_elek_delta * 100,
              "terug_prijs": self.sl_terug_prijs * 100,
              "gas_prijs": self.sl_gas_prijs * 100,
              "gas_delta": self.sl_gas_delta * 100,
              "jaren": self.sl_jaren
          }
      }
      # Zet om naar nette JSON tekst met inspringing
      return json.dumps(instellingen, indent=4)

  # **************************************************************************
  # **************************************************************************
  def import_from_json(self, json_bestand):
      """Laadt een geüpload JSON bestand en overschrijft de session state"""
      import json
      try:
          data = json.load(json_bestand)
          
          # Overschrijf de basis data in session state
          st.session_state.init_verbruik = data["verbruik"]
          st.session_state.init_vast = data["vast"]
          st.session_state.init_wp = data["wp"]
          
          # Sla de slider-waarden op in session state zodat de sliders deze overnemen
          st.session_state.load_sliders = data["sliders"]
          
          # Forceer Streamlit om de pagina direct te vernieuwen met de nieuwe data
          st.rerun()
      except Exception as e:
          st.error(f"Fout bij het laden van het JSON-bestand: {e}")
      

  # **************************************************************************
  # **************************************************************************
  def export_to_pdf(self, pdf_verbruik, pdf_vast, pdf_wp):
      import io
      from reportlab.lib.pagesizes import A4
      from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
      from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
      from reportlab.lib import colors
      import plotly.express as px

      # 1. Globale variabelen/versie veiligstellen
      version = getattr(self, 'version', '1.0')



      """ Om Cloud probleem op te sporen
      # 2. Plotly Grafiek Genereren
      try:
          fig_pdf = px.bar(self.df_grafiek_laatste, x="Installatie", y="Bedrag (€)", color="Type Kosten", text_auto='.2s', height=400, color_discrete_map={"Aanschaf": "#94a3b8", "Vaste Kosten": "#38bdf8", "Verbruik": "#f43f5e"})
          fig_pdf.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=40, r=10, t=10, b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#000000"))
          fig_pdf.update_xaxes(title=None, showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#000000"))
          fig_pdf.update_yaxes(title=None, showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#000000"))
          chart_img_bytes = fig_pdf.to_image(format="png", width=600, height=350, scale=2)
      except Exception:
          chart_img_bytes = None
      """

      # Haal de try/except weg zodat we de echte fout in de Streamlit logs kunnen zien
      fig_pdf = px.bar(self.df_grafiek_laatste, x="Installatie", y="Bedrag (€)", color="Type Kosten", text_auto='.2s', height=400, color_discrete_map={"Aanschaf": "#94a3b8", "Vaste Kosten": "#38bdf8", "Verbruik": "#f43f5e"})
      fig_pdf.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=40, r=10, t=10, b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#000000"))
      fig_pdf.update_xaxes(title=None, showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#000000"))
      fig_pdf.update_yaxes(title=None, showgrid=True, gridcolor="#e2e8f0", tickfont=dict(color="#000000"))
      
      # Forceer het converteren
      chart_img_bytes = fig_pdf.to_image(format="png", width=600, height=350, scale=2)




      # 3. Document Setup (A4 breedte = 595pt. Marges 25+25=50pt. Beschikbare breedte = 545pt)
      # Linkerkolom (200) + Tussenruimte (25) + Rechterkolom (320) = exact 545pt.
      buffer = io.BytesIO()
      doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
      story = []
      
      # 4. Typografie & Stijlen
      styles = getSampleStyleSheet()
      title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=5, textColor=colors.HexColor("#0f172a"))
      section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=11, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#1e293b"))
      normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.HexColor("#334155"))
      
      # Stijl voor tekst IN de tabellen (voorkomt tekst overlap bij lange zinnen)
      table_body_style = ParagraphStyle('TableBody', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.HexColor("#1e293b"))
      table_body_center = ParagraphStyle('TableBodyCenter', parent=table_body_style, alignment=1) # 1 = gecentreerd

      # 5. Header toevoegen
      story.append(Paragraph(f"⚡ FC Warmtepomp Calculator (v{version})", title_style))
      story.append(Paragraph(f"<b>EvaluatiePeriode:</b> {self.sl_jaren} jaar  |  <b>Gasprijs:</b> € {self.sl_gas_prijs:.2f}/m³  |  <b>Elektraprijs:</b> € {self.sl_elek_prijs:.2f}/kWh", normal_style))
      story.append(Spacer(1, 10))

      # Standaard tabelstijl voor een strakke look
      base_table_style = TableStyle([
          ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
          ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
          ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
          ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
          ('FONTSIZE', (0, 0), (-1, 0), 9),
          ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
          ('TOPPADDING', (0, 0), (-1, 0), 5),
          ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
          ('FONTSIZE', (0, 1), (-1, -1), 9),
          ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
          ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
          ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
      ])


      # --- LINKS: VERBRUIK & VASTE KOSTEN & SLIDERS ---
      left_flowables = []
      
      # 1. Energie Verbruik
      left_flowables.append(Paragraph("📋 Energie Verbruik", section_style))
      verbruik_data = [["Energie Item", "Waarde"]]
      for k, v in pdf_verbruik.items():
          verbruik_data.append([Paragraph(k, table_body_style), Paragraph(str(v), table_body_style)])
      t_verbruik = Table(verbruik_data, colWidths=[130, 70])
      t_verbruik.setStyle(base_table_style)
      left_flowables.append(t_verbruik)
      
      left_flowables.append(Spacer(1, 15))
      

      """
      # 3. NIEUW: Sliders / Uitgangspunten Calculatie
      left_flowables.append(Paragraph("🎛️ Geselecteerde Instellingen", section_style))
      
      # Voeg hier alle variabelen toe die aan uw Streamlit-sliders gekoppeld zijn
      slider_data = [
          ["Instelling", "Waarde"],
          ["EvaluatiePeriode", f"{self.sl_jaren} jaar"],
          ["Gasprijs", f"€ {self.sl_gas_prijs:.2f}/m³"],
          ["Elektraprijs", f"€ {self.sl_elek_prijs:.2f}/kWh"],
          # Voeg hier eventuele extra sliders toe, bijvoorbeeld:
          # ["Budget", f"€ {self.sl_budget}"],
      ]
      
      formatted_slider_data = []
      for r_idx, row in enumerate(slider_data):
          if r_idx == 0:
              formatted_slider_data.append(row)
          else:
              formatted_slider_data.append([
                  Paragraph(row[0], table_body_style), 
                  Paragraph(row[1], table_body_style)
              ])

      t_sliders = Table(formatted_slider_data, colWidths=[130, 70])
      t_sliders.setStyle(base_table_style)
      left_flowables.append(t_sliders)
      """


      # 2. Vaste Kosten
      left_flowables.append(Paragraph("📋 Vaste Kosten", section_style))
      vast_data = [["Kosten Item", "Waarde"]]
      for k, v in pdf_vast.items():
          vast_data.append([Paragraph(k, table_body_style), Paragraph(str(v), table_body_style)])
      t_vast = Table(vast_data, colWidths=[130, 70])
      t_vast.setStyle(base_table_style)
      left_flowables.append(t_vast)

      left_flowables.append(Spacer(1, 15))






      # --- RECHTS: GRAFIEK, RESULTATEN & EIGENSCHAPPEN ---
      right_flowables = []
      
      # Grafiek
      if chart_img_bytes:
          right_flowables.append(Paragraph("📊 Kosten Evaluatie Grafiek", section_style))
          right_flowables.append(Image(io.BytesIO(chart_img_bytes), width=320, height=186))
          right_flowables.append(Spacer(1, 10))

      # Gemiddelde Resultaten
      right_flowables.append(Paragraph("📊 Gemiddelde Resultaten (Netto)", section_style))
      output_data = [
          ["Resultaat indicator", "CV", "WP1", "WP2", "WP3"],
          ["Kosten / Maand avg", f"€ {int(self.kosten_overzicht['CV']['Totaal']/self.sl_jaren/12)}", f"€ {int(self.kosten_overzicht['WP1']['Totaal']/self.sl_jaren/12)}", f"€ {int(self.kosten_overzicht['WP2']['Totaal']/self.sl_jaren/12)}", f"€ {int(self.kosten_overzicht['WP3']['Totaal']/self.sl_jaren/12)}"],
          ["Kosten / Jaar avg", f"€ {int(self.kosten_overzicht['CV']['Totaal']/self.sl_jaren)}", f"€ {int(self.kosten_overzicht['WP1']['Totaal']/self.sl_jaren)}", f"€ {int(self.kosten_overzicht['WP2']['Totaal']/self.sl_jaren)}", f"€ {int(self.kosten_overzicht['WP3']['Totaal']/self.sl_jaren)}"],
          ["Netto Totaal Evaluatie", f"€ {int(self.kosten_overzicht['CV']['Totaal'])}", f"€ {int(self.kosten_overzicht['WP1']['Totaal'])}", f"€ {int(self.kosten_overzicht['WP2']['Totaal'])}", f"€ {int(self.kosten_overzicht['WP3']['Totaal'])}"]
      ]
      
      # Omzetten naar Paragraphs voor automatische uitlijning en wrapping
      formatted_output_data = []
      for r_idx, row in enumerate(output_data):
          formatted_row = []
          for c_idx, cell in enumerate(row):
              if r_idx == 0:
                  formatted_row.append(cell) # Headers blijven platte tekst voor de TableStyle
              else:
                  style = table_body_style if c_idx == 0 else table_body_center
                  formatted_row.append(Paragraph(cell, style))
          formatted_output_data.append(formatted_row)

      t_output = Table(formatted_output_data, colWidths=[120, 50, 50, 50, 50])
      t_output.setStyle(base_table_style)
      right_flowables.append(t_output)

      right_flowables.append(Spacer(1, 15))
      
      # Installatie Eigenschappen (pdf_wp)
      right_flowables.append(Paragraph("⚙️ Installatie Eigenschappen", section_style))
      wp_data = [["Eigenschap", "CV", "WP1", "WP2", "WP3"]]
      
      rijen = pdf_wp["Installatie"]
      for idx, rij in enumerate(rijen):
          wp_data.append([
              Paragraph(rij, table_body_style), 
              Paragraph(str(pdf_wp["CV"][idx]), table_body_center), 
              Paragraph(str(pdf_wp["WP1"][idx]), table_body_center), 
              Paragraph(str(pdf_wp["WP2"][idx]), table_body_center), 
              Paragraph(str(pdf_wp["WP3"][idx]), table_body_center)
          ])
      
      t_wp = Table(wp_data, colWidths=[100, 55, 55, 55, 55])
      t_wp.setStyle(base_table_style)
      right_flowables.append(t_wp)

 
      # --- MASTER LAYOUT (2 KOLOMMEN) ---
      master_data = [[left_flowables, "", right_flowables]]
      master_table = Table(master_data, colWidths=[200, 25, 320])
      master_table.setStyle(TableStyle([
          ('VALIGN', (0,0), (-1,-1), 'TOP'),
          ('LEFTPADDING', (0,0), (-1,-1), 0),
          ('RIGHTPADDING', (0,0), (-1,-1), 0),
          ('BOTTOMPADDING', (0,0), (-1,-1), 0),
          ('TOPPADDING', (0,0), (-1,-1), 0),
      ]))
      
      story.append(master_table)
      
      # Bouw PDF document
      doc.build(story)
      buffer.seek(0)
      return buffer
      
 
 
# ****************************************************************************
# ****************************************************************************
def main():
  # Dashboard schermlay-out hersteld naar stabiele weergave
  st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h3 {margin-top: 0rem; margin-bottom: 0.5rem;}
    </style>
  """, unsafe_allow_html=True)
  
  st.title("⚡ FC Warmtepomp Calculator (v%.1f)" % version)
  
  model = EnergieModel()
  Col_Left, Col_Right = st.columns([1, 1.8])
  
  with Col_Left:
    model.create_table_energie_verbruik()
    model.create_sliders()
    model.create_PV_Opwek()
    model.create_table_vaste_kosten()
      
  model.run_calculations()
    
  with Col_Right:
    model.create_chart ()
    model.create_table_output ()
    model.create_table_installatie ()

    # FIX: Haal de benodigde dictionaries VEILIG op uit de state VOORDAT de achtergrond-thread start
    state_verbruik = dict(st.session_state.init_verbruik)
    state_vast = dict(st.session_state.init_vast)
    state_wp = dict(st.session_state.init_wp)

    # Maak de JSON data live aan voor de downloadknop
    json_data_string = model.export_to_json()

    # Geef de veilige data mee via een argumentloze lambda naar de export_to_pdf
    col_json_0, col_json1, col_json2 = st.columns ( 3 )
    #col_json_0, col_json1, col_json2 = st.columns ( [1,1,2] )

    with col_json_0 :
      st.download_button ( 
        label     = "📥 PDF Rapport"
       ,data      = lambda: model.export_to_pdf(state_verbruik, state_vast, state_wp)
       ,file_name = "Warmtepomp_Berekening_Rapport.pdf"
       ,mime      ="application/pdf"
       ,type      ="primary"
       ,width     = "stretch"
    )

    # --- JSON OPSLAAN & LADEN SECTIE ---
    #st.subheader("💾 Model Data Beheer")
    
    
    #col_json1, col_json2 = st.columns(2)
    with col_json1:
      st.download_button(
        label="📤 Exporteer Data",
        data=json_data_string,
        file_name="warmtepomp_model_instellingen.json",
        mime="application/json",
        width="stretch"
      )
        
    with col_json2:
      # Een compacte file uploader die alleen naar .json bestanden zoekt
      geupload_bestand = st.file_uploader(
        "Importeer Data (JSON)", 
        type=["json"], 
        width="stretch",
        label_visibility= "collapsed" #"visible" 
      )
      if geupload_bestand is not None:
        model.import_from_json(geupload_bestand)

  # nog wat tekst / toelichting
  #st.title("⚡ FC Warmtepomp Calculator (v%.1f)" % version)
  line  = "Op dit moment wordt nog niets gedaan met PV-panelen, Thuisaccu, Zonneboiler, E-Auto."
  line += "<br>De eerst volgende stap is om PV-Panelen mee te nemen"
  line += ", zodat eigen verbruik stijgt en de kosten van een warmtepomp dalen."
  line += "<br>gelijktijdig wordt dan ook de thuisaccu meegenomen, omdat dat exact hetzelfde mechanisme is."
  line += "<br>Daarna zal rente worden meegenomen."
  line += "<br>Zonneboiler is waarschijnlijk te moeilijk en ook minder zinvol, evenals E-Auto"
  st.html ( line )


# ****************************************************************************
# ****************************************************************************
# Main program
# ****************************************************************************
# ****************************************************************************
if __name__ == "__main__":
  #DF = Get_KNMI_Uur_QT ( 2025, Station = 375 )
  #print ( DF )
  #This_Is_The_End
    
  main()
       

# ****************************************************************************
# ****************************************************************************
#  - Save File
#  - run hier in spyder (dan staat de omgeving goed)
#  - voer dan hier het volgende commando uit
#      !streamlit run St_Warmtepomp.py
# ****************************************************************************
# ****************************************************************************

