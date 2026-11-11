# Resumen de algoritmos

## Procesamiento de imagen y color (`app/color.py`)
1. **Segmentación de la prenda (`segmentar`)**: estima el color de fondo con la mediana del borde de la foto en espacio LAB, marca como fondo lo parecido que toca el borde (componentes conectados) y refina con **GrabCut**. Luego limpia con morfología (apertura/cierre), descarta manchas pequeñas y rellena huecos.
2. **Recorte PNG (`procesar_imagen`)**: aplica la máscara como canal alfa suavizado (Gauss) y recorta al rectángulo de la prenda.
3. **Paleta dominante (`extraer_paleta`)**: **K-Means** (k ≤ 3) en LAB sobre una muestra de hasta 6 000 píxeles de la prenda; convierte cada centro a HSV, calcula su porcentaje y le asigna nombre (`nombre_color`, reglas por matiz/saturación/brillo).
4. **Detección de estampado (`detectar_estampado`)**: bordes **Canny** dentro de la prenda erosionada; si la densidad de bordes > 7 % y hay ≥ 2 colores, es estampada.
5. **Armonía entre dos colores (`armonia`)**: clasifica por distancia de matiz en neutros, monocromática, análoga, complementaria, triádica, base neutra suave o contraste fuerte, y da un puntaje 0-100.
6. **Puntaje de combinación (`comparar`)**: promedio ponderado por área de todos los pares de colores (regla 60-30-10); resta 14 puntos si ambas prendas son estampadas. `veredicto` lo traduce a Excelente / Buena / Regular / Mala.
7. **Sugerencia de outfits (`sugerir_outfits`)**: filtra por stock, categoría complementaria y género compatible, ordena por afinidad y toma las 2 mejores por categoría (con ruido aleatorio ±5 si se piden "nuevas").

## Seguridad (`app/seguridad.py`)
- **Cifrado de contraseñas**: PBKDF2-HMAC-SHA256, 200 000 iteraciones y sal aleatoria de 16 bytes por usuario; comparación en tiempo constante.
- **Sesiones**: token aleatorio (`secrets`) con vigencia de 8 h; roles Administrador / Cliente verificados en el servidor.
- **Recuperación**: código de 6 dígitos guardado como hash, vigencia 10 min, máximo 5 intentos; se envía al correo del usuario.
- **Anti fuerza bruta**: bloqueo de 60 s tras 5 intentos fallidos por IP + correo.

## Probador con cámara (`static/assets/js/app.js`)
- **Detección de postura** con MediaPipe (hombros, codos, muñecas, caderas, rodillas, tobillos) y suavizado exponencial entre cuadros.
- **Malla articulada**: la prenda se divide en una cuadrícula 12×12; cada vértice gira según el hueso (hombro→codo→muñeca, cadera→rodilla→tobillo) con mezcla suave (smoothstep), y se dibuja con **transformaciones afines por triángulo**.
