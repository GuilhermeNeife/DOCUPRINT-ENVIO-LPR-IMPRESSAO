import os
import re
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

# ------------------------------------------------------------
# CONFIGURAÇÕES POR MÁQUINA (incluindo grupo)
# ------------------------------------------------------------
COMMON_FORMATS_PB = ["A4", "A3", "SRA3", "22X32", "24X32", "24,5X34", "25,2X35,6", "32X45", "32X48"]
COMMON_PAPERS_PB  = ["OFFSET 63G", "OFFSET 70G", "OFFSET 75G", "OFFSET 90G", "AVENA 70G", "AVENA 80G", "BOLD 90G"]

COMMON_FORMATS_CL = ["22X32", "24X32", "25X36", "32X45", "32X48"]
COMMON_PAPERS_CL  = ["COUCHE 90G", "OFFSET 63G", "OFFSET 70G", "OFFSET 75G", "OFFSET 90G", "AVENA 70G", "AVENA 80G", "BOLD 90G"]

SPECIAL_FORMATS_RICOH = ["CAPADUPLEX", "Capas 28X56", "Capas 32X60"]
NO_PAPER_FORMATS = SPECIAL_FORMATS_RICOH

# Configuração com grupo identificador
MACHINE_CONFIG = {
    "OCÉ 1":   {"ip": "192.168.200.80", "group": "PB", "formats": COMMON_FORMATS_PB, "papers": COMMON_PAPERS_PB},
    "OCÉ 2":   {"ip": "192.168.200.81", "group": "PB", "formats": COMMON_FORMATS_PB, "papers": COMMON_PAPERS_PB},
    "RICOH":   {"ip": "192.168.200.84", "group": "CL", "formats": COMMON_FORMATS_CL + SPECIAL_FORMATS_RICOH, "papers": COMMON_PAPERS_CL},
    "BALTORO": {"ip": "192.168.200.73", "group": "CL", "formats": COMMON_FORMATS_CL, "papers": COMMON_PAPERS_CL},
}

