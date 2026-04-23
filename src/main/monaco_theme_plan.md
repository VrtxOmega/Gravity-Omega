# Monaco Editor Theme Implementation Plan

## Goal
Create and apply a custom 'veritas-dark' Monaco editor theme with specific color, font, and line height settings, ensuring it's registered before any editor instance mounts.

## Steps
1.  **Define Theme Configuration:** Create a JavaScript file (`monaco_theme_config.js`) containing the `veritasDarkTheme` object with all specified color rules and editor UI colors.
2.  **Register and Apply Theme:** Within `monaco_theme_config.js`, use `monaco.editor.defineTheme` to register the new theme and `monaco.editor.setTheme` to apply it globally.
3.  **Set Global Editor Options:** Configure `monaco.editor.setOptions` for `fontSize`, `fontFamily`, and `lineHeight` within `monaco_theme_config.js`.
4.  **Integrate into Main Process:** Instruct RJ to import/require `monaco_theme_config.js` in the main Electron process's `main.js` (or equivalent file where Monaco is initialized) to ensure it runs before any editor instances are created.
5.  **Open File for Review:** Open `monaco_theme_config.js` in the UI for RJ to review and integrate.