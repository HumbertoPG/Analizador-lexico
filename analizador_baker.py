import tokenize
import io
import token
import keyword
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

def validar_parametros_uno_a_uno(idx_a, idx_b, longitud_comun, mapa_params, umbral):
    sub_bloques_validos = []
    
    mapa_a_b = {}
    mapa_b_a = {}
    
    inicio_actual = 0
    
    for i in range(longitud_comun):
        param_a = mapa_params[idx_a + i]
        param_b = mapa_params[idx_b + i]
        
        if param_a is not None and param_b is not None:
            conflicto = False
            
            if param_a in mapa_a_b and mapa_a_b[param_a] != param_b:
                conflicto = True
            if param_b in mapa_b_a and mapa_b_a[param_b] != param_a:
                conflicto = True
                
            if conflicto:
                if i - inicio_actual >= umbral:
                    sub_bloques_validos.append((inicio_actual, i))
                
                mapa_a_b = {param_a: param_b}
                mapa_b_a = {param_b: param_a}
                inicio_actual = i
            else:
                mapa_a_b[param_a] = param_b
                mapa_b_a[param_b] = param_a

    if longitud_comun - inicio_actual >= umbral:
        sub_bloques_validos.append((inicio_actual, longitud_comun))
        
    return sub_bloques_validos

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
    
def extraer_coincidencias(SA, LCP, mapa_archivos, mapa_lineas, mapa_params, umbral_tokens=15):
    coincidencias_fase2 = []
    n = len(SA)
    en_bloque = False
    inicio_bloque = 0
    
    for i in range(1, n):
        if LCP[i] >= umbral_tokens:
            if not en_bloque:
                en_bloque = True
                inicio_bloque = i - 1 
        else:
            if en_bloque:
                pares = _procesar_bloque(inicio_bloque, i, SA, LCP, mapa_archivos, mapa_lineas, mapa_params, umbral_tokens)
                coincidencias_fase2.extend(pares)
                en_bloque = False
                
    if en_bloque:
        pares = _procesar_bloque(inicio_bloque, n, SA, LCP, mapa_archivos, mapa_lineas, mapa_params, umbral_tokens)
        coincidencias_fase2.extend(pares)
        
    return coincidencias_fase2

def _procesar_bloque(inicio, fin, SA, LCP, mapa_archivos, mapa_lineas, mapa_params, umbral):
    longitud_comun_fase1 = min(LCP[inicio+1:fin]) 
    plagios_confirmados = []
    
    for i in range(inicio, fin):
        for j in range(i + 1, fin):
            idx_a = SA[i]
            idx_b = SA[j]
            archivo_a = mapa_archivos[idx_a]
            archivo_b = mapa_archivos[idx_b]
            
            if archivo_a == archivo_b:
                continue
                
            sub_bloques = validar_parametros_uno_a_uno(idx_a, idx_b, longitud_comun_fase1, mapa_params, umbral)
            
            for despl_inicio, despl_fin in sub_bloques:
                longitud_real = despl_fin - despl_inicio
                
                idx_real_a = idx_a + despl_inicio
                idx_real_b = idx_b + despl_inicio
                
                linea_inicio_a = mapa_lineas[idx_real_a]
                linea_fin_a = mapa_lineas[min(idx_real_a + longitud_real - 1, len(mapa_lineas) - 1)]
                
                linea_inicio_b = mapa_lineas[idx_real_b]
                linea_fin_b = mapa_lineas[min(idx_real_b + longitud_real - 1, len(mapa_lineas) - 1)]
                
                if linea_inicio_a != -1 and linea_inicio_b != -1:
                    plagios_confirmados.append({
                        "tokens_validos": longitud_real,
                        "archivo_a": archivo_a,
                        "lineas_a": f"{linea_inicio_a}-{linea_fin_a}",
                        "archivo_b": archivo_b,
                        "lineas_b": f"{linea_inicio_b}-{linea_fin_b}"
                    })
                    
    return plagios_confirmados

def obtener_tokens_limpios(codigo_fuente):
    codigo_bytes = codigo_fuente.encode('utf-8')
    buffer = io.BytesIO(codigo_bytes)
    tokens_a_ignorar = {
        tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, 
        tokenize.ENCODING, tokenize.ENDMARKER, tokenize.INDENT, tokenize.DEDENT
    }
    tokens_filtrados = []

    for tok in tokenize.tokenize(buffer.readline):
        if tok.type not in tokens_a_ignorar:
            tokens_filtrados.append({
                'tipo': token.tok_name[tok.type],
                'valor': tok.string,
                'linea': tok.start[0]
            })
    return tokens_filtrados

