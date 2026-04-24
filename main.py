import tkinter as tk
from tkinter import ttk
import os
import pandas as pd

import analizador_baker
import analizador_plano
import diff_plano
import diff_token

class InterfazDual:
    def __init__(self, root):
        self.root = root
        self.root.title("Comparador de Código 1-a-1 | Analizador de Plagio")
        self.root.geometry("1400x850")

        self.colores = [
            "#ffb3ba", "#ffdfba", "#ffffba", "#baffc9", "#bae1ff", 
            "#e6b3ff", "#ffb3e6", "#c2c2f0", "#e0e0e0", "#ffc2c2"
        ]

        self.archivo_a = tk.StringVar()
        self.archivo_b = tk.StringVar()
        self.metodo = tk.StringVar(value="Ninguno")
        self.titulo_resultados = tk.StringVar(value="Coincidencias Detectadas")

        self._construir_layout()
        self._actualizar_dropdowns()

    def _construir_layout(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=3)
        self.main_frame.columnconfigure(2, weight=2)

        col1 = ttk.Frame(self.main_frame)
        col1.grid(row=0, column=0, sticky="nsew", padx=5)
        ttk.Label(col1, text="Seleccionar Código A:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.combo_a = ttk.Combobox(col1, textvariable=self.archivo_a, state="readonly")
        self.combo_a.pack(fill=tk.X, pady=5)
        self.combo_a.bind("<<ComboboxSelected>>", self.cargar_y_comparar)
        self.txt_a = tk.Text(col1, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4", wrap=tk.NONE)
        self.txt_a.pack(fill=tk.BOTH, expand=True)

        col2 = ttk.Frame(self.main_frame)
        col2.grid(row=0, column=1, sticky="nsew", padx=5)
        frame_metodo = ttk.Frame(col2)
        frame_metodo.pack(fill=tk.X)
        ttk.Label(frame_metodo, text="Método:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.combo_metodo = ttk.Combobox(frame_metodo, textvariable=self.metodo, state="readonly", values=["Ninguno", "Baker", "Suffix Plano", "Diff Plano", "Diff Tokens"])
        self.combo_metodo.pack(side=tk.RIGHT, pady=5, fill=tk.X, expand=True, padx=(5,0))
        self.combo_metodo.bind("<<ComboboxSelected>>", self.cargar_y_comparar)
        
        ttk.Label(col2, text="Seleccionar Código B:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5,0))
        self.combo_b = ttk.Combobox(col2, textvariable=self.archivo_b, state="readonly")
        self.combo_b.pack(fill=tk.X, pady=5)
        self.combo_b.bind("<<ComboboxSelected>>", self.cargar_y_comparar)
        self.txt_b = tk.Text(col2, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4", wrap=tk.NONE)
        self.txt_b.pack(fill=tk.BOTH, expand=True)

        col3 = ttk.Frame(self.main_frame)
        col3.grid(row=0, column=2, sticky="nsew", padx=5)

        self.lbl_titulo = tk.Label(col3, textvariable=self.titulo_resultados, font=("Arial", 11, "bold"), fg="#2c3e50")
        self.lbl_titulo.pack(pady=5)
        
        self.txt_resumen = tk.Text(col3, font=("Arial", 10), bg="#f5f5f5", wrap=tk.WORD)
        self.txt_resumen.pack(fill=tk.BOTH, expand=True)
        self.txt_resumen.tag_config("texto_normal", foreground="#333333")

    def _actualizar_dropdowns(self):
        if os.path.exists("./files"):
            archivos = sorted([f for f in os.listdir("./files") if f.endswith(".py")])
            self.combo_a['values'] = archivos
            self.combo_b['values'] = archivos

    def cargar_y_comparar(self, event=None):
        file_a = self.archivo_a.get()
        file_b = self.archivo_b.get()
        metodo = self.metodo.get()

        self.titulo_resultados.set("Coincidencias Detectadas")

        if not file_a or not file_b: return

        for txt in [self.txt_a, self.txt_b, self.txt_resumen]:
            txt.config(state=tk.NORMAL)
            txt.delete(1.0, tk.END)
            for tag in txt.tag_names(): 
                if tag != "texto_normal": txt.tag_delete(tag)

        try:
            with open(f"./files/{file_a}", 'r', encoding='utf-8') as f: self.txt_a.insert(tk.END, f.read())
            with open(f"./files/{file_b}", 'r', encoding='utf-8') as f: self.txt_b.insert(tk.END, f.read())
        except Exception as e:
            self.txt_resumen.insert(tk.END, f"Error cargando archivos: {e}")

        if metodo != "Ninguno":
            self.ejecutar_comparacion(file_a, file_b, metodo)

        for txt in [self.txt_a, self.txt_b, self.txt_resumen]: 
            txt.config(state=tk.DISABLED)

    def ejecutar_comparacion(self, fa, fb, m):
        ruta1, ruta2 = f"./files/{fa}", f"./files/{fb}"
        clones = []
        unidad = ""

        try:

            if m == "Baker":
                clones = analizador_baker.comparar_dos_baker(ruta1, ruta2)
                unidad = "Tokens"
            elif m == "Suffix Plano":
                clones = analizador_plano.comparar_dos_plano(ruta1, ruta2)
                unidad = "Chars"
            elif m == "Diff Plano":
                clones = diff_plano.detectar_plagio_plano(ruta1, ruta2)
                unidad = "Chars"
            elif m == "Diff Tokens":
                clones = diff_token.detectar_plagio_tokenizado(ruta1, ruta2)
                unidad = "Tokens"

            with open(ruta1, 'r', encoding='utf-8') as f:
                total_lineas_a = sum(1 for _ in f)
            if total_lineas_a == 0: total_lineas_a = 1

            lineas_afectadas = set()
            for c in clones:
                try:
                    l_ini, l_fin = map(int, c["lineas_a"].split("-"))
                    for linea in range(l_ini, l_fin + 1):
                        lineas_afectadas.add(linea)
                except Exception:
                    pass
            
            similitud = (len(lineas_afectadas) / total_lineas_a) * 100
            
            self.titulo_resultados.set(f"Coincidencias (Similitud: {similitud:.1f}%)")

            if not clones:
                self.txt_resumen.insert(tk.END, "No se encontraron similitudes.", "texto_normal")
                return

            for i, c in enumerate(clones[:150]):
                color = self.colores[i % len(self.colores)]
                tag_name = f"match_{i}"
                
                for txt, lines_str in [(self.txt_a, c["lineas_a"]), (self.txt_b, c["lineas_b"])]:
                    l_ini, l_fin = lines_str.split("-")
                    txt.tag_add(tag_name, f"{l_ini}.0", f"{l_fin}.end")
                    txt.tag_config(tag_name, background=color, foreground="black")

                tag_cuadro = f"cuadro_{i}"
                self.txt_resumen.insert(tk.END, "■ ", (tag_cuadro,))
                self.txt_resumen.tag_config(tag_cuadro, foreground=color, font=("Arial", 14, "bold"))
                info = f"{c['tamano']} {unidad} | L:{c['lineas_a']} | L:{c['lineas_b']}\n\n"
                self.txt_resumen.insert(tk.END, info, "texto_normal")

        except Exception as e:
            self.txt_resumen.insert(tk.END, f"Error en algoritmo: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = InterfazDual(root)
    root.mainloop()
