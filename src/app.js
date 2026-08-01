/*!
 * app.js — 画面まわり
 *
 * ・入力するたびに候補を洗い出し、チップとして並べる
 * ・チップを押すと「そのまま残す」に切り替わる（＝変換前に選んでおける）
 * ・保護設定は localStorage に保存する
 */
(function () {
  'use strict';

  const Converter = window.AntonymConverter;
  const Dictionary = window.AntonymDictionary;

  const $ = (id) => document.getElementById(id);
  const el = {
    input: $('input'),
    output: $('output'),
    candidates: $('candidates'),
    manual: $('manual'),
    manualAdd: $('manual-add'),
    manualList: $('manual-list'),
    autoProtect: $('auto-protect'),
    highlight: $('highlight'),
    copy: $('copy'),
    sample: $('sample'),
    clear: $('clear'),
    swap: $('swap'),
    keepAll: $('keep-all'),
    keepNone: $('keep-none'),
    statChars: $('stat-chars'),
    statCandidates: $('stat-candidates'),
    statConverted: $('stat-converted'),
    statKept: $('stat-kept'),
    dictCount: $('dict-count'),
    dictList: $('dict-list'),
    dictSearch: $('dict-search'),
    toast: $('toast'),
  };

  const STORAGE_KEY = 'antonym-translator/v1';

  const state = {
    // チップで「そのまま」に切り替えた語
    keptTerms: new Set(),
    // 自分で登録した語句
    manualTerms: [],
    autoProtect: true,
    highlight: true,
  };

  const SAMPLE = [
    '今日はとても暑いので、大きい氷をたくさん買いました。',
    '新しい仕事は難しいけれど、成功すると嬉しいです。',
    '朝早く起きて、明るい未来を信じて前に進む。',
    'The big dog was very happy and started running.',
  ].join('\n');

  /* ---------------- 保存・復元 ---------------- */

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        manualTerms: state.manualTerms,
        keptTerms: [...state.keptTerms],
        autoProtect: state.autoProtect,
        highlight: state.highlight,
        text: el.input.value,
      }));
    } catch (e) { /* プライベートモードなどでは保存しない */ }
  }

  function restore() {
    let data = null;
    try {
      data = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    } catch (e) { data = null; }
    if (!data) return;
    if (Array.isArray(data.manualTerms)) state.manualTerms = data.manualTerms;
    if (Array.isArray(data.keptTerms)) state.keptTerms = new Set(data.keptTerms);
    if (typeof data.autoProtect === 'boolean') state.autoProtect = data.autoProtect;
    if (typeof data.highlight === 'boolean') state.highlight = data.highlight;
    if (typeof data.text === 'string') el.input.value = data.text;
    el.autoProtect.checked = state.autoProtect;
    el.highlight.checked = state.highlight;
  }

  /* ---------------- 変換 ---------------- */

  function protectSet() {
    return new Set([...state.keptTerms, ...state.manualTerms]);
  }

  function render() {
    const text = el.input.value;

    // 1. 候補（保護を無視して、変換されうる語をすべて拾う）
    const candidates = Converter.analyze(text);
    renderCandidates(candidates);

    // 2. 本変換
    const result = Converter.convert(text, {
      protect: protectSet(),
      autoProtect: state.autoProtect,
    });
    renderOutput(result, text);

    // 3. 統計
    el.statChars.textContent = text.length;
    el.statCandidates.textContent = candidates.length;
    el.statConverted.textContent = result.convertedCount;
    el.statKept.textContent = result.segments.filter((s) => s.type === 'protected').length;

    save();
  }

  function renderOutput(result, sourceText) {
    el.output.textContent = '';
    el.output.classList.toggle('plainview', !state.highlight);

    if (!sourceText.trim()) {
      const empty = document.createElement('span');
      empty.className = 'empty';
      empty.textContent = 'ここに変換結果が表示されます。';
      el.output.appendChild(empty);
      return;
    }

    for (const seg of result.segments) {
      if (seg.type === 'converted') {
        const mark = document.createElement('mark');
        mark.className = 'conv';
        mark.textContent = seg.text;
        mark.title = '原文: ' + seg.source;
        el.output.appendChild(mark);
      } else if (seg.type === 'protected') {
        const span = document.createElement('span');
        span.className = 'kept';
        span.textContent = seg.text;
        span.title = 'そのまま残した部分';
        el.output.appendChild(span);
      } else {
        el.output.appendChild(document.createTextNode(seg.text));
      }
    }
  }

  function renderCandidates(candidates) {
    el.candidates.textContent = '';

    if (!candidates.length) {
      const p = document.createElement('p');
      p.className = 'empty-note';
      p.textContent = el.input.value.trim()
        ? '変換できる語が見つかりませんでした。'
        : '原文を入力すると、ここに候補が並びます。';
      el.candidates.appendChild(p);
      return;
    }

    for (const c of candidates) {
      const kept = state.keptTerms.has(c.from);
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.setAttribute('aria-pressed', kept ? 'true' : 'false');
      chip.title = kept
        ? `「${c.from}」はそのまま残ります（クリックで変換する）`
        : `「${c.from}」→「${c.to}」に変換されます（クリックでそのまま残す）`;

      const from = document.createElement('span');
      from.textContent = c.from;
      chip.appendChild(from);

      const arrow = document.createElement('span');
      arrow.className = 'arrow';
      arrow.textContent = '→';
      chip.appendChild(arrow);

      const to = document.createElement('span');
      to.className = 'target';
      to.textContent = c.to;
      chip.appendChild(to);

      if (c.count > 1) {
        const count = document.createElement('span');
        count.className = 'count';
        count.textContent = '×' + c.count;
        chip.appendChild(count);
      }

      const stateLabel = document.createElement('span');
      stateLabel.className = 'state';
      stateLabel.textContent = kept ? '🔒 そのまま' : '';
      chip.appendChild(stateLabel);

      chip.addEventListener('click', () => {
        if (state.keptTerms.has(c.from)) state.keptTerms.delete(c.from);
        else state.keptTerms.add(c.from);
        render();
      });

      el.candidates.appendChild(chip);
    }
  }

  function renderManual() {
    el.manualList.textContent = '';
    if (!state.manualTerms.length) {
      const p = document.createElement('p');
      p.className = 'empty-note';
      p.textContent = 'まだ登録されていません。ここに登録した語句は、文中のどこにあってもそのまま残ります。';
      el.manualList.appendChild(p);
      return;
    }
    state.manualTerms.forEach((term, i) => {
      const chip = document.createElement('span');
      chip.className = 'chip-static';

      const label = document.createElement('span');
      label.textContent = term;
      label.title = term;
      chip.appendChild(label);

      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '×';
      remove.title = '削除';
      remove.setAttribute('aria-label', `「${term}」を削除`);
      remove.addEventListener('click', () => {
        state.manualTerms.splice(i, 1);
        renderManual();
        render();
      });
      chip.appendChild(remove);

      el.manualList.appendChild(chip);
    });
  }

  /* ---------------- 辞書一覧 ---------------- */

  function renderDictionary(query) {
    const q = (query || '').trim().toLowerCase();
    el.dictList.textContent = '';
    const rows = Dictionary.entries.filter((e) => {
      if (!q) return true;
      return e.a.toLowerCase().includes(q) || e.b.toLowerCase().includes(q);
    });
    for (const e of rows.slice(0, 400)) {
      const row = document.createElement('div');
      const pair = document.createElement('span');
      pair.textContent = `${e.a} ⇄ ${e.b}`;
      row.appendChild(pair);
      const tag = document.createElement('span');
      tag.className = 'tag';
      tag.textContent = e.tag;
      row.appendChild(tag);
      el.dictList.appendChild(row);
    }
    if (!rows.length) {
      const p = document.createElement('p');
      p.className = 'empty-note';
      p.textContent = '見つかりませんでした。';
      el.dictList.appendChild(p);
    }
  }

  /* ---------------- ユーティリティ ---------------- */

  let toastTimer = null;
  function toast(message) {
    el.toast.textContent = message;
    el.toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.toast.classList.remove('show'), 1800);
  }

  function debounce(fn, wait) {
    let t = null;
    return function () {
      clearTimeout(t);
      t = setTimeout(fn, wait);
    };
  }

  function addManualTerm(raw) {
    const term = raw.trim();
    if (!term) return;
    if (state.manualTerms.includes(term)) {
      toast('すでに登録されています');
      return;
    }
    state.manualTerms.push(term);
    el.manual.value = '';
    renderManual();
    render();
    toast('そのまま残す語句に追加しました');
  }

  /* ---------------- イベント ---------------- */

  const renderSoon = debounce(render, 120);

  el.input.addEventListener('input', renderSoon);

  el.manualAdd.addEventListener('click', () => addManualTerm(el.manual.value));
  el.manual.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' && !ev.isComposing) {
      ev.preventDefault();
      addManualTerm(el.manual.value);
    }
  });

  el.autoProtect.addEventListener('change', () => {
    state.autoProtect = el.autoProtect.checked;
    render();
  });

  el.highlight.addEventListener('change', () => {
    state.highlight = el.highlight.checked;
    render();
  });

  el.keepAll.addEventListener('click', () => {
    for (const c of Converter.analyze(el.input.value)) state.keptTerms.add(c.from);
    render();
  });

  el.keepNone.addEventListener('click', () => {
    state.keptTerms.clear();
    render();
  });

  el.sample.addEventListener('click', () => {
    el.input.value = SAMPLE;
    render();
  });

  el.clear.addEventListener('click', () => {
    el.input.value = '';
    el.input.focus();
    render();
  });

  el.swap.addEventListener('click', () => {
    const result = Converter.convert(el.input.value, {
      protect: protectSet(),
      autoProtect: state.autoProtect,
    });
    if (!result.text) return;
    el.input.value = result.text;
    render();
    toast('変換結果を原文に移しました');
  });

  el.copy.addEventListener('click', async () => {
    const text = el.output.textContent;
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      toast('コピーしました');
    } catch (e) {
      // クリップボード API が使えない環境向けのフォールバック
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); toast('コピーしました'); }
      catch (err) { toast('コピーできませんでした'); }
      document.body.removeChild(ta);
    }
  });

  el.dictSearch.addEventListener('input', debounce(() => renderDictionary(el.dictSearch.value), 120));

  /* ---------------- 起動 ---------------- */

  restore();
  el.dictCount.textContent = Dictionary.entries.length;
  renderDictionary('');
  renderManual();
  render();
})();
