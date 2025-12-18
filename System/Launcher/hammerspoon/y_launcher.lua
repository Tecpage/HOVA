-- y_launcher.lua
--
-- Hammerspoon Shortcut für den Y‑Launcher.
--
-- Ziel: Ein Klick auf eine "zusätzliche" Maustaste (z.B. obere Seitentaste) startet
--       Start_Y.command (im iCloud Ordner Y/) und öffnet den Launcher in einem
--       neuen Chrome‑Fenster.
--
-- WICHTIG: Die Button-Nummer hängt von der Maus ab.
--   - Linke Taste: 0, rechte Taste: 1
--   - Zusatztasten: "otherMouseDown" mit buttonNumber 2..31
--
-- Zum Ermitteln: DEBUG=true setzen, Hammerspoon neu laden und die Taste drücken.

local HOME = os.getenv("HOME")
local Y_ROOT = HOME .. "/Library/Mobile Documents/com~apple~CloudDocs/Y"
local START_CMD = Y_ROOT .. "/Start_Y.command"

-- Setze hier die gewünschte Maustaste:
-- Typisch sind 3/4/5 (je nach Maus). Mit DEBUG findest du die korrekte Nummer.
local TARGET_BUTTON = 4
local DEBUG = false

local function runLauncher()
  -- Startet den Launcher im Hintergrund (ohne Terminal)
  local cmd = string.format('bash "%s" >/dev/null 2>&1 &', START_CMD)
  hs.execute(cmd)
end

local tap = hs.eventtap.new({ hs.eventtap.event.types.otherMouseDown }, function(e)
  local btn = e:getProperty(hs.eventtap.event.properties.mouseEventButtonNumber)
  if DEBUG then
    hs.alert.show("Mouse button: " .. tostring(btn))
  end

  if btn == TARGET_BUTTON then
    runLauncher()
    return true
  end

  return false
end)

tap:start()

return {
  run = runLauncher,
}
