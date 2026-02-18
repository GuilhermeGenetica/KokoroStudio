# Kokoro Studio 82M - Pro TTS 🎙️

O **Kokoro Studio 82M** é uma aplicação de interface gráfica avançada (GUI) para conversão de Texto para Fala (Text-to-Speech - TTS) utilizando o modelo Kokoro. Desenvolvido com CustomTkinter, ele oferece um ambiente de estúdio completo para sintetizar vozes, ajustar parâmetros de áudio, gerenciar ficheiros e reproduzir os resultados diretamente na aplicação.

## ✨ Principais Recursos

* **Síntese de Voz Multilingue:** Suporta Inglês (EUA/UK), Português (Brasil), Espanhol, Francês, Italiano, Japonês, Chinês e Hindi.
* **Ajustes de Áudio em Tempo Real:** Controles deslizantes para Velocidade, Ganho de Volume (dB) e Pitch (Tom).
* **Gestor de Ficheiros Integrado:** Selecione pastas de trabalho, renomeie, converta ficheiros para MP3 ou apague áudios diretamente pela interface.
* **Player de Áudio Embutido:** Ouça suas gerações instantaneamente com controles de Play, Pause, Stop, Avançar e Retroceder, além de uma barra de progresso visual.
* **Conversão Inteligente:** Exporta em `.wav` de alta qualidade nativamente ou converte automaticamente para `.mp3`.

---

## 🛠️ Pré-requisitos e Instalação (Passo a Passo)

Para rodar o Kokoro Studio, você precisará do **Python** instalado no seu sistema, juntamente com bibliotecas de processamento de áudio, inteligência artificial e a ferramenta **FFmpeg** (necessária para manipulação de MP3).

### Passo 1: Instalar o Python e o pip
1. Acesse o site oficial: [python.org/downloads](https://www.python.org/downloads/)
2. Baixe a versão mais recente do Python (recomenda-se a versão 3.10 ou superior).
3. **MUITO IMPORTANTE (Windows):** Durante a instalação, certifique-se de marcar a caixa **"Add Python to PATH"** (Adicionar Python ao PATH) antes de clicar em "Install Now".
4. Verifique a instalação abrindo o Terminal (ou Prompt de Comando) e digitando:
   ```bash
   python --version
   pip --version


```

### Bibliotecas:
# Interface Gráfica
customtkinter

# Processamento de Áudio e Matemática
numpy
scipy
soundfile

# Manipulação de Formatos (MP3) e Player
pydub
pygame

# Inteligência Artificial e TTS
torch
torchaudio
kokoro


### Passo 2: Instalar o FFmpeg (Obrigatório para MP3)

A biblioteca `pydub` precisa do FFmpeg para converter os ficheiros `.wav` gerados pelo modelo para `.mp3`.

* **No Windows:**
1. Baixe o executável do [FFmpeg (gyan.dev)](https://www.gyan.dev/ffmpeg/builds/) (procure por `ffmpeg-release-essentials.zip`).
2. Extraia o ficheiro zip na sua unidade `C:\` (ex: `C:\ffmpeg`).
3. Adicione a pasta `bin` (ex: `C:\ffmpeg\bin`) nas **Variáveis de Ambiente** do Windows (`Path`).


* **No macOS:**
Abra o terminal e use o Homebrew:
```bash
brew install ffmpeg

```

* **No Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install ffmpeg

```


### Passo 3: Instalar o PyTorch

O modelo Kokoro requer o PyTorch. O script atual está configurado para usar o processador (CPU) de forma a garantir estabilidade em qualquer máquina (`device='cpu'`).
No terminal, execute:

```bash
pip install torch torchvision torchaudio

```

*(Nota: Se desejar aceleração por GPU no futuro, consulte o site oficial do [PyTorch](https://pytorch.org/get-started/locally/) para o comando específico com suporte CUDA).*

### Passo 4: Instalar as Bibliotecas do Projeto

Agora, instale todas as dependências requeridas pelo programa executando o seguinte comando no seu terminal:

```bash
pip install -q kokoro>=0.9.4 soundfile
apt-get -qq -y install espeak-ng > /dev/null 2>&1
pip install customtkinter numpy soundfile scipy pydub pygame

```

**Resumo das bibliotecas:**

* `customtkinter`: Cria a interface gráfica moderna e escura.
* `numpy` & `scipy`: Usados para o processamento e manipulação dos arrays de áudio (como o efeito de Pitch).
* `soundfile`: Grava o áudio gerado pelo modelo em formato `.wav`.
* `pydub`: Manipula a conversão de formatos de áudio (para `.mp3`).
* `pygame`: Motor do player de áudio integrado na aba direita.
* `kokoro`: A biblioteca oficial/pipeline (KPipeline) responsável pela inteligência artificial de Text-to-Speech.

---

## 🚀 Como Executar o Programa

1. Guarde o código principal num ficheiro chamado `kokoro_play.py`.
2. Abra o terminal ou Prompt de Comando na pasta onde o ficheiro foi salvo.
3. Execute o script com o comando:
```bash
python kokoro_play.py

```


4. A janela do **Kokoro Studio** será aberta e estará pronta para uso! Na primeira vez que gerar um áudio, o modelo Kokoro fará o download dos ficheiros de voz necessários em segundo plano, então pode demorar alguns segundos a mais.

---

## 📖 Guia Rápido de Uso

1. **Configurações (Painel Esquerdo):**
* Selecione o idioma desejado (ex: Português, Inglês).
* Escolha a voz que melhor se adapta à emoção ou timbre desejado.
* Ajuste os controles deslizantes de Velocidade, Volume (Ganho) e Pitch conforme a sua preferência.


2. **Entrada de Texto (Centro):**
* Escreva ou cole o texto que deseja transformar em áudio na caixa de texto central.
* Defina um nome para o ficheiro e escolha a extensão (`.mp3` ou `.wav`). Se deixar em branco, o sistema criará um nome automático (ex: `audio_kokoro_1.mp3`).
* Clique em **"▶️ PLAY / GERAR"**.


3. **Gestor de Ficheiros (Painel Direito):**
* Veja todos os ficheiros gerados na pasta de trabalho atual.
* Selecione um ficheiro na lista para habilitar os controlos de baixo.
* **Player de Áudio:** Use os controlos (Play, Pause, Stop, Retroceder, Avançar) para ouvir o ficheiro selecionado diretamente na aplicação.
* **Ações:** Clique em "✏️" para renomear, "MP3" para converter um ficheiro `.wav` existente, ou "🗑️" para apagar.



## ⚠️ Solução de Problemas

* **Erro "Biblioteca pydub não encontrada" ou "Erro na Conversão MP3":** Verifique se o passo 2 (Instalação do FFmpeg) foi concluído com sucesso e se o sistema reconhece o comando `ffmpeg` no terminal.
* **Erro "pygame não está instalado":** Certifique-se de que rodou `pip install pygame`. Sem ele, a área de reprodução de áudio não funcionará.
* **A aplicação demora para gerar o primeiro áudio:** Isso é normal. O `KPipeline` faz o download dos pesos do modelo (pesam cerca de 82MB) na primeira inicialização de um novo idioma.


```
