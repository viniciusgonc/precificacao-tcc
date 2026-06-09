import asyncio
import json
import os
import re
import sys
import time
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

ROOT = str(Path(__file__).resolve().parents[1])

st.set_page_config(
    page_title="Precificação MEI (Gemini)",
    page_icon="💰",
    layout="centered",
)

# Inicialização do cliente nativo do Google GenAI SDK
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# ── CONFIGURAÇÕES DE TEMA NA SIDEBAR ──────────────────────────────────────────
st.sidebar.title("🎨 Customização da Interface")

modo_tela = st.sidebar.radio("Modo de Exibição", ["Claro", "Escuro"], index=0)

paletas_cores = {
    "Roxo Real": {"primary": "#8B5CF6", "hover": "#7C3AED", "text": "#FFFFFF"},
    "Azul Clássico": {"primary": "#3B82F6", "hover": "#2563EB", "text": "#FFFFFF"},
    "Verde Esmeralda": {"primary": "#10B981", "hover": "#059669", "text": "#FFFFFF"},
    "Rosa Coral": {"primary": "#F43F5E", "hover": "#E11D48", "text": "#FFFFFF"}
}

cor_selecionada = st.sidebar.selectbox("Cor de Destaque (User)", list(paletas_cores.keys()))
ui_cor = paletas_cores[cor_selecionada]

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

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
}}

.stApp {{
    background-color: {css_bg_app};
}}

[data-testid="stSidebar"] {{
    background-color: {css_sidebar} !important;
    border-right: 1px solid {css_border};
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stChatMessage"] {{
    border-radius: 16px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    border: 1px solid {css_border};
}}

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

