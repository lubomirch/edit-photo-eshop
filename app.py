import streamlit as st
from rembg import remove, new_session
from PIL import Image
import io
import zipfile

# Definice AI session pro rembg
# (Tím zajistíme, že se model načte jen jednou pro celou dobu běhu appky)
if 'rembg_session' not in st.session_state:
    # default_model = 'u2net' (dobrý kompromis rychlosti a kvality)
    # Můžete zkusit i 'silueta' pro jednodušší objekty, je rychlejší.
    st.session_state['rembg_session'] = new_session("u2net")

st.set_page_config(page_title="Profi E-shop Photo Editor", layout="wide")
st.title("📸 Profi Hromadný AI editor produktových fotek")

# Nastavení parametrů v postranním panelu
with st.sidebar:
    st.header("1. Nastavení ořezu")
    
    # NOVÉ: Pokročilé nastavení pro problémové fotky (šedé pozadí)
    use_alpha_matting = st.checkbox(
        "Pokročilé vyhlazení hran (agresivnější ořez)", 
        value=False,
        help="Zkuste zapnout, pokud na bílých produktech zůstává šedý okraj. Zpracování bude POMALEJŠÍ."
    )
    
    st.markdown("---")
    st.header("2. Nastavení výstupu")
    target_size = st.number_input("Rozměr (px)", value=1000, step=100)
    margin = st.number_input("Okraj (px)", value=50, step=10)
    quality = st.slider("Kvalita JPG (komprese)", 10, 100, 85)

uploaded_files = st.file_uploader("Nahrajte produktové fotografie (i hromadně)", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"Zpracovat {len(uploaded_files)} fotek"):
        progress_bar = st.progress(0)
        zip_buffer = io.BytesIO()
        session = st.session_state['rembg_session']
        
        # Nastavení pro alpha matting (hodnoty byly vyladěny pro většinu produktů)
        remove_kwargs = {}
        if use_alpha_matting:
            remove_kwargs = {
                'alpha_matting': True,
                'alpha_matting_foreground_threshold': 240, # Vyšší číslo = agresivnější hledání objektu
                'alpha_matting_background_threshold': 10,  # Nižší číslo = agresivnější odstranění pozadí
                'alpha_matting_erode_size': 5              # Kolik pixelů masky odříznout (stisknout)
            }
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    # 1. AI zpracování s pokročilými parametry
                    input_data = uploaded_file.getvalue()
                    output_data = remove(input_data, session=session, **remove_kwargs)
                    img = Image.open(io.BytesIO(output_data)).convert("RGBA")
                    
                    # 2. Ořez (zbavení se přebytečného průhledného místa)
                    bbox = img.getbbox()
                    if bbox: img = img.crop(bbox)
                    
                    # 3. Změna velikosti se zachováním poměru stran
                    max_product_size = target_size - (2 * margin)
                    img.thumbnail((max_product_size, max_product_size), Image.Resampling.LANCZOS)
                    
                    # 4. Vytvoření bílého plátna a vycentrování
                    canvas = Image.new("RGB", (target_size, target_size), (255, 255, 255))
                    paste_x = (target_size - img.width) // 2
                    paste_y = (target_size - img.height) // 2
                    
                    # U bílých produktů na šedém pozadí někdy vznikají artefakty na hraně. 
                    # Tento krok se snaží masku o pixel stisknout, aby zmizely poslední šedé fleky.
                    # canvas.paste(img, (paste_x, paste_y), img) # Původní metoda
                    
                    # Pokročilá metoda vložení, která lépe zvládá problematické hrany po alpha mattingu
                    # Vyrobíme si masku z alfa kanálu
                    alpha_mask = img.split()[3]
                    canvas.paste(img, (paste_x, paste_y), mask=alpha_mask)
                    
                    # 5. Uložení do bufferu (JPG s optimalizací)
                    img_byte_arr = io.BytesIO()
                    canvas.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
                    
                    # 6. Přidání do ZIPu
                    file_name = uploaded_file.name.rsplit('.', 1)[0] + ".jpg"
                    zip_file.writestr(file_name, img_byte_arr.getvalue())
                    
                except Exception as e:
                    st.error(f"Chyba při zpracování {uploaded_file.name}: {e}")
                
                # Aktualizace progress baru
                progress_bar.progress((i + 1) / len(uploaded_files))
        
        st.success("✅ Vše hotovo!")
        
        st.download_button(
            label="⬇️ Stáhnout všechny upravené fotky (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="upravene_fotky.zip",
            mime="application/zip"
        )