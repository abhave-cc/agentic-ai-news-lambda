const AGENT_ENDPOINT = "https://q63t7rkpq3r2fyxutwcwl2r5i40ehgkg.lambda-url.eu-west-2.on.aws/";

const runButton = document.getElementById("runButton");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

function setList(elementId, items) {
  const el = document.getElementById(elementId);
  el.innerHTML = "";

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "None returned";
    el.appendChild(li);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    el.appendChild(li);
  });
}

function setArticles(articles) {
  const el = document.getElementById("articles");
  el.innerHTML = "";

  if (!articles || articles.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No articles returned";
    el.appendChild(li);
    return;
  }

  articles.forEach((article) => {
    const li = document.createElement("li");
    const link = document.createElement("a");

    link.href = article.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = article.title || "Untitled article";

    const source = document.createElement("span");
    source.textContent = article.source ? ` — ${article.source}` : "";

    li.appendChild(link);
    li.appendChild(source);
    el.appendChild(li);
  });
}

runButton.addEventListener("click", async () => {
  const topic = document.getElementById("topic").value.trim();
  const maxResults = Number(document.getElementById("maxResults").value);

  if (!topic) {
    statusEl.textContent = "Please enter a topic.";
    return;
  }

  runButton.disabled = true;
  statusEl.textContent = "Running research agent...";
  resultsEl.classList.add("hidden");

  try {
    const response = await fetch(AGENT_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        topic,
        max_results: maxResults,
      }),
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Agent request failed");
    }

    const body = typeof payload.body === "string" ? JSON.parse(payload.body) : payload;
    const summary = body.summary || {};

    document.getElementById("summary").textContent =
      summary.summary || summary.raw_model_output || "No summary returned";

    setList("themes", summary.key_themes);
    setList("risks", summary.risks);
    setList("opportunities", summary.opportunities);
    setList("questions", summary.follow_up_questions);
    setArticles(body.source_articles);

    resultsEl.classList.remove("hidden");
    statusEl.textContent = `Completed using ${body.model || "model"}.`;
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  } finally {
    runButton.disabled = false;
  }
});
