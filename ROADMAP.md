RPG Translator Suite (RTS)
Roadmap técnico focado na implementação do pipeline real de dados: extração → persistência → tradução → validação → reinserção.
Estado atual: Pre-Alpha
Objetivo imediato: tornar o pipeline de tradução funcional e seguro antes de expandir a aplicação.
1. Princípios do Roadmap
O RTS possui uma arquitetura considerada sólida pela auditoria, com 172 testes unitários passando. O problema atual não é estrutural: são funcionalidades críticas ainda não implementadas.
A prioridade deste roadmap é, portanto:
Integridade dos dados
Persistência
I/O confiável
Tradução funcional
Reinserção segura
Recuperação contra falhas
Expansão somente após o pipeline básico estar fechado
Fora do escopo imediato
Até o fechamento do pipeline básico, ficam temporariamente adiados:
Interface gráfica
Geração de patches
IA avançada
Novas engines além das previstas nas fases de expansão
Otimizações prematuras
Refatoração arquitetural
2. Pipeline-Alvo
O pipeline deverá evoluir de:
Jogo
  ↓
Detecção
  ↓
Extração parcial
  ↓
[TRADUÇÃO]
  ↓
[VALIDAÇÃO]
  ↓
[ARMAZENAMENTO]
  ↓
[REINSERÇÃO]
  ↓
Jogo traduzido
para:
Jogo original
      ↓
Detecção
      ↓
Leitura / Encoding
      ↓
Extração completa
      ↓
Proteção de Tokens
      ↓
Persistência SQLite
      ↓
Tradução
      ↓
Checkpoint / Retry
      ↓
Validação
      ↓
Reinserção
      ↓
Backup
      ↓
Jogo traduzido
O objetivo principal é fechar o ciclo de vida do dado sem perda ou corrupção.
FASE 1 — CORREÇÕES CRÍTICAS
Prioridade: P0 — Bloqueante
Objetivo: implementar os componentes que atualmente impedem o pipeline de funcionar.
Estimativa: 80–100 horas
1.1 — Implementar DatabaseManager com SQLite
Problema atual
O DatabaseManager existe apenas como interface. Os métodos ainda não possuem implementação real.
Consequência:
traduções não são persistidas;
dados podem ser perdidos;
não existe estado confiável do processo de tradução.
Implementação
Criar:
src/rpg_translator_suite/database/sqlite_manager.py
Implementar:
conexão SQLite;
criação automática do banco;
schema;
CRUD de traduções;
transações;
commit/rollback;
migrações básicas;
consultas por ID;
consultas por texto;
atualização de traduções;
controle de timestamps.
Tabelas iniciais
translations
translation_memory
glossary
A estrutura deve permanecer compatível com os modelos existentes.
Critério de conclusão
DatabaseManager funcional;
banco criado automaticamente;
inserção e leitura funcionando;
atualização funcionando;
rollback testado;
testes específicos de persistência implementados.
1.2 — Implementar TokenProtector
Problema atual
Escape codes são enviados diretamente para tradução.
Isso pode transformar:
\N[1]
em algo inválido como:
\Nome[1]
Implementação
Criar:
src/rpg_translator_suite/utils/token_protector.py
Fluxo:
Texto original
      ↓
Extrair tokens
      ↓
Substituir por placeholders
      ↓
Texto seguro para tradução
      ↓
Tradução
      ↓
Restaurar tokens
Deve preservar, entre outros:
\N[n]
\P[n]
\V[n]
\C[n]
\I[n]
\FS[n]
\.
\!
\>
\<
|
$
&
^
Critério de conclusão
tokens identificados corretamente;
placeholders não ambíguos;
tokens restaurados corretamente;
quantidade de tokens preservada;
testes com múltiplos tokens;
testes com tokens repetidos;
testes de regressão para corrupção.
1.3 — Implementar QwenTranslator
Problema atual
BaseProvider.translate() está definido, porém nenhum provider concreto funcional está disponível.
Implementação
Criar:
src/rpg_translator_suite/providers/qwen_translator.py
Responsabilidades:
comunicação com API Qwen;
autenticação via configuração externa;
timeout;
tratamento de erros;
retry básico;
rate limiting;
conversão entre TranslationRequest e resposta da API;
logging estruturado.
API keys não devem ser armazenadas no código-fonte.
Critério de conclusão
tradução real funcionando;
erros de API tratados;
timeout configurável;
retry básico;
testes utilizando mock da API;
nenhuma credencial hardcoded.
1.4 — Extração Completa do RPG Maker MV
Problema atual
O extractor praticamente se limita a:
Game.json
└── mapInfos[*].name
A maior parte do conteúdo traduzível não é extraída.
Implementação
Expandir:
src/rpg_translator_suite/engines/mv/extractor.py
Game.json
Extrair, conforme aplicável:
mapInfos[*].name

