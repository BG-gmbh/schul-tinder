(function () {
  var params = new URLSearchParams(window.location.search);
  var code = params.get("flash");
  if (!code) return;

  var messages = {
    invalid: "Benutzername oder Passwort falsch.",
    shortuser: "Benutzername mindestens 3 Zeichen.",
    shortpass: "Passwort mindestens 6 Zeichen.",
    mismatch: "Passwörter stimmen nicht überein.",
    taken: "Dieser Benutzername ist schon vergeben.",
    logout: "Du bist ausgeloggt.",
    needlogin: "Bitte zuerst einloggen.",
    levels: "Bitte für jedes Fach Pro oder Noob wählen.",
    saved: "Einstellungen gespeichert.",
  };

  var text = messages[code];
  if (!text) return;

  var ul = document.getElementById("flash-banner");
  if (!ul) return;

  var li = document.createElement("li");
  var cls =
    code === "saved"
      ? "flash-success"
      : code === "logout"
        ? "flash-info"
        : code === "needlogin"
          ? "flash-warning"
          : "flash-error";
  li.className = cls;
  li.textContent = text;
  ul.appendChild(li);

  try {
    var u = new URL(window.location.href);
    u.searchParams.delete("flash");
    window.history.replaceState({}, "", u.pathname + u.search);
  } catch (e) {}
})();
