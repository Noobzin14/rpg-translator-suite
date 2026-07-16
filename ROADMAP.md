# ROADMAP.md

# RPG Translator Suite (RTS)

> Plataforma open source para tradução de jogos RPG Maker e engines similares.

Status: Planejamento

---

# Visão

Criar uma ferramenta moderna para tradução de jogos que permita:

- extrair textos;
- traduzir;
- validar;
- reimportar;
- gerar patches;
- preservar completamente a estrutura do jogo.

O objetivo é se tornar uma referência para tradução de RPG Maker.

---

# Filosofia

- Arquitetura baseada em plugins
- Engine independente
- Interface moderna (Qt/PySide6)
- Código aberto
- Extensível
- Seguro
- Modular

---

# Roadmap

## Sprint 0.1 — Fundação

### Objetivos

Criar toda a infraestrutura da aplicação.

### Recursos

- Estrutura do projeto
- ConfigManager
- Logging
- PluginManager
- Sistema de configurações
- Janela principal
- Arquitetura desacoplada

Status

- ✅ Concluído

---

## Sprint 0.2 — Detecção de Engine

### Objetivos

Reconhecer automaticamente o tipo de projeto.

Suporte

- RPG Maker XP
- RPG Maker VX
- RPG Maker VX Ace
- RPG Maker MV
- RPG Maker MZ

Recursos

- Detectar versão
- Detectar idioma
- Validar estrutura
- Abrir projeto

---

## Sprint 0.3 — Extração

Extrair todos os textos possíveis.

MV/MZ

- Actors
- Classes
- Skills
- Items
- Weapons
- Armors
- Enemies
- Troops
- States
- Animations
- CommonEvents
- System
- Todos os MapXXX.json

XP/VX/VXA

- Scripts
- MapInfos
- Mapas
- Banco de dados

---

## Sprint 0.4 — Banco de Tradução

SQLite.

Tabela principal

- ID
- Engine
- Arquivo
- Mapa
- Evento
- Original
- Tradução
- Status
- Revisor
- Comentários

---

## Sprint 0.5 — Editor

Editor semelhante ao Poedit.

Recursos

- Pesquisa
- Filtros
- Histórico
- Undo / Redo
- Navegação rápida
- Comparação
- Destaque de variáveis

---

## Sprint 0.6 — Glossário

Banco de termos.

Exemplo

Quest → Missão

Dragonic → Dracônico

Save → Salvar

Sempre sugerir traduções consistentes.

---

## Sprint 0.7 — Memória de Tradução

Quando uma frase já foi traduzida.

Exemplo

Potion

↓

Poção

Nova ocorrência

↓

Sugestão automática.

---

## Sprint 0.8 — IA

Suporte opcional

- OpenAI
- Gemini
- Claude
- Ollama
- LM Studio

A IA deverá preservar automaticamente

- \V[]
- \N[]
- \I[]
- \C[]
- Tags
- Escape codes

---

## Sprint 0.9 — Reimportação

Gerar novamente

- JSON
- RXDATA
- RVData
- RVData2

Sem corromper eventos.

---

## Sprint 1.0 — Primeira versão pública

Recursos

- Editor
- Extração
- Importação
- Patch
- IA
- Glossário
- Memória
- Backup automático

Suporte

- XP
- VX
- VX Ace
- MV
- MZ

---

# Pós 1.0

## v1.1

Comparador de versões

Exemplo

v1.25

↓

v1.26

↓

132 textos novos

---

## v1.2

Gerador de Patch

Produzir

arquivo.rtpatch

Contendo apenas diferenças.

Nunca distribuir arquivos originais.

---

## v1.3

Instalador

Selecionar jogo

↓

Selecionar patch

↓

Aplicar tradução

---

## v1.4

Validador

Verificar

- JSON inválido
- Variáveis
- Escape Codes
- Eventos
- Overflow
- Tags
- Quebra de comandos

---

## v1.5

Comparação Visual

Mostrar

Original

↓

Traduzido

↓

Diferenças

---

## v2.0

Editor Visual

Ao clicar em um diálogo.

Mostrar

- mapa
- evento
- posição
- NPC
- face
- imagem
- contexto

---

## v2.5

Colaboração

- múltiplos tradutores
- revisão
- comentários
- histórico
- merge

---

## v3.0

IA Contextual

A IA deverá compreender

- personagem
- mapa
- missão
- evento
- sexo
- emoção
- contexto

Para produzir traduções muito mais naturais.

---

# Community Edition

Recursos

- Tradução
- Patch
- Glossário
- IA
- Memória
- Plugins

Sem

- Exportação comercial
- API
- CI/CD

---

# Studio Edition

Inclui tudo da Community

Mais

- Exportação completa
- CLI
- API
- Git
- GitHub
- GitLab
- Azure DevOps
- Build automático
- QA
- Cloud
- Gestão de equipe

---

# Estrutura

rpg-translator-suite/

├── app/
│   ├── core/
│   ├── gui/
│   ├── database/
│   ├── translation/
│   ├── validation/
│   ├── patcher/
│   └── plugins/
│
├── plugins/
│   ├── rpgmaker_xp/
│   ├── rpgmaker_vx/
│   ├── rpgmaker_vxace/
│   ├── rpgmaker_mv/
│   ├── rpgmaker_mz/
│   └── renpy/
│
├── docs/
├── tests/
├── resources/
└── examples/

---

# Tecnologias

| Camada | Tecnologia |
|---------|------------|
| Linguagem | Python 3.12+ |
| Interface | PySide6 |
| Banco | SQLite |
| Plugins | Python |
| Configuração | JSON |
| Testes | pytest |
| Empacotamento | PyInstaller |
| Versionamento | Git |

---

# Objetivo Final

Construir uma plataforma capaz de traduzir jogos de diversas engines mantendo a integridade do projeto, oferecendo uma experiência moderna para tradutores independentes e também recursos avançados para estúdios profissionais.
