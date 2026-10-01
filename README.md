# Varten Site

Versão rebrandeda da referência visual enviada, mantendo o mesmo layout e linguagem visual.

## Arquivos
- index.html
- style.css
- script.js

## Rodar localmente
```bash
cd varten-site-reference
python3 -m http.server 5500
```

Abra:
http://localhost:5500

## Publicação por script

Fluxo `dev → prod`, plano, validação e publicação em `docs/release.md`.

```sh
./scripts/deploy-prod.sh --plan
./scripts/deploy-prod.sh --check
./scripts/deploy-prod.sh --publish
```