def generar_cadena_generica(tokens_limpios):
    cadena_transformada = []
    lista_parametros = []
    lista_lineas = [] 

    for tok in tokens_limpios:
        tipo = tok['tipo']
        valor = tok['valor']
        linea = tok['linea']
        es_keyword = keyword.iskeyword(valor)

        if (tipo == 'NAME' and not es_keyword) or (tipo == 'NUMBER') or (tipo == 'STRING'):
            cadena_transformada.append('P')
            lista_parametros.append(valor)
        else:
            cadena_transformada.append(valor)
            
        lista_lineas.append(linea) 

    return cadena_transformada, lista_parametros, lista_lineas

def procesar_directorio(ruta_carpeta):
    dataset_procesado = []
    if not os.path.isdir(ruta_carpeta): return dataset_procesado

    for nombre_archivo in os.listdir(ruta_carpeta):
        if nombre_archivo.endswith(".py"):
            ruta_completa = os.path.join(ruta_carpeta, nombre_archivo)
            try:
                with open(ruta_completa, 'r', encoding='utf-8') as f:
                    codigo_fuente = f.read()

                tokens_limpios = obtener_tokens_limpios(codigo_fuente)
                cadena_gen, params_orig, lineas = generar_cadena_generica(tokens_limpios)

                dataset_procesado.append({
                    'archivo': nombre_archivo,
                    'cadena_generica': cadena_gen,
                    'parametros_originales': params_orig,
                    'lineas': lineas,
                    'tokens_totales': len(tokens_limpios)
                })
            except Exception as e:
                print(f"Error procesando {nombre_archivo}: {e}")
    return dataset_procesado

def construir_cadena_global(dataset_procesado):
    cadena_global = []
    mapa_archivos = []
    mapa_parametros = []
    mapa_lineas = [] 

    vocabulario = {'P': 1}
    siguiente_id = 2
    
    separador_actual = 100000 

    for data in dataset_procesado:
        cadena_gen = data['cadena_generica']
        params = data['parametros_originales']
        lineas = data['lineas']
        archivo = data['archivo']

        param_idx = 0
        for i, token_str in enumerate(cadena_gen):
            
            if token_str not in vocabulario:
                vocabulario[token_str] = siguiente_id
                siguiente_id += 1
                
            cadena_global.append(vocabulario[token_str])
            mapa_archivos.append(archivo)
            mapa_lineas.append(lineas[i])

            if token_str == 'P':
                mapa_parametros.append(params[param_idx])
                param_idx += 1
            else:
                mapa_parametros.append(None)

        cadena_global.append(separador_actual)
        separador_actual += 1
        mapa_archivos.append(archivo)
        mapa_parametros.append(None)
        mapa_lineas.append(-1) 

    cadena_global.append(0)
    mapa_archivos.append("FINAL")
    mapa_parametros.append(None)
    mapa_lineas.append(-1)

    return cadena_global, mapa_archivos, mapa_parametros, mapa_lineas

def comparar_dos_baker(ruta1, ruta2, umbral=15):
    def procesar_individual(ruta):
        with open(ruta, 'r', encoding='utf-8') as f:
            tokens = obtener_tokens_limpios(f.read())
        return generar_cadena_generica(tokens)

    cad_a, params_a, lineas_a = procesar_individual(ruta1)
    cad_b, params_b, lineas_b = procesar_individual(ruta2)

    dataset = [
        {'archivo': 'A', 'cadena_generica': cad_a, 'parametros_originales': params_a, 'lineas': lineas_a},
        {'archivo': 'B', 'cadena_generica': cad_b, 'parametros_originales': params_b, 'lineas': lineas_b}
    ]
    
    global_t, global_arch, global_params, global_lineas = construir_cadena_global(dataset)
    SA = sais(global_t)
    LCP = construir_lcp(global_t, SA)
    
    clones = extraer_coincidencias(SA, LCP, global_arch, global_lineas, global_params, umbral)
    
    resultados = []
    for c in clones:
        if c["archivo_a"] == 'A':
            l_a = c["lineas_a"]
            l_b = c["lineas_b"]
        else:
            l_a = c["lineas_b"]
            l_b = c["lineas_a"]
            
        resultados.append({
            "tamano": c["tokens_validos"], 
            "lineas_a": l_a, 
            "lineas_b": l_b
        })
        
    return resultados

def obtener_reporte_baker(ruta=None):
    if ruta is None:
        ruta = _default_input_dir()
    resultados = procesar_directorio(ruta)
    if not resultados: return pd.DataFrame()
    
    cadena_global, mapa_archivos, mapa_params, mapa_lineas = construir_cadena_global(resultados)
    SA = sais(cadena_global)
    LCP = construir_lcp(cadena_global, SA)
    
    clones = extraer_coincidencias(SA, LCP, mapa_archivos, mapa_lineas, mapa_params, umbral_tokens=15)
    
    registros = []
    impresos = set()
    for clon in clones:
        registros.append({
            "Archivo A": clon["archivo_a"],
            "Líneas A": clon["lineas_a"],
            "Archivo B": clon["archivo_b"],
            "Líneas B": clon["lineas_b"],
            "Tokens Coincidentes": clon["tokens_validos"]
        })
    return pd.DataFrame(registros)