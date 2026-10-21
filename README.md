# 📄 Hotfolder — Envio de PDF via LPR

Aplicação desktop em **Python + Tkinter** para envio em lote de arquivos **PDF** a impressoras de produção (OCÉ, RICOH, BALTORO) através do comando **`lpr`** (Line Printer Remote), com suporte a **arrastar e soltar (drag & drop)**, seleção de **formato de papel**, **gramatura** e **fila de destino** montada dinamicamente conforme a máquina escolhida.

---

## 🎯 Objetivo

Automatizar o envio de PDFs para diferentes impressoras de uma gráfica, montando o nome da fila de impressão (`queue`) conforme o **grupo da máquina** (`PB` = preto e branco / `CL` = colorida) e o **formato/papel** selecionado, sem que o operador precise montar o comando `lpr` manualmente.

---

## 🖥️ Funcionalidades

- **Seleção de máquina** com IP exibido automaticamente
- **Arrastar e soltar** arquivos `.pdf` na janela (via `tkinterdnd2`)
- **Adição manual** de arquivos por duplo clique na lista
- **Remoção individual** ou **limpeza total** da lista
- **Seleção de formato e papel/gramatura** — populados dinamicamente conforme a máquina
- **Identificação opcional** do lote (ex.: `cliente_lote`) que é anexada ao nome do trabalho
- **Barra de progresso** com percentual e nome do arquivo em envio
- **Cancelamento** do envio em andamento
- **Log de eventos** com timestamp
- **Envio em thread separada** (não trava a interface)
- **Limpeza automática** da pasta temporária ao fechar o programa

---

## ⚙️ Como funciona

### 1. Configuração por máquina

Cada máquina tem:

| Campo     | Descrição |
|-----------|-----------|
| `ip`      | IP da impressora na rede |
| `group`   | `"PB"` (preto e branco) ou `"CL"` (colorida) |
| `formats` | Lista de formatos disponíveis |
| `papers`  | Lista de papéis/gramaturas disponíveis |

```python
MACHINE_CONFIG = {
    "OCÉ 1":   {"ip": "192.168.200.80", "group": "PB", "formats": [...], "papers": [...]},
    "OCÉ 2":   {"ip": "192.168.200.81", "group": "PB", "formats": [...], "papers": [...]},
    "RICOH":   {"ip": "192.168.200.84", "group": "CL", "formats": [...], "papers": [...]},
    "BALTORO": {"ip": "192.168.200.73", "group": "CL", "formats": [...], "papers": [...]},
}
```

### 2. Regra de montagem do nome da fila

A fila de destino (`queue`) do comando `lpr` é montada assim:

| Situação | Exemplo |
|----------|---------|
| **Formato especial** (Ricoh: `CAPADUPLEX`, `Capas 28X56`, `Capas 32X60`) | `CAPADUPLEX` (sem papel) |
| **Grupo PB** (OCÉ) | `A4 OFFSET 63G` (com espaço) |
| **Grupo CL** (RICOH / BALTORO) | `22X32_COUCHE_90G` (com underscore) |

> ⚠️ A escolha entre **espaço** (PB) e **underscore** (CL) é fundamental para que o `lpr` encontre a fila correta no servidor de impressão.

### 3. Comando executado

Para cada arquivo, o programa copia o PDF para uma pasta temporária e executa:

```bash
lpr -S <IP> -P "<fila>" -J "<identificacao>" "<arquivo_temp.pdf>"
```

Onde:

- `-S <IP>` → servidor de impressão (a própria impressora)
- `-P "<fila>"` → fila montada dinamicamente
- `-J "<identificacao>"` → nome do trabalho (`basename-AAAA-MM-DD-identificacao`)

---

## 📋 Pré-requisitos

### Sistema operacional

- Linux (recomendado) ou macOS — o `lpr` já vem instalado na maioria das distros.
- No **Windows** é necessário instalar o **`lpr`** (via *Print Services for Unix* ou via **WSL/Cygwin**).

### Python

- Python **3.8+**

### Dependências Python

```bash
pip install tkinterdnd2
```

