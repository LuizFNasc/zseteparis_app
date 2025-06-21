import streamlit as st
import requests

# Configurações da API Yampi via Dooki
YAMPI_STORE_ALIAS = st.secrets["YAMPI_STORE_ALIAS"]
YAMPI_TOKEN       = st.secrets["YAMPI_TOKEN"]
YAMPI_SECRET_KEY  = st.secrets["YAMPI_SECRET_KEY"]

YAMPI_API_URL    = (
    f"https://api.dooki.com.br/v2/{YAMPI_STORE_ALIAS}/catalog/products"
    "?include=skus&limit=200"
)

def get_yampi_products():
    headers = {
        "User-Token":      YAMPI_TOKEN,
        "User-Secret-Key": YAMPI_SECRET_KEY,
        "Accept":          "application/json"
    }
    resp = requests.get(YAMPI_API_URL, headers=headers)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    skus = []
    for prod in data:
        imgs = prod.get("images", [])
        for sku in prod.get("skus", {}).get("data", []):
            skus.append({
                "sku":           sku["sku"],
                "name":          prod["name"],
                "price_sale":    sku.get("price_sale", 0.0),
                "price_discount":sku.get("price_discount", 0.0),
                "purchase_url":  sku.get("purchase_url"),
                "images":        imgs
            })
    return skus

def decision_tree(ans, products):
    """
    Recebe answers e lista de produtos, retorna até 3 SKUs que 
    contêm no nome as palavras-chave definidas pela árvore.
    """
    ht  = ans["hair_type"]
    ch  = ans["chemistry"]
    obj = ans["objective"]
    freq= ans["frequency"]
    veg = ans["vegan"]
    size= ans["kit_size"]

    # Monta lista de keywords
    keys = []
    if ht in ["Liso","Ondulado"]:
        if ch in ["Alisamento","Progressiva"]:
            keys += ["Progressiva","Nano Liss"]
        else:
            if obj == "Hidratar":    keys += ["Teia"]
            if obj == "Reconstruir": keys += ["Gold"]
            if obj == "Detox":       keys += ["Detox","Genesis"]
    elif ht in ["Cacheado","Crespo"]:
        if obj == "Definição de cachos": keys += ["Cachos"]
        if obj == "Hidratar e nutrir":   keys += ["Teia","Alquimia"]
        if obj == "Detox":               keys += ["Detox","Genesis"]
    elif ht in ["Fino","Ralo"]:
        if obj == "Anti-queda / Anti-caspa": keys += ["Anti-Queda","Anti-Caspa"]
        if obj == "Reconstruir / Fortalecer": keys += ["Gold","Aminoácidos"]
    else:  # Grosso / Espesso
        if obj == "Reduzir volume": keys += ["Redutor de Volume"]
        if obj == "Nutrição intensa": keys += ["Óleos","Alquimia"]

    # Ajusta por vegano/natural
    if veg == "Sim":
        keys = [k for k in keys if "Vegano" in k or "Natural" in k] or keys

    # Ajusta por tamanho (procura no sku ou name)
    if size == "Home Care (500–900 ml)":
        size_marker = ["500","900","Home Care"]
    elif size == "Home Care Premium (1 kg)":
        size_marker = ["1 kg","Premium"]
    else:
        size_marker = ["2 kg","Profissional"]

    # Filtra produtos que contenham pelo menos uma key e um marker de tamanho
    def matches(p):
        text = (p["name"] + " " + p["sku"]).lower()
        return any(k.lower() in text for k in keys) and any(m.lower() in text for m in size_marker)

    filtered = [p for p in products if matches(p)]
    # Se não achar, relaxa só por keys
    if not filtered:
        filtered = [p for p in products if any(k.lower() in (p["name"]+p["sku"]).lower() for k in keys)]
    return filtered[:3]

# --- UI Streamlit ---
st.set_page_config(page_title="Diagnóstico Capilar", page_icon="✂️")
st.title("Diagnóstico Capilar ZSete Paris")

with st.form("quiz_form"):
    name      = st.text_input("Nome*")
    phone     = st.text_input("Telefone*", placeholder="(XX) XXXXX-XXXX")
    email     = st.text_input("E-mail*", placeholder="seu@email.com")
    hair_type = st.selectbox("1) Tipo de cabelo*", 
                 ["Liso","Ondulado","Cacheado","Crespo","Fino","Ralo","Grosso","Espesso"])
    chemistry = st.selectbox("2) Seu cabelo possui química?", 
                 ["Não","Tintura","Alisamento","Progressiva","Botox","Relaxamento"])
    objective = st.selectbox("3) Qual seu principal objetivo?",
                 ["Hidratar e nutrir","Reconstruir / Fortalecer",
                  "Reduzir volume e controlar frizz","Definição de cachos",
                  "Detox","Anti-queda / Anti-caspa","Proteção térmica e brilho"])
    frequency = st.selectbox("4) Frequência de uso?",
                 ["Home Care leve (1–2×/sem)","Tratamento intensivo (diário)",
                  "Profissional (salão)"])
    vegan     = st.selectbox("5) Prefere vegano / natural?", ["Não","Sim"])
    kit_size  = st.selectbox("6) Tamanho do kit?",
                 ["Home Care (500–900 ml)","Home Care Premium (1 kg)","Profissional (2 kg+)"])
    submitted = st.form_submit_button("Ver recomendações")

if submitted:
    required = [name, phone, email, hair_type, chemistry, objective]
    if not all(required):
        st.error("Por favor, preencha todos os campos obrigatórios.")
    else:
        answers = {
            "hair_type":  hair_type,
            "chemistry":  chemistry,
            "objective":  objective,
            "frequency":  frequency,
            "vegan":      vegan,
            "kit_size":   kit_size
        }
        products = get_yampi_products()
        recs     = decision_tree(answers, products)
        if recs:
            st.success("Aqui estão suas recomendações:")
            for p in recs:
                price = p["price_discount"]
                with st.expander(f"{p['name']} — R$ {price:.2f}"):
                    if p["images"]:
                        st.image(p["images"][0]["url"], width=200)
                    st.write(f"Preço original: R$ {p['price_sale']:.2f}")
                    st.markdown(f"[Comprar agora]({p['purchase_url']})")
        else:
            st.warning("Não encontramos produtos exatos para seu perfil. Veja abaixo algumas opções:")
            for p in products[:3]:
                st.write(f"- {p['name']} — R$ {p['price_discount']:.2f}")
