import streamlit as st
from datetime import datetime,date,timedelta
from generacion_potencia import download_redata, tablas, graficar_bolas, graficar_FC, graficar_FU,graficar_mix, graficar_mix_queso


if 'año_seleccionado' not in st.session_state:
    st.session_state.año_seleccionado = 2025

nombres_meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
# Usado para el select box de años
lista_años = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]

def es_bisiesto(año):
    return (año % 4 == 0 and año % 100 != 0) or (año % 400 == 0)
año_bisiesto = es_bisiesto(st.session_state.año_seleccionado)



if año_bisiesto:
    horas_año = 8760
else:
    horas_año = 8784

print (horas_año)

#constantes para la descarga de REData
category = 'generacion'
widget_gen = 'estructura-generacion'
widget_pot = 'potencia-instalada'
time_trunc = 'month'

#horas equivalentes máximas de cada tecnología
horas_eq_max = {
    'Ciclo combinado' : 6000,
    'Nuclear' : 8000,
    'Solar fotovoltaica' : 2000,
    'Eólica' : 2200,
    'Hidráulica' : 4000,
    'Cogeneración' : 7000,
    'Turbinación bombeo' : 2000
    }
#visualización tipo código en horizontal de las horas equivalentes maximas
code_heqmax = f'''Horas equivalentes máximas: {horas_eq_max}'''

fecha_hoy = datetime.now().date()
num_mes_hoy = fecha_hoy.month
año_hoy = fecha_hoy.year

#calculamos fecha_ini fecha_fin para la llamada a REData
if st.session_state.año_seleccionado == año_hoy:
    if num_mes_hoy == 1:  # Si estamos en enero
        primer_dia_año = date(año_hoy - 1, 1, 1)  # Primer día del año anterior
        ultimo_dia_mes_anterior = date(año_hoy - 1, 12, 31)  # Último día de diciembre del año anterior
        num_mes_anterior = 12
    else:
        primer_dia_año = date(año_hoy, 1, 1)  # Primer día del año actual
        ultimo_dia_mes_anterior = date(año_hoy, num_mes_hoy, 1) - timedelta(days = 1)  # Último día del mes anterior
        fecha_ini = primer_dia_año
        fecha_fin = ultimo_dia_mes_anterior
        num_mes_anterior = num_mes_hoy - 1 
    nombre_mes_anterior = nombres_meses[num_mes_anterior]  
else:
    fecha_ini = date(st.session_state.año_seleccionado, 1, 1)  # Primer día del año seleccionado
    fecha_fin = date(st.session_state.año_seleccionado, 12, 31) #ultimo día del año seleccionado
    nombre_mes_anterior = 'Diciembre'

print(fecha_ini, fecha_fin)



#horas: calculadas entre los días 1 de enero y el último día del mes obtenido
horas_totales = ((fecha_fin-fecha_ini).days + 1) * 24


#horas_proporcional: para el año en curso o si se selecciona el mes anterior cuando el año es el actual en curso
horas_proporcional = horas_totales / horas_año
print(horas_totales, horas_proporcional)





df_in_gen = download_redata(category, widget_gen, fecha_ini,fecha_fin, time_trunc)
df_in_pot = download_redata(category, widget_pot, fecha_ini,fecha_fin, time_trunc)
df_out_ratio_select_fc, df_out_ratio_select_fu, df_out_ratio_select_mix, colores_tecnologia = tablas(df_in_gen,df_in_pot, horas_totales, horas_proporcional, horas_eq_max)

graf_bolas = graficar_bolas(df_out_ratio_select_fc, colores_tecnologia)
graf_fc  =graficar_FC(df_out_ratio_select_fc, colores_tecnologia)
graf_fu  =graficar_FU(df_out_ratio_select_fu, colores_tecnologia)

colores_tecnologia['Resto'] = '#FFFFE0'
graf_mix = graficar_mix(df_out_ratio_select_mix, colores_tecnologia)
graf_mix_queso = graficar_mix_queso(df_out_ratio_select_mix, colores_tecnologia)

