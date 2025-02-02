import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


@st.cache_data
def download_redata(category, widget, start_date, end_date, time_trunc):
    column_mapping = {
        "estructura-generacion": {"valor": "gen_TWh", "porcentaje": "porc_gen", "coef":1000000},
        "potencia-instalada": {"valor": "pot_GW", "porcentaje": "porc_pot", "coef": 1000}
    }
    end_point='https://apidatos.ree.es/es/datos'
    url=f'{end_point}/{category}/{widget}?start_date={start_date}T00:00&end_date={end_date}T23:59&time_trunc={time_trunc}'
    request=requests.get(url)
    data=request.json()
    datos = []
    for tech in data["included"]:
        tech_name = tech["attributes"]["title"]
        for entry in tech["attributes"]["values"]:
            datos.append({"mes": entry["datetime"], "tecnologia": tech_name, "valor": entry["value"],"porcentaje":entry["percentage"]})

    # Convertir a DataFrame
    df_in_gen = pd.DataFrame(datos)
    df_in_gen['mes']=pd.to_datetime(df_in_gen['mes'], utc=True).dt.tz_convert('Europe/Madrid').dt.tz_localize(None)
    df_in_gen['mes_num']=df_in_gen['mes'].dt.month
    coef = column_mapping[widget]["coef"]
    df_in_gen['valor']=df_in_gen['valor']/coef
    if widget in column_mapping:
        df_in_gen.rename(columns={
            "valor": column_mapping[widget]["valor"],
            "porcentaje": column_mapping[widget]["porcentaje"]
        }, inplace=True)
    
    return df_in_gen

def tablas(df_in_gen,df_in_pot, horas, horas_proporcional, horas_tec_teoricas):
    #montamos un dataframe de entrada con los datos de gen y pot
    df_in  =pd.merge(df_in_gen,df_in_pot, on = ['mes', 'mes_num', 'tecnologia'], how = 'outer',)
    df_in['horas_eq'] = round(df_in['gen_TWh']  *1000 / df_in['pot_GW'], 1)
    df_in['gen_TWh'] = round(df_in['gen_TWh'], 1)
    df_in['pot_GW'] = round(df_in['pot_GW'], 1)
    #a partir del anterior, agrupamos por tecnología
    df_out_ratio = df_in.groupby('tecnologia').agg({
        'gen_TWh':'sum',
        'pot_GW':'last',
        'horas_eq':'sum'
    })
    df_out_ratio = df_out_ratio.reset_index()

    #eliminamos las filas de gen y pot total
    df_out_ratio=df_out_ratio[~df_out_ratio['tecnologia'].isin(['Generación total','Potencia total'])]
    #calculamos totales de generacion y potencia
    gen_total=round(df_out_ratio['gen_TWh'].sum(),1)
    pot_total=round(df_out_ratio['pot_GW'].sum(),1)
    #añadimos columnas FC y %mix
    df_out_ratio['horas_eq']=df_out_ratio['horas_eq'].astype(int)
    df_out_ratio['FC']=round(df_out_ratio['horas_eq']/horas,3)
    df_out_ratio['%_mix']=round(df_out_ratio['gen_TWh']/gen_total,3)

    #creamos un df solo con las tecnologias seleccionadas
    tec_select=['Ciclo combinado', 'Hidráulica', 'Nuclear', 'Solar fotovoltaica', 'Turbinación bombeo', 'Eólica', 'Cogeneración']
    df_out_ratio_select=df_out_ratio[df_out_ratio['tecnologia'].isin(tec_select)].copy()
    #colores asociados (lo pongo aquí para tener la relacion directa)
    colores=["#555867","#4be4ff","#ff2b2b","#ff8700","#004280","#09ab3b","#6d3fc0"]
    #creamos un diccionario de colores asociados a cada tecnología
    colores_tecnologia = {tec: colores[i % len(colores)] for i, tec in enumerate(tec_select)}

    #añadimos columna horas max para calcular un FC relativo al maximo teórico de cada tecnologia
    df_out_ratio_select['horas_eq_max'] = horas_proporcional * df_out_ratio_select['tecnologia'].map(horas_tec_teoricas)
    df_out_ratio_select['horas_eq_max']=df_out_ratio_select['horas_eq_max'].astype(int)
    #calculamos el FU factor de uso, en base a las horas equivalentes maximas
    df_out_ratio_select['FU']=round(df_out_ratio_select['horas_eq']/df_out_ratio_select['horas_eq_max'],3)
    df_out_ratio_select['FNU'] = 1 - df_out_ratio_select['FU']
    #calculamos el %mix
    df_out_ratio_select['%_mix'] = round(df_out_ratio_select['gen_TWh'] / gen_total, 3)

    #DATAFRAMES DE SALIDA PARA LOS GRÁFICOS
    df_out_ratio_select_fc=df_out_ratio_select.sort_values(['FC'],ascending=False) #usado para bolas y FC barras
    df_out_ratio_select_fu=df_out_ratio_select.sort_values(['FU'],ascending=False)
    df_out_ratio_select_mix = df_out_ratio_select.sort_values(['%_mix'], ascending = False)

    #añadimos al mix 'resto' de tecnologías
    mix_tec_select = df_out_ratio_select_mix['%_mix'].sum()
    mix_resto=round(1-mix_tec_select,3)
    gen_resto=round(gen_total-df_out_ratio_select_mix['gen_TWh'].sum(),1)
    pot_resto=pot_total-df_out_ratio_select_mix['pot_GW'].sum()
    mix_tec_select,mix_resto,gen_resto
    nueva_fila = {
        'tecnologia': 'Resto',
        'gen_TWh': gen_resto,
        'pot_GW': pot_resto,  # Opcional: si no aplica, puedo dejar como None
        'horas_eq': None,
        'FC': None,
        '%_mix': mix_resto,
        'horas_eq_max': None,
        'FU': None
        }
    print(pot_total,pot_resto)
    df_out_ratio_select_mix=pd.concat([df_out_ratio_select_mix,pd.DataFrame([nueva_fila])],ignore_index=True)
    df_out_ratio_select_mix=df_out_ratio_select_mix.sort_values(['%_mix'],ascending=False)

    

    return df_out_ratio_select_fc, df_out_ratio_select_fu, df_out_ratio_select_mix, colores_tecnologia

