# FFmpeg Tools (Windows Context Menu)

Uma ferramenta poderosa e visual para automatizar tarefas comuns do FFmpeg diretamente pelo menu de contexto (botão direito) do Windows.

## 🚀 Funcionalidades

### 🎬 Manipulação de Vídeo

- **Concatenar Vídeos**: Junte vários arquivos em um só.
  - **Smart Analysis**: A interface avisa se os vídeos têm resoluções ou FPS diferentes.
  - **Safe Mode**: Se houver incompatibilidade, o script `safe_concat.py` entra em ação automaticamente para redimensionar e normalizar os vídeos.
  - **Heurísticas de Resolução**: Escolha como resolver conflitos — Maior Duração Total, Maior Resolução, Maioria, Primeiro Arquivo ou Manual.
  - **Modos de Ajuste**: Letterbox (barras pretas) ou Crop (Centro, Cima, Baixo, Esquerda, Direita).
- **Crop Espacial**: Recorte uma região (W×H) do vídeo ou GIF, com posição manual (X, Y) ou centralizada.
- **Flash de Memória**: Intercale fragmentos de um segundo vídeo no primeiro, criando um efeito de "flashes de memória".
  - Configurável: número de fragmentos (sorteados), subfragmentos por grupo, tamanho e espaçamento em frames.
  - Seed reproduzível para resultados consistentes.
- **Cortar Início/Fim**: Remova um número exato de frames do começo ou do final.
- **Loop Final**: Extraia o trecho final e repita-o N vezes (Normal ou Ping-Pong).
- **Redimensionar**: Converta rapidamente para 720p.
- **Mover/Remover Áudio**: Mute o vídeo ou extraia apenas o som em MP3.

### 🖼️ Imagem e Áudio

- **Imagem para Vídeo**: Crie um vídeo de alta compatibilidade a partir de uma única imagem, escolhendo a duração (frames) e o FPS.
- **Mix de Áudio**: Combine vários arquivos de áudio em um único mix.
- **Substituir Áudio**: Troque a trilha sonora de um vídeo por um arquivo de áudio externo.

### 🔄 Conversão

- **Converter para MP4 (H.264)**: Garanta compatibilidade universal.
- **Converter para GIF**: Crie GIFs otimizados com paleta de cores inteligente.

## 🛠️ Requisitos

- **Python 3.x**
- **PyQt6** (`pip install PyQt6`)
- **FFmpeg** instalado e configurado no seu PATH do Windows.

## 📥 Como Usar

1. Clone ou baixe esta pasta para o seu computador.
2. Certifique-se de que o **FFmpeg** está acessível pelo terminal.
3. Execute o programa através do `main_gui.py` ou do atalho `ffmpeg_tools.bat`.
4. Arraste e solte seus arquivos na interface e selecione a operação desejada.

## 📂 Estrutura do Projeto

- `main_gui.py`: Interface principal em PyQt6 com suporte a Drag-and-Drop.
- `safe_concat.py`: Script auxiliar para concatenação robusta de vídeos com formatos mistos (resolução, FPS, áudio).
- `ffmpeg_tools.bat`: Atalho para execução rápida da interface.
- `ffmpeg_tools.ico`: Ícone personalizado da aplicação.

---

_Desenvolvido para facilitar o workflow de edição rápida de vídeos._
