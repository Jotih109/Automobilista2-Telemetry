# 🏎️ Claudio — Dashboard de Telemetria para Automobilista 2

> ⚠️ **PROJETO EM DESENVOLVIMENTO** — Este projeto ainda está incompleto. Algumas funcionalidades podem estar ausentes, instáveis ou sujeitas a mudanças significativas sem aviso prévio. Contribuições e sugestões são bem-vindas!

---

## 📖 Sobre o Projeto

**Claudio** é um dashboard de telemetria em tempo real desenvolvido em **Python** para o simulador **Automobilista 2 (AMS2)**. A aplicação recebe dados via protocolo **UDP (pCars2)**, processa as informações e as exibe em uma interface gráfica moderna construída com **PyQt5** e **PyQtGraph**.

O objetivo é fornecer ao piloto uma ferramenta de análise de desempenho semelhante às usadas em equipes de motorsport real — permitindo comparar voltas, identificar onde o tempo é perdido e acompanhar o estado do carro em tempo real.

---

## ✅ Funcionalidades Implementadas

### Painel Lateral (Sidebar)
- **Marcha atual** em destaque com cor dinâmica (Neutro = verde, Ré = vermelho, Redline = vermelho)
- **Velocidade (km/h)** em tempo real
- **Barra de RPM** com gradiente de cor baseado no percentual do RPM máximo
- **Bargraphs verticais** de Acelerador e Freio (GAS / BRK)
- **Dados do carro:** Combustível restante (L), voltas estimadas, consumo médio, pressão do turbo e ângulo do volante
- **Temperaturas e pressões** dos 4 pneus individualmente (FL, FR, RL, RR) com desgaste
- **Condições climáticas:** Temperatura ambiente, temperatura da pista, densidade de chuva e molhamento da pista
- **Assistências eletrônicas:** Indicadores de ABS, TC e Pit Limiter ativos
- **Seletor de Referência (Ghost):** Permite alternar entre Personal Best, Sessão Atual, Volta Ideal ou nenhum

### Área Principal — Gráficos
- **Velocidade (Km/h):** Curva da volta atual + curva fantasma da referência
- **Acelerador (%):** Curva da volta atual + curva fantasma da referência
- **Freio (%):** Curva da volta atual + curva fantasma da referência
- **RPM:** Curva da volta atual + curva fantasma da referência
- Linhas verticais de separação de **S1** e **S2** atualizadas dinamicamente conforme o ghost selecionado
- Cursor vermelho de posição temporal sincronizado em todos os gráficos
- Escala X automática baseada no tempo da melhor volta
- Escala Y dinâmica para velocidade e RPM

### Métricas de Topo
- **Volta Atual:** Tempo da volta em andamento
- **Melhor Volta:** Melhor tempo válido da sessão (≥ 30s para ignorar saídas dos boxes)
- **Delta Geral:** Diferença em tempo real vs. referência selecionada (`+X.XXs` / `-X.XXs`)
- **Setores S1, S2, S3:** Tempos do setor atual + tempo da referência + delta individual por setor
- **Ref / Est:** Tempo da volta de referência e projeção estimada de conclusão da volta atual

### Sistema de Referência (Ghost)
- **Personal Best:** Melhor volta pessoal salva em disco (persiste entre sessões)
- **Sessão Atual:** Melhor volta da sessão em andamento (apenas na memória)
- **Volta Ideal Teórica (Theoretical Best):** Costura automática (*splicing*) dos melhores setores já rodados — forma uma volta impossível que serve como referência máxima
- **Live Delta** calculado por interpolação de distância percorrida, não por tempo bruto — muito mais preciso em pistas com variação de ritmo

### Histórico de Voltas
- Tabela ao vivo com todas as voltas completadas na sessão
- Exibe tempos de S1, S2, S3 e Total
- Delta vs. melhor volta da sessão em cada linha
- Destaque automático na volta mais rápida

### Persistência e Exportação
- Voltas e ghosts salvos em JSON organizados por `pista/carro/` dentro da pasta `telemetry_data/`
- Exportação manual de screenshot (`.png`) da análise completa pelo botão **"Exportar Análise (Imagem)"**
- Exportação automática de imagem a cada novo **Personal Best** concluído (configurável via `AUTO_EXPORT_ON_BEST_LAP`)

### Modo Mock (Teste Offline)
- `MockTelemetryProvider` interno para simular uma corrida sem precisar abrir o jogo
- Útil para testar a interface, ajustar gráficos e verificar lógica de setores/delta

---

## 🚧 O que Ainda Está Incompleto / Planejado

> Esta seção lista funcionalidades que **ainda não foram implementadas** ou que estão parcialmente prontas.

- [ ] **Mapa da pista** — visualização do traçado com posição do carro em tempo real (`mapa.py` em desenvolvimento)
- [ ] **Comparação lado a lado de múltiplas voltas** — sobreposição de mais de 2 voltas nos gráficos
- [ ] **Análise de danos** — o campo `car_damage` já existe no modelo mas não é exibido na UI
- [ ] **Tela de análise pós-sessão** — revisão detalhada offline de voltas salvas
- [ ] **Suporte a múltiplos monitores** — janelas separadas para sidebar e gráficos
- [ ] **Configurações persistentes** — salvar preferências do usuário (referência padrão, tema, etc.)
- [ ] **Suporte a outras pistas/jogos** — arquitetura de providers permite extensão, mas apenas AMS2 está implementado
- [ ] **Testes automatizados** — sem cobertura de testes unitários no momento
- [ ] **Instalador / Executável** — distribuição como `.exe` para Windows ainda não disponível