> `tkinter` já vem com o Python na maioria das instalações. Caso falte:
>
> - Debian/Ubuntu: `sudo apt install python3-tk`
> - Fedora: `sudo dnf install python3-tkinter`

### Rede

- As impressoras precisam estar acessíveis na rede local e com o **serviço LPR habilitado**.

---

## 🚀 Como usar

1. **Execute o programa**:

   ```bash
   python hotfolder.py
   ```

2. **Selecione a máquina** no combo do topo — o IP será exibido ao lado.

3. **Arraste PDFs** para a área cinza ou dê **duplo clique** na lista para selecionar arquivos manualmente.

4. **Escolha o formato** e, se necessário, o **papel/gramatura** (para formatos especiais como `CAPADUPLEX`, o campo de papel é desabilitado automaticamente).

5. *(Opcional)* Preencha a **identificação** — será anexada ao nome do trabalho na impressora.

6. Clique em **"Enviar arquivos"**.

7. Acompanhe pela **barra de progresso** e pelo **log de eventos**.

8. Ao final:
   - Se todos enviarem com sucesso → mensagem de confirmação e lista é limpa.
   - Se houver falhas → mensagem de erro parcial com detalhes no log.

---

## 🧱 Estrutura do código

```
HotfolderApp
├── __init__                → monta a interface
├── on_machine_change       → atualiza IP, formatos e papéis
├── on_format_change        → habilita/desabilita papel para formatos especiais
├── on_drop                 → trata drag & drop
├── add_files_manually      → seleção via diálogo
├── delete_selected         → remove arquivos selecionados
├── clear_all               → limpa lista
├── start_send              → valida e dispara thread de envio
├── cancel                  → sinaliza cancelamento
├── _send_thread            → thread que executa o lpr para cada arquivo
├── log                     → escreve no Text do log
├── reset_progress          → zera barra e label
└── _cleanup_on_exit        → remove pasta temp ao fechar
```

---

## 🔧 Personalização

### Adicionar uma nova máquina

Basta editar o dicionário `MACHINE_CONFIG`:

```python
MACHINE_CONFIG["NOVA MAQUINA"] = {
    "ip": "192.168.200.99",
    "group": "PB",                       # ou "CL"
    "formats": ["A4", "A3"],
    "papers": ["OFFSET 75G"],
}
```

O combo na tela é populado automaticamente a partir das chaves do dicionário.

### Adicionar novos formatos especiais (sem papel)

```python
SPECIAL_FORMATS_RICOH = ["CAPADUPLEX", "Capas 28X56", "Capas 32X60", "MEU_FORMATO"]
```

Formatos nesta lista automaticamente:

- Não exigem seleção de papel
- Usam o próprio nome como **fila** (`queue`)

---

## 🐛 Solução de problemas

| Sintoma | Possível causa | Solução |
|---------|----------------|---------|
| `lpr: command not found` | `lpr` não instalado | Instale via `sudo apt install cups-bsd` (Debian/Ubuntu) |
| `FALHA: ... - conexão recusada` | IP errado / impressora offline | Verifique o IP e se a impressora está ligada |
| Arquivo envia, mas não imprime | Nome de fila incorreto | Confira no servidor se a fila existe com **exatamente** aquele nome (com espaço ou underscore) |
| Janela não abre | Falta `tkinter` | `sudo apt install python3-tk` |
| Drag & drop não funciona | Falta `tkinterdnd2` | `pip install tkinterdnd2` |

---

## 📌 Observações técnicas

- **Threads**: o envio roda em uma thread separada (`daemon=True`) para manter a interface responsiva. Atualizações de widgets são feitas via `root.after(0, ...)` para respeitar a *thread-safety* do Tkinter.
- **Arquivos temporários**: cada PDF é copiado para `tempfile.mkdtemp()` antes do envio e apagado logo após o `lpr` retornar. A pasta é removida no `WM_DELETE_WINDOW`.
- **Timeout**: cada envio tem limite de **90 segundos** para evitar travar em impressoras lentas ou offline.
- **Nome do trabalho**: `basename[:40]-DD-MM-YYYY-identificacao`, com `-` extras removidos nas pontas.

---

## 📄 Licença

Uso interno. Adapte conforme a necessidade da sua gráfica.
