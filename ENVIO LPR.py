import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from datetime import datetime
import subprocess

# Dados das máquinas com seus respectivos IPs para Color e PB
machines_color = {
    "OCÉ 1": "192.168.200.80",
    "OCÉ 2": "192.168.200.81",
    "OCÉ 3": "192.168.200.85",
    "NUVERA": "192.168.200.72"
}

machines_pb = {
    "OCÉ 1": "192.168.200.80",
    "OCÉ 2": "192.168.200.81",
    "OCÉ 3": "192.168.200.85",
    "NUVERA": "192.168.200.72"
}

formats_color = ["A4", "20,5X26", "22X32", "A3", "SRA3"]
formats_pb = ["A4", "20,5X26", "22X32", "A3", "SRA3", "24X32", "24,5X34", "32X45", "32X48"]

papers_color = ["OFFSET 63G", "OFFSET 70G", "OFFSET 75G", "OFFSET 90G", "AVENA 70G", "AVENA 80G"]
papers_pb = ["OFFSET 63G", "OFFSET 70G", "OFFSET 75G", "OFFSET 90G", "AVENA 70G", "AVENA 80G"]

# Inicialmente, use máquinas PB
machines = machines_pb
formats = formats_pb
papers = papers_pb

# Pega a data atual
current_date = datetime.now().strftime("%d-%m-%Y")

# Dicionário para armazenar o caminho completo dos arquivos
file_paths = {}

def on_drop(event):
    # Usa uma regex para garantir que arquivos com espaços e múltiplos arquivos sejam tratados corretamente
    dropped_files = re.findall(r'\{.*?\}|\S+', event.data)  # Captura arquivos com ou sem {}

    for file in dropped_files:
        file = file.strip('{}')  # Remove chaves ao redor do arquivo, se existirem
        file = os.path.normpath(file)  # Normaliza o caminho do arquivo para garantir compatibilidade

        if file.endswith(".pdf"):  # Filtra apenas arquivos PDF
            file_name = os.path.basename(file)  # Obtém o nome do arquivo
            # Verifica se o arquivo já está na listbox para evitar duplicatas
            if file_name not in listbox_files.get(0, tk.END):
                listbox_files.insert(tk.END, file_name)
                file_paths[file_name] = file  # Armazena o caminho completo no dicionário

def on_double_click(event):
    select_files_manually()

def select_files_manually():
    selected_files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
    if selected_files:
        for file in selected_files:
            file_name = os.path.basename(file)
            if file.endswith(".pdf") and file_name not in listbox_files.get(0, tk.END):
                listbox_files.insert(tk.END, file_name)
                file_paths[file_name] = file  # Armazena o caminho completo no dicionário

def delete_selected_files():
    selected_files = listbox_files.curselection()
    if selected_files:
        for index in selected_files[::-1]:
            file_name = listbox_files.get(index)
            listbox_files.delete(index)
            del file_paths[file_name]  # Remove o arquivo do dicionário também

def clear_selection():
    listbox_files.delete(0, tk.END)
    file_paths.clear()  # Limpa também o dicionário de caminhos


def extract_relevant_part(filename):
    # Remove a extensão
    name, _ = os.path.splitext(filename)
    
    # Divide o nome em partes separadas por "-"
    parts = name.split("-")
    
    # Pega apenas os primeiros 4 elementos (ajuste conforme necessário)
    relevant_part = "-".join(parts[:4])
    
    return relevant_part.strip()