---

## 📂 Estrutura do Projeto

```text
Claudio-main/
├── core/
│   ├── engine.py           # Thread a 60 Hz: captura estado e emite sinal Qt
│   ├── models.py           # TelemetryState — modelo padronizado de dados
│   └── session_manager.py  # Lógica de voltas, setores, splicing, ghost e consumo
├── providers/
│   ├── base.py             # Classe base abstrata (interface do provider)
│   ├── automobilista2.py   # Provider UDP real (protocolo pCars2 / AMS2)
│   └── mock.py             # Simulador interno para testes sem o jogo
├── ui/
│   ├── main_window.py      # Janela principal: gráficos, métricas e histórico
│   ├── sidebar_panel.py    # Painel lateral com mostradores do carro
│   ├── components.py       # Todos os widgets reutilizáveis (Cards, Plots, etc.)
│   └── mapa.py             # [EM DESENVOLVIMENTO] Visualização do mapa da pista
├── exportacoes/            # Screenshots PNG exportadas automaticamente
├── telemetry_data/         # Ghosts e histórico de voltas em JSON (por pista/carro)
├── main.pyw                # Ponto de entrada da aplicação
├── mock_game.py            # Emulador de pacotes UDP para desenvolvimento offline
├── requirements.txt        # Dependências Python
├── reset.bat               # Limpa dados salvos (CMD)
└── reset.ps1               # Limpa dados salvos (PowerShell)
```

---

## 🛠️ Requisitos

- **Python 3.8** ou superior
- **Automobilista 2** instalado (para uso com dados reais)
- Sistema operacional: **Windows** (testado no Windows 10/11)

### Dependências Python

```
PyQt5>=5.15.10
pyqtgraph>=0.13.7
```

---

## 📦 Instalação

**1. Clone ou baixe o repositório:**
```bash
git clone https://github.com/seu-usuario/claudio.git
cd claudio
```

**2. (Recomendado) Crie um ambiente virtual:**
```bash
python -m venv venv
venv\Scripts\activate
```

**3. Instale as dependências:**
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuração no Automobilista 2

Para que o jogo envie os dados de telemetria para o aplicativo:

1. Abra o **Automobilista 2**
2. Vá em **Opções → Jogabilidade → Telemetria UDP**  
   *(Options → Gameplay → UDP Telemetry)*
3. Configure os campos:

| Campo | Valor |
|-------|-------|
| Protocolo | `Project CARS 2` |
| Frequência UDP | `2` (60 Hz recomendado) |
| IP UDP | `127.0.0.1` |
| Porta UDP | `5606` |

---

## 🚀 Como Executar

### ▶️ Modo Normal (com o jogo rodando)

```bash
python main.pyw
```

O dashboard iniciará a escuta na porta UDP `5606`. Assim que você entrar na pista no AMS2, os dados aparecerão automaticamente.

---

### 🧪 Modo Simulação (sem o jogo — teste offline)

**Terminal 1** — inicia o simulador de pacotes UDP:
```bash
python mock_game.py
```

**Terminal 2** — inicia o dashboard:
```bash
python main.pyw
```

Ou ative o modo mock diretamente no código: em `main.pyw`, altere:
```python
MOCK_MODE = True
```

---

## 🧹 Limpeza de Dados

Para apagar todos os ghosts e histórico de voltas salvos:

**PowerShell:**
```powershell
.\reset.ps1
```

**CMD:**
```cmd
reset.bat
```

---

## 🗂️ Como os Dados São Salvos

Os dados de telemetria são organizados automaticamente em:

```
telemetry_data/
└── NomeDaPista/
    └── NomeDoCarro/
        ├── best_lap_ghost.json       # Melhor volta pessoal (persiste entre sessões)
        ├── ideal_lap_ghost.json      # Volta ideal teórica (melhor setor de cada)
        └── 2026-07-24_19-30_1-44-527.json   # Cada volta completada
```

Cada arquivo JSON contém:
- **`metadata`:** pista, carro, tempo de volta, tempos de setores e timestamp
- **`telemetry`:** arrays de tempo, distância, velocidade, acelerador, freio, RPM e setor

---

## 🤝 Contribuindo

Este projeto está em desenvolvimento ativo e contribuições são bem-vindas!

Se quiser ajudar:
1. Faça um fork do repositório
2. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
3. Faça commit das suas alterações: `git commit -m 'Adiciona minha feature'`
4. Envie para o fork: `git push origin feature/minha-feature`
5. Abra um Pull Request

---

## 📜 Licença

Projeto desenvolvido para fins de análise de telemetria e aprimoramento de pilotagem no Automobilista 2.  
Uso pessoal e educacional. Nenhuma afiliação com a **Reiza Studios**.
#   A u t o m o b i l i s t a 2 - T e l e m e t r y  
 