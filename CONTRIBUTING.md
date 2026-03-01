# Guía de Contribución

Gracias por tu interés en contribuir a Ragnarok 🎉

## 📌 Antes de contribuir

- Revisa si ya existe un issue o pull request relacionado
- Mantén coherencia con el estilo de código actual
- Lee el [Código de Conducta](CODE_OF_CONDUCT.md)
- Usa lenguaje claro y técnico cuando corresponda

## 🛠 Proceso de contribución

### 1. Preparación
```bash
# Fork el repositorio desde GitHub
# Clona tu fork localmente
git clone https://github.com/tu-usuario/ragnarok.git
cd ragnarok

# Crea una rama descriptiva
git checkout -b tipo/descripcion-breve
```

### 2. Tipos de ramas
- `feat/nueva-funcionalidad` - Nuevas características
- `fix/correccion-bug` - Corrección de bugs
- `docs/mejora-documentacion` - Mejoras en documentación
- `refactor/mejora-codigo` - Refactorización
- `test/nuevas-pruebas` - Pruebas unitarias

### 3. Realiza tus cambios

```bash
# Haz cambios en tu rama
# Verifica que el código sea funcional
python API/main.py  # o según corresponda

# Agrega tus cambios
git add .

# Crea commits descriptivos
git commit -m "tipo: descripción clara del cambio"
```

### 4. Verifica antes de enviar

- ✅ El código sigue el estilo del proyecto
- ✅ No hay errores de sintaxis
- ✅ Los cambios funcionan localmente
- ✅ Documentación actualizada (si aplica)
- ✅ Sin archivos no versionados (excepto los necesarios)

### 5. Envía Pull Request

```bash
# Push a tu fork
git push origin tu-rama

# Ve a GitHub y abre un Pull Request
# - Describe qué cambios realizas
# - Por qué son necesarios
# - Cualquier detalle relevante
```

## ✍ Convenciones de código

### Python
- Sigue [PEP 8](https://pep8.org/)
- Nombra variables con `snake_case`
- Nombra clases con `PascalCase`
- Usa type hints cuando sea posible

### Ejemplo
```python
def validar_contraseña(contraseña: str) -> bool:
    """Valida formato de contraseña."""
    return len(contraseña) >= 8
```

### Markdown
- Títulos con `#`, `##`, `###`
- Código con bloques triple backticks con lenguaje
- Enlaces: `[texto](url)`
- Listas ordenadas y desordenadas claras

## 🐛 Reportar bugs

Si encuentras un bug:

1. **Abre un Issue** con título descriptivo
2. **Describe el problema**:
   - Qué pasos lo reproducen
   - Resultado esperado vs actual
   - Capturas de pantalla si aplica
3. **Información del sistema**:
   - Python version
   - Sistema operativo
   - Resultado de `pip list`

### Ejemplo
```
Título: Error de autenticación con contraseñas especiales

Pasos para reproducir:
1. Registrar usuario con contraseña: P@ss!123
2. Intentar login
3. Se rechaza la contraseña

Error actual: 401 Unauthorized
Error esperado: Login exitoso
```

## ✋ Mejoras y sugerencias

- Abre un **Discussion** o **Issue** con etiqueta `enhancement`
- Describe la mejora deseada
- Explica el caso de uso
- Sé receptivo al feedback

## 💬 Preguntas

- Usa **Issues** con etiqueta `question` para dudas técnicas
- Revisa primero el FAQ en README.md
- Describe tu contexto y qué intentas lograr

## 📋 Checklist final antes de enviar PR

- [ ] Mi código sigue el estilo del proyecto
- [ ] He actualizado la documentación si es necesario
- [ ] Los cambios no rompen funcionalidad existente
- [ ] Mi rama está actualizada con `main`
- [ ] El título del PR es descriptivo
- [ ] La descripción explica el cambio claramente

## 🎓 Recursos útiles

- [Git Documentation](https://git-scm.com/doc)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [PEP 8 Style Guide](https://pep8.org/)

**¡Gracias por contribuir! Tu participación es valiosa.** 🙌