actors[*]
  ├── name
  ├── nickname
  └── profile

classes[*]
skills[*]
  ├── name
  └── description

items[*]
  ├── name
  └── description

weapons[*]
  ├── name
  └── description

armors[*]
  ├── name
  └── description

enemies[*]
states[*]
animations[*]
tilesets[*]
commonEvents[*]
system.*
Map*.json
Processar:
events[]
pages[]
list[]
commands
Com atenção especial aos comandos:
101 — Show Text
102 — Show Choices
105 — Change Actor Name
119 — Change Party Member Name
301 — Transfer Player
605+ — Script command
Critério de conclusão
O extractor deve produzir uma coleção completa de TranslationEntry para os textos suportados, preservando:
arquivo de origem;
contexto;
localização;
metadados;
texto original;
tokens.
FASE 1 — GATE DE SEGURANÇA
A Fase 2 só começa quando os quatro componentes críticos estiverem implementados e testados:
SQLite              ✅
TokenProtector      ✅
QwenTranslator      ✅
MV Extraction       ✅
Além disso:
testes existentes continuam passando;
nenhum teste crítico regressivo;
dados extraídos podem ser persistidos;
tokens não são corrompidos durante o fluxo de tradução.
O RTS continua sendo considerado Pre-Alpha até este gate ser concluído.
FASE 2 — ALTA PRIORIDADE
Prioridade: P1 — Fechamento do ciclo I/O
Estimativa: 60–80 horas
Objetivo: transformar traduções armazenadas em um jogo traduzido funcional, com tolerância básica a falhas.
2.1 — Implementar TextInserter
Criar:
src/rpg_translator_suite/engines/mv/inserter.py
Responsabilidades:
Ler traduções do SQLite;
carregar arquivos originais;
localizar cada entrada;
substituir o texto;
preservar a estrutura JSON;
preservar tokens;
preservar encoding;
escrever em translated/.
Fluxo:
SQLite
  ↓
TranslationEntry
  ↓
TextInserter
  ↓
JSON original
  ↓
Texto traduzido
  ↓
translated/
Regra crítica
Os arquivos originais nunca devem ser sobrescritos durante a reinserção normal.
Critério de conclusão
textos reinseridos corretamente;
estrutura JSON preservada;
arquivos originais intactos;
encoding preservado;
tokens preservados;
testes de reinserção implementados.
2.2 — Validador Básico
Criar:
src/rpg_translator_suite/utils/validator.py
Validar no mínimo:
texto não vazio;
JSON válido;
tokens preservados;
quantidade de tokens;
encoding;
estrutura dos dados;
anomalias de tamanho;
entradas sem tradução.
O validador deve produzir resultados claros, por exemplo:
VALID
WARNING
ERROR
2.3 — Suporte a Múltiplos Encodings
Criar:
src/rpg_translator_suite/utils/encoding.py
Suportar:
UTF-8
UTF-8-SIG
UTF-16
Shift-JIS
Windows-1252
Implementar:
detecção;
leitura;
escrita;
preservação quando possível;
tratamento de BOM.
Observação
O RPG Maker MV utiliza UTF-8 inclusive em projetos japoneses. O suporte a Shift-JIS é necessário para ampliar a robustez do pipeline e preparar a arquitetura para engines/projetos que utilizem esse encoding.
2.4 — Checkpoint e Retry
Atualizar:
src/rpg_translator_suite/core/translator.py
Implementar:
Tradução
   ↓
