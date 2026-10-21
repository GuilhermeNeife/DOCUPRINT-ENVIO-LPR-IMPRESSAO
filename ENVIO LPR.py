import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from datetime import datetime
import subprocess
import shutil
import tempfile

# Dados das máquinas e suas configurações
machines = {
    "OCÉ 1": "192.168.200.80",
    "OCÉ 2": "192.168.200.81",
    "OCÉ 3": "192.168.200.85"
}

formats_pb = ["A4", "20,5X26", "22X32", "A3", "SRA3", "24X32", "24,5X34", "32X45", "32X48"]
papers_pb = ["OFFSET 63G", "OFFSET 70G", "OFFSET 75G", "OFFSET 90G", "AVENA 70G", "AVENA 80G"]

# Pega a data atual
current_date = datetime.now().strftime("%d-%m-%Y")

# Dicionário para armazenar o caminho completo dos arquivos
file_paths = {"OCÉ 1": [], "OCÉ 2": [], "OCÉ 3": []}

# Cria uma única pasta temporária para todos os arquivos
common_temp_dir = tempfile.mkdtemp()

def on_drop(event, machine_name):
    dropped_files = re.findall(r'\{.*?\}|\S+', event.data)  # Captura arquivos com ou sem {}
    
    for file in dropped_files:
        file = file.strip('{}')  # Remove chaves ao redor do arquivo, se existirem
        file = os.path.normpath(file)  # Normaliza o caminho do arquivo para garantir compatibilidade

        if file.endswith(".pdf"):  # Filtra apenas arquivos PDF
            file_name = os.path.basename(file)  # Obtém o nome do arquivo
            # Verifica se o arquivo já está na listbox para evitar duplicatas
            if file_name not in listbox_files[machine_name].get(0, tk.END):
                listbox_files[machine_name].insert(tk.END, file_name)
                file_paths[machine_name].append(file)  # Armazena o caminho completo no dicionário

def on_double_click(event, machine_name):
    select_files_manually(machine_name)

def select_files_manually(machine_name):
    selected_files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
    if selected_files:
        for file in selected_files:
            file_name = os.path.basename(file)
            if file.endswith(".pdf") and file_name not in listbox_files[machine_name].get(0, tk.END):
                listbox_files[machine_name].insert(tk.END, file_name)
                file_paths[machine_name].append(file)  # Armazena o caminho completo no dicionário

# Função para remover arquivos selecionados da listbox
def delete_selected_files(machine_name):
    selected_files = listbox_files[machine_name].curselection()
    if selected_files:
        for index in selected_files[::-1]:
            listbox_files[machine_name].delete(index)
            file_paths[machine_name].pop(index)

# Função para remover todos os arquivos da listbox
def clear_all_files(machine_name):
    listbox_files[machine_name].delete(0, tk.END)
    file_paths[machine_name].clear()

# Função para criar um arquivo temporário com um nome único e copiar o PDF para ele
def criar_arquivo_temporario(orig_file_path, index):
    try:
        temp_file_path = os.path.join(common_temp_dir, f"arquivo_temp_{index}.pdf")  # Nome único para cada arquivo
        shutil.copy(orig_file_path, temp_file_path)  # Copia o arquivo original para o temporário
        return temp_file_path
    except Exception as e:
        print(f"Erro ao criar arquivo temporário: {e}")
        return None

# Função para esvaziar ou apagar a pasta temporária após o envio
def limpar_pasta_temporaria():
    try:
        if os.path.exists(common_temp_dir):
            # Remove todos os arquivos dentro da pasta
            for temp_file in os.listdir(common_temp_dir):
                temp_file_path = os.path.join(common_temp_dir, temp_file)
                os.remove(temp_file_path)
            print(f"Todos os arquivos temporários foram removidos da pasta {common_temp_dir}.")
        else:
            print(f"Pasta temporária {common_temp_dir} não encontrada.")
    except Exception as e:
        print(f"Erro ao limpar a pasta temporária: {e}")

