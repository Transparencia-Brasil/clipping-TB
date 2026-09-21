# r-template-tb

Repositório template para novas análises e modelagens da Transparência Brasil.


## Organização deste repositório

```
r-template-tb/
├── data/           -> Diretório que contém dados ou subdiretórios específicos (ex: `data/raw`).
├── docs/           -> Contém subsets de dados gerados durante a análise
├── src/            -> Scripts reusáveis de suporte para filtragem e/ou tratamento de dados
├── .gitignore      -> Arquivos ou extensões a serem ignoradas no envio ao GitHub
├── LICENSE         -> Licença utilizada para o repositório
└── r-template-tb.Rproj   -> Indica a raiz do projeto e informações prévias
```


### Dicas para desenvolver

* Opcionalmente, crie subdiretórios dentro de `/data` a fim de facilitar a organização. Por exemplo, para dados brutos `data/raw`, ou para dados prontos para análise com o nome `data/ready`. Dados temporários podem ser colocados em `data/temp` (incluído no `.gitignore`).

* Relatórios que usam dados prontos ficam em `docs/`. Coloque o html de versões para publicação em `docs/` e eles estarão disponíveis [na página do projeto](https://transparencia-brasil.github.io/r-template-tb/). Existem templates para arquivos `rmd` e `qmd`.

* Utilize numeração de arquivos para manter o código em um ordem, exemplo: `src/00-plot-aesthetics.R`, `src/01-download-raw-data.R`.