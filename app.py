import streamlit as st
import pickle
import pandas as pd
import requests
import time
import os
import gdown
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------
# Download .pkl files from Google Drive if not found
# ---------------------------
MOVIE_DICT_ID = "1ZhCjfwMihHx9rjKir-t0NQKxRmGdDXpo"  # movie_dict.pkl
SIMILARITY_ID = "1vqOJkVTNl00QJmE6fRx5_1TD9eyruUOI"  # similarity.pkl

if not os.path.exists("movie_dict.pkl"):
    st.info("Downloading movie_dict.pkl from Google Drive ⏳")
    gdown.download(f"https://drive.google.com/uc?id={MOVIE_DICT_ID}", "movie_dict.pkl", quiet=False)

if not os.path.exists("similarity.pkl"):
    st.info("Downloading similarity.pkl from Google Drive ⏳")
    gdown.download(f"https://drive.google.com/uc?id={SIMILARITY_ID}", "similarity.pkl", quiet=False)

# ---------------------------
# Create a session with retry strategy
# ---------------------------
def create_session():
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 504)
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    return s

session = create_session()

# ---------------------------
# API Configuration
# ---------------------------
API_KEY = 'aace42b1e267ae6e4abc7010b48b26e0'
BASE_URL = 'https://api.themoviedb.org/3/movie'
TIMEOUT = 10

# ---------------------------
# Fetch movie poster function
# ---------------------------
@st.cache_data
def fetch_poster(movie_id, retries=3):
    for attempt in range(retries):
        try:
            url = f'{BASE_URL}/{movie_id}?api_key={API_KEY}&language=en-US'
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get('poster_path'):
                return "https://image.tmdb.org/t/p/w500" + data['poster_path']
            else:
                return "https://via.placeholder.com/500x750?text=No+Poster"

        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                st.warning(f"Timeout fetching poster for movie ID {movie_id}")
                return "https://via.placeholder.com/500x750?text=Poster+Error"

        except requests.exceptions.ConnectionError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                st.warning(f"Connection error fetching poster for movie ID {movie_id}")
                return "https://via.placeholder.com/500x750?text=Connection+Error"

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                st.warning(f"Error fetching poster: {str(e)}")
                return "https://via.placeholder.com/500x750?text=Error"

    return "https://via.placeholder.com/500x750?text=Error"

# ---------------------------
# Recommendation logic
# ---------------------------
def recommend(movie):
    try:
        movie_index = movies[movies['title'] == movie].index[0]
        distances = similarity[movie_index]
        movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

        recommend_movies = []
        recommend_movies_poster = []

        for i in movies_list:
            movie_id = int(movies.iloc[i[0]].movie_id)
            recommend_movies.append(movies.iloc[i[0]].title)
            recommend_movies_poster.append(fetch_poster(movie_id))

        return recommend_movies, recommend_movies_poster

    except Exception as e:
        st.error(f"Error in recommendation: {str(e)}")
        return [], []

# ---------------------------
# Load data
# ---------------------------
@st.cache_resource
def load_data():
    try:
        movie_dict = pickle.load(open('movie_dict.pkl', 'rb'))
        movies_df = pd.DataFrame(movie_dict)
        similarity_matrix = pickle.load(open('similarity.pkl', 'rb'))
        return movies_df, similarity_matrix
    except FileNotFoundError:
        st.error("Data files not found. Please ensure 'movie_dict.pkl' and 'similarity.pkl' exist.")
        st.stop()

movies, similarity = load_data()

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Movie Recommender", layout="wide")
st.title('🎬 Movie Recommender System')
st.write("Find movies similar to your favorite film!")

selected_movie_name = st.selectbox(
    "Select a movie:",
    movies['title'].values,
    help="Choose a movie to get recommendations"
)

if st.button('🔍 Get Recommendations', key='recommend_btn'):
    with st.spinner('Fetching recommendations...'):
        names, posters = recommend(selected_movie_name)

        if names:
            st.subheader(f"Movies similar to '{selected_movie_name}':")
            cols = st.columns(5)
            for idx, col in enumerate(cols):
                with col:
                    st.text(names[idx])
                    st.image(posters[idx], use_container_width=True)
        else:
            st.error("Could not fetch recommendations. Please try again.")



