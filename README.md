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

## Como rodar (no seu PC)

```bash
# Opção 1 — duplo clique
rodar_local.bat

# Opção 2 — terminal
pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

Abre em `http://127.0.0.1:8501`. No PC, use sempre o `rodar_local.bat` para não expor na rede.

## Publicar e compartilhar com a empresa

Fluxo recomendado: **GitHub + Streamlit Community Cloud** (link com senha).

### 1. Preparar os dados que vão no link

No PC, com a base já carregada na aba Dados:

1. Duplo clique em `preparar_publicacao.bat`
2. Isso copia `data/ultima` → `data/publicada` (essa pasta sobe no GitHub)

### 2. Subir o código

Crie um repositório no GitHub (pode ser **privado**) e faça push da pasta do projeto.

### 3. Publicar no Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io) com a conta Google/GitHub
2. **New app** → escolha o repositório → Main file: `app.py`
3. Em **Advanced settings → Secrets**, cole:

```toml
APP_PASSWORD = "senha-da-equipe"
```

4. Deploy. O Streamlit gera um link `https://....streamlit.app`

### 4. Compartilhar

Envie o **link + a senha** só para quem pode ver faturamento/estoque.

Sempre que atualizar os números:

1. Suba os CSVs na aba Dados (no PC)
2. Rode `preparar_publicacao.bat`
3. Commit + push → o Cloud redesenha o dash sozinho

**Importante:** o snapshot em `data/publicada` contém dados comerciais. Use repositório privado e senha no app.

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
