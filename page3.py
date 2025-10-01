import streamlit as st
from geopy.geocoders import Nominatim
import time
import numpy as np
import pandas as pd

st.title("Geocoding de Artistas Musicais") 

# Carregar dados
df = pd.read_csv('.\spotify.csv')

# Função para geocoding (pode ser lento para muitos dados)
@st.cache_data
def get_coordinates(artist_name):
    geolocator = Nominatim(user_agent="streamlit_app")
    try:
        location = geolocator.geocode(artist_name, timeout=10)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return None, None

# Aplicar apenas a uma amostra (geocoding é lento)
sample_df = df.head(44).copy()  # Apenas primeiras 20 linhas

st.subheader("Geocoding de Artistas (pode demorar)")
latest_iteration = st.empty()
progress_bar = st.progress(0) 

lats, lons = [], []
for i, artist in enumerate(sample_df['Artist name']):
    lat, lon = get_coordinates(artist)
    lats.append(lat if lat else np.random.uniform(-90, 90))
    lons.append(lon if lon else np.random.uniform(-180, 180))
    latest_iteration.text(f'Iteration {i+1}') 
    progress_bar.progress((i + 1) / len(sample_df)) 

sample_df['lat'] = lats
sample_df['lon'] = lons 

# Filtrar apenas linhas com coordenadas válidas
map_df = sample_df.dropna(subset=['lat', 'lon'])
st.map(map_df[['lat', 'lon']])