# GRAFICO 1. DE BOLAS --------------------------------------------------------------------------------------------
def graficar_bolas(df_out_ratio_select_fc, colores_tecnologia):
    graf_bolas=px.scatter(df_out_ratio_select_fc, x = 'pot_GW', y = 'gen_TWh', size = 'horas_eq', 
                        size_max = 100, color = df_out_ratio_select_fc['tecnologia'], 
                        hover_name = df_out_ratio_select_fc['tecnologia'],
                        color_discrete_map = colores_tecnologia,
                        hover_data={
                            'tecnologia':False,
                            'FC':True
                        }
                        )
    graf_bolas.update_traces(
        text=df_out_ratio_select_fc['tecnologia'],  # Usa los índices (tecnologías) como texto
        textposition='middle center',  # Coloca el texto en el centro de las burbujas
        )
    graf_bolas.update_layout(
        #title=dict(
        #    text='Potencia instalada, generación y sus horas equivalentes',
        #    x=.5,
        #    xanchor='center'

        #),
        legend=dict(
            title='',
            orientation='h',
            yanchor='top',
            y=1.1,
            xanchor='center',
            x=.5
        ),
        showlegend=True
        )
    graf_bolas.update_xaxes(
        showgrid=True
    )
    
    return graf_bolas


#GRÁFICO 2. PRIMERO DE BARRAS. FC--------------------------------------------------------------------------
def graficar_FC(df_out_ratio_select_fc, colores_tecnologia):
    graf_FC=px.bar(df_out_ratio_select_fc,x='FC',y='tecnologia',
                        orientation='h',
                        color=df_out_ratio_select_fc['tecnologia'], 
                        hover_name=df_out_ratio_select_fc['tecnologia'],
                        color_discrete_map=colores_tecnologia,
                        text_auto=True,
                        hover_data={
                            'tecnologia':False,
                            'horas_eq':True
                        },
                        text='FC',
                        
                        )
    graf_FC.update_traces(
        texttemplate='%{text:.1%}',
        textposition='inside', 
        
        )
    graf_FC.update_layout(
        #title=dict(
        #    text='Factor de carga (%)',
        #    x=.5,
        #    xanchor='center',
        #),
        xaxis_tickformat='.0%',
        bargap=.4,
        showlegend=False,
        yaxis=dict(visible=True, title_text=None),
    )

    graf_FC.update_xaxes(
        showgrid=True,
        range=[0,1.01],
        dtick=0.2,
        tickmode='linear'
    )

    return graf_FC