.status-box {{
    background: {css_bg_chat_bot};
    border-left: 3px solid {ui_cor['primary']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: {css_text_bot};
    margin: 4px 0;
}}

.fase-badge {{
    display: inline-block;
    background-color: {ui_cor['primary']}22;
    color: {ui_cor['primary']};
    border: 1px solid {ui_cor['primary']}55;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    font-weight: 600;
    margin-bottom: 8px;
}}
</style>
""", unsafe_allow_html=True)


SYSTEM_PROMPT = """
# ATUAÇÃO DO AGENTE
Você é um consultor de precificação para Microempreendedores Individuais (MEIs) brasileiros. Alie rigor matemático a um atendimento didático, transparente, focado em educação financeira e acolhedor.
 
## 1. REGRAS CRÍTICAS DE CONDUÇÃO (ANTI-ALUCINAÇÃO)
- PROIBIDO CÁLCULO MANUAL: Você não calcula nada de cabeça. Valores numéricos de preço e ponto de equilíbrio devem vir EXCLUSIVAMENTE do retorno das ferramentas MCP. Nunca deduza valores no texto.
- PROIBIDO PARALELISMO DEPENDENTE: Nunca chame calcular_ponto_de_equilibrio junto com ferramentas de preço no mesmo turno. Aguarde o preço ser gerado no backend pelo Python para, no passo sequencial seguinte do loop, usar o valor exato retornado.
- PROIBIDO CHAMAR TOOLS DE PREÇO ANTES DO SINAL VERDE: As ferramentas calcular_preco_por_margem_contribuicao, calcular_preco_unitario e calcular_produto_unico só podem ser acionadas DEPOIS que o usuário enviar a mensagem de confirmação. Antes disso, apenas apresente o checklist e aguarde.
 
## 2. PROTOCOLO SEQUENCIAL DE TRIAGEM
 
### FASE 1: Insumos e Custos Diretos (R$)
- Identifique se o produto opera em LOTE ou ITEM ÚNICO.
- **Diferenciação de Volume:** Explique brevemente ao usuário que vender um **produto único** (ex: um serviço exclusivo ou item artesanal principal) exige que ele carregue uma responsabilidade maior sobre a estrutura da empresa, enquanto uma operação de **múltiplos produtos** permite diluir esses percentuais entre diferentes vendas.
- Se for lote, apresente a divisão em reais e confirme o custo unitário bruto de base com o usuário antes de avançar.
- Se houver custos diretos unitários já informados, registre-os como custo unitário de insumos.
 
### FASE 2: Despesas Variáveis (%)
- Identifique taxas de cartões, marketplaces, impostos sobre venda, comissões e outros percentuais.
- Use consolidar_despesas_variaveis se houver taxas picadas.
- Confirme o percentual consolidado com o usuário.
- Custos variáveis em reais (frete fixo por unidade, embalagem) somam ao custo da Fase 1, nunca como percentual.
 
### FASE 3: Despesas Fixas Estruturais (R$ para %)
- Solicite a soma das contas fixas mensais e o faturamento mensal geral da empresa.
- Chame obrigatoriamente converter_custo_fixo_para_percentual. Mostre o resultado em %.
- Reforce o impacto: se o MEI vende múltiplos produtos, esse percentual é o que este produto específico vai "carregar" para ajudar a pagar a estrutura interna.
 
### FASE 4: Diagnóstico, Educação e Coleta de Margem Alvo
- Chame a ferramenta validar_percentuais com os dados coletados.
- **Momento Didático (Markup vs. Margem):** Explique de forma simples a diferença entre as estratégias:
    * *Markup:* Aplica um multiplicador sobre o custo. É bom para comércio com muitos itens, mas perigoso se o custo fixo for alto, pois pode inflar o preço e travar as vendas.
    * *Margem de Contribuição:* Define quanto do preço final (em %) sobra para pagar os custos fixos e gerar lucro real. É mais seguro para o MEI proteger seu caixa.
- **Investigação da Margem Desejada:** NUNCA sugira um valor fixo de 40% por padrão. Pergunte abertamente ao usuário qual o percentual de lucro ou margem de contribuição ele deseja obter com a venda, explicando que isso depende do nicho e do mercado. Aguarde a resposta dele sobre a margem desejada.
- Se o custo fixo percentual calculado for acima de 30%, alerte o usuário e recomende o uso da estratégia de Margem de Contribuição Alvo em vez do Markup Tradicional.
- Após o usuário definir a margem/lucro desejado, apresente o checklist abaixo.
 
Modelo de checklist:
"Perfeito! Já tenho o diagnóstico estrutural do seu negócio em mãos. Para não darmos um tiro no escuro, vou realizar o cálculo usando estes valores exatos do seu negócio:
- Custo Unitário de Insumos: R$ X,XX
- Taxas e Despesas Variáveis: X,X%
- Custo Fixo (% sobre faturamento): X,X%
- Dinâmica de Venda: [Único Produto / Múltiplos Produtos]
- Estratégia Escolhida: [Margem de Contribuição Alvo de X% ou Markup Tradicional com X% de Lucro]
 
Me confirme se os valores estão corretos e me dê o seu sinal verde (digite 'Pode calcular') para eu rodar o sistema e te entregar o preço ideal de vitrine e a sua meta de vendas!"
 
### FASE 5: Execução Pós-Sinal Verde e Transparência
- Só realize o cálculo após o usuário confirmar com "Pode calcular" ou equivalente.
- Apresente o resultado do Python detalhando cada linha: custo, valor destinado às taxas e margem de contribuição em reais.
 
### FASE 6: Ponto de Equilíbrio
- Dispare calcular_ponto_de_equilibrio de forma isolada usando os valores reais calculados.
- Explique ao usuário quantas unidades ele precisa vender para cobrir os custos fixos mensais com base no cenário dele (seja diluído em múltiplos produtos ou focado no produto único).
 
## 3. MAPEAMENTO DE PARÂMETROS MCP
- consolidar_despesas_variaveis -> taxa_maquininha_cartao, comissao_marketplace, imposto_sobre_venda, outros_percentuais
- converter_custo_fixo_para_percentual -> custo_fixo_mensal, faturamento_mensal
- validar_percentuais -> despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_preco_unitario -> custo_total, quantidade, despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_produto_unico -> custo_producao, despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_ponto_de_equilibrio -> custos_fixos_mensais, preco_unitario, custo_unitario
- calcular_preco_por_margem_contribuicao -> custo_unitario, despesas_variaveis, margem_contribuicao_alvo
 
## 4. REGRAS DE SINTAXE E SEGURANÇA
- Percentuais sempre na base 100 (ex: 8% = 8.0, NUNCA 0.08).
- Parâmetros numéricos sem aspas (ex: 10.0, 550.0).
- Nunca escreva marcações de ferramenta no texto final, como "<function=...>".
- Nunca invente valores ausentes. Faça perguntas objetivas quando faltar info.
- Idioma: Português do Brasil.
"""

# ── HELPERS GLOBAIS E TRADUTOR DE SCHEMA GEMINI ────────────────────────────────
CAMPOS_VALIDOS_API = {"role", "content", "name", "tool_call_id", "tool_calls"}

FRASES_SINAL_VERDE = [
    "pode calcular",
    "calcular agora",
    "confirmo, pode calcular",
    "confirmo pode calcular",
    "sim, pode calcular",
    "pode calcular!",
]

TOOLS_CALCULO_FINAL = {
    "calcular_preco_unitario",
    "calcular_produto_unico",
    "calcular_preco_por_margem_contribuicao",
}

TOOLS_PONTO_EQUILIBRIO = {"calcular_ponto_de_equilibrio"}

def deve_exibir(msg: dict) -> bool:
    if msg["role"] not in ("user", "assistant"):
        return False
    if msg.get("tool_calls"):
        return False
    conteudo = msg.get("content")
    if not conteudo or not str(conteudo).strip():
        return False
    return True

def detectar_sinal_verde(texto: str) -> bool:
    texto_normalizado = texto.strip().lower()
    return any(frase in texto_normalizado for frase in FRASES_SINAL_VERDE)

def atualizar_contexto_negocio(texto: str):
    keywords = [
        "não vendo só", "não vendo apenas", "também vendo", "outros produtos",
        "loja física", "loja online", "vendo online", "vendo no instagram",
        "vendo no whatsapp", "home office", "sem loja", "autônomo",
    ]
    for kw in keywords:
        if kw in texto.lower():
            obs = texto.strip()
            if obs not in st.session_state.dados_precificacao["contexto_negocio"]:
                st.session_state.dados_precificacao["contexto_negocio"].append(obs)
            break

def limpar_resposta(texto: str) -> str:
    if not texto:
        return texto
    texto = re.sub(r'<function=\w+>\s*\{.*?\}\s*</function>', '', texto, flags=re.DOTALL)
    texto = re.sub(r'<function=\w+>.*', '', texto, flags=re.DOTALL)
    linhas = [linha for inline in [[l for l in texto.splitlines() if l.strip()]] for linha in inline]
    return '\n'.join(linhas).strip()

def mensagens_para_api(messages: list) -> list:
    api_msgs = []
    for i, msg in enumerate(messages):
        if msg["role"] == "system":
            api_msgs.append({k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API})
            continue

        is_old_tool_log = False
        if msg["role"] == "tool" or (msg["role"] == "assistant" and msg.get("tool_calls")):
            user_msgs_depois = sum(
                1 for m in messages[i + 1:] if m["role"] == "user"
            )
            if user_msgs_depois >= 2:
                is_old_tool_log = True

        if not is_old_tool_log:
            filtered_msg = {k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API}
            api_msgs.append(filtered_msg)

    return api_msgs

# ── TRADUTOR DE HISTÓRICO CORRIGIDO (PRESERVA PARTS NATIVOS DO GOOGLE) ──────────
def converter_para_gemini(messages: list) -> list:
    gemini_contents = []
    for msg in messages:
        if msg["role"] == "system":
            continue
            
        role = "user" if msg["role"] in ("user", "tool") else "model"
        parts = []
        
        if msg["role"] == "user":
            parts.append(types.Part.from_text(text=msg["content"]))
        elif msg["role"] == "assistant":
            # SALVAREI AS PARTES ORIGINAIS (TEXTO + PENSAMENTO + TOOL) DE FORMA INTACTA
            if "gemini_parts" in msg and msg["gemini_parts"]:
                parts.extend(msg["gemini_parts"])
            else:
                if msg.get("content"):
                    parts.append(types.Part.from_text(text=msg["content"]))
        elif msg["role"] == "tool":
            content_json = msg["content"]
            if isinstance(content_json, str):
                try:
                    content_json = json.loads(content_json)
                except:
                    content_json = {"raw_result": content_json}
            parts.append(types.Part.from_function_response(
                name=msg["name"],
                response=content_json
            ))
            
        if gemini_contents and gemini_contents[-1].role == role:
            gemini_contents[-1].parts.extend(parts)
        else:
            gemini_contents.append(types.Content(role=role, parts=parts))
            
    return gemini_contents

def label_fase(fase: int) -> str:
    labels = {
        1: "Fase 1 — Custos Diretos",
        2: "Fase 2 — Despesas Variáveis",
        3: "Fase 3 — Despesas Fixas",
        4: "Fase 4 — Diagnóstico & Checklist",
        5: "Fase 5 — Cálculo Autorizado",
        6: "Fase 6 — Ponto de Equilíbrio",
    }
    return labels.get(fase, f"Fase {fase}")

def simular_streaming_texto(texto: str):
    if not texto:
        return
    placeholder = st.empty()
    texto_acumulado = ""
    for palavra in texto.split(" "):
        texto_acumulado += palavra + " "
        placeholder.markdown(texto_acumulado + "▌")
        time.sleep(0.015)
    placeholder.markdown(texto_acumulado)

# ── STATE MACHINE — Inicialização do session_state ──────────────────────────────
if "fase_protocolo" not in st.session_state:
    st.session_state.fase_protocolo = 1

if "dados_precificacao" not in st.session_state:
    st.session_state.dados_precificacao = {
        "custo_unitario": None,
        "quantidade": None,
        "tipo_produto": None,
        "despesas_variaveis": None,
        "custo_fixo_mensal": None,
        "faturamento_mensal": None,
        "despesas_fixas_pct": None,
        "estrategia": None,
        "lucro_ou_margem_alvo": None,
        "preco_calculado": None,
        "contexto_negocio": [],
    }

if "sinal_verde" not in st.session_state:
    st.session_state.sinal_verde = False

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

# ── Indicador de fase na sidebar ─────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### 📍 Progresso da Consulta")
fases_labels = ["Custos Diretos", "Despesas Variáveis", "Despesas Fixas", "Diagnóstico", "Cálculo", "Equilíbrio"]
for i, fl in enumerate(fases_labels, start=1):
    if i < st.session_state.fase_protocolo:
        st.sidebar.markdown(f"✅ Fase {i}: {fl}")
    elif i == st.session_state.fase_protocolo:
        st.sidebar.markdown(f"🔵 **Fase {i}: {fl}** ← atual")
    else:
        st.sidebar.markdown(f"⬜ Fase {i}: {fl}")

# Botão para reiniciar a consulta
st.sidebar.divider()
if st.sidebar.button("🔄 Nova Consulta"):
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.fase_protocolo = 1
    st.session_state.sinal_verde = False
    st.session_state.dados_precificacao = {
        "custo_unitario": None, "quantidade": None, "tipo_produto": None,
        "despesas_variaveis": None, "custo_fixo_mensal": None,
        "faturamento_mensal": None, "despesas_fixas_pct": None,
        "estrategia": None, "lucro_ou_margem_alvo": None,
        "preco_calculado": None, "contexto_negocio": [],
    }
    st.rerun()

# ── Render histórico ──────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if not deve_exibir(msg):
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
    if msg.get("tool_usada"):
        with st.expander(f"⚙️ Tool utilizada: `{msg['tool_usada']}`", expanded=False):
            st.caption("Esta ferramenta MCP foi disparada com sucesso para computar os dados de forma exata.")

# ── Query / Fluxo do Agente Autônomo Gemini com Loop Iterativo ────────────────
async def query_agent(prompt: str):
    atualizar_contexto_negocio(prompt)

    if detectar_sinal_verde(prompt):
        st.session_state.sinal_verde = True
        if st.session_state.fase_protocolo == 4:
            st.session_state.fase_protocolo = 5

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

                    # ── INJEÇÃO DINÂMICA DE TOOLS CONFIGURADA PARA SCHEMA GEMINI ───────
                    gemini_declarations = []
                    for tool in tools_response.tools:
                        if not st.session_state.sinal_verde:
                            if tool.name in TOOLS_CALCULO_FINAL or tool.name in TOOLS_PONTO_EQUILIBRIO:
                                continue
                        
                        gemini_declarations.append({
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        })

                    gemini_tools = [{"function_declarations": gemini_declarations}] if gemini_declarations else None

                    tool_usada = None
                    resposta_final = ""

                    # ── O LOOP DE AGENTE 'WHILE TRUE' RECURSIVO INTEGRADO ────────────────
                    while True:
                        mensagens_api = mensagens_para_api(st.session_state.messages)
                        
                        if not st.session_state.sinal_verde and st.session_state.fase_protocolo < 5:
                            lembrete_fase = {
                                "role": "system",
                                "content": (
                                    f"[GUARDRAIL INTERNO] O protocolo está na {label_fase(st.session_state.fase_protocolo)}. "
                                    f"O sinal verde ainda NÃO foi dado pelo usuário. Preencha o checklist com os valores reais das ferramentas."
                                    f"Dados estruturais atuais: {json.dumps(st.session_state.dados_precificacao, ensure_ascii=False)}."
                                )
                            }
                            mensagens_api = mensagens_api + [lembrete_fase]

                        gemini_contents = converter_para_gemini(mensagens_api)

                        status_box.markdown('<div class="status-box">🧠 Consultando inteligência de negócios (Gemini 3.1)…</div>', unsafe_allow_html=True)
                        
                        config = types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            tools=gemini_tools,
                            temperature=0.1
                        )
                        
                        response = await client.aio.models.generate_content(
                            model="gemini-3.1-flash-lite",
                            contents=gemini_contents,
                            config=config,
                        )

                        tool_calls = response.function_calls

                        if not tool_calls:
                            try:
                                resposta_final = limpar_resposta(response.text)
                            except:
                                resposta_final = "Cálculos concluídos com sucesso pelo motor estrutural."
                            break

                        openai_tool_calls = []
                        for tc in tool_calls:
                            call_id = f"call_{int(time.time())}_{tc.name}"
                            args_dict = dict(tc.args) if tc.args else {}
                            openai_tool_calls.append({
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(args_dict, ensure_ascii=False)
                                }
                            })

                        # SALVANDO OS PARTS NATIVOS COMPLETO (INCLUINDO ASSINATURAS DO GOOGLE)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": openai_tool_calls,
                            "gemini_parts": list(response.candidates[0].content.parts) if response.candidates else []
                        })

                        for tc in tool_calls:
                            tool_name = tc.name
                            tool_args = dict(tc.args) if tc.args else {}
                            tool_usada = tool_name

                            status_box.markdown(f'<div class="status-box">⚙️ Executando: <code>{tool_name}</code>…</div>', unsafe_allow_html=True)

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

                            # ── ATUALIZAÇÕES DOS ESTADOS DE FORMA INDENTADA E LIMPA ──
                            if tool_name == "converter_custo_fixo_para_percentual" and "percentual" in result_dict:
                                st.session_state.dados_precificacao["despesas_fixas_pct"] = result_dict["percentual"]
                                if st.session_state.fase_protocolo <= 3:
                                    st.session_state.fase_protocolo = 4
                            elif tool_name == "consolidar_despesas_variaveis" and "despesas_variaveis_totais" in result_dict:
                                st.session_state.dados_precificacao["despesas_variaveis"] = result_dict["despesas_variaveis_totais"]
                                if st.session_state.fase_protocolo <= 2:
                                    st.session_state.fase_protocolo = 3
                            elif tool_name == "validar_percentuais":
                                if st.session_state.fase_protocolo <= 3:
                                    st.session_state.fase_protocolo = 4
                            elif tool_name in TOOLS_CALCULO_FINAL:
                                preco = result_dict.get("preco_unitario") or result_dict.get("preco_final") or result_dict.get("preco_venda")
                                if preco:
                                    st.session_state.dados_precificacao["preco_calculado"] = preco
                                st.session_state.fase_protocolo = 6
                            elif tool_name == "calcular_ponto_de_equilibrio":
                                st.session_state.fase_protocolo = 6

                            st.session_state.messages.append({
                                "role": "tool",
                                "tool_call_id": openai_tool_calls[0]["id"],
                                "name": tool_name,
                                "content": json.dumps(result_dict, ensure_ascii=False),
                            })

                        # Delay protetivo estável de 2 segundos para o rate limit
                        await asyncio.sleep(2.0)

                    status_box.empty()
                    simular_streaming_texto(resposta_final)

                    if tool_usada:
                        with st.expander(f"⚙️ Tool utilizada: `{tool_usada}`", expanded=False):
                            st.caption("Esta ferramenta MCP foi disparada com sucesso para computar os dados de forma exata.")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": resposta_final,
                        "tool_usada": tool_usada,
                        "gemini_parts": list(response.candidates[0].content.parts) if response.candidates else []
                    })

        except Exception as e:
            import traceback
            status_box.error(f"Ocorreu uma inconsistência no processamento: {str(e)}")
            st.code(traceback.format_exc(), language="text")

if prompt := st.chat_input("Como posso te ajudar a precificar hoje?"):
    asyncio.run(query_agent(prompt))