class Precificacao:

    def _calcular_markup(
            self,
            despesas_variaveis: float,
            despesas_fixas: float,
            lucro_pretendido: float
    ) -> float:
        """
        Calcula o markup multiplicador a partir dos percentuais de custos e lucro.

        O markup é o fator pelo qual o custo de produção deve ser multiplicado
        para gerar um preço de venda que cubra todas as despesas e ainda entregue
        o lucro desejado. É um método interno usado pelos métodos públicos de
        precificação — não deve ser chamado diretamente pelo MCP.

        Fórmula: markup = 100 / (100 - (DV + DF + LP))
        Onde DV = despesas variáveis, DF = despesas fixas, LP = lucro pretendido.

        Exemplo: com DV=10%, DF=15%, LP=20% → markup = 100 / (100 - 45) = 1.8182
        Isso significa que o preço de venda será 1.82x o custo de produção.

        Args:
            despesas_variaveis: percentual (%) de custos que variam com cada venda,
                como taxas de marketplace, comissão de vendedor, embalagem por unidade.
                Exemplo: 10.0 representa 10%.
            despesas_fixas: percentual (%) dos custos fixos do negócio rateados sobre
                o produto, como aluguel, energia elétrica, internet, contador.
                Exemplo: 15.0 representa 15%.
            lucro_pretendido: percentual (%) de lucro líquido desejado sobre o preço
                de venda final. Exemplo: 20.0 representa 20%.

        Returns:
            float: o markup calculado, sempre maior que 1.0.

        Raises:
            ValueError: se a soma dos três percentuais for >= 100, pois tornaria
                o markup matematicamente impossível (divisão por zero ou negativo).
            ValueError: se a soma dos percentuais for negativa.
        """
        soma_percentuais = despesas_variaveis + despesas_fixas + lucro_pretendido

        if soma_percentuais >= 100:
            raise ValueError(
                "A soma de despesas variáveis, despesas fixas e lucro pretendido "
                "deve ser menor que 100%."
            )

        if soma_percentuais < 0:
            raise ValueError(
                "A soma dos percentuais não pode ser negativa."
            )

        return 100 / (100 - soma_percentuais)

    def _calcular_custo_unitario(
            self,
            custo_total: float,
            quantidade: int
    ) -> float:
        """
        Calcula quanto custa produzir uma única unidade de um produto feito em lote.

        Divide o custo total de produção do lote pela quantidade produzida.
        É um método interno auxiliar — não deve ser chamado diretamente pelo MCP.

        Exemplo: se o empreendedor gastou R$50 para fazer 100 brigadeiros,
        o custo unitário é R$0,50 por brigadeiro.

        Args:
            custo_total: valor total em reais gasto para produzir o lote completo,
                incluindo matéria-prima, embalagem, gás, ingredientes, etc.
                Deve ser maior que zero.
            quantidade: número total de unidades produzidas no lote.
                Deve ser um número inteiro positivo maior que zero.

        Returns:
            float: custo de produção por unidade em reais.

        Raises:
            ValueError: se custo_total for menor ou igual a zero.
            ValueError: se quantidade for menor ou igual a zero.
        """
        if custo_total <= 0:
            raise ValueError("O custo total deve ser maior que zero.")

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        return custo_total / quantidade

    def calcular_preco_unitario(
            self,
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
        custo_unitario = self._calcular_custo_unitario(custo_total, quantidade)
        markup = self._calcular_markup(despesas_variaveis, despesas_fixas, lucro_pretendido)
        preco_unitario = custo_unitario * markup
        preco_total = preco_unitario * quantidade

        return {
            "custo_unitario": round(custo_unitario, 2),
            "markup": round(markup, 4),
            "preco_unitario": round(preco_unitario, 2),
            "preco_total": round(preco_total, 2)
        }

    def calcular_produto_unico(
            self,
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
        if custo_producao <= 0:
            raise ValueError("O custo de produção deve ser maior que zero.")

        markup = self._calcular_markup(despesas_variaveis, despesas_fixas, lucro_pretendido)
        preco_final = custo_producao * markup

        return {
            "custo_producao": round(custo_producao, 2),
            "markup": round(markup, 4),
            "preco_final": round(preco_final, 2)
        }