/*!
 * ads.js — 広告枠の描画
 *
 * HTML 側には枠だけ置いておく:
 *   <div class="ad-slot" data-ad-slot="content"></div>
 *
 * site-config.js の adsense.client が空のあいだは何も表示しない。
 * （枠だけが残って余白が空くことがないよう、要素ごと隠す）
 */
(function () {
  'use strict';

  const config = (window.SITE_CONFIG && window.SITE_CONFIG.adsense) || {};
  const client = (config.client || '').trim();
  const slots = config.slots || {};

  const containers = document.querySelectorAll('.ad-slot[data-ad-slot]');
  if (!containers.length) return;

  // 未設定なら枠を消して終わり
  if (!/^ca-pub-\d+$/.test(client)) {
    for (const el of containers) el.remove();
    return;
  }

  // AdSense のスクリプトは1回だけ読み込む
  const SRC = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + encodeURIComponent(client);
  if (!document.querySelector('script[data-adsense]')) {
    const script = document.createElement('script');
    script.async = true;
    script.src = SRC;
    script.crossOrigin = 'anonymous';
    script.setAttribute('data-adsense', '');
    document.head.appendChild(script);
  }

  for (const el of containers) {
    const slotId = (slots[el.dataset.adSlot] || '').trim();
    if (!/^\d+$/.test(slotId)) {
      el.remove(); // このユニットだけ未設定
      continue;
    }

    const label = document.createElement('span');
    label.className = 'ad-label';
    label.textContent = 'スポンサーリンク';
    el.appendChild(label);

    const ins = document.createElement('ins');
    ins.className = 'adsbygoogle';
    ins.style.display = 'block';
    ins.setAttribute('data-ad-client', client);
    ins.setAttribute('data-ad-slot', slotId);
    ins.setAttribute('data-ad-format', 'auto');
    ins.setAttribute('data-full-width-responsive', 'true');
    el.appendChild(ins);

    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      /* 広告ブロッカーなどで失敗しても本体の動作には影響させない */
    }
  }
})();
