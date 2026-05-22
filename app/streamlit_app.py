import asyncio
import json
import os
import sys
import time
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from groq import AsyncGroq
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

ROOT = str(Path(__file__).resolve().parents[1])

st.set_page_config(
    page_title="Precificação MEI",
    page_icon="💰",
    layout="centered",
)

# ── CONFIGURAÇÕES DE TEMA NA SIDEBAR ──────────────────────────────────────────
st.sidebar.title("🎨 Customização da Interface")

# Escolha do modo de exibição
modo_tela = st.sidebar.radio("Modo de Exibição", ["Claro", "Escuro"], index=0)

# Pequena paleta conceitual de cores para os balões do usuário
paletas_cores = {
    "Roxo Real": {"primary": "#8B5CF6", "hover": "#7C3AED", "text": "#FFFFFF"},
    "Azul Clássico": {"primary": "#3B82F6", "hover": "#2563EB", "text": "#FFFFFF"},
    "Verde Esmeralda": {"primary": "#10B981", "hover": "#059669", "text": "#FFFFFF"},
    "Rosa Coral": {"primary": "#F43F5E", "hover": "#E11D48", "text": "#FFFFFF"}
}

cor_selecionada = st.sidebar.selectbox("Cor de Destaque (User)", list(paletas_cores.keys()))
ui_cor = paletas_cores[cor_selecionada]

# Definição das variáveis CSS baseadas no modo de exibição selecionado
if modo_tela == "Claro":
    css_bg_app = "#F3F4F6"
    css_bg_chat_bot = "#FFFFFF"
    css_text_bot = "#1F2937"
    css_border = "#E5E7EB"
    css_sidebar = "#FFFFFF"
else:
    css_bg_app = "#111827"
    css_bg_chat_bot = "#1F2937"
    css_text_bot = "#F9FAFB"
    css_border = "#374151"
    css_sidebar = "#1F2937"

# ── CUSTOM CSS DINÂMICO INJETADO ──────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
}}

/* Cor de fundo da aplicação */
.stApp {{
    background-color: {css_bg_app};
}}

/* Estilização da Sidebar */
[data-testid="stSidebar"] {{
    background-color: {css_sidebar} !important;
    border-right: 1px solid {css_border};
}}

/* Top header area limpa */
[data-testid="stHeader"] {{
    background: transparent;
}}

/* Customização geral dos balões do Streamlit */
[data-testid="stChatMessage"] {{
    border-radius: 16px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    border: 1px solid {css_border};
}}

/* Distinção visual para balões de mensagens do Usuário e do Assistente */
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) {{
    background-color: {ui_cor['primary']} !important;
    color: {ui_cor['text']} !important;
    border: none;
}}

[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) p,
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) li,
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) strong {{
    color: {ui_cor['text']} !important;
}}

[data-testid="stChatMessage"]:has([data-testid="assistant-avatar"]) {{
    background-color: {css_bg_chat_bot} !important;
    color: {css_text_bot} !important;
}}

/* Estilização das abinhas retráteis (Expanders) de Tools */
.stExpander {{
    background-color: {css_bg_chat_bot} !important;
    border: 1px solid {css_border} !important;
    border-radius: 10px !important;
    margin-top: 6px;
}}

.stExpander summary {{
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    color: {ui_cor['primary']} !important;
    font-weight: 500;
}}