#GRÁFICO 3: SEGUNDO DE BARRAS. FU-----------------------------------------------------------------------------------------
def graficar_FU(df_out_ratio_select_fu, colores_tecnologia):
    graf_FU=px.bar(df_out_ratio_select_fu, x='FU', y='tecnologia',
                        orientation='h',
                        color=df_out_ratio_select_fu['tecnologia'], 
                        hover_name=df_out_ratio_select_fu['tecnologia'],
                        color_discrete_map=colores_tecnologia,
                        width=1300,
                        text_auto=True,
                        hover_data={
                            'tecnologia':False,
                            'horas_eq_max':True
                        },
                        text='FU'
                        
                        )
    graf_FU.update_traces(
        texttemplate='%{text:.1%}',
        textposition='inside', 
        
        )
    graf_FU.update_layout(
        #title=dict(
        #    text='Factor de Uso. Según horas máximas equivalentes (%)',
        #    x=.5,
        #    xanchor='center',
        #),
        xaxis_tickformat='.0%',
        bargap=.4,
        showlegend=False,
        yaxis=dict(visible=True, title_text=None),
    )

    graf_FU.add_bar(
        x=df_out_ratio_select_fu['FNU'],
        y=df_out_ratio_select_fu['tecnologia'],
        orientation='h',
        marker_color=df_out_ratio_select_fu['tecnologia'].map(colores_tecnologia),
        marker_opacity=0.3,  # Mayor transparencia
        hoverinfo='skip',  # Opcional: no mostrar información de estas barras en hover
        showlegend=False
    )

    graf_FU.update_xaxes(
        showgrid=True
    )

    return graf_FU

# GRAFICO 4. MIX GENERACION EN BARRAS---------------------------------------------
def graficar_mix(df_out_ratio_select_mix, colores_tecnologia):
    graf_mix = px.bar(df_out_ratio_select_mix, x = '%_mix', y = 'tecnologia',
                        orientation = 'h',
                        color = df_out_ratio_select_mix['tecnologia'], 
                        hover_name = df_out_ratio_select_mix['tecnologia'],
                        color_discrete_map = colores_tecnologia,
                        #width=1300,
                        text_auto = True,
                        hover_data = {
                            'tecnologia' : False,
                            'gen_TWh' : True,
                            'pot_GW': True
                        },
                        text = '%_mix'
                        
                        )
    graf_mix.update_traces(
        #formateamos el texto de las barras
        texttemplate = '%{text:.1%}',
        textposition = 'inside',  # Coloca el texto en el centro de las burbujas
        #textfont=dict(size=12, color="black"),  # Tamaño y color del texto
        )
    graf_mix.update_layout(
        #title=dict(
        #    text='Aportación al mix de generación (%)',
        #    x=.5,
        #    xanchor='center',
        #),
        xaxis_tickformat = '.0%',
        bargap = .4,
        showlegend = False,
        yaxis = dict(visible = True, title_text = None),
    )

    graf_mix.update_xaxes(
        showgrid = True
    )
    return graf_mix

#GRAFICO 4. MIX GENERACION EN QUESO------------------------------------------
def graficar_mix_queso(df_out_ratio_select_mix, colores_tecnologia):
    graf_mix_queso = px.pie(
        df_out_ratio_select_mix, 
        names = 'tecnologia', 
        #values = '%_mix',
        values = 'gen_TWh',
        color = 'tecnologia',
        color_discrete_map = colores_tecnologia,
        hover_name = 'tecnologia',
        hole = .4,
    )

    graf_mix_queso.update_traces(textinfo = 'percent+label',
                                 textposition = 'inside',
                                 insidetextorientation='horizontal'
    )
    
    #graf_mix_queso.update_layout(
    #    title=dict(
    #        text='Aportación al mix de generación (%)',
    #        x=.5,
    #        xanchor='center',
    #    )
    #)

    return graf_mix_queso



