# Giro de Estoque

Ferramenta para calcular **giro de kits, lançamentos e itens promocionados**.

## Fórmula

```
giro = quantidade vendida ÷ (quantidade vendida + estoque atual)
```

- **1,0 (100%)** → tudo que havia disponível já foi vendido (estoque zerado)
- **0,0 (0%)** → nada vendido, só estoque parado

## Bases necessárias

| Base | Arquivo | Chave |
|------|---------|-------|
| Vendas ABC | CSV `;` (cp1252) | BCPS na coluna `Quebra2` + código do produto |
| Saldo estoque | CSV `;` (cp1252) | BCPS em `Quebra 1` (`Loja: 12488 - ...`) + código |
| dCentro | aba `dCentros` do Excel ou `data/dcentros.csv` | BCPS → praça, canal, cluster |

Opcional: CSV `codigo;tipo` com valores `kit`, `lancamento`, `promocionado`.

## Como rodar (somente no seu PC)

O app **não sobe na internet**. Ele abre em `http://127.0.0.1:8501` e os arquivos ficam locais.

```bash
# Opção 1 — duplo clique
rodar_local.bat

# Opção 2 — terminal
pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

O botão **Deploy** do Streamlit (se aparecer) é só da interface padrão — ignore. Com `toolbarMode = minimal` e bind em `127.0.0.1`, a ferramenta fica restrita a este computador.

## O que a ferramenta mostra

- Giro geral e por **produto / loja / praça / canal**
- Distribuição de vendas por praça e canal
- Alertas: alto giro, estoque parado, ruptura
- Exportação Excel de cada visão

## Próximos envios

Para ampliar além de kits, envie:

1. ABC vendas + saldo estoque de **lançamentos**
2. ABC vendas + saldo estoque de **itens promocionados**
3. (opcional) lista `codigo;tipo` se quiser misturar tudo numa única carga
