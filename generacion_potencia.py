# %%
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


@st.cache_data
def download_redata(category,widget,start_date,end_date,time_trunc):
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

def tablas(df_in_gen,df_in_pot, horas, horas_proporcional,horas_tec_teoricas):
    #montamos un dataframe de entrada con los datos de gen y pot
    df_in=pd.merge(df_in_gen,df_in_pot, on=['mes', 'mes_num','tecnologia'], how='outer',)
    df_in['horas_gen']=round(df_in['gen_TWh']*1000/df_in['pot_GW'],1)
    df_in['gen_TWh']=round(df_in['gen_TWh'],1)
    df_in['pot_GW']=round(df_in['pot_GW'],1)
    #a partir del anterior, agrupamos por tecnología
    df_out_ratio=df_in.groupby('tecnologia').agg({
        'gen_TWh':'sum',
        'pot_GW':'last',
        'horas_gen':'sum'
    })
    df_out_ratio=df_out_ratio.reset_index()

    #eliminamos las filas de gen y pot total
    df_out_ratio=df_out_ratio[~df_out_ratio['tecnologia'].isin(['Generación total','Potencia total'])]
    #calculamos totales de generacion y potencia
    gen_total=round(df_out_ratio['gen_TWh'].sum(),1)
    pot_total=round(df_out_ratio['pot_GW'].sum(),1)
    #añadimos columnas FC y %mix
    df_out_ratio['horas_gen']=df_out_ratio['horas_gen'].astype(int)
    df_out_ratio['FC']=round(df_out_ratio['horas_gen']/horas,3)
    df_out_ratio['%_mix']=round(df_out_ratio['gen_TWh']/gen_total,3)

    #creamos un df solo con las tecnologias seleccionadas
    tec_select=['Ciclo combinado', 'Hidráulica', 'Nuclear', 'Solar fotovoltaica', 'Turbinación bombeo', 'Eólica', 'Cogeneración']
    df_out_ratio_select=df_out_ratio[df_out_ratio['tecnologia'].isin(tec_select)].copy()
    #colores asociados (lo pongo aquí para tener la relacion directa)
    colores=["#555867","#4be4ff","#ff2b2b","#ff8700","#004280","#09ab3b","#6d3fc0"]
    #creamos un diccionario de colores asociados a cada tecnología
    colores_tecnologia = {tec: colores[i % len(colores)] for i, tec in enumerate(tec_select)}

    #añadimos columna horas max para calcular un FC relativo al maximo teórico de cada tecnologia
    df_out_ratio_select['horas_max']=horas_proporcional*df_out_ratio_select['tecnologia'].map(horas_tec_teoricas)
    df_out_ratio_select['horas_max']=df_out_ratio_select['horas_max'].astype(int)
    #calculamos el FC relativo según horas máximas
    df_out_ratio_select['FC_rel']=round(df_out_ratio_select['horas_gen']/df_out_ratio_select['horas_max'],3)
    #calculamos el %mix
    df_out_ratio_select['%_mix']=round(df_out_ratio_select['gen_TWh']/gen_total,3)

    #DATAFRAMES DE SALIDA PARA LOS GRÁFICOS
    df_out_ratio_select_fc=df_out_ratio_select.sort_values(['FC'],ascending=False) #usado para bolas y FC barras
    df_out_ratio_select_fcrel=df_out_ratio_select.sort_values(['FC_rel'],ascending=False)
    df_out_ratio_select_mix=df_out_ratio_select.sort_values(['%_mix'],ascending=False)

    #añadimos al mix 'resto' de tecnologías
    mix_tec_select=df_out_ratio_select_mix['%_mix'].sum()
    mix_resto=round(1-mix_tec_select,3)
    gen_resto=round(gen_total-df_out_ratio_select_mix['gen_TWh'].sum(),1)
    pot_resto=pot_total-df_out_ratio_select_mix['pot_GW'].sum()
    mix_tec_select,mix_resto,gen_resto
    nueva_fila = {
        'tecnologia': 'Resto',
        'gen_TWh': gen_resto,
        'pot_GW': pot_resto,  # Opcional: si no aplica, puedes dejar como None
        'horas_gen': None,
        'FC': None,
        '%_mix': mix_resto,
        'horas_max': None,
        'FC_rel': None
        }
    print(pot_total,pot_resto)
    df_out_ratio_select_mix=pd.concat([df_out_ratio_select_mix,pd.DataFrame([nueva_fila])],ignore_index=True)
    df_out_ratio_select_mix=df_out_ratio_select_mix.sort_values(['%_mix'],ascending=False)

    

    return df_out_ratio_select_fc,df_out_ratio_select_fcrel,df_out_ratio_select_mix,colores_tecnologia

