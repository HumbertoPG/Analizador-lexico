import os
from difflib import SequenceMatcher
from pathlib import Path


def _resolver_demo_dir():
    base_dir = Path(__file__).resolve().parent
    for folder_name in ("files", "src"):
        candidate = base_dir / folder_name
        if candidate.is_dir():
            return candidate
    return base_dir / "files"

def detectar_plagio_plano(ruta_a, ruta_b, umbral_caracteres=80):
    """
    Compara dos archivos en texto plano usando difflib.
    """
    try:
        with open(ruta_a, 'r', encoding='utf-8') as f:
            texto_a = f.read()
        with open(ruta_b, 'r', encoding='utf-8') as f:
            texto_b = f.read()
    except Exception as e:
        return f"Error leyendo archivos: {e}"

    matcher = SequenceMatcher(None, texto_a, texto_b)
    bloques_coincidentes = matcher.get_matching_blocks()

    resultados = []
    
    for bloque in bloques_coincidentes:
        if bloque.size >= umbral_caracteres:
            fragmento = texto_a[bloque.a : bloque.a + bloque.size]
            
            linea_inicio_a = texto_a.count('\n', 0, bloque.a) + 1
            linea_fin_a = texto_a.count('\n', 0, bloque.a + bloque.size) + 1
            
            linea_inicio_b = texto_b.count('\n', 0, bloque.b) + 1
            linea_fin_b = texto_b.count('\n', 0, bloque.b + bloque.size) + 1
            
            resultados.append({
                "tamano": bloque.size,
                "lineas_a": f"{linea_inicio_a}-{linea_fin_a}",
                "lineas_b": f"{linea_inicio_b}-{linea_fin_b}"
            })

    return resultados

if __name__ == "__main__":
    data_dir = _resolver_demo_dir()
    archivo1 = data_dir / "codigo_A.py"
    archivo2 = data_dir / "codigo_B.py"
    
    if os.path.exists(archivo1) and os.path.exists(archivo2):
        clones = detectar_plagio_plano(archivo1, archivo2, umbral_caracteres=80)
        
        print("\n=== PLAGIO EN TEXTO PLANO (DIFFLIB) ===")
        for i, clon in enumerate(clones, 1):
            print(f"\n[Coincidencia #{i}] - {clon['tamano']} caracteres")
            print(f"  -> Archivo A (Líneas {clon['lineas_a']})")
            print(f"  -> Archivo B (Líneas {clon['lineas_b']})")