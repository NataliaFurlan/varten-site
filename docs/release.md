# Publicação de varten-site

## Fluxo

Desenvolva na `dev` (ou integre sua branch de trabalho nela), teste e envie seus
commits para `origin/dev`. O script valida **esse commit**, gera um artefato e
promove a mesma versão para `origin/prod`. Não troca sua branch, não inclui
alterações sem commit e não faz merges com conflitos automaticamente.

```sh
./scripts/deploy-prod.sh --plan
./scripts/deploy-prod.sh --check
./scripts/deploy-prod.sh --publish
```

Sem argumento, o comando mostra o plano. `--plan` usa referências locais, sem
consultar a rede. `--check` e `--publish` exigem árvore limpa e `dev` sincronizada
com o GitHub; atualizam referências, validam e compilam em pasta temporária.
Os artefatos e recibos ficam em `.releases/`, ignorada pelo Git.

`prod` começa a partir da versão validada de `dev` na primeira publicação,
desde que ela contenha a história de `origin/main`. Publicações posteriores
exigem que `dev` contenha `origin/prod`. Se houver divergência, incorpore `prod`
na `dev`, resolva e teste antes de tentar de novo. A atualização usa uma trava
sobre o commit remoto observado e só permite avanço de histórico; uma alteração
concorrente interrompe a promoção. A branch local `prod` não é atualizada;
`origin/prod` é a referência da versão promovida.

Se ainda não existir `dev`, crie a branch a partir da versão atual de desenvolvimento:

```sh
git switch -c dev
# Registre o código validado e os scripts em commits antes de executar.
git push -u origin dev
```

Nenhum desses comandos foi executado automaticamente para publicar esta implementação.
O envio à `dev` pode disparar o ambiente de teste já configurado na Hostinger.
Não aponte produção para `dev`.

## Pré-requisitos

Git, Python 3.9+, acesso ao GitHub pelo remote `origin` e as ferramentas do projeto.
Dependências Node são instaladas com `npm ci` e o lockfile do commit. Nenhum `.env`
de desenvolvimento é copiado para o build isolado. O portal força a URL da API
de produção. Segredos da API ficam nas variáveis do ambiente da Hostinger.

## Ligação com a hospedagem (configurar uma vez)

Copie `deploy.local.example.json` para `.deploy.local.json` e preencha a
configuração real. O arquivo local fica fora do Git. Os exemplos ainda não
comprovam uma ligação com a Hostinger; confira o hPanel antes de publicar.

**hostinger-git**: no hPanel, conecte ESTE repositório à branch `prod` com
publicação automática. Confirme as opções `auto_deploy_confirmed` e
`commit_verification` no arquivo local somente após conferir a configuração.
O script atualiza `origin/prod` e espera o endereço de verificação retornar
exatamente o commit promovido. Um site antigo respondendo HTTP 200 não basta.
O build remoto precisa preservar `.git`/Git ou receber `RELEASE_COMMIT` com o
hash completo da versão que está compilando; o build falha se não puder obter
esse identificador. Não fixe manualmente um hash para todas as versões.

**ssh**, para sites estáticos e portal: configure um alias no `~/.ssh/config`
com host, usuário, porta e chave de acesso da hospedagem. Informe `ssh_alias`,
o `web_root` absoluto correto e `verification_url` no arquivo local. O script
confere acesso à pasta, promove `prod`, envia o artefato por rsync e grava o
marcador de versão por último. Requer SSH e rsync local/remoto. Não apaga arquivos
da hospedagem; assets antigos podem ser limpos numa manutenção separada.
Essa transferência não é uma troca atômica de todo o site: publique versões
compatíveis e mantenha arquivos/endereços antigos durante a transição.

O método SSH entrega somente o artefato web; documentos, entrevistas, `.env`,
scripts e arquivos do repositório não são enviados. O exemplo dos sites usa SSH.
Não use uma publicação Git que exponha o repositório inteiro na pasta pública.

## Site estático

Não há build Node. O artefato contém `index.html`, `style.css`, `script.js`,
pastas `assets`, `images`, `fonts` quando existirem e `.htaccess` quando existir.
Se adicionar assets em outra pasta, atualize a lista no script antes de publicar.
Confira todos os links, imagens e formulários na versão hospedada.

## Resultado e falhas

`receipt.json` registra commit, artefato, checksum e estado:
`validated` (local), `promoted` (branch remota atualizada) ou `deployed`
(commit confirmado na hospedagem). No mobile, o estado final é `promoted`:
APK pronto para entregar, sem distribuição automática.

Se a transferência ou a hospedagem falhar após a promoção, `prod` já foi alterada.
O script retorna erro, preserva o recibo e não declara sucesso nem reverte sozinho.
Corrija a hospedagem e execute novamente; a mesma versão pode ser reenviada.
Para reverter código, faça um commit de reversão na `dev`, valide e promova;
nunca use reset/force push para reescrever produção.

Para uma versão que envolve vários projetos: prepare banco, publique API
compatível com clientes anteriores, publique portal e por último entregue APK.
Cada projeto tem publicação independente; este conjunto não é uma transação
única entre repositórios. Teste o fluxo real após publicar.
