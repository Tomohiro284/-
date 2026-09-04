/*!
 * hero.js — 冒頭のデモ
 *
 * 実際の変換エンジンで例文を変換し、変換された語だけを
 * 原文 ⇄ 対義語 で入れ替わりつづける形にして見せる。
 * （見せかけのアニメーションではなく、本物の出力を使っている）
 */
(function () {
  'use strict';

  const host = document.getElementById('hero-demo');
  if (!host || !window.AntonymConverter) return;

  const SENTENCE = '今日はとても暑いので、大きい氷をたくさん買いました。';
  const result = window.AntonymConverter.convert(SENTENCE, { protect: new Set() });

  // JS なしのときに見える初期テキストを消してから組み立てる
  host.textContent = '';

  let i = 0;
  for (const seg of result.segments) {
    if (seg.type === 'converted') {
      const word = document.createElement('span');
      word.className = 'flip-word';
      word.style.setProperty('--i', i++);

      const a = document.createElement('span');
      a.className = 'f-a';
      a.textContent = seg.source;

      const b = document.createElement('span');
      b.className = 'f-b';
      b.textContent = seg.text;

      // 幅は長いほうに合わせる（入れ替わりで行が揺れないように）
      word.append(a, b);
      host.appendChild(word);
    } else {
      host.appendChild(document.createTextNode(seg.text));
    }
  }
})();