# VISUALIZACION EN STREAMLIT
st.header('Tecnologías de generación', divider='rainbow')
st.markdown("¡Sígueme en [Bluesky](https://bsky.app/profile/poweravenger.bsky.social)!")
st.info('Todos los datos son elaborados a partir de REData / Generación / Estructura generación y Potencia instalada (sistema eléctrico nacional todas las tecnologías). Rango temporal: Mensual, siendo los datos agrupados por años.',icon="ℹ️")
#año_select=st.selectbox('Selecciona un año', options=lista_años, index=len(lista_años)-1)
st.selectbox('Selecciona un año', options=lista_años, key = 'año_seleccionado')
st.markdown(f'Último mes del que se disponen datos: :orange[{nombre_mes_anterior}].')

st.subheader('Gráfico 1: Horas Equivalentes', divider = 'rainbow')
st.info('En el eje Y tienes la generación de cada tecnología. En el eje X tienes la potencia instalada. Todo ello para el año seleccionado (ver último mes del que se disponen datos).\n'
        'La relación entre ambas magnitudes determinan las **:orange[horas equivalentes]**. \n'   
        'Es el tiempo que hubiera estado generando una tecnología a tope de su capacidad instalada. En principio, cuanto más gorda la bola, mejor.'

        , icon="ℹ️"
)
st.caption(f'Horas equivalentes: Generación vs Potencia Instalada. Año {st.session_state.año_seleccionado} hasta el mes de {nombre_mes_anterior}.')
st.write(graf_bolas)

st.subheader('Gráfico 2: Factor de Carga', divider = 'rainbow')
st.info('A partir de las horas equivalentes y las horas totales del periodo analizado, calculamos el :orange[FC o Factor de Carga] (en %), siendo éste un dato totalmente objetivo.\n'
        'El FC realmente nos da una idea del aprovechamiento o eficiencia de una tecnología de generación. \n'
        'Cuanto mayor es el tamaño de la barra (o de la bola de arriba), más se ha aprovechado la potencia instalada de cada tecnología.'

        , icon="ℹ️"
)
st.caption(f'Factor de Carga: Horas equivalentes vs horas totales. Año {st.session_state.año_seleccionado} hasta el mes de {nombre_mes_anterior}.')
st.write(graf_fc)

st.subheader('Gráfico 3: Factor de Uso', divider = 'rainbow')
st.info('Existe un límite teórico de generación en función del recurso disponible. No es lo mismo la disponibilidad de una central nuclear que la de un parque eólico.\n'
        'Aquí es cuando entra en juego el :orange[FU o Factor de Uso] (en %), siendo éste un dato bastante subjetivo.\n'
        'El FU es interesante porque nos da una idea del aprovechamiento **relativo** de dicho recurso disponible para cada una de las tecnologías de generación. \n'
        
        , icon="ℹ️"
)
st.code(code_heqmax, language='python')
st.caption(f'Factor de Uso: Según horas equivalentes máximas. Año {st.session_state.año_seleccionado} hasta el mes de {nombre_mes_anterior}.')
st.write(graf_fu)

st.subheader('Gráfico 4: Mix de generación', divider = 'rainbow')
st.info('Este gráfico está relacionado con el eje Y de las bolas. Generación pura y dura, con dos opciones de visualización.\n'
        'Fíjate que cuanto más arriba esté la bola, el sector o barra son más grandes.\n'
               
        , icon="ℹ️"
)
tipo_mix = st.toggle('Cambiar de tipo de gráfico')
st.caption(f'Mix de generación (en %). Año {st.session_state.año_seleccionado} hasta el mes de {nombre_mes_anterior}.')
espacio_mix = st.empty()
if tipo_mix:
    espacio_mix.write(graf_mix)
else:
    espacio_mix.write(graf_mix_queso)


#st.write(df_out_ratio_select_fu)
#st.write(df_out_ratio_select_mix)