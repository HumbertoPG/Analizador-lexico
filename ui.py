import tkinter as tk
from tkinter import ttk
import os
import pandas as pd

# Importamos las funciones que empaquetaste en tus otros archivos
# (Asegúrate de que los nombres de los archivos y funciones coincidan con los tuyos)
from analizador_baker import obtener_reporte_baker
from analizador_plano import obtener_reporte_plano

class PlagioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Plagio - Reto")
        self.root.geometry("1200x700")

        # Paleta de colores suaves para los diferentes bloques de plagio
        self.colores = [
            "#ffb3ba", "#ffdfba", "#ffffba", "#baffc9", "#bae1ff", 
            "#e6b3ff", "#ffb3e6", "#c2c2f0", "#e0e0e0", "#ffc2c2"
        ]

        self.df_baker = pd.DataFrame()
        self.df_plano = pd.DataFrame()
        self.archivo_actual = None

        self._construir_ui()
        self._cargar_archivos_src()

    def _construir_ui(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.frame_izq = ttk.Frame(self.paned, width=200)
        self.paned.add(self.frame_izq, weight=1)

        tk.Label(self.frame_izq, text="Archivos en ./src", font=("Arial", 11, "bold")).pack(pady=5)
        self.lista_archivos = tk.Listbox(self.frame_izq, font=("Consolas", 10))
        self.lista_archivos.pack(fill=tk.BOTH, expand=True)
        self.lista_archivos.bind('<<ListboxSelect>>', self.al_seleccionar_archivo)

        self.frame_centro = ttk.Frame(self.paned)
        self.paned.add(self.frame_centro, weight=4)

        frame_top = ttk.Frame(self.frame_centro)
        frame_top.pack(fill=tk.X, pady=5)
        tk.Label(frame_top, text="Método de Análisis:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)

        self.combo_metodo = ttk.Combobox(
            frame_top, 
            values=["Ninguno", "Baker", "Suffix Array Plano"], 
            state="readonly", 
            width=25
        )
        self.combo_metodo.current(0)
        self.combo_metodo.pack(side=tk.LEFT, padx=10)
        self.combo_metodo.bind('<<ComboboxSelected>>', self.al_cambiar_metodo)

        self.btn_escanear = ttk.Button(frame_top, text="▶ Ejecutar Análisis Global", command=self.ejecutar_analisis)
        self.btn_escanear.pack(side=tk.RIGHT)

        self.txt_codigo = tk.Text(self.frame_centro, wrap=tk.NONE, font=("Consolas", 11), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.txt_codigo.pack(fill=tk.BOTH, expand=True)

        self.frame_der = ttk.Frame(self.paned, width=250)
        self.paned.add(self.frame_der, weight=1)

        tk.Label(self.frame_der, text="Coincidencias Detectadas", font=("Arial", 11, "bold")).pack(pady=5)
        self.txt_resumen = tk.Text(self.frame_der, font=("Arial", 10), wrap=tk.WORD, bg="#f5f5f5")
        self.txt_resumen.pack(fill=tk.BOTH, expand=True)

    def _cargar_archivos_src(self):
        self.lista_archivos.delete(0, tk.END)
        if os.path.exists("./src"):
            archivos = sorted([f for f in os.listdir("./src") if f.endswith(".py")])
            for arch in archivos:
                self.lista_archivos.insert(tk.END, arch)

    def ejecutar_analisis(self):
        """Llama a los módulos externos para generar los dataframes una sola vez."""
        self.btn_escanear.config(text="Analizando...", state=tk.DISABLED)
        self.root.update()
        
        try:
            self.df_baker = obtener_reporte_baker("./src")
            self.df_plano = obtener_reporte_plano("./src")
            self.btn_escanear.config(text="✓ Análisis Completado")
        except Exception as e:
            self.btn_escanear.config(text="Error en Análisis")
            print(f"Error generando dataframes: {e}")
        finally:
            self.btn_escanear.config(state=tk.NORMAL)

    def al_seleccionar_archivo(self, event):
        seleccion = self.lista_archivos.curselection()
        if not seleccion: return
        self.archivo_actual = self.lista_archivos.get(seleccion[0])
        self.actualizar_vista()

    def al_cambiar_metodo(self, event):
        self.actualizar_vista()

    def actualizar_vista(self):
        if not self.archivo_actual: return

        self.txt_codigo.config(state=tk.NORMAL)
        self.txt_codigo.delete(1.0, tk.END)
        for tag in self.txt_codigo.tag_names():
            self.txt_codigo.tag_delete(tag)

        ruta = os.path.join("./src", self.archivo_actual)
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                self.txt_codigo.insert(tk.END, f.read())
        except Exception as e:
            print(f"Error al cargar código: {e}")

        self.txt_codigo.config(state=tk.DISABLED)

        self.txt_resumen.config(state=tk.NORMAL)
        self.txt_resumen.delete(1.0, tk.END)

        self.txt_resumen.tag_config("texto_normal", foreground="#333333", font=("Arial", 10))

        metodo = self.combo_metodo.get()
        df_activo = pd.DataFrame()
        
        if metodo == "Baker": df_activo = self.df_baker
        elif metodo == "Suffix Array Plano": df_activo = self.df_plano

        if df_activo.empty or metodo == "Ninguno":
            self.txt_resumen.insert(tk.END, "Sin coincidencias o análisis no ejecutado.", ("texto_normal",))
            self.txt_resumen.config(state=tk.DISABLED)
            return

        mascara = (df_activo["Archivo A"] == self.archivo_actual) | (df_activo["Archivo B"] == self.archivo_actual)
        df_filtro = df_activo[mascara].copy()

        if df_filtro.empty:
            self.txt_resumen.insert(tk.END, "El archivo está limpio.", ("texto_normal",))
            self.txt_resumen.config(state=tk.DISABLED)
            return

        col_tamano = "Tokens Coincidentes" if "Tokens Coincidentes" in df_filtro.columns else "Caracteres Coincidentes"
        
        if col_tamano in df_filtro.columns:
            df_filtro = df_filtro.sort_values(by=col_tamano, ascending=False)

        LIMITE_UI = 150
        total_reales = len(df_filtro)
        df_filtro = df_filtro.head(LIMITE_UI)

        if total_reales > LIMITE_UI:
            self.txt_resumen.insert(tk.END, f"⚠️ ¡Exceso de coincidencias ({total_reales})!\n", ("alerta",))
            self.txt_resumen.insert(tk.END, f"Mostrando solo el Top {LIMITE_UI} más grande.\n", ("texto_normal",))
            self.txt_resumen.insert(tk.END, "="*30 + "\n\n", ("texto_normal",))
            self.txt_resumen.tag_config("alerta", foreground="red", font=("Arial", 10, "bold"))

        color_idx = 0
        for index, row in df_filtro.iterrows():
            es_a = row["Archivo A"] == self.archivo_actual
            
            lineas_str = row["Líneas A"] if es_a else row["Líneas B"]
            lineas_vinculo = row["Líneas B"] if es_a else row["Líneas A"]
            
            archivo_vinculado = row["Archivo B"] if es_a else row["Archivo A"]
            tamano_coincidencia = row[col_tamano] if col_tamano in df_filtro.columns else "?"

            try:
                l_inicio, l_fin = lineas_str.split("-")
                idx_inicio = f"{l_inicio}.0"
                idx_fin = f"{l_fin}.end"
                
                nombre_tag = f"plagio_{index}"
                color_actual = self.colores[color_idx % len(self.colores)]

                # Pintar el código principal
                self.txt_codigo.tag_add(nombre_tag, idx_inicio, idx_fin)
                self.txt_codigo.tag_config(nombre_tag, background=color_actual, foreground="black")

                tag_cuadro = f"cuadro_{index}"
                self.txt_resumen.insert(tk.END, "■ ", (tag_cuadro,))
                self.txt_resumen.tag_config(tag_cuadro, foreground=color_actual, font=("Arial", 14))

                texto_info = f"{tamano_coincidencia} {col_tamano.split()[0]} | Líneas {lineas_str} | Líneas {lineas_vinculo}\n"
                self.txt_resumen.insert(tk.END, texto_info, ("texto_normal", "bold_info"))
                self.txt_resumen.tag_config("bold_info", font=("Arial", 10, "bold"))

                self.txt_resumen.insert(tk.END, f"  Plagio con: {archivo_vinculado}\n\n", ("texto_normal",))

            except Exception as e:
                print(f"Error parseando líneas: {e}")
            
            color_idx += 1

        self.txt_resumen.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = PlagioApp(root)
    root.mainloop()
