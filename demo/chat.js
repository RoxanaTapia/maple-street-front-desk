(function () {
  var thread = document.getElementById("thread");
  var form = document.getElementById("composer");
  var box = document.getElementById("message");
  var button = document.getElementById("send");

  function addLine(kind, text) {
    var line = document.createElement("p");
    line.className = kind;
    line.textContent = text;
    thread.appendChild(line);
    thread.scrollTop = thread.scrollHeight;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var message = box.value.trim();
    if (!message) {
      return;
    }
    addLine("customer", message);
    box.value = "";
    box.disabled = true;
    button.disabled = true;
    fetch("/reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message })
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        var reply = result.data && typeof result.data.reply === "string" ? result.data.reply : "";
        addLine("reply", result.ok && reply ? reply : "Please try again.");
      })
      .catch(function () {
        addLine("reply", "Please try again.");
      })
      .then(function () {
        box.disabled = false;
        button.disabled = false;
        box.focus();
      });
  });
})();