# Função para enviar arquivos
def send_files(machine_name):
    selected_format = combobox_formats[machine_name].get()
    selected_paper = combobox_papers[machine_name].get()
    optional_text = entry_optional_text[machine_name].get()

    if not selected_format or not selected_paper:
        messagebox.showwarning("Aviso", "Por favor, selecione um formato e tipo de papel.")
        return

    # Preenche identificação vazia se o campo não foi modificado
    if optional_text == "Identificação (Opcional)":
        optional_text = ""

    combined_format_paper = f"{selected_format} {selected_paper}"

    machine_ip = machines[machine_name]
    files_to_send = file_paths[machine_name]

    if not files_to_send:
        messagebox.showwarning("Aviso", f"Nenhum arquivo selecionado para envio na máquina {machine_name}.")
        return

    for index, file_path in enumerate(files_to_send, start=1):
        filename = os.path.basename(file_path)
        fictitious_name = f"{filename[:35]}-{current_date}-{optional_text}".strip("-")

        # Criar arquivo temporário com nome único
        temp_file_path = criar_arquivo_temporario(file_path, index)
        if not temp_file_path:
            messagebox.showerror("Erro", f"Falha ao criar arquivo temporário para {filename}.")
            continue

        # Monta o comando lpr para enviar o PDF temporário
        command = f'lpr -S {machine_ip} -P "{combined_format_paper}" -J "{fictitious_name}" "{temp_file_path}"'
        print(f"Executando comando: {command}")
        
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                success_message = f"Arquivo {fictitious_name} enviado com sucesso para {machine_ip}."
            else:
                error_message = f"Erro ao enviar arquivo: {result.stderr.decode()}"
                print(error_message)
                messagebox.showerror("Erro", error_message)
                
        except subprocess.CalledProcessError as e:
            error_message = f"Erro ao executar o comando LPR: {e}"
            print(error_message)
            messagebox.showerror("Erro", f"Falha ao enviar o arquivo {filename}: {e}")

    print(f"Todos os arquivos foram enviados para {machine_name}.")
    messagebox.showinfo("Sucesso", f"Arquivos enviados com sucesso para {machine_name}!")

    # Limpar a pasta temporária após o envio

    
    # Limpa a lista de arquivos
    listbox_files[machine_name].delete(0, tk.END)
    file_paths[machine_name].clear()


# Função para centralizar a janela
def center_window(window):
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')


# Inicializa a janela principal com TkinterDnD
root = TkinterDnD.Tk()
root.title("HOTFOLDERS")
root.geometry("1050x470")
root.resizable(False, False)
root.attributes("-toolwindow", 1)
# Frame principal
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Criando estruturas de widgets para cada máquina
listbox_files = {}
combobox_formats = {}
combobox_papers = {}
entry_optional_text = {}

for i, machine_name in enumerate(machines.keys()):
    # Frame da máquina
    machine_frame = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN)
    machine_frame.grid(row=0, column=i, padx=10, pady=10)

    # Label de arrastar arquivos
    label_drag_drop = tk.Label(machine_frame, text=f"Arraste arquivos PDF para {machine_name}", width=43, height=5, bg="lightgray", fg="red", wraplength=250)
    label_drag_drop.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
    label_drag_drop.drop_target_register(DND_FILES)
    label_drag_drop.dnd_bind('<<Drop>>', lambda e, m=machine_name: on_drop(e, m))

    # Listbox para mostrar os arquivos
    listbox_files[machine_name] = tk.Listbox(machine_frame, selectmode=tk.MULTIPLE, width=51, height=10,selectbackground="red")
    listbox_files[machine_name].grid(row=1, column=0, columnspan=2, padx=5, pady=5)

    # Bind de clique duplo para seleção manual de arquivos
    listbox_files[machine_name].bind("<Double-1>", lambda e, m=machine_name: on_double_click(e, m))

    # Botões para remover arquivos
    btn_delete_selected = tk.Button(machine_frame, text="Remover Selecionados", command=lambda m=machine_name: delete_selected_files(m), width=20, bg="red", fg="white")
    btn_delete_selected.grid(row=2, column=0, padx=5, pady=5)

    btn_clear_all = tk.Button(machine_frame, text="Limpar Todos", command=lambda m=machine_name: clear_all_files(m), width=20, bg="gray", fg="white")
    btn_clear_all.grid(row=2, column=1, padx=5, pady=5)

    # Seletor de formato
    combobox_formats[machine_name] = ttk.Combobox(machine_frame, values=formats_pb, state="readonly", width=20)
    combobox_formats[machine_name].grid(row=3, column=0, padx=5, pady=5)
    combobox_formats[machine_name].set("Selecione o Formato")

    # Seletor de papel
    combobox_papers[machine_name] = ttk.Combobox(machine_frame, values=papers_pb, state="readonly", width=20)
    combobox_papers[machine_name].grid(row=3, column=1, padx=5, pady=5)
    combobox_papers[machine_name].set("Selecione o Papel")

    # Campo de texto para identificação
    entry_optional_text[machine_name] = tk.Entry(machine_frame, width=22)
    entry_optional_text[machine_name].grid(row=4, column=1, padx=10, pady=10)

    Identificador_text = tk.Label(machine_frame,text="Identificação (Opcional)")
    Identificador_text.grid(row=4,column=0,padx=10,pady=10)

   

    # Botão de enviar arquivos
    btn_send = tk.Button(machine_frame, text="Enviar Arquivos", command=lambda m=machine_name: send_files(m), width=40, bg="green", fg="white")
    btn_send.grid(row=5, column=0, columnspan=2, padx=5, pady=10)

center_window(root)
# Inicializa a interface Tkinter
root.mainloop()