/* Status info boxes de carregamento sutil */
.status-box {{
    background: {css_bg_chat_bot};
    border-left: 3px solid {ui_cor['primary']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: {css_text_bot};
    margin: 4px 0;
}}
</style>
""", unsafe_allow_html=True)


SYSTEM_PROMPT = """
# ATUAÇÃO DO AGENTE
Você é um consultor de precificação para Microempreendedores Individuais (MEIs) brasileiros. Alie rigor matemático a um atendimento didático, transparente e acolhedor.

## 1. REGRAS CRÍTICAS DE CONDUÇÃO (ANTI-ALUCINAÇÃO)
- PROIBIDO CÁLCULO MANUAL: Você não calcula nada de cabeça. Valores numéricos de preço e ponto de equilíbrio devem vir EXCLUSIVAMENTE do retorno das ferramentas MCP. Nunca deduza valores no texto.
- PROIBIDO PARALELISMO DEPENDENTE: Nunca chame calcular_ponto_de_equilibrio junto com ferramentas de preço (calcular_preco_por_margem_contribuicao ou calcular_preco_unitario). Aguarde o preço ser gerado no backend pelo Python para, no turno seguinte, usar o valor exato.

## 2. PROTOCOLO SEQUENCIAL DE TRIAGEM
Siga rigorosamente as etapas abaixo. Mesmo que o usuário envie os dados todos de uma vez, passe pelas fases de confirmação de forma transparente.

### FASE 1: Insumos e Custos Diretos (R$)
- Identifique se o produto opera em LOTE ou ITEM UNICO.
- Se for lote, apresente a divisão em reais e confirme o custo unitário bruto de base com o usuário antes de avançar.

### FASE 2: Despesas Variáveis (%)
- Identifique taxas de cartões ou marketplaces. Use consolidar_despesas_variaveis se houver taxas picadas.
- Confirme o percentual consolidado com o usuário. Custos variáveis em reais (como frete fixo) devem ser somados direto no custo bruto da Fase 1, nunca aqui.

### FASE 3: Despesas Fixas Estruturais (R$ para %)
- Solicite a soma das contas fixas mensais (aluguel, luz, agua, DAS) e o faturamento mensal geral da empresa.
- Chame obrigatoriamente converter_custo_fixo_para_percentual. Mostre o resultado em % ao usuário e explique o impacto desse peso na estrutura do negócio.

### FASE 4: Diagnóstico e Checklist de Confirmação (UX OBRIGATÓRIA)
- Chame a ferramenta validar_percentuais com os dados coletados.
- Se o custo fixo percentual for abusivo (acima de 30% ou 40%), avise o usuário que o Markup tradicional gerará um preço inviável de mercado. Interrompa a rota de Markup e proponha a estratégia de Margem de Contribuição Alvo (sugira 40% de margem).
- ANTES de acionar qualquer ferramenta de cálculo final de preço, você deve parar a geração e apresentar exatamente este modelo de mensagem na tela:

"Perfeito! Já tenho o diagnóstico estrutural do seu negócio em mãos. Para não darmos um tiro no escuro, vou realizar o cálculo usando estes valores exatos do seu negócio:
- Custo Unitário de Insumos: R$ X,XX
- Taxas e Despesas Variáveis: X,X%
- Estratégia Escolhida: [Margem de Contribuição Alvo de X% ou Markup Tradicional com X% de Lucro]

Me confirme se os valores estão corretos e me dê o seu sinal verde (digite 'Pode calcular') para eu rodar o sistema e te entregar o preço ideal de vitrine e a sua meta de vendas!"

### FASE 5: Execução Pós-Sinal Verde e Transparência
- SÓ acione as ferramentas de preço final (calcular_preco_por_margem_contribuicao, calcular_preco_unitario ou calcular_produto_unico) após o usuário responder confirmando o checklist da Fase 4.
- Assim que ele autorizar, dispare a tool de preço. Apresente o resultado do Python detalhando cada linha: custo, valor retornado que vai para as taxas e valor que sobra.
- No turno seguinte, dispare calcular_ponto_de_equilibrio de forma isolada e exiba a meta física de quantas unidades ele precisa vender no mês para pagar a estrutura.

## 3. MAPEAMENTO DE PARAMETROS MCP
Gere os JSONs usando rigorosamente a nomenclatura do Python:
- consolidar_despesas_variaveis -> taxa_maquininha_cartao, comissao_marketplace, imposto_sobre_venda, outros_percentuais
- converter_custo_fixo_para_percentual -> custo_fixo_mensal, faturamento_mensal
- validar_percentuais -> despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_preco_unitario -> custo_total, quantidade, despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_produto_unico -> custo_producao, despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_ponto_de_equilibrio -> custos_fixos_mensais, preco_unitario, custo_unitario
- calcular_preco_por_margem_contribuicao -> custo_unitario, despesas_variaveis, margem_contribuicao_alvo

## 4. REGRAS DE SINTAXE
- Percentuais: Sempre na base 100 (ex: 8% = 8.0, 53.33% = 53.33). Nunca use frações decimais (0.08).
- Sem marcas no texto: Nunca escreva marcas como "<function=...>" ou semelhantes por extenso nas respostas.
- Tipagem pura: Parâmetros numéricos sem aspas (ex: 10.0, 550.0).
- Idioma: Português do Brasil.
"""

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 💰 Assistente de Precificação")
st.caption("Converse naturalmente sobre como precificar seus produtos e serviços.")
st.divider()

# ── Session state ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

# ── Helpers ─────────────────────────────────────────────────────────────────────
CAMPOS_VALIDOS_API = {"role", "content", "name", "tool_call_id", "tool_calls"}

# ── EFICIÊNCIA DE TOKENS: FILTRO INTELIGENTE IMPLEMENTADO ABAIXO ──────────────────
def mensagens_para_api(messages: list) -> list:
    api_msgs = []
    for i, msg in enumerate(messages):
        # O prompt do sistema viaja sempre intacto
        if msg["role"] == "system":
            api_msgs.append({k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API})
            continue
        
        # Identifica se é um log de execução de ferramenta antigo
        is_old_tool_log = False
        if msg["role"] == "tool" or (msg["role"] == "assistant" and msg.get("tool_calls")):
            # Se houver qualquer mensagem de texto final do assistente depois dela, o bloco antigo caducou
            for posterior_msg in messages[i+1:]:
                if posterior_msg["role"] == "assistant" and posterior_msg.get("content") and not posterior_msg.get("tool_calls"):
                    is_old_tool_log = True
                    break
        
        # Se não for um log de ferramenta do passado, envia com segurança para a API
        if not is_old_tool_log:
            filtered_msg = {k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API}
            api_msgs.append(filtered_msg)
            
    return api_msgs

def deve_exibir(msg: dict) -> bool:
    if msg["role"] not in ("user", "assistant"):
        return False
    if msg.get("tool_calls"):
        return False
    conteudo = msg.get("content")
    if not conteudo or not str(conteudo).strip():
        return False
    return True

# Função para simular o efeito de máquina de escrever do ChatGPT (Streaming)
def simular_streaming_texto(texto: str):
    placeholder = st.empty()
    texto_acumulado = ""
    for palavra in texto.split(" "):
        texto_acumulado += palavra + " "
        placeholder.markdown(texto_acumulado + "▌")
        time.sleep(0.015)
    placeholder.markdown(texto_acumulado)

# ── Render histórico de conversas ───────────────────────────────────────────────
for msg in st.session_state.messages:
    if not deve_exibir(msg):
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
    if msg.get("tool_usada"):
        with st.expander(f"⚙️ Tool utilizada: `{msg['tool_usada']}`", expanded=False):
            st.caption("Esta ferramenta MCP foi disparada com sucesso para computar os dados de forma exata.")

# ── Query / Fluxo do Agente de IA ───────────────────────────────────────────────
async def query_agent(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_box = st.empty()

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(ROOT, "server.py")]
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    status_box.markdown('<div class="status-box">🔌 Sincronizando ferramentas de precificação…</div>', unsafe_allow_html=True)
                    tools_response = await session.list_tools()

                    groq_tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema,
                            },
                        }
                        for tool in tools_response.tools
                    ]

                    groq_client = AsyncGroq()
                    tool_usada = None

                    status_box.markdown('<div class="status-box">🧠 Consultando inteligência de negócios…</div>', unsafe_allow_html=True)
                    response = await groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=mensagens_para_api(st.session_state.messages),
                        tools=groq_tools,
                    )

                    message = response.choices[0].message

                    if message.tool_calls:
                        st.session_state.messages.append(
                            message.model_dump(exclude_none=True)
                        )

                        for tool_call in message.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            tool_usada = tool_name

                            status_box.markdown(f'<div class="status-box">⚙️ Executando operação estrutural: `{tool_name}`…</div>', unsafe_allow_html=True)

                            result = await session.call_tool(tool_name, tool_args)

                            try:
                                if result.content:
                                    raw = result.content[0]
                                    result_text = raw.text if hasattr(raw, "text") else str(raw)
                                    result_dict = json.loads(result_text.strip()) if result_text.strip() else {}
                                else:
                                    result_dict = {}
                            except (json.JSONDecodeError, AttributeError, IndexError) as e:
                                result_dict = {"raw_result": str(e)}

                            st.session_state.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": json.dumps(result_dict, ensure_ascii=False),
                            })

                        status_box.markdown('<div class="status-box">✍️ Estruturando resposta interpretada…</div>', unsafe_allow_html=True)
                        final_response = await groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=mensagens_para_api(st.session_state.messages),
                        )
                        resposta_final = final_response.choices[0].message.content
                    else:
                        resposta_final = message.content

                    status_box.empty()
                    simular_streaming_texto(resposta_final)

                    if tool_usada:
                        with st.expander(f"⚙️ Tool utilizada: `{tool_usada}`", expanded=False):
                            st.caption("Esta ferramenta MCP foi disparada com sucesso para computar os dados de forma exata.")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": resposta_final,
                        "tool_usada": tool_usada,
                    })

        except Exception as e:
            import traceback
            status_box.error(f"Ocorreu uma inconsistência no processamento: {str(e)}")
            st.code(traceback.format_exc(), language="text")

if prompt := st.chat_input("Como posso te ajudar a precificar hoje?"):
    asyncio.run(query_agent(prompt))