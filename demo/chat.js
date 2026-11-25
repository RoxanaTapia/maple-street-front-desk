(function () {
  var thread = document.getElementById("thread");
  var form = document.getElementById("composer");
  var box = document.getElementById("message");
  var button = document.getElementById("send");
  var chips = document.querySelectorAll("#chips button");
  var composing = false;
  var waiting = false;

  box.addEventListener("compositionstart", function () {
    composing = true;
  });
  box.addEventListener("compositionend", function () {
    composing = false;
  });
  box.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    if (composing || event.isComposing || event.keyCode === 229) {
      return;
    }
    event.preventDefault();
    if (!box.value.trim()) {
      return;
    }
    form.requestSubmit();
  });

  Array.prototype.forEach.call(chips, function (chip) {
    chip.addEventListener("click", function () {
      send(chip.getAttribute("data-message") || "");
    });
  });

  function reducedMotion() {
    try {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (error) {
      return false;
    }
  }

  function answeredIn(ms) {
    var seconds = ms / 1000;
    if (!(seconds >= 0)) {
      seconds = 0;
    }
    if (seconds < 0.05) {
      return "Answered in under 0.1s";
    }
    return "Answered in " + seconds.toFixed(1) + "s";
  }

  function scrollThread() {
    thread.scrollTop = thread.scrollHeight;
  }

  function addCustomer(text) {
    var line = document.createElement("p");
    line.className = "customer dk-enter";
    line.textContent = text;
    thread.appendChild(line);
    scrollThread();
  }

  function setWaiting(state) {
    waiting = state;
    box.disabled = state;
    button.disabled = state;
    Array.prototype.forEach.call(chips, function (chip) {
      chip.disabled = state;
    });
  }

  function showTyping() {
    if (reducedMotion()) {
      return null;
    }
    var line = document.createElement("p");
    line.className = "reply typing";
    line.setAttribute("role", "status");
    var label = document.createElement("span");
    label.className = "visually-hidden";
    label.textContent = "Typing";
    line.appendChild(label);
    var dot;
    for (dot = 0; dot < 3; dot += 1) {
      var mark = document.createElement("span");
      mark.className = "dot";
      mark.setAttribute("aria-hidden", "true");
      line.appendChild(mark);
    }
    thread.appendChild(line);
    scrollThread();
    return line;
  }

  function validSource(source) {
    return source && typeof source.label === "string" && source.label &&
      typeof source.excerpt === "string" && source.excerpt;
  }

  function addSource(block, source) {
    var list = block.querySelector(".source-chips");
    if (!list) {
      list = document.createElement("ul");
      list.className = "dk-chips source-chips";
      block.appendChild(list);
    }
    var item = document.createElement("li");
    var opener = document.createElement("button");
    opener.type = "button";
    opener.textContent = source.label;
    opener.setAttribute("aria-expanded", "false");
    var excerpt = document.createElement("p");
    excerpt.className = "excerpt dk-source";
    excerpt.hidden = true;
    excerpt.textContent = source.excerpt;
    opener.addEventListener("click", function () {
      var open = excerpt.hidden;
      excerpt.hidden = !open;
      opener.setAttribute("aria-expanded", open ? "true" : "false");
      if (open && window.DemoKit && typeof window.DemoKit.highlight === "function") {
        window.DemoKit.highlight(excerpt);
      }
    });
    item.appendChild(opener);
    list.appendChild(item);
    block.appendChild(excerpt);
  }

  function addReply(data, ms) {
    var block = document.createElement("div");
    block.className = "reply-block dk-enter";
    var line = document.createElement("p");
    line.className = "reply";
    line.textContent = data.reply;
    block.appendChild(line);
    if (data.tag) {
      var tag = document.createElement("p");
      tag.className = "tag";
      tag.textContent = data.tag;
      block.appendChild(tag);
    }
    var elapsed = document.createElement("p");
    elapsed.className = "elapsed";
    elapsed.textContent = answeredIn(ms);
    block.appendChild(elapsed);
    (data.sources || []).forEach(function (source) {
      if (validSource(source)) {
        addSource(block, source);
      }
    });
    if (data.checks && data.checks.length) {
      var drawer = document.createElement("details");
      drawer.className = "behind";
      var summary = document.createElement("summary");
      summary.textContent = "Behind this reply";
      drawer.appendChild(summary);
      var list = document.createElement("ul");
      data.checks.forEach(function (check) {
        if (typeof check !== "string" || !check) {
          return;
        }
        var item = document.createElement("li");
        item.textContent = check;
        list.appendChild(item);
      });
      drawer.appendChild(list);
      block.appendChild(drawer);
    }
    thread.appendChild(block);
    scrollThread();
  }

  function send(message) {
    var text = (message || "").trim();
    if (!text || waiting) {
      return;
    }
    addCustomer(text);
    box.value = "";
    setWaiting(true);
    var started = window.performance && window.performance.now ? window.performance.now() : Date.now();
    var typing = null;
    var typingTimer = null;
    if (!reducedMotion()) {
      typingTimer = window.setTimeout(function () {
        typing = showTyping();
      }, 120);
    }
    fetch("/reply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, trace: true })
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        var now = window.performance && window.performance.now ? window.performance.now() : Date.now();
        var payload = result.data || {};
        var reply = typeof payload.reply === "string" ? payload.reply : "";
        addReply({
          reply: result.ok && reply ? reply : "Please try again.",
          tag: typeof payload.tag === "string" ? payload.tag : "",
          checks: Array.isArray(payload.checks) ? payload.checks : [],
          sources: Array.isArray(payload.sources) ? payload.sources : []
        }, now - started);
      })
      .catch(function () {
        var now = window.performance && window.performance.now ? window.performance.now() : Date.now();
        addReply({ reply: "Please try again.", tag: "", checks: [], sources: [] }, now - started);
      })
      .then(function () {
        if (typingTimer) {
          window.clearTimeout(typingTimer);
        }
        if (typing && typing.parentNode) {
          typing.parentNode.removeChild(typing);
        }
        setWaiting(false);
        box.focus();
      });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    send(box.value);
  });
})();
