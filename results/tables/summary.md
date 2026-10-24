# Tabelas agregadas (média ± erro padrão, aquecimento descartado)

## Métricas globais por cenário

| Perfil | Cenário | Usuários | N | Tempo médio (ms) | P95 (ms) | Vazão (req/s) | Total req. | Falhas (%) | CPU gateway (%) | CPU customers (%) | CPU vets (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Perfil 1 — Leitura | A — Leve (30) | 30 | 10 | 19.51 ± 2.29 | 49.80 ± 4.20 | 19.68 ± 0.05 | 1760 ± 5 | 7.01 ± 7.01 | 6.14 ± 0.30 | 31.14 ± 4.80 | 1.52 ± 0.33 |
| Perfil 1 — Leitura | B — Moderado (80) | 80 | 10 | 163.92 ± 53.34 | 544.00 ± 162.59 | 48.32 ± 1.44 | 4336 ± 128 | 16.03 ± 8.70 | 20.26 ± 2.11 | 173.43 ± 33.50 | 1.94 ± 0.21 |
| Perfil 1 — Leitura | C — Elevado (150) | 150 | 10 | 50.05 ± 9.85 | 315.30 ± 61.63 | 96.49 ± 0.62 | 8606 ± 54 | 72.75 ± 7.54 | 20.43 ± 2.20 | 84.89 ± 20.14 | 1.40 ± 0.37 |
| Perfil 2 — Escrita | A — Leve (30) | 30 | 10 | 354.17 ± 182.86 | 1773.10 ± 1029.57 | 17.03 ± 1.14 | 1524 ± 102 | 19.31 ± 9.68 | 7.19 ± 0.91 | 88.28 ± 16.32 | 0.82 ± 0.09 |
| Perfil 2 — Escrita | B — Moderado (80) | 80 | 10 | 63.89 ± 7.79 | 195.90 ± 70.68 | 51.12 ± 0.27 | 4591 ± 24 | 79.03 ± 9.13 | 10.19 ± 1.27 | 53.59 ± 16.35 | 0.67 ± 0.25 |
| Perfil 2 — Escrita | C — Elevado (150) | 150 | 10 | 33.09 ± 2.53 | 65.90 ± 14.90 | 97.61 ± 0.19 | 8694 ± 18 | 91.40 ± 5.11 | 14.69 ± 1.04 | 32.71 ± 13.89 | 0.54 ± 0.22 |

## Tempo médio (ms) por operação

| Perfil | Cenário | GET /owners | GET /owners/{id} | GET /vets | POST /owners |
|---|---|---:|---:|---:|---:|
| Perfil 1 — Leitura | A — Leve (30) | 31.49 | 6.13 | 6.54 | 45.87 |
| Perfil 1 — Leitura | B — Moderado (80) | 279.73 | 83.60 | 7.87 | 113.31 |
| Perfil 1 — Leitura | C — Elevado (150) | 78.12 | 29.73 | 6.73 | 69.93 |
| Perfil 2 — Escrita | A — Leve (30) | 865.26 | 252.80 | 6.36 | 298.98 |
| Perfil 2 — Escrita | B — Moderado (80) | 150.51 | 28.30 | 4.58 | 67.63 |
| Perfil 2 — Escrita | C — Elevado (150) | 44.93 | 11.53 | 4.29 | 52.56 |

## P95 (ms) por operação

| Perfil | Cenário | GET /owners | GET /owners/{id} | GET /vets | POST /owners |
|---|---|---:|---:|---:|---:|
| Perfil 1 — Leitura | A — Leve (30) | 48.40 | 8.60 | 9.20 | 54.10 |
| Perfil 1 — Leitura | B — Moderado (80) | 619.30 | 268.20 | 15.00 | 314.70 |
| Perfil 1 — Leitura | C — Elevado (150) | 421.20 | 172.00 | 11.10 | 212.40 |
| Perfil 2 — Escrita | A — Leve (30) | 3222.40 | 1515.00 | 10.30 | 1031.40 |
| Perfil 2 — Escrita | B — Moderado (80) | 1027.60 | 118.10 | 8.40 | 146.40 |
| Perfil 2 — Escrita | C — Elevado (150) | 159.40 | 20.40 | 7.90 | 61.50 |
