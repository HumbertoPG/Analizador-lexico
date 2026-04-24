import os
import pandas as pd
from pathlib import Path


def _default_input_dir():
    base_dir = Path(__file__).resolve().parent
    for folder_name in ("files", "src"):
        candidate = base_dir / folder_name
        if candidate.is_dir():
            return str(candidate)
    return str(base_dir / "files")

def analizar_archivo(df, nombre_archivo):

    if df.empty:
        print("El DataFrame está vacío.")
        return df

    mascara = (df["Archivo A"] == nombre_archivo) | (df["Archivo B"] == nombre_archivo)
    df_filtrado = df[mascara].copy()

    if df_filtrado.empty:
        print(f"\nNo se encontraron coincidencias de plagio para: {nombre_archivo}")
        return df_filtrado

    archivos_a = set(df_filtrado["Archivo A"])
    archivos_b = set(df_filtrado["Archivo B"])
    otros_archivos = (archivos_a.union(archivos_b)) - {nombre_archivo}

    print(f"\n========== ANÁLISIS DE: {nombre_archivo} ==========")
    print(f"Total de bloques plagiados encontrados: {len(df_filtrado)}")
    print(f"Comparte código con ({len(otros_archivos)} archivos): {', '.join(otros_archivos)}")
    print("=====================================================\n")

    return df_filtrado

def sais(T):
    return sorted(range(len(T)), key=lambda i: T[i:])

def construir_lcp(T, SA):
    n = len(T)
    rank = [0] * n
    for i in range(n):
        rank[SA[i]] = i

    lcp = [0] * n
    h = 0
    for i in range(n):
        if rank[i] > 0:
            j = SA[rank[i] - 1]
            while i + h < n and j + h < n and T[i + h] == T[j + h]:
                h += 1
            lcp[rank[i]] = h
            if h > 0:
                h -= 1
    return lcp

def procesar_directorio_plano(ruta_carpeta):
    dataset_procesado = []
    if not os.path.isdir(ruta_carpeta): return dataset_procesado

    for nombre_archivo in os.listdir(ruta_carpeta):
        if nombre_archivo.endswith(".py"):
            ruta_completa = os.path.join(ruta_carpeta, nombre_archivo)
            try:
                with open(ruta_completa, 'r', encoding='utf-8') as f:
                    codigo_fuente = f.read()

                cadena_numerica = []
                lineas = []
                linea_actual = 1

                for char in codigo_fuente:
                    cadena_numerica.append(ord(char))
                    lineas.append(linea_actual)

                    if char == '\n':
                        linea_actual += 1

                dataset_procesado.append({
                    'archivo': nombre_archivo,
                    'cadena_numerica': cadena_numerica,
                    'lineas': lineas
                })
            except Exception as e:
                print(f"Error procesando {nombre_archivo}: {e}")
    return dataset_procesado

def construir_cadena_global_plana(dataset_procesado):
    cadena_global = []
    mapa_archivos = []
    mapa_lineas = []

    separador_actual = 2000000

    for data in dataset_procesado:
        cadena_num = data['cadena_numerica']
        lineas = data['lineas']
        archivo = data['archivo']

        for i, num_char in enumerate(cadena_num):
            cadena_global.append(num_char)
            mapa_archivos.append(archivo)
            mapa_lineas.append(lineas[i])

        cadena_global.append(separador_actual)
        separador_actual += 1
        mapa_archivos.append(archivo)
        mapa_lineas.append(-1)

    cadena_global.append(0)
    mapa_archivos.append("FINAL")
    mapa_lineas.append(-1)

    return cadena_global, mapa_archivos, mapa_lineas

