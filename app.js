function auth() {
  return {
    user: user.value,
    pwd: pwd.value,
    secret: secret.value
  };
}

function ipsList() {
  return ips.value.split("\n").map(x => x.trim()).filter(Boolean);
}

function setCmd(text) {
  cmds.value = text;
}

function connect() {
  fetch("/connect", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ips: ipsList(), auth: auth()})
  }).then(r => r.json()).then(data => {
    output.textContent = JSON.stringify(data, null, 2);
  });
}

function run() {
  fetch("/run", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      ips: ipsList(),
      auth: auth(),
      cmds: cmds.value.split("\n"),
      exec: exec.checked,
      config: config.checked,
      dry: dry.checked
    })
  }).then(r => r.json()).then(data => {
    output.textContent = data.output.join("\n");
    diff.textContent = data.diff.join("\n");
  });
}

function rollback() {
  fetch("/rollback", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ips: ipsList(), auth: auth()})
  }).then(r => r.json()).then(data => {
    output.textContent = data.join("\n");
  });
}