def send_files():
    selected_machine = combobox_machines.get()  # Nome da máquina selecionada
    selected_format = combobox_formats.get()
    selected_paper = combobox_papers.get()
    optional_text = entry_optional_text.get()

    if not selected_machine or not selected_format or not selected_paper:
        messagebox.showwarning("Aviso", "Por favor, selecione uma máquina, formato e tipo de papel.")
        return

    # Combina o formato e o tipo de papel para seguir o padrão esperado
    combined_format_paper = f"{selected_format} {selected_paper}"

    machine_ip = machines[selected_machine]  # Obtém o IP da máquina selecionada
    files_to_send = listbox_files.get(0, tk.END)

    if not files_to_send:
        messagebox.showwarning("Aviso", "Nenhum arquivo selecionado para envio.")
        return

    # Função para extrair a parte relevante do nome do arquivo
    def extract_relevant_part(filename):
        # Remove a extensão
        name, _ = os.path.splitext(filename)
        
        # Divide o nome em partes separadas por "-"
        parts = name.split("-")
        
        # Pega apenas os primeiros 4 elementos (ajuste conforme necessário)
        relevant_part = "-".join(parts[:4])
        
        return relevant_part.strip()

    for file in files_to_send:
        # Pega o caminho completo do arquivo
        file_path = file_paths.get(file)
        if not file_path:
            print(f"Erro: Caminho não encontrado para o arquivo {file}")
            continue

        filename = os.path.basename(file_path)
        # Extrai apenas a parte relevante do nome
        relevant_name = extract_relevant_part(filename)
        
        # Adiciona data e texto opcional ao nome fictício
        fictitious_name = f"{relevant_name}-{current_date}-{optional_text}" if optional_text else f"{relevant_name}-{current_date}"

        # Monta o comando lpr combinando o formato e o tipo de papel corretamente
        command = f'lpr -S {machine_ip} -P "{combined_format_paper}" -J "{fictitious_name}" "{file_path}"'
        
        # Exibe o comando completo no console para verificação
        print(f"Executando comando: {command}")
        
        try:
            # Executa o comando lpr e captura stdout e stderr
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Verifica se o comando foi bem-sucedido
            if result.returncode == 0:
                success_message = f"Arquivo {fictitious_name} enviado com sucesso para {machine_ip}."
                print(success_message)  # Exibe a mensagem de sucesso no console
                messagebox.showinfo("Sucesso", success_message)  # Exibe uma messagebox com o sucesso
            else:
                error_message = f"Erro ao enviar arquivo: {result.stderr.decode()}"
                print(error_message)  # Exibe o erro no console
                messagebox.showerror("Erro", error_message)  # Exibe uma messagebox com o erro
                
        except subprocess.CalledProcessError as e:
            error_message = f"Erro ao executar o comando LPR: {e}"
            print(error_message)  # Exibe o erro no console
            messagebox.showerror("Erro", f"Falha ao enviar o arquivo {filename}: {e}")
    
    print("Todos os arquivos foram enviados.")  # Mensagem no console ao final do envio
    messagebox.showinfo("Sucesso", "Arquivos enviados com sucesso!")  # Exibe uma messagebox ao final


# Função para alternar entre Color e PB
def toggle_color_mode():
    global machines, formats, papers
    if btn_color_pb.config('text')[-1] == 'Color':
        btn_color_pb.config(text="PB", bg="black", fg="white")
        machines = machines_pb
        formats = formats_pb
        papers = papers_pb
    else:
        btn_color_pb.config(text="Color", bg="blue", fg="white")
        machines = machines_color
        formats = formats_color
        papers = papers_color
    
    # Atualizar as comboboxes com os novos valores
    update_comboboxes()

# Função para atualizar os valores das comboboxes
def update_comboboxes():
    combobox_machines['values'] = list(machines.keys())
    combobox_formats['values'] = formats
    combobox_papers['values'] = papers
    combobox_machines.set('')
    combobox_formats.set('')
    combobox_papers.set('')

# Função para limpar todas as seleções
def reset_selections():
    combobox_machines.set('')
    combobox_formats.set('')
    combobox_papers.set('')
    clear_selection()

# Inicializa a janela principal com TkinterDnD
root = TkinterDnD.Tk()  
root.title("Gerenciador de Arquivos e Envio")
root.geometry("730x370")

# Frame para a esquerda e direita
frame_left = tk.Frame(root)
frame_left.grid(row=0, column=0, padx=10, pady=10, sticky="n")

