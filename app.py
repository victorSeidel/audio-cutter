import os
import random
from pydub import AudioSegment
from pydub.utils import which
import streamlit as st

AudioSegment.converter = "ffmpeg"  # Tenta usar o FFmpeg do sistema
AudioSegment.ffmpeg = "ffmpeg"     # Garante que o pydub use o FFmpeg instalado

# Testa se o FFmpeg está acessível
os.system("ffmpeg -version")

st.set_page_config(page_title="Cortador de Áudio 0dB", layout="centered")
st.title("Cortador de Áudio em 0dB")

st.markdown("""
Este aplicativo corta um áudio em múltiplos trechos com base em pontos onde o volume é próximo de 0dB nos dois canais.
""")

# Upload do áudio
uploaded_file = st.file_uploader("Escolha um arquivo de áudio", type=["mp3", "wav", "ogg", "flac"])

prefixo = st.text_input("Nome para os arquivos", "audio")
naming_format = st.text_input("Formato de numeração (ex: P)", "P")
num_cortes = st.slider("Número de cortes", 1, 50, 10)
col1, col2 = st.columns(2)
with col1:
    min_intervalo = st.number_input("Intervalo mínimo (min)", 0.5, 10.0, 2.0)
with col2:
    max_intervalo = st.number_input("Intervalo máximo (min)", 0.5, 10.0, 4.0)
offset = st.slider("Offset após ponto de silêncio (ms)", -500, 500, 0)

output_dir = "cortes_web"
os.makedirs(output_dir, exist_ok=True)

@st.cache_data
def find_zero_crossings(audio_segment):
    zero_points = []
    samples = audio_segment.get_array_of_samples()
    frame_count = len(samples) // audio_segment.channels

    for i in range(frame_count):
        idx = i * audio_segment.channels
        left = samples[idx]
        right = samples[idx + 1] if audio_segment.channels > 1 else left

        if abs(left) < 100 and abs(right) < 100:
            zero_points.append(i * 1000 / audio_segment.frame_rate)

    return zero_points

if uploaded_file:
    st.audio(uploaded_file)

    if st.button("Processar Áudio"):
        try:
            audio = AudioSegment.from_file(uploaded_file)
            total_duration = len(audio)

            zero_points = find_zero_crossings(audio)
            if not zero_points:
                st.error("Não foram encontrados pontos com L e R em 0dB!")
            else:
                min_ms = int(min_intervalo * 60 * 1000)
                max_ms = int(max_intervalo * 60 * 1000)
                possiveis_intervalos = list(set(
                    random.randint(min_ms, max_ms) for _ in range(num_cortes * 2)
                ))
                random.shuffle(possiveis_intervalos)
                intervalos = possiveis_intervalos[:num_cortes]

                pontos_corte = [0]
                for intervalo in intervalos:
                    proximo = pontos_corte[-1] + intervalo
                    candidatos = [p for p in zero_points if p > proximo]
                    if not candidatos:
                        break
                    ponto_real = min(candidatos, key=lambda p: abs(p - proximo))
                    ponto_offset = ponto_real + offset
                    if ponto_offset < total_duration:
                        pontos_corte.append(int(ponto_offset))
                    else:
                        break

                cortes_feitos = 0
                with st.spinner("Cortando..."):
                    for i in range(len(pontos_corte) - 1):
                        ini = pontos_corte[i]
                        fim = pontos_corte[i + 1]
                        corte = audio[ini:fim]
                        nome = f"{prefixo} {naming_format}{i+1:02d}.mp3"
                        caminho = os.path.join(output_dir, nome)
                        corte.export(caminho, format="mp3")
                        st.success(f"Corte salvo: {nome}")
                        cortes_feitos += 1

                st.success(f"{cortes_feitos} cortes realizados com sucesso!")
                st.markdown("### Arquivos gerados:")
                for file in os.listdir(output_dir):
                    st.download_button(label=file, file_name=file, data=open(os.path.join(output_dir, file), "rb"), mime="audio/mp3")

        except Exception as e:
            st.error(f"Erro: {str(e)}")
