/*!
 * converter.js — 対義語変換エンジン
 *
 * 1) 辞書 + 活用展開から「変換元 → 変換先」の索引を作る
 * 2) 入力テキストを走査し、最長一致で置換する
 * 3) ただし「保護」に指定された語・文はそのまま残す
 *
 * DOM に依存しないので Node からもそのままテストできる。
 */
(function (root, factory) {
  const dict = typeof require === 'function' && typeof module === 'object'
    ? require('./dictionary.js')
    : root.AntonymDictionary;
  const conj = typeof require === 'function' && typeof module === 'object'
    ? require('./conjugate.js')
    : root.AntonymConjugate;
  const value = factory(dict, conj);
  if (typeof module === 'object' && module.exports) module.exports = value;
  else root.AntonymConverter = value;
})(typeof self !== 'undefined' ? self : this, function (Dictionary, Conjugate) {
  'use strict';

  const KANJI = /[々一-鿿豈-﫿]/;
  const HIRAGANA = /[ぁ-ゖ]/;
  const ASCII_WORD = /[A-Za-z]/;
  const ASCII_WORD_CHAR = /[A-Za-z0-9'’_-]/;

  // 既定で保護するパターン（URL・メール・`code`・#タグ・@メンション）
  const AUTO_PROTECT_PATTERNS = [
    /https?:\/\/[^\s、。」』）)]+/g,
    /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g,
    /`[^`\n]+`/g,
    /[#＃][^\s#＃、。]+/g,
    /@[A-Za-z0-9_]+/g,
  ];

  /* ------------------------------------------------------------------ *
   * 索引の構築
   * ------------------------------------------------------------------ */
  function buildIndex() {
    const ja = new Map(); // 表層形 → { to, weak, tag, base }
    const en = new Map(); // 小文字表記 → { to, tag, base }
    const deferred = []; // 可能形などの派生形（見出し語の登録後に追加）
    let maxJaLen = 1;

    // 仮名だけの語は、後ろに平仮名が続くときは一致させない
    // （「〜はいい」の中の「はい」を拾わないため）
    const KANA_ONLY = /^[ぁ-ゖァ-ヺーｦ-ﾟ]+$/;

    const addJa = (from, to, meta) => {
      if (!from || !to || from === to) return;
      if (ja.has(from)) return; // 先に登録された対応を優先する
      ja.set(from, {
        to,
        weak: !!meta.weak,
        kana: KANA_ONLY.test(from),
        tag: meta.tag,
        base: meta.base,
        lang: 'ja',
      });
      if (from.length > maxJaLen) maxJaLen = from.length;
    };
    const addEn = (from, to, meta) => {
      if (!from || !to) return;
      const key = from.toLowerCase();
      if (key === to.toLowerCase()) return;
      if (en.has(key)) return;
      en.set(key, { to, tag: meta.tag, base: meta.base, lang: 'en' });
    };

    for (const entry of Dictionary.entries) {
      if (entry.lang === 'en') {
        const forms = Conjugate.expandEnglish(entry);
        const rev = Conjugate.expandEnglish({ ...entry, a: entry.b, b: entry.a });
        for (const [from, to] of forms) addEn(from, to, { tag: entry.tag, base: entry.a });
        for (const [from, to] of rev) addEn(from, to, { tag: entry.tag, base: entry.b });
        continue;
      }
      const forward = Conjugate.expandPair(entry);
      const backward = Conjugate.expandPair({ ...entry, a: entry.b, b: entry.a, typeA: entry.typeB, typeB: entry.typeA });
      for (const [from, to, derived] of forward) {
        const meta = { weak: entry.weak, tag: entry.tag, base: entry.a };
        if (derived) deferred.push([from, to, meta]);
        else addJa(from, to, meta);
      }
      for (const [from, to, derived] of backward) {
        const meta = { weak: entry.weak, tag: entry.tag, base: entry.b };
        if (derived) deferred.push([from, to, meta]);
        else addJa(from, to, meta);
      }
    }

    // 見出し語をすべて登録してから、派生形を隙間に入れる
    for (const [from, to, meta] of deferred) addJa(from, to, meta);

    return { ja, en, maxJaLen };
  }

  const INDEX = buildIndex();

  /* ------------------------------------------------------------------ *
   * 保護範囲の計算
   * ------------------------------------------------------------------ */
  function collectProtectedRanges(text, terms, useAutoProtect) {
    const ranges = [];

    if (useAutoProtect) {
      for (const re of AUTO_PROTECT_PATTERNS) {
        re.lastIndex = 0;
        let m;
        while ((m = re.exec(text)) !== null) {
          if (m[0].length === 0) { re.lastIndex++; continue; }
          ranges.push([m.index, m.index + m[0].length]);
        }
      }
    }

    const list = [...terms].filter((t) => t && t.length > 0);
    if (list.length) {
      // 長いものから先に当てる
      const sorted = list.slice().sort((x, y) => y.length - x.length);
      const lower = text.toLowerCase();
      for (const term of sorted) {
        // 英字だけの指定は大文字小文字を無視して探す
        const isAscii = /^[\x20-\x7E]+$/.test(term);
        const needle = isAscii ? term.toLowerCase() : term;
        const hay = isAscii ? lower : text;
        let from = 0;
        for (;;) {
          const at = hay.indexOf(needle, from);
          if (at === -1) break;
          ranges.push([at, at + term.length]);
          from = at + Math.max(1, term.length);
        }
      }
    }

    if (!ranges.length) return [];
    ranges.sort((x, y) => x[0] - y[0] || y[1] - x[1]);
    const merged = [ranges[0].slice()];
    for (let i = 1; i < ranges.length; i++) {
      const cur = ranges[i];
      const top = merged[merged.length - 1];
      if (cur[0] <= top[1]) top[1] = Math.max(top[1], cur[1]);
      else merged.push(cur.slice());
    }
    return merged;
  }

  function rangeStartingAt(ranges, i) {
    for (const r of ranges) {
      if (r[0] === i) return r;
      if (r[0] > i) break;
    }
    return null;
  }

  // [start, end) が保護範囲に少しでも重なるか。
  // 「重なる語は変換しない」ことで、保護範囲の途中に飛び込むのを防ぐ。
  function overlapsRange(ranges, start, end) {
    for (const r of ranges) {
      if (start < r[1] && end > r[0]) return r;
      if (r[0] >= end) break;
    }
    return null;
  }

  /* ------------------------------------------------------------------ *
   * 英語の見た目（大文字小文字）を合わせる
   * ------------------------------------------------------------------ */
  function matchCase(source, target) {
    if (source === source.toUpperCase() && /[A-Z]{2,}/.test(source)) return target.toUpperCase();
    if (/^[A-Z]/.test(source)) return target.charAt(0).toUpperCase() + target.slice(1);
    return target;
  }

  /* ------------------------------------------------------------------ *
   * 変換本体
   * ------------------------------------------------------------------ */
  function convert(text, options) {
    const opts = options || {};
    const protectTerms = opts.protect instanceof Set ? opts.protect : new Set(opts.protect || []);
    const autoProtect = opts.autoProtect !== false;
    const collectOnly = !!opts.collectOnly; // 候補の洗い出しだけ行う（保護を無視）

    const ranges = collectOnly ? [] : collectProtectedRanges(text, protectTerms, autoProtect);
    const segments = [];
    const matches = [];
    let converted = 0;
    let i = 0;

    const pushSeg = (type, str, extra) => {
      if (!str) return;
      const prev = segments[segments.length - 1];
      if (prev && prev.type === type && type === 'plain') prev.text += str;
      else segments.push(Object.assign({ type, text: str }, extra || {}));
    };

    while (i < text.length) {
      // 1. 保護範囲
      if (!collectOnly) {
        const r = rangeStartingAt(ranges, i);
        if (r) {
          pushSeg('protected', text.slice(r[0], r[1]));
          i = r[1];
          continue;
        }
      }

      const ch = text[i];

      // 2. 英単語（単語単位でまとめて判定）
      if (ASCII_WORD.test(ch)) {
        let j = i;
        while (j < text.length && ASCII_WORD_CHAR.test(text[j])) j++;
        const word = text.slice(i, j);
        const blocked = !collectOnly && overlapsRange(ranges, i, j);
        const hit = blocked ? null : INDEX.en.get(word.toLowerCase());
        if (hit) {
          const to = matchCase(word, hit.to);
          matches.push({ from: word, to, tag: hit.tag, lang: 'en' });
          if (!collectOnly) {
            pushSeg('converted', to, { source: word });
            converted++;
          }
        } else if (!collectOnly) {
          pushSeg('plain', word);
        }
        i = j;
        continue;
      }

      // 3. 日本語（最長一致）
      let matched = null;
      const max = Math.min(INDEX.maxJaLen, text.length - i);
      for (let len = max; len >= 1; len--) {
        const slice = text.substr(i, len);
        const hit = INDEX.ja.get(slice);
        if (!hit) continue;
        if (hit.weak) {
          const before = i > 0 ? text[i - 1] : '';
          const after = i + len < text.length ? text[i + len] : '';
          if (hit.kana) {
            // 「はい」＋「い」のように、平仮名が続くなら語の途中とみなす
            if (HIRAGANA.test(after)) continue;
          } else if (KANJI.test(before) || KANJI.test(after)) {
            // 「上」が「上手」「上野」の一部になっている場合
            continue;
          }
        }
        if (!collectOnly && overlapsRange(ranges, i, i + len)) continue; // 保護範囲に食い込む一致は使わない
        matched = { slice, hit, len };
        break;
      }

      if (matched) {
        matches.push({ from: matched.slice, to: matched.hit.to, tag: matched.hit.tag, lang: 'ja' });
        if (!collectOnly) {
          pushSeg('converted', matched.hit.to, { source: matched.slice });
          converted++;
        }
        i += matched.len;
        continue;
      }

      if (!collectOnly) pushSeg('plain', ch);
      i++;
    }

    return {
      text: segments.map((s) => s.text).join(''),
      segments,
      matches,
      convertedCount: converted,
    };
  }

  /**
   * 入力に含まれる「変換されうる語」を洗い出す。
   * 保護対象を事前に選ぶための候補リストになる。
   */
  function analyze(text) {
    const { matches } = convert(text, { collectOnly: true });
    const byTerm = new Map();
    for (const m of matches) {
      const cur = byTerm.get(m.from);
      if (cur) cur.count++;
      else byTerm.set(m.from, { from: m.from, to: m.to, tag: m.tag, lang: m.lang, count: 1 });
    }
    return [...byTerm.values()];
  }

  function stats() {
    return { ja: INDEX.ja.size, en: INDEX.en.size, pairs: Dictionary.entries.length };
  }

  return { convert, analyze, stats, index: INDEX, AUTO_PROTECT_PATTERNS };
});
