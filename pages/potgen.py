import streamlit as st
from datetime import datetime,date,timedelta
from generacion_potencia import download_redata, tablas, graficar_bolas, graficar_FC, graficar_FU,graficar_mix, graficar_mix_queso





st.subheader('Tecnologías de generación', divider='rainbow')
st.markdown("¡Sígueme en [Bluesky](https://bsky.app/profile/poweravenger.bsky.social)!")
st.info('Todos los datos son elaborados a partir de REData / Generación / Estructura generación y Potencia instalada (sistema eléctrico nacional todas las tecnologías). Rango temporal: Mensual, siendo los datos agrupados por años.',icon="ℹ️")

fecha_hoy=datetime.now().date()
mes_hoy=fecha_hoy.month
año_hoy=fecha_hoy.year

lista_años=[2018,2019,2020,2021,2022,2023,2024]
año_select=st.selectbox('Selecciona un año', options=lista_años, index=len(lista_años)-1)

#calculamos fecha_ini fecha_fin para la llamada a REData
if año_select==año_hoy:
    if mes_hoy == 1:  # Si estamos en enero
        primer_dia_año = date(año_hoy - 1, 1, 1)  # Primer día del año anterior
        ultimo_dia_mes_anterior = date(año_hoy - 1, 12, 31)  # Último día de diciembre del año anterior
    else:
        primer_dia_año = date(año_hoy, 1, 1)  # Primer día del año actual
        ultimo_dia_mes_anterior = date(año_hoy, mes_hoy, 1) - timedelta(days=1)  # Último día del mes anterior
        
        fecha_ini=primer_dia_año
        fecha_fin=ultimo_dia_mes_anterior   
else:
    fecha_ini = date(año_select, 1, 1)  # Primer día del año seleccionado
    fecha_fin = date(año_select,12,31) #ultimo día del año seleccionado


print(fecha_ini,fecha_fin)

#constantes para la descarga de REData
category='generacion'
widget_gen='estructura-generacion'
widget_pot='potencia-instalada'
time_trunc='month'

#horas: calculadas entre los días 1 de enero y el último día del mes obtenido
horas=((fecha_fin-fecha_ini).days+1)*24
horas_año=8760
#horas_proporcional: para el año en curso o si se selecciona el mes anterior cuando el año es el actual en curso
horas_proporcional=horas/horas_año
print(horas,horas_proporcional)
#horas equivalentes máximas de cada tecnología
horas_eq_max={
    'Ciclo combinado' : 6000,
    'Nuclear' : 8000,
    'Solar fotovoltaica' : 2000,
    'Eólica' : 2200,
    'Hidráulica' : 4000,
    'Cogeneración' : 7000,
    'Turbinación bombeo' : 2000
    }

#para la visualización del código en vertical. NO usado.
code_bis = f"""horas_eq_max = {{
    'Ciclo combinado': {horas_eq_max['Ciclo combinado']},
    'Nuclear': {horas_eq_max['Nuclear']},
    'Solar fotovoltaica': {horas_eq_max['Solar fotovoltaica']},
    'Eólica': {horas_eq_max['Eólica']},
    'Hidráulica': {horas_eq_max['Hidráulica']},
    'Cogeneración': {horas_eq_max['Cogeneración']},
    'Turbinación bombeo': {horas_eq_max['Turbinación bombeo']}
}}
"""
#visualización en horizontal. SÍ se usa.
code=f''''Horas equivalentes máximas: {horas_eq_max}'''

df_in_gen=download_redata(category,widget_gen,fecha_ini,fecha_fin,time_trunc)
df_in_pot=download_redata(category,widget_pot,fecha_ini,fecha_fin,time_trunc)
df_out_ratio_select_fc, df_out_ratio_select_fu, df_out_ratio_select_mix,colores_tecnologia=tablas(df_in_gen,df_in_pot, horas, horas_proporcional,horas_eq_max)

graf_bolas=graficar_bolas(df_out_ratio_select_fc,colores_tecnologia)
graf_fc=graficar_FC(df_out_ratio_select_fc, colores_tecnologia)
graf_fu=graficar_FU(df_out_ratio_select_fu, colores_tecnologia)

colores_tecnologia['Resto']= '#FFFFE0'
graf_mix=graficar_mix(df_out_ratio_select_mix, colores_tecnologia)
graf_mix_queso=graficar_mix_queso(df_out_ratio_select_mix, colores_tecnologia)

st.write(graf_bolas)
st.write(graf_fc)
st.code(code, language='python')
st.write(graf_fu)


tipo_mix=st.toggle('Cambiar de tipo de gráfico')
espacio_mix=st.empty()
if tipo_mix:
    espacio_mix.write(graf_mix)
else:
    espacio_mix.write(graf_mix_queso)


st.write(df_out_ratio_select_fu)