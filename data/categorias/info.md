
# Origem dos dados dessa pasta:

Guia de classificação de notícias do clipping da Transparência Brasil, escrito pela equipe
(documento "Descrições para o clipping.docx"), convertido para Markdown e dividido em um
arquivo por etapa da classificação da fase 02. Cada etapa recebe só o seu arquivo:

- `guia_areas.md` (seções 1, 2.1–2.4, 3, 5.1, 5.2, 5.8 e 6): Área temática 1 e Tema;
- `guia_projetos.md` (seções 2.5, 4, 5.3–5.5 e 7): Projeto ou iniciativa;
- `guia_relatorios.md` (seções 2.6, 5.6, 5.7 e 8) + `catalogo_relatorios.csv`: Relatório.

A seção 9 (formato de classificação) ficou de fora: cada etapa tem o seu formato de resposta.
Ao atualizar o guia no Word, leve a mudança para o arquivo da etapa correspondente.

O classificador lê dos próprios arquivos as opções válidas de resposta, então a estrutura dos
títulos precisa ser mantida:

- em `guia_areas.md`, `## 3.x. Nome` dentro de `# 3. Áreas temáticas`: uma área temática;
- em `guia_areas.md`, `#### Nome` abaixo de uma área: um tema dessa área (área sem temas usa o
  próprio nome);
- em `guia_projetos.md`, `### Nome` dentro de `# 4. Projetos e iniciativas`: um projeto ou iniciativa.

`catalogo_relatorios.csv`: relatórios da TB dos últimos 3 anos (título exato, data e área
temática), extraídos da aba "relatórios dos últimos 3 anos" da planilha "Esquema de
categorias + lista de relatórios" da equipe. O classificador só grava na coluna Relatório
títulos que estejam neste arquivo; ao publicar um relatório novo, acrescente uma linha.
