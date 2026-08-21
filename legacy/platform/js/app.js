/* ============================================================
   No-Resume Skill Market — Application Logic (clean)
   ============================================================ */

window.App = (function () {
  'use strict';

  const DATA = window.PLATFORM_DATA;
  const I18N = window.I18N || { ru: {} };

  // ─── Текущий язык ───
  let currentLang = 'ru';

  // ─── Состояние приложения ───
  const state = {
    selectedSkills: new Set(),
    activeCategory: 'all',
    selectedFormat: null,
    candidates: [], // база кандидатов для дашборда
  };

  // ─── Перевод ───
  function t(key) {
    const dict = I18N[currentLang] || I18N.ru || {};
    return dict[key] !== undefined ? dict[key] : (I18N.ru[key] !== undefined ? I18N.ru[key] : key);
  }

  // ─── Утилиты ───
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => {
      return { '&': '&', '<': '<', '>': '>', '"': '"', "'": '&#39;' }[c];
    });
  const clamp = (n, min = 0, max = 100) => Math.min(max, Math.max(min, n));

  function skillById(id) {
    return DATA.skills.find((s) => s.id === id) || { id, name: id, category: 'Custom' };
  }

  function scoreClass(score) {
    if (score >= 75) return 'high';
    if (score >= 50) return 'medium';
    return 'low';
  }

  // ═══════════════════ НАВИГАЦИЯ ═══════════════════
  function go(view) {
    $$('.view').forEach((v) => v.classList.remove('active'));
    const target = $('#view-' + view);
    if (target) target.classList.add('active');

    $$('.nav-btn').forEach((b) => b.classList.toggle('active', b.dataset.view === view));

    if (view === 'candidate') renderCandidateView();
    if (view === 'employer') renderEmployerView();

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ═══════════════════ ЧЕК-ЛИСТ НАВЫКОВ ═══════════════════
  function renderSkillFilters() {
    const wrap = $('#skillFilters');
    if (!wrap) return;
    const cats = ['all', ...DATA.skillCategories];
    wrap.innerHTML = cats
      .map(
        (c) => `
          <button class="filter-chip ${state.activeCategory === c ? 'active' : ''}" data-cat="${esc(c)}">
            ${c === 'all' ? 'Все' : c}
          </button>`
      )
      .join('');

    wrap.querySelectorAll('.filter-chip').forEach((ch) => {
      ch.addEventListener('click', () => {
        state.activeCategory = ch.dataset.cat;
        renderSkillFilters();
        renderSkillsCloud();
      });
    });
  }

  function renderSkillsCloud() {
    const wrap = $('#skillsCloud');
    if (!wrap) return;
    const filtered = DATA.skills.filter(
      (s) => state.activeCategory === 'all' || s.category === state.activeCategory
    );

    wrap.innerHTML = filtered
      .map(
        (s) => `
          <div class="skill-chip ${state.selectedSkills.has(s.id) ? 'selected' : ''}" data-id="${s.id}">
            ${esc(s.name)}
            <span class="cat-tag">${s.category}</span>
          </div>`
      )
      .join('');

    wrap.querySelectorAll('.skill-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const id = chip.dataset.id;
        if (state.selectedSkills.has(id)) state.selectedSkills.delete(id);
        else state.selectedSkills.add(id);
        updateSelectedCount();
        renderSkillsCloud();
      });
    });
  }

  function updateSelectedCount() {
    const badge = $('#selectedCount');
    const btn = $('#startTestBtn');
    const hint = $('#testHint');
    if (badge) badge.textContent = `${state.selectedSkills.size} выбрано`;
    if (btn) btn.disabled = state.selectedSkills.size === 0;
    if (hint) {
      hint.textContent =
        state.selectedSkills.size === 0
          ? 'Выберите хотя бы 1 навык'
          : 'ИИ сгенерирует уникальний тест под ваши навыки';
    }
  }

  function addCustomSkill() {
    const input = $('#customSkillInput');
    const val = input.value.trim();
    if (!val) return;
    const id = 'custom-' + val.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    if (!DATA.skills.some((s) => s.id === id)) {
      DATA.skills.push({ id, name: val, category: 'Custom' });
    }
    state.selectedSkills.add(id);
    input.value = '';
    if (state.activeCategory !== 'all') {
      state.activeCategory = 'all';
      renderSkillFilters();
    }
    renderSkillsCloud();
    updateSelectedCount();
  }

  function renderCandidateView() {
    renderSkillFilters();
    renderSkillsCloud();
    updateSelectedCount();
    $('#formatCard').style.display = 'none';
    $('#testContainer').innerHTML = '';
    $('#resultsContainer').innerHTML = '';
  }

  // ═══════════════════ ФОРМАТЫ ТЕСТА ═══════════════════
  function showFormatSelection() {
    $('#formatCard').style.display = 'block';
    state.selectedFormat = null;
    renderFormats();
    $('#testContainer').innerHTML = '';
    $('#resultsContainer').innerHTML = '';
  }

  function renderFormats() {
    const wrap = $('#formatsRow');
    const formats = [
      { key: 'text', icon: '💬', title: 'Текстовый сценарий', desc: 'Симуляция капризного клиента, декомпозиция, уточняющие вопросы' },
      { key: 'coding', icon: '⌨️', title: 'Coding Live', desc: 'Микросервис + ИИ-копилот, поиск багов ТЗ и защита от галлюцинаций' },
      { key: 'visual', icon: '🎨', title: 'Visual Audit', desc: 'Поиск багов в макете, UI/UX аудит, внимание к деталям' },
    ];

    wrap.innerHTML = formats
      .map(
        (f) => `
          <div class="format-option ${state.selectedFormat === f.key ? 'selected' : ''}" data-key="${f.key}">
            <div class="format-icon">${f.icon}</div>
            <h3>${f.title}</h3>
            <p>${f.desc}</p>
          </div>`
      )
      .join('');

    wrap.querySelectorAll('.format-option').forEach((el) => {
      el.addEventListener('click', () => {
        state.selectedFormat = el.dataset.key;
        renderFormats();
      });
    });

    const btn = $('#confirmFormatBtn');
    if (btn) btn.disabled = false;
  }

  // ═══════════════════ ЗАПУСК ТЕСТА ═══════════════════
  function startTest() {
    if (!state.selectedFormat) return;
    $('#formatCard').style.display = 'none';

    if (state.selectedFormat === 'text') renderTextTest();
    else if (state.selectedFormat === 'coding') renderCodingTest();
    else renderVisualTest();
  }

  function renderTestShell(format, bodyHTML, nextLabel) {
    const scenario = DATA.scenarios[format];
    return `
      <div class="card test-header">
        <div class="test-progress">
          <span>🎮 ${scenario.title}</span>
          <div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div>
        </div>
        <div class="test-question">Решите задачу как «Архитектор процесса»</div>
        <div class="test-metrics">
          ${scenario.default.metrics.map((m) => `<span class="metrics-chip">📌 ${m}</span>`).join('')}
        </div>
      </div>
      <div class="card test-body">
        ${bodyHTML}
      </div>
      <div class="test-actions">
        <button class="btn btn-primary" id="finishTestBtn">${nextLabel || 'Завершить тест →'}</button>
      </div>
    `;
  }

  // ─── Текстовый тест ───
  function renderTextTest() {
    const questions = DATA.promptQuestions;
    const qs = questions
      .map((q, qi) => {
        let inner = '';
        if (q.type === 'prompt') {
          inner = `
            <textarea class="prompt-textarea" data-q="${q.id}" placeholder="${esc(q.placeholder || 'Введите ваш промпт...')}"></textarea>
            <ul class="rubric-list">${q.rubric.map((r) => `<li>${r}</li>`).join('')}</ul>
          `;
        } else {
          inner = `
            <div class="options-list">
              ${q.options
                .map(
                  (o, oi) => `
                    <div class="option-item" data-q="${q.id}" data-opt="${oi}">${o.text}</div>
                  `
                )
                .join('')}
            </div>
          `;
        }
        return `
          <div class="question-block">
            <div class="question-label">${qi + 1}. ${q.question}</div>
            ${inner}
          </div>
        `;
      })
      .join('');

    $('#testContainer').innerHTML = renderTestShell('text', qs);

    $$('.option-item').forEach((el) => {
      el.addEventListener('click', () => {
        const qid = el.dataset.q;
        $$(`.option-item[data-q="${qid}"]`).forEach((x) => x.classList.remove('selected'));
        el.classList.add('selected');
      });
    });

    $('#finishTestBtn').addEventListener('click', () => {
      // Собираем ответы
      let scoreSum = 0;
      let count = 0;

      // q1
      const q1 = $('#testContainer').querySelector('.option-item[data-q="q1"].selected');
      if (q1) {
        scoreSum += DATA.promptQuestions[0].options[parseInt(q1.dataset.opt, 10)].score;
        count++;
      }
      // prompt q2
      const promptArea = $('#testContainer').querySelector('.prompt-textarea[data-q="q2"]');
      const promptText = promptArea ? promptArea.value : '';
      let promptScore = 0;
      if (promptText.trim().length > 20) promptScore = clamp(Math.round(promptText.trim().length / 3));
      else if (promptText.trim().length > 0) promptScore = 30;
      scoreSum += promptScore;
      count++;
      // q3
      const q3 = $('#testContainer').querySelector('.option-item[data-q="q3"].selected');
      if (q3) {
        scoreSum += DATA.promptQuestions[2].options[parseInt(q3.dataset.opt, 10)].score;
        count++;
      }
      // q4
      const q4 = $('#testContainer').querySelector('.option-item[data-q="q4"].selected');
      if (q4) {
        scoreSum += DATA.promptQuestions[3].options[parseInt(q4.dataset.opt, 10)].score;
        count++;
      }

      const textScore = count > 0 ? Math.round(scoreSum / count) : 0;
      finishTest('text', { text: textScore, prompt: promptScore });
    });
  }

  // ─── Coding тест ───
  function renderCodingTest() {
    const scenario = DATA.scenarios.coding.default;
    const body = `
      <h3>📋 ЗАДАЧА</h3>
      <p>${esc(scenario.task)}</p>
      <div class="coding-layout">
        <div>
          <div class="code-label">ИСХОДНЫЙ КОД (в нём есть баги ТЗ — найди и исправь)</div>
          <pre class="code-block">${esc(scenario.starterCode)}</pre>
        </div>
        <div>
          <div class="code-label">ВАША ПРАВКА / ПРОМПТ ДЛЯ ИИ-КОПИЛОТА</div>
          <textarea id="codeEditor" class="code-editor" placeholder="Вставьте исправленный код или промпт для ИИ-копилота..."></textarea>
        </div>
      </div>
    `;

    $('#testContainer').innerHTML = renderTestShell('coding', body);

    $('#finishTestBtn').addEventListener('click', () => {
      const code = $('#codeEditor').value;
      let score = 40;
      if (code.length > 100) score += 10;
      if (/email|unique|unic/i.test(code)) score += 20;
      if (/404|HTTPException|raise/i.test(code)) score += 20;
      if (/pagination|limit|page/i.test(code)) score += 10;
      score = clamp(score);
      finishTest('coding', { coding: score });
    });
  }

  // ─── Visual тест ───
  function renderVisualTest() {
    const scenario = DATA.scenarios.visual.default;
    const bugCards = scenario.actions
      .map(
        (b) => `
          <div class="bug-card" data-bug="${b.id}">
            <div>🔍 ${b.label}</div>
            <button class="btn btn-ghost btn-small bug-btn" data-bug="${b.id}">Отметить</button>
          </div>`
      )
      .join('');

    const body = `
      <h3>🎨 ЗАДАЧА: АУДИТ МАКЕТА</h3>
      <p>${esc(scenario.task)}</p>

      <div class="visual-demo">
        <div class="visual-sidebar">
          <div class="visual-group">📋 Меню
            <span style="background:#eee;padding:3px 6px;border-radius:4px;color:#999">Главная</span>
            <span style="background:#eee;padding:3px 6px;border-radius:4px;color:#999">Заказы</span>
            <span style="background:#eee;padding:3px 6px;border-radius:4px;color:#999">Настройки</span>
          </div>
          <div class="visual-group">🏷 Профиль
            <span style="background:#eee;color:#999;padding:3px 6px;border-radius:4px">Контакты не заполнены</span>
          </div>
        </div>
        <div class="visual-main-block">
          <div class="visual-hero" style="background:linear-gradient(90deg,#c9d1d9,#e8ecf8)"></div>
          <p style="font-size:12px; color:#636e72; font-weight:300; background:#f4f5f7; padding:6px; border-radius:4px">
            ⚠️ Текст «Действует до 31.12» имеет контраст 2.4:1 (WCAG AA требует ≥4.5:1)
          </p>
          <button class="visual-btn" style="opacity:0.3; pointer-events:none" disabled>Заказать</button>
          <span style="font-size:10px; color:#999">← кнопка без hover/disabled-состояний</span>
          <p style="font-size:12px; margin-top:6px; color:#888">После нажатия — нет подтверждения</p>
          <p style="font-size:12px; color:#888">Пагинация «1 2 3» не скроллит к списку</p>
        </div>
      </div>

      <h3 style="color:var(--accent); margin-top:20px;">✅ Отметьте все найденные баги:</h3>
      <div style="display:flex; gap:12px; flex-wrap:wrap; margin-top:10px">${bugCards}</div>
    `;

    $('#testContainer').innerHTML = renderTestShell('visual', body);

    $('#testContainer').addEventListener('click', (e) => {
      const btn = e.target.closest('.bug-btn');
      if (!btn) return;
      const wasFound = btn.dataset.found === 'true';
      btn.dataset.found = wasFound ? 'false' : 'true';
      btn.classList.toggle('btn-secondary', !wasFound);
      btn.textContent = wasFound ? 'Отметить' : '✅ Отмечено';
    });

    $('#finishTestBtn').addEventListener('click', () => {
      const found = $('#testContainer').querySelectorAll('.bug-btn[data-found="true"]').length;
      const score = Math.round((found / scenario.actions.length) * 100);
      finishTest('visual', { visual: score });
    });
  }

  // ═══════════════════ ФИНАЛИЗАЦИЯ ТЕСТА ═══════════════════
  function finishTest(format, testScores) {
    // Карта навыков кандидата (по выбранным скиллам)
    const skillMap = {};
    state.selectedSkills.forEach((id) => {
      skillMap[id] = clamp(55 + Math.round(Math.random() * 20) + (testScores[format] ? Math.round(testScores[format] / 10) : 0));
    });

    // Мэтчинг с компаниями
    const matches = DATA.companies
      .filter((c) => c.vacancyStatus !== 'archived')
      .map((c) => {
        let totalWeight = 0;
        let weightedSum = 0;
        for (const [skillId, weight] of Object.entries(c.weights)) {
          if (skillMap[skillId] !== undefined) {
            totalWeight += weight;
            weightedSum += weight * skillMap[skillId];
          }
        }
        const match = totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 0;
        return { company: c, match, skillMap };
      })
      .sort((a, b) => b.match - a.match);

    const bestMatch = matches[0];
    const score = bestMatch ? bestMatch.match : 0;

    const candidateResult = {
      name: 'Александр С.',
      email: 'alex@skill.market',
      skills: Array.from(state.selectedSkills).map(skillById),
      skillMap,
      score,
      matches,
      format,
      testScores,
      history: matches.slice(0, 3).map((m) => ({
        company: m.company.name,
        prompt: `Кандидат решал кейс «${m.company.position}» — его история промптов и ход мыслей отображается для рекрутера`,
        score: m.match,
      })),
    };

    // Добавляем в базу для дашборда
    if (!state.candidates) state.candidates = [];
    // Дважды не добавляем одного и того же (имя + выбор)
    const existingIdx = state.candidates.findIndex((x) => x.name === 'Александр С.');
    if (existingIdx >= 0) state.candidates[existingIdx] = candidateResult;
    else state.candidates.push(candidateResult);

    renderResults(candidateResult);
  }

  function renderResults(c) {
    const container = $('#resultsContainer');
    const passed = c.matches.some((m) => m.match >= m.company.threshold);
    const rejected = c.matches.find((m) => m.match < m.company.threshold);

    // Матрица совпадений
    const matchBars = c.matches
      .slice(0, 4)
      .map(
        (m) => `
          <div class="match-bar-row">
            <div class="match-label">${esc(m.company.name)}</div>
            <div class="match-bar-track"><div class="match-bar-fill" style="width:${m.match}%"></div></div>
            <div class="match-bar-value">${m.match}%</div>
          </div>`
      )
      .join('');

    // ИИ-карта роста при провале
    let growth = '';
    if (!passed && rejected) {
      const weakSkills = Object.keys(rejected.company.weights)
        .filter((id) => !c.skillMap[id] || c.skillMap[id] < rejected.company.weights[id])
        .map((id) => skillById(id).name);
      const resources = DATA.learningResources
        .filter((r) => weakSkills.some((s) => r.skill.toLowerCase().includes(s.toLowerCase())))
        .slice(0, 4);
      growth = `
        <div class="card growth-card result-card">
          <div class="growth-title">📈 ИИ-карта развития (вместо «простите, вы нам не подошли»)</div>
          <ul class="growth-list">
            ${weakSkills
              .slice(0, 4)
              .map((s) => `<li>Подтяните: <strong>${s}</strong> — до барьера компании ${esc(rejected.company.name)}</li>`)
              .join('')}
          </ul>
          <div class="growth-title">📚 Ресурсы для закрытия пробелов</div>
          <ul class="resources-list">
            ${
              resources
                .map(
                  (r) =>
                    `<li><a href="${r.url}" target="_blank" rel="noopener">${esc(r.title)} <span class="resource-type">${r.type}</span></a></li>`
                )
                .join('') || '<li>Подберите материалы по вашим слабым навыкам</li>'
            }
          </ul>
        </div>
      `;
    }

    // Карусель альтернативных офферов (вторичный рынок)
    const offers = (DATA.altOffers || [])
      .map((off) => {
        const comp = DATA.companies.find((x) => x.id === off.companyId) || DATA.companies[0];
        return `
          <div class="offer-card">
            <div class="company-logo" style="background:${comp.color}">${comp.logo}</div>
            <h4>${esc(comp.name)}</h4>
            <div class="industry">${esc(comp.industry)} · ${esc(comp.position)}</div>
            <div class="score" style="color:var(--accent)">Совпадение: ${off.matchScore || c.score}%</div>
            <div class="note">${off.note || 'Оффер без повторного теста'}</div>
            <button class="btn btn-primary btn-small">Принять оффер</button>
          </div>`;
      })
      .join('');

    // Позиции, на которые кандидат не претендовал
    const suggestedPositions = DATA.companies
      .filter((comp) => comp.vacancyStatus !== 'archived' && c.score < comp.threshold && c.score >= comp.threshold * 0.8)
      .slice(0, 2)
      .map(
        (comp) => `
          <div class="offer-card">
            <div class="company-logo" style="background:${comp.color}">${comp.logo}</div>
            <h4>${esc(comp.name)}</h4>
            <div class="industry">${esc(comp.position)}</div>
            <div class="note">Вы не откликались, но по навыкам подходите (${Math.round((c.score / comp.threshold) * 100)}% от порога)</div>
            <button class="btn btn-outline btn-small">Посмотреть</button>
          </div>`
      )
      .join('');

    container.innerHTML = `
      <div class="results-grid">
        <div class="card score-big-card result-card">
          <div class="certificate-header">🎓 <span>Сертификат навыков (Proof of Skill)</span></div>
          <div class="score-ring" style="background: conic-gradient(var(--primary) ${c.score * 3.6}deg, rgba(255,255,255,0.08) 0)">
            <div class="score-ring-inner">
              <div class="score-ring-number">${c.score}<small style="font-size:16px">%</small></div>
              <div class="score-ring-label">Score</div>
            </div>
          </div>
          <div class="score-status ${passed ? 'pass' : 'fail'}">
            ${passed ? '✅ Барьер одной из компаний пройден!' : '⚡ Барьер не достигнут — но у нас есть карта роста'}
          </div>
          ${
            passed
              ? `<div class="verdict-badge pass">🎉 Приглашение от ${esc(c.matches.find((m) => m.match >= m.company.threshold).company.name)}</div>`
              : `<div class="verdict-badge fail">📈 Персональная карта развития готова</div>`
          }
          <p style="margin-top:14px; font-size:13px; color:var(--text-muted)">
            Навыки: ${c.skills.map((s) => esc(s.name)).slice(0, 6).join(', ')}${c.skills.length > 6 ? '…' : ''}
          </p>
        </div>

        <div class="card result-card">
          <h3>📊 Совпадение с вакансиями (0–100%)</h3>
          <div style="margin-top:16px">${matchBars}</div>
          <p style="font-size:12px; color:var(--text-muted); margin-top:10px">
            Работодателю видна ваша история промптов и матрица навыков — без единого CV.
          </p>
        </div>

        ${growth}

        <div class="card result-card">
          <h3>🎠 Карусель альтернативных офферов</h3>
          <div class="alt-offers slider" style="margin-top:14px">${offers}</div>
        </div>

        ${
          suggestedPositions
            ? `<div class="card result-card">
                <h3>💡 Вы на это не претендовали — но вы подходите!</h3>
                <div class="alt-offers slider" style="margin-top:14px">${suggestedPositions}</div>
              </div>`
            : ''
        }
      </div>

      <div style="margin-top:24px; display:flex; gap:12px; flex-wrap:wrap">
        <button class="btn btn-ghost" id="retakeBtn">🔄 Пройти новый тест</button>
        <button class="btn btn-primary" id="viewDashboardBtn">📊 Просмотреть как работодатель</button>
      </div>
    `;

    $('#retakeBtn').addEventListener('click', () => {
      state.selectedSkills.clear();
      state.selectedFormat = null;
      renderCandidateView();
    });

    $('#viewDashboardBtn').addEventListener('click', () => go('employer'));
  }

  // ═══════════════════ КАБИНЕТ РАБОТОДАТЕЛЯ ═══════════════════
  function renderEmployerView() {
    renderCompanySelect();
    renderVacancyBuilder();
    renderCandidatesTable();
  }

  function renderCompanySelect() {
    const sel = $('#vacancyCompany');
    if (!sel) return;
    sel.innerHTML = DATA.companies
      .map((c) => `<option value="${c.id}">${esc(c.name)} — ${esc(c.position)}</option>`)
      .join('');
  }

  function renderVacancyBuilder() {
    const wrap = $('#vacancySliders');
    if (!wrap) return;

    // Собираем агрегированные веса по всем компаниям
    const allWeights = {};
    DATA.companies.forEach((c) => {
      Object.entries(c.weights).forEach(([skill, weight]) => {
        allWeights[skill] = Math.max(allWeights[skill] || 0, weight);
      });
    });

    const entries = Object.entries(allWeights).slice(0, 12);

    wrap.innerHTML = entries
      .map(
        ([skill, weight]) => `
          <div class="slider-row">
            <div class="slider-label">${esc(skillById(skill).name)}</div>
            <input type="range" min="0" max="100" value="${weight}" class="slider-input" data-skill="${skill}" />
            <div class="slider-value" data-value="${skill}">${weight}%</div>
          </div>`
      )
      .join('');

    // Обновление компаний при изменении ползунков
    wrap.querySelectorAll('.slider-input').forEach((slider) => {
      slider.addEventListener('input', () => {
        const val = parseInt(slider.value, 10);
        const skill = slider.dataset.skill;
        wrap.querySelector(`[data-value="${skill}"]`).textContent = val + '%';

        // Применяем к компании из выпадающего списка
        const companyId = $('#vacancyCompany').value;
        const company = DATA.companies.find((c) => c.id === companyId);
        if (company && company.weights[skill] !== undefined) {
          company.weights[skill] = val;
        }
      });
    });
  }

  function publishVacancy() {
    toast('✅ Новая вакансия опубликована. Бот-верификатор подтвердит её актуальность в течение 7 дней.');
  }

  // ─── Дашборд кандидатов ───
  function renderCandidatesTable() {
    const tbody = $('#candidatesTableBody');
    if (!tbody) return;

    if (!state.candidates || state.candidates.length === 0) generateDemoCandidates();

    const selectedCompanyId = $('#dashCompanyFilter').value;
    const hideLow = $('#hideLowMatches').checked;

    let list = state.candidates;

    if (selectedCompanyId !== 'all') {
      list = list.filter((c) => c.matches.some((m) => m.company.id === selectedCompanyId));
    }
    if (hideLow) list = list.filter((c) => c.score >= 50);

    const rows = list
      .map((c) => {
        const best = c.matches[0] || { company: DATA.companies[0] };
        const com = best.company;
        const statusLabel =
          com.vacancyStatus === 'pending_expire'
            ? '⚠ На грани скрытия'
            : com.vacancyStatus === 'archived'
            ? 'Архив'
            : 'Активна';
        const statusClass =
          com.vacancyStatus === 'pending_expire' ? 'pending' : com.vacancyStatus === 'archived' ? 'archived' : 'confirmed';
        return { c, com, score: best.match ?? c.score, statusLabel, statusClass };
      })
      .sort((a, b) => b.score - a.score);

    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:40px; color:var(--text-muted)">Пока нет кандидатов. Пройдите тест как соискатель — вкладка выше.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows
      .map(
        (t) => `
          <tr>
            <td>
              <div class="candidate-cell">
                <div class="candidate-avatar">${esc((t.c.name || 'А')[0])}</div>
                <div>
                  <div class="candidate-name">${esc(t.c.name)}</div>
                  <div class="candidate-email">${esc(t.c.email)}</div>
                </div>
              </div>
            </td>
            <td><strong>${esc(t.com.name)}</strong><div style="font-size:12px; color:var(--text-muted)">${esc(t.com.position)}</div></td>
            <td><span class="c-score ${scoreClass(t.score)}">${t.score}%</span></td>
            <td>
              <div class="skills-tags">
                ${t.c.skills.slice(0, 3).map((s) => `<span class="skill-tag">${esc(s.name)}</span>`).join('')}
              </div>
            </td>
            <td><span class="vacancy-status ${t.statusClass}">${t.statusLabel}</span></td>
            <td><button class="btn btn-outline btn-small" data-open="${esc(t.c.email)}">Открыть</button></td>
          </tr>`
      )
      .join('');

    tbody.querySelectorAll('[data-open]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const cand = state.candidates.find((c) => c.email === btn.dataset.open);
        if (cand) openCandidateModal(cand);
      });
    });
  }

  function generateDemoCandidates() {
    const demos = [
      { name: 'Мария С.', email: 'maria@skill.dev', skills: ['python', 'fastapi', 'llm', 'sql'] },
      { name: 'Дмитрий К.', email: 'dmitry@skill.dev', skills: ['go', 'docker', 'kubernetes', 'algorithms'] },
      { name: 'Ирина Л.', email: 'irina@skill.dev', skills: ['figma', 'uiux', 'css', 'llm'] },
      { name: 'Владимир Р.', email: 'vlad@skill.dev', skills: ['python', 'postgresql', 'microservices'] },
    ];

    state.candidates = demos.map((d) => {
      const skillMap = {};
      d.skills.forEach((id) => (skillMap[id] = 70 + Math.round(Math.random() * 30)));

      const matches = DATA.companies
        .filter((com) => Object.keys(com.weights).some((w) => skillMap[w] !== undefined))
        .map((com) => {
          let total = 0,
            sum = 0;
          for (const [k, v] of Object.entries(com.weights)) {
            if (skillMap[k] !== undefined) {
              total += v;
              sum += v * skillMap[k];
            }
          }
          return { company: com, match: total > 0 ? Math.round(sum / total) : 0, skillMap };
        })
        .sort((a, b) => b.match - a.match);

      const score = matches[0] ? matches[0].match : 55;
      const best = matches[0]?.company;

      return {
        name: d.name,
        email: d.email,
        skills: d.skills.map(skillById),
        skillMap,
        score,
        matches,
        history: [
          {
            company: best?.name || '—',
            prompt: `Промпт кандидата для кейса «${best?.position || '—'}»: собран уточняющие вопросы, проверил галлюцинации ИИ, предложил архитектуру решения.`,
            score,
          },
        ],
      };
    });
  }

  function openCandidateModal(cand) {
    const modal = $('#candidateModal');
    const content = $('#candidateModalContent');
    const best = cand.matches[0]?.company || DATA.companies[0];

    content.innerHTML = `
      <div class="candidate-detail-header">
        <div>
          <h2>${esc(cand.name)}</h2>
          <div class="candidate-detail-sub">${esc(cand.email)} · ${cand.skills.map((s) => esc(s.name)).join(', ')}</div>
        </div>
        <span class="c-score ${scoreClass(cand.score)}">${cand.score}%</span>
      </div>

      <div class="card" style="background:var(--bg); margin-bottom:12px">
        <h3 style="color:var(--accent)">📊 Матрица совпадения</h3>
        <div style="margin-top:14px">
          ${cand.matches
            .slice(0, 3)
            .map(
              (m) => `
                <div class="match-bar-row">
                  <div class="match-label">${esc(m.company.name)}</div>
                  <div class="match-bar-track"><div class="match-bar-fill" style="width:${m.match}%"></div></div>
                  <div class="match-bar-value">${m.match}%</div>
                </div>`
            )
            .join('')}
        </div>
      </div>

      <div class="card" style="background:var(--bg)">
        <h3 style="color:var(--accent)">🧠 История промптов / ход мысли</h3>
        <pre style="background:#0d1117; padding:14px; border-radius:8px; margin-top:10px; font-size:12.5px; color:#c9d1d9; white-space:pre-wrap">${esc(cand.history[0]?.prompt || 'Тестовый прогон кейса…')}</pre>
      </div>

      <div style="display:flex; gap:12px; margin-top:20px; flex-wrap:wrap">
        <button class="btn btn-primary">Пригласить на интервью</button>
        <button class="btn btn-ghost">Отклонить</button>
      </div>
    `;

    modal.style.display = 'flex';
  }

  function closeCandidateModal() {
    $('#candidateModal').style.display = 'none';
  }

  // ─── Осведомление (toast) ───
  function toast(msg) {
    const existing = document.querySelector('.demo-toast');
    if (existing) existing.remove();
    const el = document.createElement('div');
    el.className = 'demo-toast';
    el.textContent = msg;
    Object.assign(el.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      zIndex: '1000',
      background: 'var(--success)',
      color: '#08261f',
      padding: '14px 24px',
      borderRadius: '12px',
      fontSize: '15px',
      fontWeight: '600',
      boxShadow: '0 12px 30px rgba(0,0,0,0.4)',
    });
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }

  // ═══════════════════ ПЕРЕКЛЮЧЕНИЕ ЯЗЫКА ═══════════════════
  function setLang(lang) {
    currentLang = lang;
    document.documentElement.lang = lang;

    // Обновить активную кнопку
    $$('.lang-btn').forEach((b) => b.classList.toggle('active', b.dataset.lang === lang));

    // Статичные тексты
    applyStaticTranslations();

    // Перерисовать динамические части
    const activeView = document.querySelector('.view.active');
    if (activeView && activeView.id === 'view-candidate') renderCandidateView();
    if (activeView && activeView.id === 'view-employer') renderEmployerView();
  }

  function applyStaticTranslations() {
    const map = [
      // Навигация
      ['.nav-btn[data-view="landing"]', 'nav_landing'],
      ['.nav-btn[data-view="candidate"]', 'nav_candidate'],
      ['.nav-btn[data-view="employer"]', 'nav_employer'],
      ['#btnDemoCandidate', 'btn_candidate'],
      ['#btnDemoEmployer', 'btn_employer'],

      // Hero
      ['.hero-badge', 'hero_badge'],
      ['.hero h1', 'hero_title_1'],
      ['.hero-sub', 'hero_sub'],
      ['#heroStartTest', 'hero_start'],
      ['#heroEmployer', 'hero_employer'],
      ['.stat:nth-child(1) .stat-label', 'stat_1'],
      ['.stat:nth-child(2) .stat-label', 'stat_2'],
      ['.stat:nth-child(3) .stat-label', 'stat_3'],
      ['.stat:nth-child(4) .stat-label', 'stat_4'],

      // Проблемы
      ['.section-title', 'problems_title'],
      ['.problem-card:nth-child(1) h3', 'problem_1_title'],
      ['.problem-card:nth-child(1) p', 'problem_1_text'],
      ['.problem-card:nth-child(2) h3', 'problem_2_title'],
      ['.problem-card:nth-child(2) p', 'problem_2_text'],
      ['.problem-card:nth-child(3) h3', 'problem_3_title'],
      ['.problem-card:nth-child(3) p', 'problem_3_text'],
      ['.problem-card:nth-child(4) h3', 'problem_4_title'],
      ['.problem-card:nth-child(4) p', 'problem_4_text'],

      // Модули
      ['.solution-band .section-title', 'modules_title'],
      ['.module-card:nth-child(1) h3', 'module_1_title'],
      ['.module-card:nth-child(1) p', 'module_1_text'],
      ['.module-card:nth-child(2) h3', 'module_2_title'],
      ['.module-card:nth-child(2) p', 'module_2_text'],
      ['.module-card:nth-child(3) h3', 'module_3_title'],
      ['.module-card:nth-child(3) p', 'module_3_text'],
      ['.module-card:nth-child(4) h3', 'module_4_title'],
      ['.module-card:nth-child(4) p', 'module_4_text'],
      ['.module-card:nth-child(5) h3', 'module_5_title'],
      ['.module-card:nth-child(5) p', 'module_5_text'],
      ['.module-card:nth-child(6) h3', 'module_6_title'],
      ['.module-card:nth-child(6) p', 'module_6_text'],

      // Шаги
      ['.steps + .container .section-title', 'steps_title'],
      ['.step:nth-child(1) h3', 'step_1_title'],
      ['.step:nth-child(1) p', 'step_1_text'],
      ['.step:nth-child(2) h3', 'step_2_title'],
      ['.step:nth-child(2) p', 'step_2_text'],
      ['.step:nth-child(3) h3', 'step_3_title'],
      ['.step:nth-child(3) p', 'step_3_text'],
      ['.step:nth-child(4) h3', 'step_4_title'],
      ['.step:nth-child(4) p', 'step_4_text'],

      // CTA
      ['.cta-band h2', 'cta_title'],
      ['.cta-band p', 'cta_sub'],
      ['#heroStartTest2', 'cta_btn'],

      // Кабинет соискателя
      ['#view-candidate .view-title', 'cand_title'],
      ['#view-candidate .view-subtitle', 'cand_sub'],
      ['.candidate-status span', 'cand_status'],
      ['.checklist-card .card-header-row h2', 'checklist_title'],
      ['.checklist-card .muted', 'checklist_sub'],
      ['#customSkillInput', 'custom_placeholder'],
      ['#addCustomSkill', 'add_btn'],
      ['#startTestBtn', 'start_test'],
      ['#formatCard h2', 'format_title'],
      ['#confirmFormatBtn', 'start_test_btn'],
      ['#backToSkills', 'back_to_skills'],

      // Работодатель
      ['#view-employer .view-title', 'emp_title'],
      ['#view-employer .view-subtitle', 'emp_sub'],
      ['#addVacancyBtn', 'new_vacancy'],
      ['.vacancy-builder h2', 'vacancy_builder'],
      ['.vacancy-builder .muted', 'vacancy_sub'],
      ['#publishVacancyBtn', 'publish'],
      ['.employer-dashboard .dash-head h2', 'dashboard_title'],
      ['.checkbox-inline', 'hide_low'],
      ['.candidates-table th:nth-child(1)', 'th_candidate'],
      ['.candidates-table th:nth-child(2)', 'th_company'],
      ['.candidates-table th:nth-child(3)', 'th_match'],
      ['.candidates-table th:nth-child(4)', 'th_skills'],
      ['.candidates-table th:nth-child(5)', 'th_status'],

      // Футер
      ['.site-footer p', 'footer'],
    ];

    map.forEach(([sel, key]) => {
      const el = document.querySelector(sel);
      if (el) {
        if (el.tagName === 'INPUT') el.placeholder = t(key);
        else el.textContent = t(key);
      }
    });

    // Hero title — особый случай (3 части)
    const heroH1 = document.querySelector('.hero h1');
    if (heroH1) {
      heroH1.innerHTML = `${t('hero_title_1')}<br/>${t('hero_title_2')} <span class="gradient-text">${t('hero_title_3')}</span>.`;
    }
  }

  // ═══════════════════ ИНИЦИАЛИЗАЦИЯ ═══════════════════
  function init() {
    // Переключатель языка
    $$('.lang-btn').forEach((btn) => {
      btn.addEventListener('click', () => setLang(btn.dataset.lang));
    });
    setLang('ru');
    // Навигация
    $$('.nav-btn').forEach((btn) => btn.addEventListener('click', () => go(btn.dataset.view)));
    $('#btnDemoCandidate').addEventListener('click', () => go('candidate'));
    $('#btnDemoEmployer').addEventListener('click', () => go('employer'));
    $('#heroStartTest').addEventListener('click', () => go('candidate'));
    $('#heroStartTest2').addEventListener('click', () => go('candidate'));
    $('#heroEmployer').addEventListener('click', () => go('employer'));

    // Чек-лист
    $('#addCustomSkill').addEventListener('click', addCustomSkill);
    $('#customSkillInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') addCustomSkill();
    });
    $('#startTestBtn').addEventListener('click', showFormatSelection);
    $('#backToSkills').addEventListener('click', () => {
      $('#formatCard').style.display = 'none';
      renderCandidateView();
    });
    $('#confirmFormatBtn').addEventListener('click', startTest);

    // Работодатель
    $('#publishVacancyBtn').addEventListener('click', publishVacancy);
    $('#dashCompanyFilter').addEventListener('change', renderCandidatesTable);
    $('#hideLowMatches').addEventListener('change', renderCandidatesTable);
    $('#closeCandidateModal').addEventListener('click', closeCandidateModal);
    $('#candidateModal').addEventListener('click', (e) => {
      if (e.target === e.currentTarget) closeCandidateModal();
    });
    $('#addVacancyBtn').addEventListener('click', () => {
      toast('🎯 Бот-верификатор: автоматически проверяет актуальность позиции каждые 7 дней.');
      renderEmployerView();
    });

    go('landing');
  }

  document.addEventListener('DOMContentLoaded', init);

  return { go };
})();