frame_right = tk.Frame(root)
frame_right.grid(row=0, column=1, padx=10, pady=10, sticky="n")

# Lado Esquerdo
# Row 0, Column 0: Drag-and-Drop Label
label_drag_drop = tk.Label(frame_left, text="Arraste arquivos PDF aqui ou clique duas vezes para selecioná-los!",
                           width=50, height=7, bg="lightgray", fg="red", wraplength=300)
label_drag_drop.grid(row=0, column=0, padx=5, pady=5)

# Adiciona o binding para clique duplo no label
label_drag_drop.bind("<Double-1>", on_double_click)

# Row 1, Column 0: Listbox
listbox_files = tk.Listbox(frame_left, selectmode=tk.MULTIPLE, width=50, height=10, bg="white", fg="black")
listbox_files.grid(row=1, column=0, padx=5, pady=5)

# Row 2, Column 0: Botões "Deletar" e "Limpar"
button_frame = tk.Frame(frame_left)
button_frame.grid(row=2, column=0, pady=10)

btn_delete = tk.Button(button_frame, text="Deletar Selecionados", command=delete_selected_files, width=20, bg="red", fg="white")
btn_delete.grid(row=0, column=0, padx=5, pady=5)

btn_clear = tk.Button(button_frame, text="Limpar Todos", command=clear_selection, width=20, bg="gray", fg="white")
btn_clear.grid(row=0, column=1, padx=5, pady=5)

# Lado Direito
# Row 0, Column 1: Botão PB/Color (ocupa duas colunas)
btn_color_pb = tk.Button(frame_right, text="PB", command=toggle_color_mode, width=40, bg="black", fg="white")
btn_color_pb.grid(row=0, column=0, columnspan=2, pady=10)

# Row 1, Column 1: Seletor de máquina
label_machines = tk.Label(frame_right, text="Selecione a Máquina", font=("Arial", 10, "bold"))
label_machines.grid(row=1, column=0, pady=5)
combobox_machines = ttk.Combobox(frame_right, state="readonly")
combobox_machines.grid(row=1, column=1, pady=5)

# Row 2, Column 1: Seletor de formato
label_formats = tk.Label(frame_right, text="Formato", font=("Arial", 10, "bold"))
label_formats.grid(row=2, column=0, pady=5)
combobox_formats = ttk.Combobox(frame_right, state="readonly")
combobox_formats.grid(row=2, column=1, pady=5)

# Row 3, Column 1: Seletor de tipo de papel
label_papers = tk.Label(frame_right, text="Papel", font=("Arial", 10, "bold"))
label_papers.grid(row=3, column=0, pady=5)
combobox_papers = ttk.Combobox(frame_right, state="readonly")
combobox_papers.grid(row=3, column=1, pady=5)

# Row 4, Column 1: Entrada de texto opcional para nome fictício
label_optional = tk.Label(frame_right, text="Identificação", font=("Arial", 10, "bold"))
label_optional.grid(row=4, column=0, pady=5)
entry_optional_text = tk.Entry(frame_right, width=23)
entry_optional_text.grid(row=4, column=1, pady=5)

# Row 5, Column 1: Botões Limpar e Enviar
button_frame_right = tk.Frame(frame_right)
button_frame_right.grid(row=5, column=0, columnspan=2, pady=10)

btn_reset = tk.Button(button_frame_right, text="Limpar", command=reset_selections, width=20, bg="gray", fg="white")
btn_reset.grid(row=0, column=0, padx=5, pady=5)

btn_send = tk.Button(button_frame_right, text="Enviar Arquivos", command=send_files, width=20, bg="green", fg="white")
btn_send.grid(row=0, column=1, padx=5, pady=5)

# Inicializa as comboboxes
update_comboboxes()

# Configura a janela principal para aceitar drag-and-drop em qualquer lugar
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', on_drop)

root.mainloop()