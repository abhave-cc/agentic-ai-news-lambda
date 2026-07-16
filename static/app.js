function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function renderList(elementId, items) {
  const element = document.getElementById(elementId);

  clearElement(element);

  if (!Array.isArray(items) || items.length === 0) {
    const item = document.createElement("li");

    item.className = "empty-state";
    item.textContent = "No items returned.";

    element.appendChild(item);
    return;
  }

  items.forEach((value) => {
    const item = document.createElement("li");

    item.textContent = value;
    element.appendChild(item);
  });
}

function renderSources(articles) {
  const container = document.getElementById("sources");
  const countBadge = document.getElementById("sourceCount");

  clearElement(container);

  const safeArticles = Array.isArray(articles)
    ? articles
    : [];

  countBadge.textContent =
    `${safeArticles.length} source` +
    `${safeArticles.length === 1 ? "" : "s"}`;

  if (safeArticles.length === 0) {
    const emptyMessage = document.createElement("p");

    emptyMessage.className = "empty-state";
    emptyMessage.textContent =
      "No external news sources were returned.";

    container.appendChild(emptyMessage);
    return;
  }

  safeArticles.forEach((article) => {
    const card = document.createElement("article");
    const link = document.createElement("a");
    const source = document.createElement("div");

    card.className = "source-card";

    link.href = article.url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent =
      article.title || "Untitled article";

    source.className = "source-name";
    source.textContent =
      article.source || "Unknown source";

    card.appendChild(link);
    card.appendChild(source);
    container.appendChild(card);
  });
}

function renderRagSources(items) {
  const container = document.getElementById("ragSources");
  const countBadge = document.getElementById("ragCount");

  clearElement(container);

  const safeItems = Array.isArray(items)
    ? items
    : [];

  countBadge.textContent =
    `${safeItems.length} document` +
    `${safeItems.length === 1 ? "" : "s"}`;

  if (safeItems.length === 0) {
    const emptyMessage = document.createElement("p");

    emptyMessage.className = "empty-state";
    emptyMessage.textContent =
      "No internal RAG context was used.";

    container.appendChild(emptyMessage);
    return;
  }

  safeItems.forEach((item) => {
    const card = document.createElement("article");
    const title = document.createElement("h3");
    const metadata = document.createElement("div");
    const text = document.createElement("p");

    card.className = "rag-card";

    title.textContent =
      item.document || "Unnamed document";

    metadata.className = "rag-meta";
    metadata.textContent =
      typeof item.score === "number"
        ? `Relevance score: ${item.score}`
        : "Internal knowledge source";

    text.textContent =
      item.text || "No excerpt available.";

    card.appendChild(title);
    card.appendChild(metadata);
    card.appendChild(text);
    container.appendChild(card);
  });
}

function setStatus(message, state) {
  const statusElement = document.getElementById("status");

  statusElement.textContent = message;
  statusElement.className = "status";

  if (state) {
    statusElement.classList.add(state);
  }
}

async function runResearch() {
  const topicInput = document.getElementById("topic");
  const resultsElement = document.getElementById("results");
  const researchButton =
    document.getElementById("researchButton");

  const topic = topicInput.value.trim();

  if (!topic) {
    setStatus("Please enter a topic.", "error");
    resultsElement.hidden = true;
    return;
  }

  setStatus("Researching...");
  resultsElement.hidden = true;
  researchButton.disabled = true;
  researchButton.textContent = "Working...";

  try {
    const response = await fetch("/api/research", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        topic: topic,
        max_results: 5
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error || "The research request failed."
      );
    }

    const summary = data.summary || {};

    document.getElementById("summary").textContent =
      summary.summary || "No summary returned.";

    document.getElementById("modelBadge").textContent =
      data.model || "Bedrock model";

    renderList(
      "keyThemes",
      summary.key_themes
    );

    renderList(
      "risks",
      summary.risks
    );

    renderList(
      "opportunities",
      summary.opportunities
    );

    renderList(
      "recommendations",
      summary.enterprise_recommendations
    );

    renderList(
      "followUpQuestions",
      summary.follow_up_questions
    );

    renderSources(data.source_articles);
    renderRagSources(data.rag_context);

    setStatus(
      `Research completed for: ${data.topic}`,
      "success"
    );

    resultsElement.hidden = false;

  } catch (error) {
    setStatus(
      `Error: ${error.message}`,
      "error"
    );

    resultsElement.hidden = true;

  } finally {
    researchButton.disabled = false;
    researchButton.textContent = "Research";
  }
}

document
  .getElementById("researchButton")
  .addEventListener("click", runResearch);

document
  .getElementById("topic")
  .addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      runResearch();
    }
  });
