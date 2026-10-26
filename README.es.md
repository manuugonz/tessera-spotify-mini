# Spotify Mini

Spotify Mini es un controlador táctil para Tessera. Muestra canción, artista, carátula, progreso y controles de reproducción. El reproductor tiene el selector de dispositivos arriba a la izquierda y un menú de tres líneas arriba a la derecha. Ese menú reúne búsqueda, canciones recientes, playlists recomendadas y acceso a la biblioteca; la flecha vuelve al reproductor. El audio se reproduce en un dispositivo Spotify Connect; la pantalla no recibe el flujo de música.

La cuenta, el Client ID, el Client secret y los tokens OAuth permanecen en Home Assistant. El plugin usa la API 0.13 de Tessera; las revisiones comprobadas están en `docs/upstream-lock.json`.

**TECHO5 / Echo Show 8:** el firmware actual de TECHO5 no anuncia soporte para plugins Tessera. `adaptations/techo5/spotify-mini.patch` prepara un adaptador local para su interfaz de reproducción existente. Es una prueba de código sin instalar en un Echo Show. No ofrece la carátula, biblioteca ni búsqueda táctil del plugin C++ en TECHO5. Consulta [el estado de TECHO5](docs/TECHO5.md).

## Configuración

1. Usa Home Assistant 2026.10 o posterior, una cuenta Spotify Premium y una aplicación en Spotify for Developers. Configura `https://my.home-assistant.io/redirect/oauth` como URI de redirección y marca **Web API**. Si My Home Assistant está desactivado, utiliza `<URL_HOME_ASSISTANT>/auth/external/callback` con la misma URL usada al iniciar sesión. Añade tu cuenta a los usuarios permitidos de la aplicación si está en modo desarrollo. Sigue la [guía de Spotify de Home Assistant](https://www.home-assistant.io/integrations/spotify/) para estos pasos.
2. Copia `custom_components/spotify_mini` a `/config/custom_components/spotify_mini` en Home Assistant y reinícialo. **Add with a link** de Tessera no instala esta integración de Home Assistant.
3. Ve a **Ajustes → Dispositivos y servicios → Añadir integración → Spotify Mini**. Introduce Client ID y Client secret **solo en Home Assistant** y completa OAuth. Comprueba que se ha creado y funciona un `media_player` de Spotify Mini. Su ID puede ser distinto de `media_player.spotify_mini`.
4. En una pantalla Tessera con soporte de plugins, abre **Plugins → Add with a link** e introduce `https://github.com/manuugonz/tessera-spotify-mini`. Para probar sin GitHub, copia la carpeta completa a `/config/tessera-plugins/spotify_mini`. Añade el plugin a la pantalla, deja que Tessera compile e instale su firmware, coloca la tarjeta en Layout y selecciona la entidad del paso 3.
5. Inicia Spotify al menos una vez en un dispositivo Spotify Connect. Desde **Dispositivos** puedes elegir la salida. Para oír música en el Echo Show, elige su receptor Spotify Connect si aparece. La API no puede activar un dispositivo que Spotify no haya descubierto. Consulta la [explicación de Home Assistant sobre fuentes](https://www.home-assistant.io/integrations/spotify/#selecting-output-source).

El plugin sigue el tema claro u oscuro de Tessera. La búsqueda admite canciones, artistas, álbumes y playlists y muestra tres resultados por página. El menú consulta canciones recientes y busca playlists relacionadas con un artista escuchado recientemente. Si no hay canciones recientes, el apartado de playlists recomendadas aparece vacío. No utiliza el endpoint obsoleto de playlists destacadas. Home Assistant guarda hasta 20 playlists seleccionadas desde Spotify Mini para su historial interno.

El reproductor se adapta a la forma del mosaico: los formatos casi cuadrados o verticales muestran la carátula como protagonista y se abren al tocarlos; los anchos sitúan la carátula a la izquierda, con canción y controles a la derecha. La tarjeta ampliada da más espacio a la portada y separa la línea de progreso de los botones. No muestra volumen: se usa el control físico del dispositivo. Los controles son monocromos y respetan el tema claro u oscuro de Tessera.

## Compatibilidad y límites

| Función | Tessera con API de plugins | TECHO5 actual | TECHO5 con el parche local |
| --- | --- | --- | --- |
| Tarjeta Spotify Mini | Sí | No | Parcial, mediante el reproductor nativo de TECHO5 |
| Canción y controles | Sí | No en Spotify Mini | Sí |
| Carátula, menú y búsqueda táctil | Sí | No | No |
| Audio en Echo Show | Mediante su Spotify Connect independiente | Spotify Connect independiente | Igual |

Los tests locales no sustituyen una prueba física en el Echo Show 8. No se ha flasheado ni modificado el dispositivo.

Spotify exige Premium al propietario de una aplicación en modo desarrollo y limita las aplicaciones nuevas a cinco usuarios autorizados. Sus refresh tokens caducan a los seis meses, por lo que habrá que volver a iniciar sesión. Consulta las [reglas de modo desarrollo](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) y la [política de tokens](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens). La reproducción también depende de permisos, disponibilidad y de las acciones admitidas por el dispositivo.

## Pruebas

`docs/validation/` contiene los registros. El banco de Tessera renderiza cuatro formatos y ambos temas; la prueba táctil simula dispositivos, menú, teclado, búsqueda y selección. Los tests de Python usan respuestas de Spotify simuladas y un entorno de Home Assistant. No se ha usado una cuenta real ni un Echo Show físico.

Licencia MIT. Spotify, Home Assistant y Tessera son proyectos independientes.