# ------------------------------------------------------------
# CLASSE PRINCIPAL
# ------------------------------------------------------------
class HotfolderApp:
    def __init__(self, root):
        self.root = root
        root.title("Hotfolder - Envio de PDF via LPR")
        root.geometry("850x680")

        # Pasta temporária
        self.temp_dir = tempfile.mkdtemp(prefix="hotfolders_")
        self._cleanup_on_exit()

        # Controle de envio
        self.file_paths = []
        self.sending = False
        self.cancel_send = False

        # Interface
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Máquina ---
        machine_frame = ttk.LabelFrame(main_frame, text="Máquina", padding=5)
        machine_frame.pack(fill=tk.X, pady=(0,10))

        ttk.Label(machine_frame, text="Selecione a máquina:").pack(side=tk.LEFT, padx=5)
        self.machine_var = tk.StringVar()
        self.machine_combo = ttk.Combobox(machine_frame, textvariable=self.machine_var,
                                          values=list(MACHINE_CONFIG.keys()), state="readonly", width=20)
        self.machine_combo.pack(side=tk.LEFT, padx=5)
        self.machine_combo.bind("<<ComboboxSelected>>", self.on_machine_change)

        self.ip_label = ttk.Label(machine_frame, text="IP: ---", foreground="blue")
        self.ip_label.pack(side=tk.LEFT, padx=15)

        # --- Drag & Drop ---
        drop_frame = ttk.LabelFrame(main_frame, text="Arquivos PDF", padding=5)
        drop_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.drop_area = tk.Label(drop_frame, text="Arraste arquivos PDF para cá", bg="#e8e8e8",
                                  height=3, relief=tk.FLAT, font=("Arial", 10))
        self.drop_area.pack(fill=tk.X, pady=5)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.on_drop)
        self._add_tooltip(self.drop_area, "Solte arquivos .pdf aqui ou clique duplo na lista para adicionar")

        # Listbox com scroll
        list_frame = ttk.Frame(drop_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.listbox = tk.Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.bind("<Double-1>", self.add_files_manually)

        btn_frame = ttk.Frame(drop_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Remover selecionados", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Limpar todos", command=self.clear_all).pack(side=tk.RIGHT, padx=2)

        self.counter_label = ttk.Label(drop_frame, text="0 arquivo(s)", foreground="blue")
        self.counter_label.pack(anchor=tk.W, pady=2)

        # --- Formato e Papel ---
        config_frame = ttk.LabelFrame(main_frame, text="Configuração de impressão", padding=5)
        config_frame.pack(fill=tk.X, pady=5)

        ttk.Label(config_frame, text="Formato:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.format_cb = ttk.Combobox(config_frame, state="readonly", width=25)
        self.format_cb.grid(row=0, column=1, padx=5, pady=5)
        self.format_cb.bind("<<ComboboxSelected>>", self.on_format_change)

        ttk.Label(config_frame, text="Papel/Gramatura:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.paper_cb = ttk.Combobox(config_frame, state="readonly", width=25)
        self.paper_cb.grid(row=0, column=3, padx=5, pady=5)

        # --- Identificação ---
        id_frame = ttk.Frame(main_frame)
        id_frame.pack(fill=tk.X, pady=5)
        ttk.Label(id_frame, text="Identificação (opcional):").pack(side=tk.LEFT)
        self.id_entry = ttk.Entry(id_frame, width=40)
        self.id_entry.pack(side=tk.LEFT, padx=5)
        self._setup_placeholder()

        # --- Botão Enviar, Cancelar e Progresso (sempre visíveis) ---
        self.send_btn = ttk.Button(main_frame, text="Enviar arquivos", command=self.start_send)
        self.send_btn.pack(fill=tk.X, pady=5)

        self.cancel_btn = ttk.Button(main_frame, text="Cancelar", command=self.cancel, state=tk.DISABLED)
        self.cancel_btn.pack(fill=tk.X, pady=2)

        # Barra de progresso
        progress_container = ttk.Frame(main_frame)
        progress_container.pack(fill=tk.X, pady=5)
        self.progress = ttk.Progressbar(progress_container, mode='determinate', length=400)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,10))
        self.percent_label = ttk.Label(progress_container, text="0%", width=5)
        self.percent_label.pack(side=tk.RIGHT)
        self.current_file_label = ttk.Label(main_frame, text="", foreground="blue", font=("Arial", 9))
        self.current_file_label.pack(fill=tk.X, pady=2)

        # --- Log ---
        log_frame = ttk.LabelFrame(main_frame, text="Log de eventos", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=6, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9))
        scroll_log = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll_log.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_log.pack(side=tk.RIGHT, fill=tk.Y)

        # Inicializa
        if MACHINE_CONFIG:
            self.machine_combo.current(0)
            self.on_machine_change()
        self.reset_progress()

    # --------------------------------------------------------
    # Auxiliares
    # --------------------------------------------------------
    def _add_tooltip(self, widget, text):
        def enter(e):
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{widget.winfo_rootx()+10}+{widget.winfo_rooty()+20}")
            label = tk.Label(self.tooltip, text=text, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
            label.pack()
        def leave(e):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _setup_placeholder(self):
        self.placeholder = "ex: cliente_lote"
        self.id_entry.insert(0, self.placeholder)
        self.id_entry.configure(foreground="gray")
        self.id_entry.bind("<FocusIn>", self._on_focus_in)
        self.id_entry.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, event):
        if self.id_entry.get() == self.placeholder:
            self.id_entry.delete(0, tk.END)
            self.id_entry.configure(foreground="black")

    def _on_focus_out(self, event):
        if not self.id_entry.get():
            self.id_entry.insert(0, self.placeholder)
            self.id_entry.configure(foreground="gray")

    def _get_optional(self):
        text = self.id_entry.get().strip()
        if text == self.placeholder or not text:
            return ""
        return text

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def update_counter(self):
        count = len(self.file_paths)
        self.counter_label.config(text=f"{count} arquivo(s)" if count != 1 else "1 arquivo")
        if count == 0:
            self.reset_progress()

    def reset_progress(self):
        self.progress['value'] = 0
        self.progress['maximum'] = 1
        self.percent_label.config(text="0%")
        self.current_file_label.config(text="Nenhum envio em andamento")

    # --------------------------------------------------------
    # Máquina e formato
    # --------------------------------------------------------
    def on_machine_change(self, event=None):
        machine = self.machine_var.get()
        if not machine:
            return
        config = MACHINE_CONFIG[machine]
        self.ip_label.config(text=f"IP: {config['ip']}")
        self.format_cb['values'] = config["formats"]
        self.paper_cb['values'] = config["papers"]
        self.format_cb.set("")
        self.paper_cb.set("")
        if config["formats"]:
            self.format_cb.current(0)
            self.on_format_change()
        if config["papers"]:
            self.paper_cb.current(0)
        self.log(f"Máquina alterada: {machine} ({config['ip']})")

    def on_format_change(self, event=None):
        machine = self.machine_var.get()
        if not machine:
            return
        selected = self.format_cb.get()
        if selected in NO_PAPER_FORMATS:
            self.paper_cb.config(state=tk.DISABLED)
            self.paper_cb.set("(sem papel)")
            self.log(f"Formato especial: {selected} (não requer papel)")
        else:
            self.paper_cb.config(state="readonly")
            if not self.paper_cb.get() or self.paper_cb.get() == "(sem papel)":
                papers = MACHINE_CONFIG[machine]["papers"]
                if papers:
                    self.paper_cb.current(0)

    # --------------------------------------------------------
    # Arquivos
    # --------------------------------------------------------
    def on_drop(self, event):
        files = re.findall(r'\{.*?\}|\S+', event.data)
        added = 0
        for f in files:
            f = f.strip('{}')
            f = os.path.normpath(f)
            if f.lower().endswith(".pdf") and os.path.exists(f) and f not in self.file_paths:
                self.file_paths.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
                added += 1
        if added:
            self.update_counter()
            self.log(f"+{added} arquivo(s) via drag & drop")

    def add_files_manually(self, event=None):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        added = 0
        for f in files:
            f = os.path.normpath(f)
            if f not in self.file_paths:
                self.file_paths.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
                added += 1
        if added:
            self.update_counter()
            self.log(f"+{added} arquivo(s) adicionado(s) manualmente")

    def delete_selected(self):
        selected = self.listbox.curselection()
        for idx in reversed(selected):
            self.listbox.delete(idx)
            del self.file_paths[idx]
        self.update_counter()
        self.log(f"{len(selected)} arquivo(s) removido(s)")

    def clear_all(self):
        self.listbox.delete(0, tk.END)
        self.file_paths.clear()
        self.update_counter()
        self.log("Lista limpa")

    # --------------------------------------------------------
    # Envio (com separador condicional)
    # --------------------------------------------------------
    def start_send(self):
        machine = self.machine_var.get()
        if not machine:
            messagebox.showwarning("Aviso", "Selecione uma máquina.")
            return
        formato = self.format_cb.get()
        if not formato:
            messagebox.showwarning("Aviso", "Selecione um formato.")
            return
        if formato not in NO_PAPER_FORMATS:
            papel = self.paper_cb.get()
            if not papel or papel == "(sem papel)":
                messagebox.showwarning("Aviso", "Selecione o papel/gramatura.")
                return
        else:
            papel = None

        if not self.file_paths:
            messagebox.showwarning("Aviso", "Nenhum arquivo para enviar.")
            return
        if self.sending:
            messagebox.showinfo("Aguarde", "Envio já em andamento.")
            return

        total = len(self.file_paths)
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.percent_label.config(text="0%")
        self.current_file_label.config(text="Preparando envio...")

        self.sending = True
        self.cancel_send = False
        self.send_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

        thread = threading.Thread(target=self._send_thread, args=(machine, formato, papel))
        thread.daemon = True
        thread.start()

    def cancel(self):
        self.cancel_send = True
        self.log("Cancelamento solicitado...")

    def _send_thread(self, machine, formato, papel):
        config = MACHINE_CONFIG[machine]
        ip = config["ip"]
        group = config["group"]          # "PB" ou "CL"
        optional = self._get_optional()
        current_date = datetime.now().strftime("%d-%m-%Y")
        total = len(self.file_paths)
        success = 0

        # Monta o nome da fila conforme o grupo
        if formato in NO_PAPER_FORMATS:
            queue_name = formato   # ex: "CAPADUPLEX" (sem papel)
        else:
            if group == "PB":
                # OCÉ usa espaço
                queue_name = f"{formato} {papel}"
            else:
                # CL (RICOH/BALTORO) usa underscore
                queue_name = f"{formato}_{papel}".replace(" ", "_")  # garante que não haja espaços
        self.log(f"Fila gerada: {queue_name} (grupo {group})")

        for idx, orig_path in enumerate(self.file_paths, 1):
            if self.cancel_send:
                break

            file_basename = os.path.basename(orig_path)
            # Atualiza barra (antes do envio)
            self.root.after(0, lambda v=idx-1: self.progress.configure(value=v))
            percent_antes = int((idx-1) / total * 100)
            self.root.after(0, lambda p=percent_antes: self.percent_label.config(text=f"{p}%"))
            self.root.after(0, lambda i=idx, t=total, nome=file_basename:
                           self.current_file_label.config(text=f"Enviando ({i}/{t}): {nome}"))

            # Nome fictício para o trabalho
            base_name = file_basename[:40]
            fictitious = f"{base_name}-{current_date}-{optional}".strip("-")
            temp_path = os.path.join(self.temp_dir, f"{machine}_{idx}_{os.getpid()}.pdf")
            try:
                shutil.copy2(orig_path, temp_path)
            except Exception as e:
                self.log(f"ERRO cópia: {e}")
                continue

            cmd = f'lpr -S {ip} -P "{queue_name}" -J "{fictitious}" "{temp_path}"'
            self.log(f"Enviando: {fictitious} para {ip} (fila: {queue_name})")
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90)
                if result.returncode == 0:
                    success += 1
                    self.log(f"✓ OK: {fictitious}")
                else:
                    self.log(f"✗ FALHA: {fictitious} - {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                self.log(f"⏱ TIMEOUT: {fictitious}")
            except Exception as e:
                self.log(f"⚠ ERRO: {fictitious} - {e}")
            finally:
                try:
                    os.remove(temp_path)
                except:
                    pass

            # Atualiza barra após envio
            self.root.after(0, lambda v=idx: self.progress.configure(value=v))
            percent_depois = int(idx / total * 100)
            self.root.after(0, lambda p=percent_depois: self.percent_label.config(text=f"{p}%"))

        # Finalização
        self.root.after(0, lambda: self.current_file_label.config(text="Envio finalizado" if success == total else "Envio com falhas"))
        self.root.after(0, self.cancel_btn.config, {'state': tk.DISABLED})
        self.root.after(0, self.send_btn.config, {'state': tk.NORMAL})
        self.sending = False

        if not self.cancel_send:
            if success == total:
                self.log(f"✅ Todos os {total} arquivos enviados com sucesso!")
                self.root.after(0, lambda: messagebox.showinfo("Sucesso", f"{total} arquivo(s) enviado(s)"))
                self.root.after(0, self.clear_all)
                self.root.after(0, self.reset_progress)
            else:
                self.log(f"⚠ Enviados {success} de {total} (com falhas).")
                self.root.after(0, lambda: messagebox.showerror("Erro parcial", f"{success}/{total} enviados. Veja o log."))
        else:
            self.log("Envio cancelado pelo usuário.")
            self.root.after(0, self.reset_progress)

    # --------------------------------------------------------
    # Limpeza ao fechar
    # --------------------------------------------------------
    def _cleanup_on_exit(self):
        def on_closing():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except:
                pass
            self.root.destroy()
        self.root.protocol("WM_DELETE_WINDOW", on_closing)

# ------------------------------------------------------------
# EXECUÇÃO
# ------------------------------------------------------------
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = HotfolderApp(root)
    root.mainloop()