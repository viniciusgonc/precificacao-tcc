import sys
from pathlib import Path

# Adiciona a pasta src ao caminho do Python
# Isso permite importar a classe Precificacao corretamente
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from precificacao.precificacao import Precificacao


def main():
    print("=== Sistema de Precificação ===")
    print("Escolha uma opção:\n")
    print("1 - Calcular produto vendido em quantidade")
    print("2 - Calcular produto único\n")

    try:
        opcao = input("Digite a opção desejada: ")

        precificador = Precificacao()

        if opcao == "1":
            custo_total = float(input("\nInforme o custo total de produção (R$): "))
            quantidade = int(input("Informe a quantidade produzida: "))

            despesas_variaveis = float(input("Informe as despesas variáveis (%): "))
            despesas_fixas = float(input("Informe as despesas fixas (%): "))
            lucro_pretendido = float(input("Informe o lucro pretendido (%): "))

            resultado = precificador.calcular_preco_unitario(
                custo_total=custo_total,
                quantidade=quantidade,
                despesas_variaveis=despesas_variaveis,
                despesas_fixas=despesas_fixas,
                lucro_pretendido=lucro_pretendido
            )

            print("\nResultado:")
            print(f"Custo unitário: R$ {resultado['custo_unitario']:.2f}")
            print(f"Markup calculado: {resultado['markup']:.4f}")
            print(f"Preço unitário de venda: R$ {resultado['preco_unitario']:.2f}")
            print(f"Preço total de venda: R$ {resultado['preco_total']:.2f}")

        elif opcao == "2":
            custo_producao = float(input("\nInforme o custo de produção do produto (R$): "))

            despesas_variaveis = float(input("Informe as despesas variáveis (%): "))
            despesas_fixas = float(input("Informe as despesas fixas (%): "))
            lucro_pretendido = float(input("Informe o lucro pretendido (%): "))

            resultado = precificador.calcular_produto_unico(
                custo_producao=custo_producao,
                despesas_variaveis=despesas_variaveis,
                despesas_fixas=despesas_fixas,
                lucro_pretendido=lucro_pretendido
            )

            print("\nResultado:")
            print(f"Custo de produção: R$ {resultado['custo_producao']:.2f}")
            print(f"Markup calculado: {resultado['markup']:.4f}")
            print(f"Preço final de venda: R$ {resultado['preco_final']:.2f}")

        else:
            print("\nOpção inválida. Execute o programa novamente e escolha 1 ou 2.")

    except ValueError as erro:
        print(f"\nErro: {erro}")


if __name__ == "__main__":
    main()