Checkpoint
   ↓
Próxima entrada
   ↓
Checkpoint
Em caso de falha:
Erro
 ↓
Retry
 ↓
Retry exponencial
 ↓
Se falhar novamente
 ↓
Registrar erro
 ↓
Continuar
O sistema deverá permitir retomada sem perder traduções já concluídas.
Critério de conclusão
savepoint periódico;
retry exponencial;
falhas individuais isoladas;
logging detalhado;
relatório final;
retomada após interrupção.
FASE 2 — GATE DE PIPELINE
Ao final desta fase deverá ser possível executar:
Jogo MV
   ↓
Detecção
   ↓
Extração
   ↓
Proteção de tokens
   ↓
SQLite
   ↓
Qwen
   ↓
Checkpoint
   ↓
Validação
   ↓
TextInserter
   ↓
translated/
Sem necessidade de GUI.
Este é o primeiro ponto em que o projeto começa a possuir um pipeline funcional de ponta a ponta.
FASE 3 — MELHORIAS ESTRUTURAIS
Prioridade: P2
Estimativa: 40–60 horas
Objetivo: aumentar consistência, segurança e capacidade de reutilização dos dados.
3.1 — Glossário
Implementar glossário persistente.
Exemplo:
Potion → Poção
Quest → Missão
Save → Salvar
Integrar com o processo de tradução para fornecer termos conhecidos ao provider.
3.2 — Memória de Tradução
Implementar Translation Memory no SQLite.
Fluxo:
Nova string
   ↓
Buscar correspondência
   ↓
Encontrou?
 ├── Sim → reutilizar/sugerir tradução
 └── Não → traduzir
Objetivos:
reduzir chamadas à API;
manter consistência;
reutilizar traduções anteriores.
3.3 — Backups Automáticos
Atualizar:
src/rpg_translator_suite/core/project_manager.py
Antes de operações destrutivas, criar backup timestamped:
game_backup_YYYYMMDD_HHMMSS.zip
O backup deve permitir restauração dos arquivos originais.
3.4 — Hashes de Validação
Atualizar:
src/rpg_translator_suite/core/models.py
Adicionar:
original_hash
Calcular utilizando hashlib.
Fluxo:
Texto original
   ↓
Hash
   ↓
Tradução armazenada
Se o original mudar:
Hash atual != Hash armazenado
A tradução deverá ser considerada potencialmente obsoleta.
3.5 — Melhorias de Detecção
Após o pipeline estar seguro, melhorar o detector para validar conteúdo, e não apenas existência de arquivos.
Verificar:
estrutura de Game.json;
arquivos esperados;
evidências do main.js;
possíveis falsos positivos.
FASE 4 — EXPANSÃO
Prioridade: P3
Objetivo: expandir capacidade e confiabilidade depois que o pipeline básico estiver fechado.
4.1 — Paralelização
Implementar processamento concorrente de batches.
Possíveis abordagens:
ThreadPoolExecutor
ou:
asyncio
Com:
número configurável de workers;
respeito a rate limits;
controle de concorrência;
tratamento de falhas individuais.
A paralelização só deve ser introduzida depois que o fluxo sequencial estiver comprovadamente correto.
4.2 — Provider Offline
Criar:
src/rpg_translator_suite/providers/local_translator.py
Possível integração com modelos locais, como:
MarianMT;
mBART;
outros modelos compatíveis.
Objetivo:
Jogo
 ↓
RTS
 ↓
Modelo local
 ↓
Tradução
Sem dependência obrigatória de API externa.
4.3 — Suporte ao RPG Maker MZ
Criar:
src/rpg_translator_suite/engines/mz/
Implementar:
detector;
extractor;
inserter;
testes específicos.
A expansão para MZ deverá reutilizar as abstrações do Core e evitar duplicação desnecessária.
4.4 — Testes de Integração e End-to-End
Criar:
tests/integration/
tests/e2e/
Criar uma fixture mínima de RPG Maker MV contendo:
Game.json
1 mapa
1 evento
diálogo
escolha
escape codes
Testar o ciclo:
Jogo
 ↓
Detecção
 ↓
