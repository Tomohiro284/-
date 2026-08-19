/*!
 * tests/run.js — 変換エンジンのテスト
 * 実行: node tests/run.js
 */
'use strict';

const Converter = require('../src/converter.js');

let passed = 0;
const failures = [];

function eq(label, actual, expected) {
  if (actual === expected) {
    passed++;
  } else {
    failures.push(`${label}\n    期待: ${expected}\n    実際: ${actual}`);
  }
}

function conv(text, protect, options) {
  return Converter.convert(text, Object.assign({ protect: new Set(protect || []) }, options || {})).text;
}

/* ---------------- 基本の置換 ---------------- */
eq('名詞', conv('成功と失敗'), '失敗と成功');
eq('イ形容詞（終止形）', conv('大きい'), '小さい');
eq('イ形容詞（連用形）', conv('大きく開く'), '小さく閉じる');
eq('イ形容詞（過去）', conv('楽しかった'), 'つまらなかった');
eq('イ形容詞（否定）', conv('高くない'), '低くない');
eq('イ形容詞（名詞化）', conv('広さ'), '狭さ');
eq('大きな / 小さな', conv('大きな声'), '小さな声');

/* ---------------- 動詞の活用 ---------------- */
eq('一段→五段（ます形）', conv('増えました'), '減りました');
eq('五段→一段（ます形）', conv('減りません'), '増えません');
eq('五段（て形・音便）', conv('本を買って'), '本を売って');
eq('五段（た形・促音便）', conv('声を出して笑った'), '声を入れて泣いた');
eq('一段（た形）', conv('朝に起きた'), '夜に寝た');
eq('不規則（行く→来る）', conv('学校へ行きます'), '学校へ来ます');
eq('可能形', conv('window を開ける'), 'window を閉める');

/* ---------------- 一文字語の誤爆防止 ---------------- */
eq('熟語の一部は変換しない', conv('上手な上野さん'), '上手な上野さん');
eq('単独なら変換する', conv('上を見る'), '下を見る');
eq('熟語（今日）', conv('今日はいい天気'), '今日は悪い天気');

/* ---------------- 英語 ---------------- */
eq('英単語', conv('a big dog'), 'a small dog');
eq('英語の複数形', conv('two days'), 'two nights');
eq('英語の過去形（子音重ね）', conv('he stopped'), 'he started');
eq('英語の比較級', conv('bigger'), 'smaller');
eq('大文字の維持', conv('Happy'), 'Sad');
eq('全部大文字の維持', conv('BIG'), 'SMALL');
eq('部分一致はしない', conv('bigot'), 'bigot');

/* ---------------- 保護（そのまま残す） ---------------- */
eq('単語を保護', conv('大きい氷と大きい山', ['大きい']), '大きい氷と大きい谷');
eq('保護しなければ変換される', conv('大きい氷'), '小さい氷');
eq('文章を保護', conv('明るい日。大きい氷を買う。', ['大きい氷を買う']), '暗い日。大きい氷を買う。');
eq('保護は変換より優先', conv('新しい仕事', ['新しい']), '新しい仕事');
eq('保護外は変換される', conv('新しくて高い', ['新しくて']), '新しくて低い');
eq('英語を保護（大小無視）', conv('A BIG dog', ['big']), 'A BIG dog');
eq('保護範囲に食い込む語は変換しない', conv('大きい氷', ['い氷']), '大きい氷');

/* ---------------- 自動保護 ---------------- */
eq('URL を保護', conv('明るい https://ex.com/big'), '暗い https://ex.com/big');
eq('コード表記を保護', conv('明るい `big` です'), '暗い `big` です');
eq('ハッシュタグを保護', conv('明るい #big'), '暗い #big');
eq('メールを保護', conv('明るい a@big.com'), '暗い a@big.com');
eq('自動保護を切ると変換される', conv('明るい `big`', [], { autoProtect: false }), '暗い `small`');

/* ---------------- 候補の洗い出し ---------------- */
{
  const cands = Converter.analyze('今日はとても暑いので、大きい氷を買いました。');
  eq('候補の数', cands.length, 4);
  eq('候補の中身', cands.map((c) => `${c.from}→${c.to}`).join(','), 'とても→全然,暑い→寒い,大きい→小さい,買いました→売りました');
  const dup = Converter.analyze('大きい大きい大きい');
  eq('同じ語はまとめて数える', `${dup.length}/${dup[0].count}`, '1/3');
  eq('候補の洗い出しは保護を無視する', Converter.analyze('大きい').length, 1);
}

/* ---------------- セグメント ---------------- */
{
  const r = Converter.convert('大きい氷と暑い日', { protect: new Set(['暑い']) });
  eq('変換した語数', r.convertedCount, 1);
  eq('保護した区間', r.segments.filter((s) => s.type === 'protected').length, 1);
  eq('原文を保持している', r.segments.find((s) => s.type === 'converted').source, '大きい');
}

/* ---------------- 空・記号 ---------------- */
eq('空文字', conv(''), '');
eq('記号のみ', conv('！？＃'), '！？＃');
eq('改行を保つ', conv('大きい\n小さい'), '小さい\n大きい');

/* ---------------- 辞書の健全性 ---------------- */
{
  const stats = Converter.stats();
  const Dictionary = require('../src/dictionary.js');
  eq('辞書が空でない', stats.ja > 1000 && stats.en > 100, true);
  const bad = Dictionary.entries.filter((e) => !e.a || !e.b || e.a === e.b);
  eq('空・自己参照のペアがない', bad.length, 0);
}

/* ---------------- 結果 ---------------- */
console.log(`\n  ${passed} passed, ${failures.length} failed\n`);
for (const f of failures) console.log('  ✗ ' + f + '\n');
process.exit(failures.length ? 1 : 0);
