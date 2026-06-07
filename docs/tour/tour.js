/*
Copyright 2026 icecake0141
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
*/

const translations = {
  en: {
    "nav.workflow": "Workflow",
    "nav.groups": "Groups",
    "nav.lookup": "Lookups",
    "nav.alternatives": "Alternatives",
    "hero.eyebrow": "Parallel ICMP monitoring for terminal-first operators",
    "hero.title": "Watch many destinations fail, recover, and slow down in one CLI.",
    "hero.body":
      "ParaPing turns repeated ping checks into a live terminal cockpit: concurrent targets, compact history, group summaries, ASN context, and reverse DNS labels without leaving the shell.",
    "hero.repo": "View repository",
    "hero.usage": "Read usage guide",
    "workflow.eyebrow": "CLI workflow",
    "workflow.title": "Multiple destinations, one live surface.",
    "workflow.body":
      "Start with command-line targets or a host file, then keep watching the timeline while sorting, filtering, pausing, and changing views interactively.",
    "workflow.caption": "Slow responses and failed checks stay visible while healthy hosts continue updating.",
    "groups.title": "Group the view around how you operate.",
    "groups.body":
      "Use site labels, tags, ASN, or hierarchical keys such as site>tag1 to turn a long host list into a readable operational map.",
    "lookup.title": "Add network context without opening another tool.",
    "lookup.body":
      "Toggle display names between IP, reverse DNS, and aliases. Add ASN labels when route ownership matters during triage.",
    "reliability.eyebrow": "Independent updates",
    "reliability.title": "One troubled target should not freeze the rest of the story.",
    "reliability.body":
      "ParaPing is designed so each destination can keep producing results independently. Slow, failing, or pending checks do not hide what is happening elsewhere.",
    "heritage.title": "A small-tool lineage.",
    "heritage.body":
      "ParaPing is inspired by mping, an old C utility that circulated on personal websites roughly two decades ago. The goal is the same spirit: quick multi-target visibility from the terminal.",
    "deadman.title": "Also consider deadman.",
    "deadman.body":
      "deadman is a lightweight, portable, curses-based host status checker using ping. For production environments where simple handling and portability matter, it is well worth evaluating.",
    "deadman.link": "Open deadman on GitHub",
    "footer.copy": "ParaPing User Experience Tour",
    "footer.repo": "GitHub",
  },
  ja: {
    "nav.workflow": "ワークフロー",
    "nav.groups": "グループ",
    "nav.lookup": "ルックアップ",
    "nav.alternatives": "代替ツール",
    "hero.eyebrow": "ターミナルを主戦場にする運用者向けの並列ICMP監視",
    "hero.title": "複数宛先の失敗、復旧、遅延を1つのCLIで追う。",
    "hero.body":
      "ParaPing は、繰り返しの ping 確認をライブなターミナル画面にまとめます。複数宛先の並列監視、コンパクトな履歴、グループサマリー、ASN、DNS逆引きラベルをシェルの中で確認できます。",
    "hero.repo": "リポジトリを見る",
    "hero.usage": "使い方を見る",
    "workflow.eyebrow": "CLIワークフロー",
    "workflow.title": "複数の宛先を、1つのライブ画面で。",
    "workflow.body":
      "コマンドライン引数またはホストファイルから開始し、タイムラインを見ながらソート、フィルタ、一時停止、表示切替を対話的に操作できます。",
    "workflow.caption": "遅延や失敗は見えるまま、正常なホストの更新は継続します。",
    "groups.title": "運用の見方に合わせてグループ化。",
    "groups.body":
      "site、tag、ASN、site>tag1 のような階層キーを使い、長いホスト一覧を読みやすい運用マップに変えられます。",
    "lookup.title": "別ツールを開かずにネットワーク文脈を追加。",
    "lookup.body":
      "表示名は IP、DNS逆引き、alias で切り替え可能です。経路の所有者が重要な調査では ASN ラベルも表示できます。",
    "reliability.eyebrow": "独立した更新",
    "reliability.title": "1つの宛先の問題で、全体の状況を止めない。",
    "reliability.body":
      "ParaPing は各宛先が独立して結果を出し続けられるよう設計されています。遅い、失敗している、保留中のチェックがあっても、他の宛先の状況は隠れません。",
    "heritage.title": "小さなツールの系譜。",
    "heritage.body":
      "ParaPing は、約20年前に個人サイトなどで流通していた古い C 製ユーティリティ mping から着想を得ています。ターミナルから素早く複数宛先を見渡す、という精神を引き継いでいます。",
    "deadman.title": "deadman も検討してください。",
    "deadman.body":
      "deadman は ping を使った軽量でポータブルな curses ベースのホスト状態確認ツールです。シンプルな取り回しと移植性が重要な本番環境では、評価する価値があります。",
    "deadman.link": "deadman を GitHub で開く",
    "footer.copy": "ParaPing ユーザエクスペリエンスツアー",
    "footer.repo": "GitHub",
  },
};

function applyLanguage(lang) {
  const dictionary = translations[lang] || translations.en;
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.getAttribute("data-i18n");
    if (dictionary[key]) {
      node.textContent = dictionary[key];
    }
  });
  document.querySelectorAll("[data-lang-button]").forEach((button) => {
    button.classList.toggle("is-active", button.getAttribute("data-lang-button") === lang);
  });
  window.localStorage.setItem("paraping-tour-language", lang);
}

const initialLanguage = window.localStorage.getItem("paraping-tour-language") || "en";
applyLanguage(initialLanguage);

document.querySelectorAll("[data-lang-button]").forEach((button) => {
  button.addEventListener("click", () => {
    applyLanguage(button.getAttribute("data-lang-button"));
  });
});
