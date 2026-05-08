import json
from mcp.server.fastmcp import FastMCP  # ← igual ao professor
from src.precificacao.precificacao import Precificacao

mcp = FastMCP("Assistente de Precificação para MEIs")
precificador = Precificacao()


@mcp.tool()
def calcular_preco_unitario(
    custo_total: float,
    quantidade: int,
    despesas_variaveis: float,
    despesas_fixas: float,
    lucro_pretendido: float
) -> dict:
    """
           Calcula o preço de venda ideal para produtos fabricados em lote (quantidade).

        Use este método quando o empreendedor produz múltiplas unidades de um mesmo
        produto em uma única produção — por exemplo: fez 100 brigadeiros gastando
        R$50 no total, ou produziu 30 sabonetes artesanais com R$90 em insumos.

        O método divide o custo total pela quantidade para obter o custo unitário,
        depois aplica o markup para chegar ao preço de venda que garante a cobertura
        de todas as despesas e o lucro desejado.

        Etapas internas:
            1. Calcula o custo unitário: custo_total / quantidade
            2. Calcula o markup: 100 / (100 - (DV + DF + LP))
            3. Calcula o preço unitário: custo_unitario × markup
            4. Calcula o preço total: preco_unitario × quantidade

        Exemplos de uso:
            - Brigadeiros: 100 unidades com custo total de R$50
            - Cosméticos artesanais: 20 potes com custo total de R$180
            - Velas decorativas: 50 unidades com custo total de R$200

        Args:
            custo_total: valor total em reais investido na produção do lote inteiro
                (matéria-prima, embalagens, energia, etc.). Deve ser maior que zero.
            quantidade: número de unidades produzidas no lote. Deve ser maior que zero.
            despesas_variaveis: percentual (%) de custos que incidem sobre cada venda,
                como taxas de cartão, comissões, frete. Exemplo: 5.0 para 5%.
            despesas_fixas: percentual (%) dos custos fixos mensais do negócio
                alocados sobre o produto, como aluguel e energia. Exemplo: 10.0 para 10%.
            lucro_pretendido: percentual (%) de lucro líquido desejado sobre o preço
                final de venda. Exemplo: 20.0 para 20%.

        Returns:
            dict com as seguintes chaves:
                - custo_unitario (float): custo de produção por unidade em reais
                - markup (float): fator multiplicador calculado (ex: 1.4286)
                - preco_unitario (float): preço de venda recomendado por unidade em reais
                - preco_total (float): faturamento total esperado ao vender todo o lote

        Raises:
            ValueError: se custo_total ou quantidade forem inválidos.
            ValueError: se a soma dos percentuais for >= 100% ou negativa.
    """
    print("[MCP] calcular_preco_unitario foi chamada!", flush=True)
    try:
        resultado = precificador.calcular_preco_unitario(
            custo_total=custo_total,
            quantidade=quantidade,
            despesas_variaveis=despesas_variaveis,
            despesas_fixas=despesas_fixas,
            lucro_pretendido=lucro_pretendido
        )
        print(f"[MCP] resultado calculado: {resultado}", flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


@mcp.tool()
def calcular_produto_unico(
    custo_producao: float,
    despesas_variaveis: float,
    despesas_fixas: float,
    lucro_pretendido: float
) -> dict:
    """
   Calcula o preço de venda ideal para produtos únicos ou serviços individuais.

        Use este método quando o produto é feito individualmente, sem produção em lote
        — por exemplo: um quadro pintado à mão, um bolo personalizado encomendado,
        um conserto de eletrodoméstico, uma sessão de fotografia ou qualquer serviço
        onde o custo já se refere àquela entrega específica.

        Diferente do cálculo por quantidade, aqui o custo de produção já é o custo
        daquele produto ou serviço específico — não há divisão por quantidade.
        O markup é aplicado diretamente sobre esse custo para gerar o preço final.

        Exemplos de uso:
            - Artesanato sob encomenda: bolsa de crochê com R$35 em materiais
            - Serviço de design: logo criado com R$0 em custo direto, mas com horas trabalhadas valoradas
            - Bolo personalizado: encomenda específica com R$80 em ingredientes
            - Manutenção: reparo de equipamento com R$40 em peças

        Args:
            custo_producao: valor em reais gasto para produzir ou entregar este produto
                ou serviço específico (materiais, insumos, horas, deslocamento, etc.).
                Deve ser maior que zero.
            despesas_variaveis: percentual (%) de custos que incidem sobre cada venda,
                como taxas de pagamento, comissões, frete. Exemplo: 5.0 para 5%.
            despesas_fixas: percentual (%) dos custos fixos mensais do negócio
                alocados sobre este produto, como aluguel e energia. Exemplo: 10.0 para 10%.
            lucro_pretendido: percentual (%) de lucro líquido desejado sobre o preço
                final de venda. Exemplo: 20.0 para 20%.

        Returns:
            dict com as seguintes chaves:
                - custo_producao (float): custo original informado, em reais
                - markup (float): fator multiplicador calculado (ex: 1.8182)
                - preco_final (float): preço de venda recomendado em reais

        Raises:
            ValueError: se custo_producao for menor ou igual a zero.
            ValueError: se a soma dos percentuais for >= 100% ou negativa.
    """
    print("[MCP] calcular_produto_unico foi chamada!", flush=True)
    try:
        resultado = precificador.calcular_produto_unico(
            custo_producao=custo_producao,
            despesas_variaveis=despesas_variaveis,
            despesas_fixas=despesas_fixas,
            lucro_pretendido=lucro_pretendido
        )
        print(f"[MCP] resultado calculado: {resultado}", flush=True)
        return json.dumps(resultado, ensure_ascii=False)
    except ValueError as e:
        erro_dict = {"sucesso": False, "erro": str(e)}
        print(f"[MCP] erro na ferramenta: {erro_dict}", flush=True)
        return json.dumps(erro_dict, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()