def extraer_coincidencias_planas(SA, LCP, mapa_archivos, mapa_lineas, umbral_caracteres=50):
    coincidencias = []
    n = len(SA)
    en_bloque = False
    inicio_bloque = 0

    for i in range(1, n):
        if LCP[i] >= umbral_caracteres:
            if not en_bloque:
                en_bloque = True
                inicio_bloque = i - 1
        else:
            if en_bloque:
                pares = _procesar_bloque_plano(inicio_bloque, i, SA, LCP, mapa_archivos, mapa_lineas)
                coincidencias.extend(pares)
                en_bloque = False

    if en_bloque:
        pares = _procesar_bloque_plano(inicio_bloque, n, SA, LCP, mapa_archivos, mapa_lineas)
        coincidencias.extend(pares)

    return coincidencias

def _procesar_bloque_plano(inicio, fin, SA, LCP, mapa_archivos, mapa_lineas):
    longitud_comun = min(LCP[inicio+1:fin])
    plagios_detectados = []

    for i in range(inicio, fin):
        for j in range(i + 1, fin):
            idx_a = SA[i]
            idx_b = SA[j]
            archivo_a = mapa_archivos[idx_a]
            archivo_b = mapa_archivos[idx_b]

            if archivo_a == archivo_b:
                continue

            linea_inicio_a = mapa_lineas[idx_a]
            linea_fin_a = mapa_lineas[min(idx_a + longitud_comun - 1, len(mapa_lineas) - 1)]

            linea_inicio_b = mapa_lineas[idx_b]
            linea_fin_b = mapa_lineas[min(idx_b + longitud_comun - 1, len(mapa_lineas) - 1)]

            if linea_inicio_a != -1 and linea_inicio_b != -1:
                plagios_detectados.append({
                    "coincidencia_tamano": longitud_comun,
                    "archivo_a": archivo_a,
                    "lineas_a": f"{linea_inicio_a}-{linea_fin_a}",
                    "archivo_b": archivo_b,
                    "lineas_b": f"{linea_inicio_b}-{linea_fin_b}"
                })

    return plagios_detectados

def comparar_dos_plano(ruta1, ruta2, umbral=80):
    def procesar_individual(ruta):
        with open(ruta, 'r', encoding='utf-8') as f:
            codigo = f.read()

        cadena_num = []
        lineas = []
        linea_actual = 1
        for char in codigo:
            cadena_num.append(ord(char))
            lineas.append(linea_actual)
            if char == '\n': linea_actual += 1
        return cadena_num, lineas

    cad_a, lin_a = procesar_individual(ruta1)
    cad_b, lin_b = procesar_individual(ruta2)

    dataset = [
        {'archivo': 'A', 'cadena_numerica': cad_a, 'lineas': lin_a},
        {'archivo': 'B', 'cadena_numerica': cad_b, 'lineas': lin_b}
    ]

    global_t, global_arch, global_lineas = construir_cadena_global_plana(dataset)
    SA = sais(global_t)
    LCP = construir_lcp(global_t, SA)

    clones = extraer_coincidencias_planas(SA, LCP, global_arch, global_lineas, umbral)

    return [{"tamano": c["coincidencia_tamano"],
             "lineas_a": c["lineas_a"],
             "lineas_b": c["lineas_b"]} for c in clones]

def obtener_reporte_plano(ruta=None):
    if ruta is None:
        ruta = _default_input_dir()
    resultados = procesar_directorio_plano(ruta)
    if not resultados: return pd.DataFrame()

    cadena_global, mapa_archivos, mapa_lineas = construir_cadena_global_plana(resultados)
    SA = sais(cadena_global)
    LCP = construir_lcp(cadena_global, SA)

    clones = extraer_coincidencias_planas(SA, LCP, mapa_archivos, mapa_lineas, umbral_caracteres=80)

    registros = []
    for clon in clones:
        registros.append({
            "Archivo A": clon["archivo_a"],
            "Líneas A": clon["lineas_a"],
            "Archivo B": clon["archivo_b"],
            "Líneas B": clon["lineas_b"],
            "Tokens Coincidentes": clon["coincidencia_tamano"]
        })
    return pd.DataFrame(registros)
