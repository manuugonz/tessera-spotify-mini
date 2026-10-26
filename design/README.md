# Plantillas para Illustrator

Abre los SVG como documentos vectoriales. Las medidas son píxeles físicos del código TECHO5 fijado en `../docs/upstream-lock.json`, no una promesa de que el firmware actual dibuje la interfaz completa de Spotify Mini.

- `echo-show-8-guides.svg`: pantalla 1280×800; cuadrícula TECHO5 4×3; mosaico 2×2 destacado en x=27, y=85, 604×452 px cuando hay una sola página. Si hay varias páginas, los puntos inferiores reducen la altura del mosaico 2×2 a aproximadamente 444 px.
- `tessera-card-guides.svg`: tarjeta ampliada de referencia en la pantalla cuadrada Guition 480×480; la cabecera la dibuja Tessera, así que conviene diseñar el contenido bajo y=80.

Para explicar la experiencia deseada, crea mesas de trabajo separadas para: mosaico, reproductor ampliado, menú de tres líneas, selector de dispositivos, resultados de búsqueda y teclado. Marca dónde va cada control y qué pasa al tocarlo. Exporta como SVG o PDF; también sirven PNG a 1× de cada mesa. La pantalla del Echo Show 8 usa orientación horizontal.

El plugin C++ se adapta a otras dimensiones de Tessera. Su vista previa actual usa un mosaico 2×2 de 302×110 px en CYD 320×240, 448×248 px en Guition 480×480 y 495×277 px en JC8012P4A1 1280×800. Los diseños no deben depender de una sola medida fija.

En la cuadrícula 4×3 de un Echo Show 8, las proporciones de referencia con una sola página son: 1×2 = 294×452 px (carátula), 2×2 = 604×452 px (carátula), 3×2 = 914×452 px (composición horizontal) y 4×3 = 1224×686 px (composición horizontal). Son objetivos de diseño para una futura interfaz TECHO5; el adaptador actual aún no dibuja el plugin C++.

`previews/` contiene capturas reales del banco de Tessera en tema oscuro: `tile-cover-portrait-dark.png`, `tile-wide-compact-dark.png`, `tile-wide-large-dark.png`, `player-square-dark.png`, `menu-square-dark.png` y `search-keyboard-square-dark.png`. Se generan con datos simulados y sirven para comparar el resultado con el esquema aportado por el usuario.
