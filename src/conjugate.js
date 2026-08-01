/*!
 * conjugate.js — 日本語の活用形を機械的に展開する
 *
 * 対義語辞書には終止形しか登録していないので、
 * 「大きかった」「増えました」のような活用形も変換できるように、
 * 語ごとに活用形テーブルを生成して対応づける。
 *
 * A の活用形テーブルと B の活用形テーブルを同じキーで突き合わせるので、
 * 「増える(一段)」→「減る(五段)」のように活用の種類が違っても対応できる。
 */
(function (root, factory) {
  const value = factory();
  if (typeof module === 'object' && module.exports) module.exports = value;
  else root.AntonymConjugate = value;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // 五段活用の行（う → わ/い/え/お）
  const GODAN_ROW = {
    う: { a: 'わ', i: 'い', e: 'え', o: 'お' },
    く: { a: 'か', i: 'き', e: 'け', o: 'こ' },
    ぐ: { a: 'が', i: 'ぎ', e: 'げ', o: 'ご' },
    す: { a: 'さ', i: 'し', e: 'せ', o: 'そ' },
    つ: { a: 'た', i: 'ち', e: 'て', o: 'と' },
    ぬ: { a: 'な', i: 'に', e: 'ね', o: 'の' },
    ぶ: { a: 'ば', i: 'び', e: 'べ', o: 'ぼ' },
    む: { a: 'ま', i: 'み', e: 'め', o: 'も' },
    る: { a: 'ら', i: 'り', e: 'れ', o: 'ろ' },
  };

  // 音便（て形）
  const GODAN_TE = {
    う: 'って', つ: 'って', る: 'って',
    く: 'いて', ぐ: 'いで',
    す: 'して',
    ぬ: 'んで', ぶ: 'んで', む: 'んで',
  };

  // 促音便の例外（行く → 行って）
  const GODAN_TE_EXCEPTION = { 行く: 'って', いく: 'って' };

  function teToTa(te) {
    const last = te.slice(-1);
    return te.slice(0, -1) + (last === 'で' ? 'だ' : 'た');
  }

  /** 一段動詞（食べる型）の活用形 */
  function ichidanForms(word) {
    const stem = word.slice(0, -1); // 「る」を落とす
    return {
      dict: word,
      masu: stem + 'ます',
      masen: stem + 'ません',
      mashita: stem + 'ました',
      masendeshita: stem + 'ませんでした',
      nai: stem + 'ない',
      nakatta: stem + 'なかった',
      te: stem + 'て',
      ta: stem + 'た',
      tara: stem + 'たら',
      tari: stem + 'たり',
      eba: stem + 'れば',
      you: stem + 'よう',
      tai: stem + 'たい',
      teiru: stem + 'ている',
      teru: stem + 'てる',
      teita: stem + 'ていた',
      temasu: stem + 'ています',
      potential: stem + 'られる',
      causative: stem + 'させる',
      imperative: stem + 'ろ',
      stemOnly: stem,
    };
  }

  /** 五段動詞（書く型）の活用形 */
  function godanForms(word) {
    const last = word.slice(-1);
    const row = GODAN_ROW[last];
    if (!row) return { dict: word };
    const stem = word.slice(0, -1);
    const te = stem + (GODAN_TE_EXCEPTION[word] || GODAN_TE[last]);
    const ta = teToTa(te);
    return {
      dict: word,
      masu: stem + row.i + 'ます',
      masen: stem + row.i + 'ません',
      mashita: stem + row.i + 'ました',
      masendeshita: stem + row.i + 'ませんでした',
      nai: stem + row.a + 'ない',
      nakatta: stem + row.a + 'なかった',
      te: te,
      ta: ta,
      tara: ta + 'ら',
      tari: ta + 'り',
      eba: stem + row.e + 'ば',
      you: stem + row.o + 'う',
      tai: stem + row.i + 'たい',
      teiru: te + 'いる',
      teru: te + 'る',
      teita: te + 'いた',
      temasu: te + 'います',
      potential: stem + row.e + 'る',
      causative: stem + row.a + 'せる',
      imperative: stem + row.e,
      stemOnly: stem + row.i,
    };
  }

  /** イ形容詞（大きい型）の活用形 */
  function iAdjForms(word) {
    const stem = word.slice(0, -1); // 「い」を落とす
    return {
      dict: word,
      ku: stem + 'く',
      kute: stem + 'くて',
      katta: stem + 'かった',
      kunai: stem + 'くない',
      kunakatta: stem + 'くなかった',
      kereba: stem + 'ければ',
      sa: stem + 'さ',
      sugi: stem + 'すぎ',
      sou: stem + 'そう',
      karou: stem + 'かろう',
    };
  }

  const isIAdj = (w) => typeof w === 'string' && w.length >= 2 && w.endsWith('い');

  function verbForms(word, type) {
    if (type === 'v1') return ichidanForms(word);
    if (type === 'v5') return godanForms(word);
    return { dict: word };
  }

  // 他の見出し語と衝突しやすい活用形（索引には後回しで登録する）
  const DERIVED_FORMS = new Set(['potential', 'causative', 'imperative']);

  /**
   * 対義語ペアから「活用形 → 活用形」の対応リストを作る。
   * 戻り値: [[変換元, 変換先, 派生形か], ...]（終止形が先頭）
   */
  function expandPair(entry) {
    const out = [];
    const push = (from, to, derived) => {
      if (from && to && from !== to) out.push([from, to, !!derived]);
    };

    if (entry.type === 'i') {
      // 両方がイ形容詞のときだけ活用形を展開する。
      // 「忙しい → 暇な」のように品詞がずれるペアは終止形のみ。
      if (isIAdj(entry.a) && isIAdj(entry.b)) {
        const fa = iAdjForms(entry.a);
        const fb = iAdjForms(entry.b);
        for (const key of Object.keys(fa)) push(fa[key], fb[key]);
      } else {
        push(entry.a, entry.b);
      }
      return out;
    }

    if (entry.type === 'v') {
      const fa = verbForms(entry.a, entry.typeA);
      const fb = verbForms(entry.b, entry.typeB);
      for (const key of Object.keys(fa)) {
        if (key === 'stemOnly') continue; // 連用形単独は誤爆しやすいので使わない
        // 可能形・使役形は別の動詞と同じ形になることがある
        // （開く の可能形「開ける」＝ 動詞「開ける」）。
        // 索引には後から登録して、辞書の見出し語を優先させる。
        const derived = DERIVED_FORMS.has(key);
        push(fa[key], fb[key], derived);
      }
      return out;
    }

    push(entry.a, entry.b);
    return out;
  }

  /* ---------------- 英語 ---------------- */

  function pluralize(word) {
    if (/(s|sh|ch|x|z)$/.test(word)) return word + 'es';
    if (/[^aeiou]y$/.test(word)) return word.slice(0, -1) + 'ies';
    return word + 's';
  }

  function thirdPerson(word) {
    return pluralize(word);
  }

  // stop → stopp+ed のように語尾の子音を重ねる（1音節の CVC 語）
  function doubleFinal(word) {
    return /^[^aeiou]*[aeiou][bdgklmnprstvz]$/.test(word) ? word + word.slice(-1) : word;
  }

  function pastTense(word) {
    if (word.endsWith('e')) return word + 'd';
    const d = doubleFinal(word);
    if (d !== word) return d + 'ed';
    if (/[^aeiou]y$/.test(word)) return word.slice(0, -1) + 'ied';
    return word + 'ed';
  }

  function progressive(word) {
    if (word.endsWith('ie')) return word.slice(0, -2) + 'ying';
    if (word.endsWith('e') && !word.endsWith('ee')) return word.slice(0, -1) + 'ing';
    const d = doubleFinal(word);
    if (d !== word) return d + 'ing';
    return word + 'ing';
  }

  function comparative(word) {
    if (word.length > 7) return null; // longer / more ... は生成しない
    if (word.endsWith('e')) return { er: word + 'r', est: word + 'st' };
    if (/[^aeiou]y$/.test(word)) return { er: word.slice(0, -1) + 'ier', est: word.slice(0, -1) + 'iest' };
    if (/[aeiou][bdgmnptk]$/.test(word)) {
      const d = word + word.slice(-1);
      return { er: d + 'er', est: d + 'est' };
    }
    return { er: word + 'er', est: word + 'est' };
  }

  function expandEnglish(entry) {
    const out = [[entry.a, entry.b]];
    const opt = entry.opt || {};
    const both = (fn) => {
      const x = fn(entry.a);
      const y = fn(entry.b);
      if (x && y && x !== y) out.push([x, y]);
    };
    if (opt.pl) both(pluralize);
    if (opt.v) {
      both(thirdPerson);
      both(pastTense);
      both(progressive);
    }
    if (opt.adj) {
      const ca = comparative(entry.a);
      const cb = comparative(entry.b);
      if (ca && cb) {
        out.push([ca.er, cb.er]);
        out.push([ca.est, cb.est]);
      }
    }
    return out.filter(([x, y]) => x && y && x !== y);
  }

  return { expandPair, expandEnglish, ichidanForms, godanForms, iAdjForms };
});
