## Respostas automáticas (geradas a partir das médias)

1. **Tempo de resposta vs usuários.** No perfil de leitura o tempo médio foi 19.51 ms (A), 163.92 ms (B) e 50.05 ms (C). No perfil de escrita: 354.17, 63.89 e 33.09 ms. O aumento de usuários eleva o tempo de resposta, com salto mais visível no cenário C.
2. **Maior vazão.** A vazão média do perfil de escrita foi maior (leitura 54.83 req/s vs escrita 55.25 req/s).
3. **Maior degradação.** A operação com maior aumento relativo de A para C foi `GET /owners/{id}` no perfil read (6.13 ms → 29.73 ms, fator 4.85).
4. **CPU.** O consumo cresce com a carga. No cenário C o customers-service ficou em 84.89% (leitura) e 32.71% (escrita); o api-gateway em escrita/C mediu 14.69%.
5. **Maior taxa de falhas.** Perfil 2 — Escrita, C — Elevado (150): 91.40%.
