import os
import tokenize
import io
import token
import keyword
from difflib import SequenceMatcher
from pathlib import Path


def _resolver_demo_dir():
    base_dir = Path(__file__).resolve().parent
    for folder_name in ("files", "src"):
        candidate = base_dir / folder_name
        if candidate.is_dir():
            return candidate
    return base_dir / "files"

def obtener_tokens_limpios(source_code):
    bytes_code = source_code.encode('utf-8')
    buffer = io.BytesIO(bytes_code)
    tokens_to_ignore = {
        tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, 
        tokenize.ENCODING, tokenize.ENDMARKER, tokenize.INDENT, tokenize.DEDENT
    }
    tokens = []

    for tok in tokenize.tokenize(buffer.readline):
        if tok.type not in tokens_to_ignore:
            tokens.append({
                'tipo': token.tok_name[tok.type],
                'valor': tok.string,
                'linea': tok.start[0]
            })
    return tokens

def generar_cadena_generica(tokens_limpios):
    cadena_transformada = []
    lista_parametros = []
    lista_lineas = [] 

    for tok in tokens_limpios:
        tipo = tok['tipo']
        valor = tok['valor']
        es_keyword = keyword.iskeyword(valor)

        if (tipo == 'NAME' and not es_keyword) or (tipo == 'NUMBER') or (tipo == 'STRING'):
            cadena_transformada.append('P')
            lista_parametros.append(valor)
        else:
            cadena_transformada.append(valor)
            
        lista_lineas.append(tok['linea']) 

    return cadena_transformada, lista_parametros, lista_lineas

def detectar_plagio_tokenizado(ruta_a, ruta_b, umbral_tokens=15):
    try:
        with open(ruta_a, 'r', encoding='utf-8') as f:
            tokens_a_brutos = obtener_tokens_limpios(f.read())
        with open(ruta_b, 'r', encoding='utf-8') as f:
            tokens_b_brutos = obtener_tokens_limpios(f.read())
    except Exception as e:
        return f"Error leyendo archivos: {e}"
    
    estructura_a, params_a, lineas_a = generar_cadena_generica(tokens_a_brutos)
    estructura_b, params_b, lineas_b = generar_cadena_generica(tokens_b_brutos)

    matcher = SequenceMatcher(None, estructura_a, estructura_b)
    bloques_coincidentes = matcher.get_matching_blocks()

    resultados = []
    
    for bloque in bloques_coincidentes:
        if bloque.size >= umbral_tokens:
            
            linea_inicio_a = lineas_a[bloque.a]
            linea_fin_a = lineas_a[bloque.a + bloque.size - 1]
            
            linea_inicio_b = lineas_b[bloque.b]
            linea_fin_b = lineas_b[bloque.b + bloque.size - 1]

            resultados.append({
                "tamano": bloque.size,
                "lineas_a": f"{linea_inicio_a}-{linea_fin_a}",
                "lineas_b": f"{linea_inicio_b}-{linea_fin_b}"
            })

    return resultados

if __name__ == "__main__":
    data_dir = _resolver_demo_dir()
    archivo1 = data_dir / "LOW_4_1386802.py"
    archivo2 = data_dir / "LOW_6_1434903.py"
    
    if os.path.exists(archivo1) and os.path.exists(archivo2):
        clones = detectar_plagio_tokenizado(archivo1, archivo2, umbral_tokens=15)
        
        print("\n=== PLAGIO ESTRUCTURAL (DIFFLIB + TOKENS) ===")
        for i, clon in enumerate(clones, 1):
            print(f"\n[Coincidencia #{i}] - {clon['tamano']} tokens")
            print(f"  -> Archivo A (Líneas {clon['lineas_a']})")
            print(f"  -> Archivo B (Líneas {clon['lineas_b']})")