def graficar_bolas(df_out_ratio_select_fc,colores_tecnologia):
    graf_bolas=px.scatter(df_out_ratio_select_fc,x='pot_GW',y='gen_TWh',size='horas_gen', 
                        size_max=100, color=df_out_ratio_select_fc['tecnologia'], 
                        hover_name=df_out_ratio_select_fc['tecnologia'],
                        color_discrete_map=colores_tecnologia,
                        #width=1300,
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
        title=dict(
            text='Potencia instalada, generación y sus horas equivalentes',
            x=.5,
            xanchor='center'

        ),
        legend=dict(
            title='',
            orientation='h',
            yanchor='bottom',
            y=-.5,
            xanchor='center',
            x=.5
        ),
        showlegend=True
        )
    graf_bolas.update_xaxes(
        showgrid=True
    )
    
    return graf_bolas


#GRÁFICO. PRIMERO DE BARRAS. FC
def graficar_FC(df_out_ratio_select_fc,colores_tecnologia):
    graf_FC=px.bar(df_out_ratio_select_fc,x='FC',y='tecnologia',
                        orientation='h',
                        color=df_out_ratio_select_fc['tecnologia'], 
                        hover_name=df_out_ratio_select_fc['tecnologia'],
                        color_discrete_map=colores_tecnologia,
                        #width=1300,
                        text_auto=True,
                        hover_data={
                            'tecnologia':False,
                            'horas_gen':True
                        },
                        text='FC',
                        
                        )
    graf_FC.update_traces(
        texttemplate='%{text:.1%}',
        textposition='inside', 
        
        )
    graf_FC.update_layout(
        title=dict(
            text='Factor de carga (%)',
            x=.5,
            xanchor='center',
        ),
        xaxis_tickformat='.0%',
        bargap=.4,
        showlegend=False,
        yaxis=dict(visible=True, title_text=None),
    )
    return graf_FC

#GRÁFICO: SEGUNDO DE BARRAS. FC RELATIVO
def graficar_FC_rel(df_out_ratio_select_fcrel, colores_tecnologia):
    graf_FC_rel=px.bar(df_out_ratio_select_fcrel,x='FC_rel',y='tecnologia',
                        orientation='h',
                        color=df_out_ratio_select_fcrel['tecnologia'], 
                        hover_name=df_out_ratio_select_fcrel['tecnologia'],
                        color_discrete_map=colores_tecnologia,
                        width=1300,
                        text_auto=True,
                        hover_data={
                            'tecnologia':False,
                            'horas_max':True
                        },
                        text='FC_rel'
                        
                        )
    graf_FC_rel.update_traces(
        texttemplate='%{text:.1%}',
        textposition='inside', 
        
        )
    graf_FC_rel.update_layout(
        title=dict(
            text='Factor de carga según horas máximas (%)',
            x=.5,
            xanchor='center',
        ),
        xaxis_tickformat='.0%',
        bargap=.4,
        showlegend=False,
        yaxis=dict(visible=True, title_text=None),
    )

    return graf_FC_rel

def graficar_mix(df_out_ratio_select_mix,colores_tecnologia):
    graf_mix=px.bar(df_out_ratio_select_mix,x='%_mix',y='tecnologia',
                        orientation='h',
                        color=df_out_ratio_select_mix['tecnologia'], 
                        hover_name=df_out_ratio_select_mix['tecnologia'],
                        color_discrete_map=colores_tecnologia,
                        width=1300,
                        text_auto=True,
                        hover_data={
                            'tecnologia':False,
                            'gen_TWh':True,
                            'pot_GW':True
                        },
                        text='%_mix'
                        
                        )
    graf_mix.update_traces(
        #formateamos el texto de las barras
        texttemplate='%{text:.1%}',
        textposition='inside',  # Coloca el texto en el centro de las burbujas
        #textfont=dict(size=12, color="black"),  # Tamaño y color del texto
        )
    graf_mix.update_layout(
        title=dict(
            text='Aportación al mix de generación (%)',
            x=.5,
            xanchor='center',
            
        ),
        xaxis_tickformat='.0%',
        bargap=.4,
        showlegend=False,
        yaxis=dict(visible=True, title_text=None),
    )
    return graf_mix

#GRAFICO DE QUESO VARIANTE DE LAS BARRAS
def graficar_mix_queso(df_out_ratio_select_mix,colores_tecnologia):
    graf_mix_queso=px.pie(
        df_out_ratio_select_mix, 
        names='tecnologia', 
        values='%_mix',
        color='tecnologia',
        color_discrete_map=colores_tecnologia,
        hover_name='tecnologia',
        hole=.4
    )
    graf_mix_queso.update_traces(textinfo='percent+label',
                                 textposition='inside',
                                 insidetextorientation='horizontal')

    return graf_mix_queso






#NO USADO
def leyenda(colores_tecnologia):
    leyenda=go.Figure()
    
    for tecnologia, color in colores_tecnologia.items():
        leyenda.add_trace(go.Scatter(
            x=[None],  # Valores ficticios (invisibles)
            y=[None],
            mode='markers',
            marker=dict(size=20, color=color),
            name=tecnologia  # Texto de la leyenda
        ))

    # Configurar solo la leyenda
    leyenda.update_layout(
        showlegend=True,  # Mostrar la leyenda
        title='Tecnología',
        xaxis=dict(visible=False),  # Ocultar ejes
        yaxis=dict(visible=False),
        margin=dict(t=0, b=0, l=0, r=0),
        height=200

    )
    return leyenda