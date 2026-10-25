# Varten — site institucional

Site estático em português para apresentar a Varten, seu posicionamento no
desenvolvimento sob medida para empresas, produtos próprios (como o TrackFit) e contato para projetos.

## Identidade visual

Logo original preservada em `assets/logo-varten.png`; cabeçalho e rodapé usam o símbolo sem fundo em `assets/logo-varten-transparent.png`. Paleta principal:

- Fundo: `#0A0F14`.
- Fundo secundário: `#0F1720`.
- Superfícies: `#17212C`.
- Azul principal: `#83B8FF`; apoio: `#B7D7FF`.
- Texto: `#F5F7FA`; secundário: `#9BA8B4`.

A direção principal segue a referência `ideia_site4`: abertura escura com
ilustração de tecnologia, seções claras, faixa de princípios e contato.
O registro de direção e o prompt da ilustração estão em `docs/visual-direction.md`.

A apresentação do TrackFit usa uma superfície clara e seus tons lime. O produto é
identificado como em desenvolvimento; a ficha exibida é uma ilustração do conceito.

## Executar localmente

```sh
python3 -m http.server 5500 --bind 127.0.0.1
```

Abra `http://127.0.0.1:5500`. Não há instalação de dependências nem build.

## Arquivos

- `index.html`: conteúdo, navegação, apresentação do produto e contato.
- `equipe/index.html`: apresentação da equipe, acessível pelo rodapé.
- `style.css`: identidade visual, animação da abertura e layouts responsivos.
- `script.js`: menu mobile, seção ativa, cabeçalho e ano do rodapé.
- `assets/logo-varten.png`: imagem original fornecida para a marca.
- `assets/logo-varten-transparent.png`: símbolo isolado com transparência.
- `assets/hero-technology.png`: ilustração original gerada com transparência.

O menu fecha por seleção, clique fora ou Escape; Escape devolve o foco ao botão.
Há link para pular ao conteúdo, estilos de foco e suporte a movimento reduzido.
Contato por `mailto:equipe@varten.com.br`; não há formulário ou envio automático.

## Publicação por script

Fluxo `dev → prod`, plano, validação e publicação em `docs/release.md`.

```sh
./scripts/deploy-prod.sh --plan
./scripts/deploy-prod.sh --check
./scripts/deploy-prod.sh --publish
```

O pacote do site inclui `assets/`. Configure a hospedagem antes da publicação.

## TrackFit

O diretório trackfit/ contém a versão estática completa do site e da demonstração local, com logo de infinito e o carrossel de atividades. Os links do produto usam /trackfit/ para não depender de um novo subdomínio. O pacote de release inclui essa pasta. Isso prepara a publicação na mesma hospedagem da Varten, sem alteração automática de DNS. Não houve publicação na Hostinger nesta execução. A versão já hospedada privadamente no ChatGPT Sites continua independente.

A equipe fica em `/equipe/`, fora da página inicial e do menu principal. A ilustração da abertura tem flutuação suave, controle de pausa e respeita `prefers-reduced-motion`. A referência de produto usa TrackFit; as imagens ilustrativas continuam provisórias.
