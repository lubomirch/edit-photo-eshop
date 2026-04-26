import streamlit as st
from PIL import Image
import io
import zipfile

# Úvodní rychlé načtení rozhraní (aby nedošlo k chybě 503)
st.set_page_config(page_title="Profi E-shop Photo Editor", layout="wide")
st.title("📸 Profi Hromadný AI editor produktových fotek")

with st.sidebar:
    st.header("1. Nastavení ořezu")
    use_alpha_matting = st.checkbox("Pokročilé vyhlazení hran (agresivnější ořez)", value=False)
    st.markdown("---")
    st.header("2. Nastavení výstupu")
    target_size = st.number_input("Rozměr (px)", value=1000, step=100)
    margin = st.number_input("Okraj (px)", value=50, step=10)
    quality = st.slider("Kvalita JPG (komprese)", 10, 100, 85)

uploaded_files = st.file_uploader("Nahrajte produktové fotografie", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"Zpracovat {len(uploaded_files)} fotek"):
        
        # TĚŽKÉ KNIHOVNY NAČÍTÁME AŽ PO KLIKNUTÍ!
        with st.spinner("Startuji AI engine (při prvním běhu může trvat i minutu)..."):
            from rembg import remove, new_session
            # Používáme odlehčený model "u2netp", aby nedošla paměť
            session = new_session("u2net")
            
        progress_bar = st.progress(0)
        zip_buffer = io.BytesIO()
        
        remove_kwargs = {}
        if use_alpha_matting:
            remove_kwargs = {
                'alpha_matting': True,
                'alpha_matting_foreground_threshold': 240,
                'alpha_matting_background_threshold': 10,
                'alpha_matting_erode_size': 5
            }
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    input_data = uploaded_file.getvalue()
                    output_data = remove(input_data, session=session, **remove_kwargs)
                    img = Image.open(io.BytesIO(output_data)).convert("RGBA")
                    
                    bbox = img.getbbox()
                    if bbox: img = img.crop(bbox)
                    
                    max_product_size = target_size - (2 * margin)
                    img.thumbnail((max_product_size, max_product_size), Image.Resampling.LANCZOS)
                    
                    canvas = Image.new("RGB", (target_size, target_size), (255, 255, 255))
                    paste_x = (target_size - img.width) // 2
                    paste_y = (target_size - img.height) // 2
                    
                    alpha_mask = img.split()[3]
                    canvas.paste(img, (paste_x, paste_y), mask=alpha_mask)
                    
                    img_byte_arr = io.BytesIO()
                    canvas.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
                    
                    file_name = uploaded_file.name.rsplit('.', 1)[0] + ".jpg"
                    zip_file.writestr(file_name, img_byte_arr.getvalue())
                    
                except Exception as e:
                    st.error(f"Chyba při zpracování {uploaded_file.name}: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
        
        st.success("✅ Vše hotovo!")
        st.download_button(label="⬇️ Stáhnout všechny upravené fotky (ZIP)", data=zip_buffer.getvalue(), file_name="upravene_fotky.zip", mime="application/zip")
