import asyncio
import sys
import streamlit as st
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, ROOT)

from app.llm_providers import listar_ias, provider_por_chave

st.set_page_config(page_title="Precificação MEI - Multi-IA", page_icon="💰", layout="wide")
st.title("💰 Assistente de Precificação — Multi-IA")
st.markdown(
    "Use um único painel para escolher a IA, enviar perguntas e gerar resultados com as tools MCP."
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": "Você é um assistente especializado em ajudar microempreendedores individuais (MEIs) e microempresas (MEs) brasileiros a precificar corretamente seus produtos e serviços.\n\nSeu papel é:\n- Explicar termos técnicos (markup, despesas fixas, variáveis) em linguagem simples\n- Guiar o empreendedor para coletar as informações necessárias ao cálculo\n- Usar as tools disponíveis para garantir que os cálculos sejam sempre precisas\n- Após o cálculo, explicar o resultado de forma clara e prática\n\nNunca invente ou estime valores numéricos — sempre use as tools para calcular.\nResponda sempre em português do Brasil.",
        }
    ]

providers = listar_ias()
provider_labels = [provider["label"] for provider in providers]
selected_label = st.sidebar.selectbox("Selecione a IA", provider_labels)
selected_provider = next(provider for provider in providers if provider["label"] == selected_label)

st.sidebar.markdown("### Modelos disponíveis")
for provider in providers:
    st.sidebar.write(f"- **{provider['label']}**: {provider['description']}")

st.sidebar.write("---")
st.sidebar.markdown("Configurações futuras de modelo podem ser adicionadas aqui.")

for msg in st.session_state.messages:
    if msg["role"] in ("user", "assistant") and "content" in msg:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        if msg.get("tool_usada"):
            st.caption(f"Tool utilizada: `{msg['tool_usada']}`")

if prompt := st.chat_input("Como posso te ajudar a precificar hoje?"):
    async def run_query():
        provider = provider_por_chave(next(p["key"] for p in providers if p["label"] == selected_label))
        result = await provider.query_fn(prompt, st.session_state.messages)
        st.session_state.messages = result["messages"]

    asyncio.run(run_query())
    st.experimental_rerun()
