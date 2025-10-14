const runButton = document.getElementById("run");
const urlsField = document.getElementById("urls");
const consoleEl = document.getElementById("console");
const outputsEl = document.getElementById("outputs");

async function pollStatus(jobId) {
  const interval = 2000;
  const poll = async () => {
    const res = await fetch(`/api/status/${jobId}`);
    if (!res.ok) {
      consoleEl.textContent = `Job ${jobId} not found.`;
      return;
    }
    const data = await res.json();
    consoleEl.textContent = data.log.join("\n");
    if (data.status === "running") {
      setTimeout(poll, interval);
    } else {
      consoleEl.textContent += `\nStatus: ${data.status}`;
      outputsEl.innerHTML = "";
      runButton.disabled = false;
      (data.outputs || []).forEach((item) => {
        const link = document.createElement("a");
        link.href = item.src;
        link.textContent = item.video_id;
        link.target = "_blank";
        const container = document.createElement("div");
        container.className = "output-item";
        container.appendChild(link);
        outputsEl.appendChild(container);
      });
    }
  };
  poll();
}

runButton.addEventListener("click", async () => {
  const urls = urlsField.value
    .split("\n")
    .map((u) => u.trim())
    .filter(Boolean);
  if (urls.length === 0) {
    alert("Please provide at least one URL.");
    return;
  }
  runButton.disabled = true;
  consoleEl.textContent = "Submitting batch…";
  try {
    const res = await fetch("/api/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Request failed");
    }
    pollStatus(data.job_id);
  } catch (error) {
    consoleEl.textContent = `Error: ${error.message}`;
    runButton.disabled = false;
  } finally {
    if (runButton.disabled) {
      runButton.disabled = false;
    }
  }
});