Extração
 ↓
SQLite
 ↓
Tradução mock
 ↓
Validação
 ↓
Reinserção
 ↓
Jogo traduzido
Os testes E2E deverão validar principalmente:
integridade do JSON;
persistência;
preservação de tokens;
encoding;
reinserção;
recuperação após falhas.
5. Matriz de Prioridade
Componente
Fase
Prioridade
Status
SQLite
1
P0
❌
TokenProtector
1
P0
❌
QwenTranslator
1
P0
❌
Extração completa MV
1
P0
❌
TextInserter
2
P1
❌
Validador
2
P1
❌
Multi-encoding
2
P1
❌
Checkpoint/Retry
2
P1
❌
Glossário
3
P2
❌
Memória de tradução
3
P2
❌
Backups
3
P2
❌
Hashes
3
P2
❌
Paralelização
4
P3
❌
Provider offline
4
P3
❌
RPG Maker MZ
4
P3
❌
Testes E2E
4
P3
❌
6. Testes
Os 172 testes unitários existentes devem continuar passando durante todas as fases.
Novos testes deverão ser adicionados progressivamente para cobrir:
Fase 1
SQLite;
CRUD;
transações;
tokens;
extração completa;
provider Qwen com mock.
Fase 2
reinserção;
JSON;
encoding;
Shift-JIS;
validação;
checkpoint;
retry.
Fase 3
glossário;
memória;
backups;
hashes.
Fase 4
concorrência;
provider offline;
MZ;
integração;
E2E.
7. Critério de Segurança do Projeto
O RTS não deve ser considerado pronto para uso em jogos reais enquanto não houver, no mínimo:
persistência SQLite funcional;
TokenProtector;
extração completa;
provider funcional;
TextInserter;
validação;
backup;
testes de reinserção.
A prioridade absoluta é evitar:
perda de tradução
        +
corrupção de escape codes
        +
corrupção de arquivos do jogo
8. O Que NÃO Fazer Agora
Até a conclusão da Fase 2, evitar:
desenvolvimento de GUI;
sistema de patches;
Cloud;
gerenciamento de equipes;
CI/CD;
paralelização prematura;
suporte a várias engines simultaneamente;
grandes refatorações;
otimizações sem evidência de gargalo.
A arquitetura atual foi considerada sólida pela auditoria. O foco deve ser implementação, não reconstrução.
9. Estado de Conclusão
Pre-Alpha
Atualmente:
Arquitetura       ██████████  sólida
Testes unitários  ██████████  172 passando
Extração          ██░░░░░░░░  parcial
Persistência      ░░░░░░░░░░  inexistente
Tradução          ░░░░░░░░░░  provider não funcional
Validação         ░░░░░░░░░░  inexistente
Reinserção        ░░░░░░░░░░  inexistente
Meta imediata
FASE 1
  ↓
Pipeline com dados persistentes
  ↓
FASE 2
  ↓
Pipeline completo de I/O
  ↓
FASE 3
  ↓
Pipeline robusto
  ↓
FASE 4
  ↓
Expansão
10. Objetivo do Roadmap
O próximo marco do RPG Translator Suite não é uma interface bonita nem uma grande quantidade de funcionalidades.
É conseguir executar, de forma confiável:
┌───────────────────────────────┐
│        RPG Maker MV           │
└───────────────┬───────────────┘
                ↓
          Extração completa
                ↓
         Proteção de tokens
                ↓
             SQLite
                ↓
          QwenTranslator
                ↓
         Checkpoint / Retry
                ↓
            Validação
                ↓
          TextInserter
                ↓
             Backup
                ↓
┌───────────────▼───────────────┐
│       Jogo traduzido          │
└───────────────────────────────┘
Só depois de esse ciclo estar fechado, íntegro e testado o RTS deverá voltar a expandir sua superfície de funcionalidades.
Estimativa geral
Fase
Estimativa
Fase 1
80–100 h
Fase 2
60–80 h
Fase 3
40–60 h
Fase 4
80–120 h
Total
260–360 h
As estimativas são indicativas. A prioridade é a conclusão correta de cada gate técnico, não o cumprimento artificial de prazos.