(() => {
  const BACKEND_URL = "http://127.0.0.1:8000";

  const form = document.getElementById("genForm");
  const collegeEl = document.getElementById("college");
  const previewImg = document.getElementById("templatePreview");
  const healthLink = document.getElementById("healthLink");

  const nameEl = document.getElementById("name");
  const rollEl = document.getElementById("rollNumber");
  const subjectEl = document.getElementById("subject");
  const lenEl = document.getElementById("answerLength");
  const questionsEl = document.getElementById("questions");
  const pdfEl = document.getElementById("assignmentPdf");
  const clearPdfBtn = document.getElementById("clearPdfBtn");
  const pdfMeta = document.getElementById("pdfMeta");

  const msg = document.getElementById("msg");
  const generateBtn = document.getElementById("generateBtn");
  const spinner = document.querySelector(".spinner");
  const btnText = document.querySelector(".btn-text");

  const downloadBox = document.getElementById("downloadBox");
  const downloadBtn = document.getElementById("downloadBtn");
  const downloadMeta = document.getElementById("downloadMeta");

  healthLink.href = `${BACKEND_URL}/health`;
  healthLink.target = "_blank";

  function setPreview() {
    const val = (collegeEl.value || "default").toLowerCase();
    previewImg.src = `blank-sessional/${val}.png`;
  }

  function setLoading(isLoading) {
    generateBtn.disabled = isLoading;
    if (isLoading) {
      spinner.classList.remove("hidden");
      btnText.textContent = "Generating...";
    } else {
      spinner.classList.add("hidden");
      btnText.textContent = "Generate PDF";
    }
  }

  function showMsg(type, text) {
    msg.classList.remove("hidden", "error", "success");
    msg.classList.add(type);
    msg.textContent = text;
  }

  function hideMsg() {
    msg.classList.add("hidden");
    msg.textContent = "";
    msg.classList.remove("error", "success");
  }

  function clearDownload() {
    downloadBox.classList.add("hidden");
    downloadBtn.removeAttribute("data-url");
    downloadMeta.textContent = "";
  }

  function setPdfMeta(file) {
    if (!file) {
      pdfMeta.classList.add("hidden");
      pdfMeta.textContent = "";
      return;
    }
    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    pdfMeta.textContent = `Selected: ${file.name} (${sizeMb} MB)`;
    pdfMeta.classList.remove("hidden");
  }

  collegeEl.addEventListener("change", () => {
    setPreview();
    clearDownload();
  });

  pdfEl.addEventListener("change", () => {
    hideMsg();
    clearDownload();
    const file = pdfEl.files && pdfEl.files[0] ? pdfEl.files[0] : null;
    setPdfMeta(file);
  });

  clearPdfBtn.addEventListener("click", () => {
    pdfEl.value = "";
    setPdfMeta(null);
    hideMsg();
    clearDownload();
  });

  downloadBtn.addEventListener("click", () => {
    const url = downloadBtn.getAttribute("data-url");
    if (!url) {
      showMsg("error", "PDF URL missing. Please generate again.");
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideMsg();
    clearDownload();

    const name = nameEl.value.trim();
    const roll_number = rollEl.value.trim();
    const subject = subjectEl.value.trim();
    const college = (collegeEl.value || "default").trim().toLowerCase();
    const answer_length = (lenEl.value || "medium").trim().toLowerCase();
    const questions = questionsEl.value.trim();
    const pdfFile = pdfEl.files && pdfEl.files[0] ? pdfEl.files[0] : null;

    if (!name || !roll_number || !subject) {
      showMsg("error", "Please fill student name, roll number, and subject.");
      return;
    }

    if (!questions && !pdfFile) {
      showMsg("error", "Provide either manual questions OR upload an assignment PDF.");
      return;
    }

    if (pdfFile && pdfFile.type && pdfFile.type !== "application/pdf") {
      showMsg("error", "Please upload a valid PDF file.");
      return;
    }

    const fd = new FormData();
    fd.append("name", name);
    fd.append("roll_number", roll_number);
    fd.append("subject", subject);
    fd.append("college", college);
    fd.append("answer_length", answer_length);
    if (questions) fd.append("questions", questions);
    if (pdfFile) fd.append("assignment_pdf", pdfFile);

    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/generate-pdf`, { method: "POST", body: fd });
      let data = null;
      try {
        data = await res.json();
      } catch (_) {}

      if (!res.ok || !data || data.success === false) {
        const msgText = (data && (data.message || data.detail)) || `Request failed (${res.status})`;
        throw new Error(msgText);
      }

      const pdfUrl = data.pdf_url ? `${BACKEND_URL}${data.pdf_url}` : null;
      if (!pdfUrl) throw new Error("Backend did not return a pdf_url.");

      downloadBtn.setAttribute("data-url", pdfUrl);
      downloadMeta.textContent = `Ready: ${data.pages || "?"} pages · Job ID: ${data.job_id || "-"}`;
      downloadBox.classList.remove("hidden");
      showMsg("success", "PDF generated successfully. Click Download PDF.");
      downloadBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      console.error(err);
      showMsg("error", err?.message || "Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  });

  // Init
  setPreview();
  setPdfMeta(null);
})();

