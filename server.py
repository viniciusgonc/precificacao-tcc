import json
import sys
from mcp.server.fastmcp import FastMCP
from src.precificacao.precificacao import Precificacao

mcp = FastMCP("Assistente de Precificação para MEIs")
precificador = Precificacao()


@mcp.tool()
def consolidar_despesas_variaveis(
    taxa_maquininha_cartao: float = 0.0,
    comissao_marketplace: float = 0.0,
    imposto_sobre_venda: float = 0.0,
    outros_percentuais: float = 0.0
) -> str:
    """
    Agrupa e soma múltiplos custos variáveis percentuais (%) comuns em vendas.

    DIRETRIZ DE USO PARA A IA:
    Use esta ferramenta quando o microempreendedor relatar que possui várias taxas 
    percentuais picadas incidindo sobre a venda (ex: taxa da maquininha, comissão de 
    plataformas como Shopee/Mercado Livre/iFood e impostos). 
    
    REGRA CRÍTICA SOBRE VALORES EM REAIS (R$):
    Se o usuário mencionar uma despesa variável que tem valor fixo em REAIS por unidade 
    (ex: 'gasto R$ 3,00 de embalagem' ou 'R$ 5,00 de frete fixo'), você NÃO deve passar 
    esses valores para cá. Oriente o usuário que custos nominais (em reais) devem ser 
    somados DIRETAMENTE junto ao custo de materiais/produção do produto. Esta ferramenta 
    aceita APENAS taxas puramente percentuais (%).

    Args:
        taxa_maquininha_cartao: Percentual (%) cobrado pela máquina de cartão (ex: 3.5).
        comissao_marketplace: Percentual (%) cobrado por marketplaces/apps (ex: 12.0).
        imposto_sobre_venda: Percentual (%) de impostos sobre a venda (ex: 4.0).
        outros_percentuais: Outras taxas proporcionais ao preço (ex: comissões).
    """
    print("[MCP] consolidar_despesas_variaveis foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.consolidar_despesas_variaveis(
            taxa_maquininha_cartao=taxa_maquininha_cartao,
            comissao_marketplace=comissao_marketplace,
            imposto_sobre_venda=imposto_sobre_venda,
            outros_percentuais=outros_percentuais
        )
        print(f"[MCP] resultado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


@mcp.tool()
def converter_custo_fixo_para_percentual(
    custo_fixo_mensal: float,
    faturamento_mensal: float
) -> str:
    """
    Converte custos fixos estruturais em reais (R$) no percentual (%) que eles pesam no negócio.

    DIRETRIZ DE USO PARA A IA:
    Chame esta ferramenta obrigatoriamente quando o empreendedor fornecer custos fixos em 
    dinheiro (ex: aluguel, luz, internet, taxa do MEI) e um faturamento mensal estimado. 
    O método de precificação por Markup exige que o custo fixo entre como percentual. O 
    retorno desta ferramenta fornecerá a despesa_fixa percentual exata necessária para as 
    ferramentas de cálculo e validação.

    Args:
        custo_fixo_mensal: Soma em reais de todas as contas fixas da estrutura do negócio.
        faturamento_mensal: Faturamento total bruto estimado ou real da empresa no mês.
    """
    print("[MCP] converter_custo_fixo_para_percentual foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.converter_custo_fixo_para_percentual(
            custo_fixo_mensal=custo_fixo_mensal,
            faturamento_mensal=faturamento_mensal
        )
        print(f"[MCP] resultado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


@mcp.tool()
def validar_percentuais(
    despesas_variaveis: float,
    despesas_fixas: float,
    lucro_pretendido: float
) -> str:
    """
    Verifica preventivamente se a combinação de despesas e lucros permite um cálculo viável.

    DIRETRIZ DE USO PARA A IA:
    Aja como um guardião de segurança. Chame esta ferramenta SEMPRE antes de rodar os cálculos 
    finais de preço ou simulações. Se a soma dos percentuais for igual ou maior que 100%, o 
    cálculo quebrará matematicamente (divisão por zero ou preço negativo). 
    
    Se o campo 'valido' retornar False, você deve INTERROMPER o processo de cálculo imediatamente 
    e explicar ao usuário que as taxas e o lucro desejado estão altos demais para a estrutura 
    atual, orientando-o amigavelmente a rever as metas.

    Args:
        despesas_variaveis: Percentual (%) total de custos variáveis por venda.
        despesas_fixas: Percentual (%) de custos fixos rateados sobre o faturamento.
        lucro_pretendido: Percentual (%) de margem de lucro líquido desejado pelo MEI.
    """
    print("[MCP] validar_percentuais foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.validar_percentuais(
            despesas_variaveis=despesas_variaveis,
            despesas_fixas=despesas_fixas,
            lucro_pretendido=lucro_pretendido
        )
        print(f"[MCP] resultado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


@mcp.tool()
def simular_cenarios_de_lucro(
    custo_producao: float,
    despesas_variaveis: float,
    despesas_fixas: float
) -> str:
    """
    Simula três opções automáticas de preços com base em ambições distintas de lucro líquido.

    DIRETRIZ DE USO PARA A IA:
    Use esta ferramenta quando o microempreendedor não souber que margem de lucro colocar ou 
    quiser ver opções competitivas de mercado. A ferramenta aplica três cenários clássicos: 
    Conservador (15% de lucro), Moderado (25% de lucro) e Arrojado (40% de lucro). 
    Apresente as três opções geradas e explique a estratégia comercial por trás de cada uma 
    para que o cliente escolha a melhor para a realidade dele.

    Args:
        custo_producao: Custo de fabricação do item único ou custo unitário vindo de um lote.
        despesas_variaveis: Percentual (%) total de taxas dinâmicas por venda.
        despesas_fixas: Percentual (%) de custo estrutural rateado.
    """
    print("[MCP] simular_cenarios_de_lucro foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.simular_cenarios_de_lucro(
            custo_producao=custo_producao,
            despesas_variaveis=despesas_variaveis,
            despesas_fixas=despesas_fixas
        )
        print(f"[MCP] resultado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


@mcp.tool()
def calcular_preco_unitario(
    custo_total: float,
    quantidade: int,
    despesas_variaveis: float,
    despesas_fixas: float,
    lucro_pretendido: float
) -> str:
    """
    Calcula o preço de venda ideal para produtos fabricados em lote (múltiplas unidades).

    DIRETRIZ DE USO PARA A IA:
    Use este método quando o empreendedor produz múltiplas unidades de um mesmo produto em 
    uma única jornada de produção (ex: fez 100 brigadeiros gastando R$50, ou produziu 30 
    sabonetes artesanais com R$90). O método divide o custo total pela quantidade para obter 
    o custo unitário e depois aplica as taxas.

    Args:
        custo_total: Valor total investido na produção do lote inteiro (matéria-prima, energia, etc).
        quantidade: Número de unidades totais produzidas no lote.
        despesas_variaveis: Percentual (%) de custos que incidem sobre cada venda (taxas, comissões).
        despesas_fixas: Percentual (%) dos custos fixos mensais alocados sobre o produto.
        lucro_pretendido: Percentual (%) de lucro líquido desejado sobre o preço final.
    """
    print("[MCP] calcular_preco_unitario foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.calcular_preco_unitario(
            custo_total=custo_total,
            quantidade=quantidade,
            despesas_variaveis=despesas_variaveis,
            despesas_fixas=despesas_fixas,
            lucro_pretendido=lucro_pretendido
        )
        print(f"[MCP] resultado calculado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


@mcp.tool()
def calcular_produto_unico(
    custo_producao: float,
    despesas_variaveis: float,
    despesas_fixas: float,
    lucro_pretendido: float
) -> str:
    """
    Calcula o preço de venda ideal para produtos únicos ou serviços individuais.

    DIRETRIZ DE USO PARA A IA:
    Use este método quando o produto é feito sob encomenda ou de forma individual, sem produção 
    em lote (ex: um quadro pintado à mão, um bolo personalizado sob encomenda, uma bolsa de crochê 
    específica ou um serviço de manutenção/consultoria). O custo informado já é o custo total 
    daquela entrega específica.

    Args:
        custo_producao: Valor em reais gasto para produzir ou entregar este produto/serviço específico.
        despesas_variaveis: Percentual (%) de custos por venda (taxas de pagamento, comissões).
        despesas_fixas: Percentual (%) dos custos fixos mensais alocados sobre este produto.
        lucro_pretendido: Percentual (%) de lucro líquido desejado.
    """
    print("[MCP] calcular_produto_unico foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.calcular_produto_unico(
            custo_producao=custo_producao,
            despesas_variaveis=despesas_variaveis,
            despesas_fixas=despesas_fixas,
            lucro_pretendido=lucro_pretendido
        )
        print(f"[MCP] resultado calculado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


@mcp.tool()
def calcular_ponto_de_equilibrio(
    custos_fixos_mensais: float,
    preco_unitario: float,
    custo_unitario: float
) -> str:
    """
    Calcula a meta de vendas mensal (Ponto de Equilíbrio) para o negócio pagar as contas estruturais.

    DIRETRIZ DE USO PARA A IA:
    Chame esta ferramenta AUTOMATICAMENTE logo após realizar o cálculo final de preço (seja de 
    lote ou produto único) se você possuir os custos fixos nominais em reais do negócio. 
    Use o resultado para fornecer uma meta clara de vendas ao MEI ("Você precisa vender X unidades 
    para cobrir a estrutura").

    Args:
        custos_fixos_mensais: Valor total nominal em REAIS das despesas fixas da estrutura por mês.
        preco_unitario: O preço final de venda calculado e recomendado para o produto.
        custo_unitario: O custo direto em reais de fabricação/insumos de uma unidade.
    """
    print("[MCP] calcular_ponto_de_equilibrio foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.calcular_ponto_de_equilibrio(
            custos_fixos_mensais=custos_fixos_mensais,
            preco_unitario=preco_unitario,
            custo_unitario=custo_unitario
        )
        print(f"[MCP] resultado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


# ─── NOVA FERRAMENTA DE MARGEM DE CONTRIBUIÇÃO ALVO ADICIONADA ABAIXO ────────────

@mcp.tool()
def calcular_preco_por_margem_contribuicao(
    custo_unitario: float,
    despesas_variaveis: float,
    margem_contribuicao_alvo: float
) -> str:
    """
    Calcula o preço de venda ideal com base em uma meta de Margem de Contribuição Alvo (%).

    DIRETRIZ DE USO PARA A IA:
    Use esta ferramenta como uma alternativa estratégica e inteligente quando o Markup tradicional 
    inflar o preço final de vitrine de forma irrealista e não competitiva (por exemplo, devido a 
    custos fixos estruturais extremamente altos em relação a faturamentos pequenos).
    
    Esta ferramenta define o preço ideal garantindo que cada unidade vendida retenha uma fatia 
    saudável em dinheiro para ajudar a pagar a estrutura fixa da empresa e, posteriormente, gerar 
    o lucro global, de forma sustentável para o mercado.

    Args:
        custo_unitario: O custo direto de aquisição ou matéria-prima de uma única unidade em REAIS.
        despesas_variaveis: Percentual (%) de custos dinâmicos associados estritamente à venda (ex: taxas de cartão).
        margem_contribuicao_alvo: Percentual (%) do preço final de venda desejado como margem de contribuição (ex: 40.0 para 40%).
    """
    print("[MCP] calcular_preco_por_margem_contribuicao foi chamada!", file=sys.stderr, flush=True)
    try:
        resultado = precificador.calcular_preco_por_margem_contribuicao(
            custo_unitario=custo_unitario,
            despesas_variaveis=despesas_variaveis,
            margem_contribuicao_alvo=margem_contribuicao_alvo
        )
        print(f"[MCP] resultado calculado: {resultado}", file=sys.stderr, flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", file=sys.stderr, flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()