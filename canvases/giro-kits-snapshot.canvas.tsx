import { BarChart, Callout, Card, CardBody, CardHeader, Grid, H1, H2, Row, Stack, Stat, Table, Text } from "cursor/canvas";

/**
 * Snapshot kits NAT/26 — 22/09/2026
 * giro = vendida / (vendida + estoque)
 */
const SUMMARY = {
  giroPct: 13.0,
  vendida: 17803,
  estoque: 119402,
  faturamento: 1594597.96,
  skus: 43,
  lojas: 41,
  pracas: 8,
};

const PRACA = [
  { praca: "OMA", vendida: 4785, estoque: 11115, giroPct: 30.1 },
  { praca: "RN SUL", vendida: 799, estoque: 4111, giroPct: 16.3 },
  { praca: "LITORAL", vendida: 1166, estoque: 6396, giroPct: 15.4 },
  { praca: "OCE", vendida: 2223, estoque: 12861, giroPct: 14.7 },
  { praca: "NATAL", vendida: 4562, estoque: 29383, giroPct: 13.4 },
  { praca: "MOSSORÓ", vendida: 1231, estoque: 9687, giroPct: 11.3 },
  { praca: "PARAÍBA", vendida: 1297, estoque: 12902, giroPct: 9.1 },
  { praca: "SÃO LUÍS", vendida: 1740, estoque: 32947, giroPct: 5.0 },
];

const CANAL = [
  { canal: "Híbrida", vendida: 8133, estoque: 28190, giroPct: 22.4 },
  { canal: "Venda Direta", vendida: 7175, estoque: 64772, giroPct: 10.0 },
  { canal: "HUB", vendida: 2495, estoque: 26440, giroPct: 8.6 },
];

const TOP = [
  { desc: "ZAAD", vendida: 97, estoque: 262, giroPct: 27.0 },
  { desc: "MALBEC MAGNETIC", vendida: 844, estoque: 2384, giroPct: 26.1 },
  { desc: "FLORATTA RED", vendida: 656, estoque: 1862, giroPct: 26.1 },
  { desc: "LILY ACETINADOS", vendida: 363, estoque: 1054, giroPct: 25.6 },
  { desc: "MALBEC EDP", vendida: 174, estoque: 561, giroPct: 23.7 },
  { desc: "CBEM PESSEGURA", vendida: 973, estoque: 3281, giroPct: 22.9 },
  { desc: "FLORATTA RED PASSION", vendida: 455, estoque: 1611, giroPct: 22.0 },
  { desc: "FLORATTA RED P1", vendida: 1295, estoque: 4707, giroPct: 21.6 },
];

const BOTTOM = [
  { desc: "NIINA SECRETS MAKE", vendida: 10, estoque: 165, giroPct: 5.7 },
  { desc: "NSPA UVA MERLOT", vendida: 290, estoque: 5623, giroPct: 4.9 },
  { desc: "INSTANCE BAUNILHA GLOW", vendida: 336, estoque: 7265, giroPct: 4.4 },
  { desc: "MAGNIFIC ROUGE CAMELIA", vendida: 105, estoque: 2717, giroPct: 3.7 },
  { desc: "SIAGE NUTRI ROSE", vendida: 74, estoque: 2992, giroPct: 2.4 },
];

function money(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function qty(v: number) {
  return v.toLocaleString("pt-BR");
}

export default function GiroKitsSnapshot() {
  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>Giro de kits — snapshot 22/09/2026</H1>
        <Text tone="secondary">
          Fórmula: vendida ÷ (vendida + estoque atual). Bases: ABC Vendas + saldo estoque + dCentro (BCPS → praça/canal).
        </Text>
      </Stack>

      <Callout tone="info" title="Ferramenta interativa">
        Para filtrar por loja/praça/canal e exportar Excel, rode `streamlit run app.py` no projeto. Este canvas é o recorte consolidado da base de kits enviada hoje.
      </Callout>

      <Grid columns={4} gap={16}>
        <Stat value={`${SUMMARY.giroPct.toFixed(1).replace(".", ",")}%`} label="Giro geral" tone="info" />
        <Stat value={qty(SUMMARY.vendida)} label="Quantidade vendida" />
        <Stat value={qty(SUMMARY.estoque)} label="Estoque atual" />
        <Stat value={money(SUMMARY.faturamento)} label="Faturamento" />
      </Grid>

      <Grid columns={3} gap={16}>
        <Stat value={String(SUMMARY.skus)} label="SKUs (kits)" />
        <Stat value={String(SUMMARY.lojas)} label="Lojas (BCPS)" />
        <Stat value={String(SUMMARY.pracas)} label="Praças" />
      </Grid>

      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>Giro por praça (%)</CardHeader>
          <CardBody>
            <BarChart
              categories={PRACA.map((r) => r.praca)}
              series={[{ name: "Giro %", data: PRACA.map((r) => r.giroPct) }]}
              valueSuffix="%"
              height={280}
            />
            <Text tone="secondary" size="small">
              Source: ABC + estoque kits · 22/09/2026 · giro ponderado por quantidade
            </Text>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Giro por canal (%)</CardHeader>
          <CardBody>
            <BarChart
              categories={CANAL.map((r) => r.canal)}
              series={[{ name: "Giro %", data: CANAL.map((r) => r.giroPct) }]}
              valueSuffix="%"
              height={280}
            />
            <Text tone="secondary" size="small">
              Source: dCentro canal geral · Híbrida lidera com 22,4%
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <Stack gap={12}>
        <H2>Distribuição de vendas por praça</H2>
        <BarChart
          categories={PRACA.map((r) => r.praca)}
          series={[
            { name: "Vendida", data: PRACA.map((r) => r.vendida) },
            { name: "Estoque", data: PRACA.map((r) => r.estoque) },
          ]}
          height={300}
        />
        <Text tone="secondary" size="small">
          Source: ABC Vendas + saldo estoque · quantidade de kits · 22/09/2026
        </Text>
      </Stack>

      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>Maior giro (produtos)</CardHeader>
          <CardBody>
            <Table
              headers={["Produto", "Vendida", "Estoque", "Giro"]}
              rows={TOP.map((r) => [
                r.desc,
                qty(r.vendida),
                qty(r.estoque),
                `${r.giroPct.toFixed(1).replace(".", ",")}%`,
              ])}
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Menor giro (estoque parado)</CardHeader>
          <CardBody>
            <Table
              headers={["Produto", "Vendida", "Estoque", "Giro"]}
              rows={BOTTOM.map((r) => [
                r.desc,
                qty(r.vendida),
                qty(r.estoque),
                `${r.giroPct.toFixed(1).replace(".", ",")}%`,
              ])}
            />
          </CardBody>
        </Card>
      </Grid>

      <Card>
        <CardHeader>Leitura rápida</CardHeader>
        <CardBody>
          <Stack gap={8}>
            <Text>
              OMA lidera giro (30,1%) com mix enxuto; São Luís tem o maior estoque absoluto e o menor giro (5,0%).
            </Text>
            <Text>
              Canal Híbrida gira mais que o dobro de HUB (22,4% vs 8,6%). Venda Direta concentra estoque (64,8 mil un.).
            </Text>
            <Text>
              Kits de perfumaria (Zaad, Malbec, Floratta) puxam o topo; make/cuidados Eudora e Instance concentraram estoque parado.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <Row gap={8}>
        <Text tone="secondary" size="small">
          Próximo passo: enviar ABC + saldo de lançamentos e promocionados para entrar no mesmo motor (campo tipo).
        </Text>
      </Row>
    </Stack>
  );
}
