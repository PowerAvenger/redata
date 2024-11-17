import streamlit as st
import time



st.set_page_config(
    page_title="REData",
    page_icon=":bulb:",
    layout='centered',
    initial_sidebar_state='collapsed'
)

st.title('Infografías REData')
st.caption("Copyright by Jose Vidal :ok_hand:")
url_apps = "https://powerappspy-josevidal.streamlit.app/"
st.write("Visita mi mini-web de [PowerAPPs](%s) con un montón de utilidades." % url_apps)
url_linkedin = "https://www.linkedin.com/posts/jfvidalsierra_powerapps-activity-7216715360010461184-YhHj?utm_source=share&utm_medium=member_desktop"
st.write("Deja tus comentarios y propuestas en mi perfil de [Linkedin](%s)." % url_linkedin)

st.text('')
st.text('')
st.info('¡Bienvenido a mis infografías **:orange[REData]**! \n\n'
        'A partir de los datos descargados de este organismo, elaboro una serie de gráficos\n'
        'interactivos que espero te puedan aportar información adicional.\n\n'
        'No dudes en contactar para comentar errores detectados o proponer mejoras en la :orange[e]PowerAPP'
        ,icon="ℹ️")
continuar=st.button('Continuar',type='primary')
if continuar:
    st.switch_page('pages/potgen.py')