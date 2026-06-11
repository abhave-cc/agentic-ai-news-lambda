const AGENT_ENDPOINT = "https://iyrj7nrqw5xgpci5ccu5dfls5y0lifpx.lambda-url.eu-west-2.on.aws/";

const runButton = document.getElementById("runButton");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

const summaryText = document.getElementById("summaryText");

const keyThemesEl = document.getElementById("keyThemes");
const risksEl = document.getElementById("risks");
const opportunitiesEl = document.getElementById("opportunities");
const enterpriseRecommendationsEl = document.getElementById(
  "enterpriseRecommendations"
);
const followUpQuestionsEl = document.getElementById(
  "followUpQuestions"
);

const sourceArticlesEl = document.getElementById("sourceArticles");
const hackerNewsEl = document.getElementById("hackerNews");
const arxivPapersEl = document.getElementById("arxivPapers");
const ragContextEl = document.getElementById("ragContext");

const ragBadge = document.getElementById("ragBadge");
const gnewsBadge = document.getElementById("gnewsBadge");
const hnBadge = document.getElementById("hnBadge");
const arxivBadge = document.getElementById("arxivBadge");

function clearList(element) {
  element.innerHTML = "";
}

function addListItems(element, items) {
  clearList(element);

  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "None";
    element.appendChild(li);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function setBadge(element, text, success) {
  element.textContent = text;

  element.classList.remove(
    "success",
    "warning",
    "neutral"
  );

  element.classList.add(success ? "success" : "warning");
}

function renderSourceArticles(articles) {
  clearList(sourceArticlesEl);

  if (!articles || articles.length === 0) {
    sourceArticlesEl.innerHTML =
      "<li>No articles returned</li>";
    return;
  }

  articles.forEach((article) => {
    const li = document.createElement("li");

    const link = document.createElement("a");
    link.href = article.url;
    link.target = "_blank";
    link.textContent = article.title;

    li.appendChild(link);
    sourceArticlesEl.appendChild(li);
  });
}

function renderHackerNews(items) {
  clearList(hackerNewsEl);

  if (!items || items.length === 0) {
    hackerNewsEl.innerHTML =
      "<li>No Hacker News items returned</li>";
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");

    const link = document.createElement("a");
    link.href = item.url;
    link.target = "_blank";
    link.textContent =
      `${item.title} (score ${item.score || 0})`;

    li.appendChild(link);
    hackerNewsEl.appendChild(li);
  });
}

function renderArxiv(items) {
  clearList(arxivPapersEl);

  if (!items || items.length === 0) {
    arxivPapersEl.innerHTML =
      "<li>No arXiv papers returned</li>";
    return;
  }

  items.forEach((paper) => {
    const li = document.createElement("li");

    const link = document.createElement("a");
    link.href = paper.url;
    link.target = "_blank";
    link.textContent = paper.title;

    li.appendChild(link);
    arxivPapersEl.appendChild(li);
  });
}

function renderRagContext(items) {
  clearList(ragContextEl);

  if (!items || items.length === 0) {
    ragContextEl.innerHTML =
      "<li>No RAG context returned</li>";
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");

    li.textContent =
      `${item.document} (score ${Number(
        item.score || 0
      ).toFixed(2)})`;

    ragContextEl.appendChild(li);
  });
}

runButton.addEventListener("click", async () => {
  const topic = document
    .getElementById("topic")
    .value
    .trim();

  const maxResults = Number(
    document.getElementById("maxResults").value
  );

  if (!topic) {
    statusEl.textContent =
      "Please enter a topic.";
    return;
  }

  runButton.disabled = true;
  statusEl.textContent =
    "Running research agent...";

  resultsEl.classList.add("hidden");

  try {
    const response = await fetch(
      AGENT_ENDPOINT,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify({
          topic,
          max_results: maxResults,
        }),
      }
    );

    const payload =
      await response.json();

    if (!response.ok) {
      throw new Error(
        payload.error ||
          "Agent request failed"
      );
    }

    const summary =
      payload.summary || {};

    summaryText.textContent =
      summary.summary ||
      "No summary returned";

    addListItems(
      keyThemesEl,
      summary.key_themes || []
    );

    addListItems(
      risksEl,
      summary.risks || []
    );

    addListItems(
      opportunitiesEl,
      summary.opportunities || []
    );

    addListItems(
      enterpriseRecommendationsEl,
      summary.enterprise_recommendations ||
        []
    );

    addListItems(
      followUpQuestionsEl,
      summary.follow_up_questions || []
    );

    renderSourceArticles(
      payload.source_articles || []
    );

    renderHackerNews(
      payload.hacker_news || []
    );

    renderArxiv(
      payload.arxiv_papers || []
    );

    renderRagContext(
      payload.rag_context || []
    );

    const ragCount =
      payload.rag_context?.length || 0;

    const gnewsCount =
      payload.source_articles?.length || 0;

    const hnCount =
      payload.hacker_news?.length || 0;

    const arxivCount =
      payload.arxiv_papers?.length || 0;

    setBadge(
      ragBadge,
      `✓ RAG Knowledge Base used — ${ragCount} chunks retrieved`,
      ragCount > 0
    );

    setBadge(
      gnewsBadge,
      `✓ GNews used — ${gnewsCount} articles returned`,
      gnewsCount > 0
    );

    setBadge(
      hnBadge,
      `✓ Hacker News used — ${hnCount} items returned`,
      hnCount > 0
    );

    setBadge(
      arxivBadge,
      `✓ arXiv used — ${arxivCount} papers returned`,
      arxivCount > 0
    );

    resultsEl.classList.remove(
      "hidden"
    );

    statusEl.textContent =
      `Completed using ${payload.model || "AI model"}.`;
  } catch (error) {
    statusEl.textContent =
      `Error: ${error.message}`;
  } finally {
    runButton.disabled = false;
  }
});
