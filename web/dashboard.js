'use strict';

const listEl = document.getElementById('run-list');
const countEl = document.getElementById('run-count');
const contentEl = document.getElementById('content');
const placeholderEl = document.getElementById('placeholder');
const metaEl = document.getElementById('meta');
const metricsEl = document.getElementById('metrics');
const coverageEl = document.getElementById('coverage');
const issuesEl = document.getElementById('issues');
const navEl = document.getElementById('section-nav');
const reportEl = document.getElementById('report');

const STATUS = {
  pass: {label: '正常', className: 'pass'},
  partial: {label: '需复核', className: 'partial'},
  fail: {label: '异常', className: 'fail'},
  unknown: {label: '待检查', className: 'unknown'},
};
const AGENT_LABELS = {
  supervisor: '调度', data_analysis: '数据分析', ads_diagnosis: '投放诊断',
  content_review: '内容审核', strategy: '策略',
};
const SECTION_STYLE = {
  '账户总体': {className: 'overview', icon: 'overview'},
  '今日重点': {className: 'overview', icon: 'overview'},
  '待处理计划': {className: 'plans', icon: 'plans'},
  '数据发现': {className: 'plans', icon: 'plans'},
  '问题更可能在哪': {className: 'diagnosis', icon: 'diagnosis'},
  '投放诊断': {className: 'diagnosis', icon: 'diagnosis'},
  '内容审核': {className: 'diagnosis', icon: 'diagnosis'},
  '今天具体做什么': {className: 'actions', icon: 'actions'},
  '策略建议': {className: 'actions', icon: 'actions'},
  '下一次看什么': {className: 'followup', icon: 'followup'},
  '仍需观察': {className: 'followup', icon: 'followup'},
  '证据不足项': {className: 'followup', icon: 'issues'},
  '分析路径': {className: 'default', icon: 'overview'},
};
const SECTION_DISPLAY = {
  '今日重点': '账户结论',
  '策略建议': '今天具体做什么',
  '仍需观察': '下一次看什么',
  '证据不足项': '证据缺口',
  '分析路径': '分析过程',
};

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

function icon(name) {
  const paths = {
    overview: '<path d="M4 5h16M4 12h10M4 19h13"/>',
    plans: '<path d="M9 6h11M9 12h11M9 18h11"/><path d="m4 6 .5.5L6 5m-2 7 .5.5L6 11m-2 7 .5.5L6 17"/>',
    diagnosis: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4M11 8v3l2 2"/>',
    actions: '<path d="M5 12l4 4L19 6"/>',
    followup: '<path d="M12 8v5l3 2"/><circle cx="12" cy="12" r="9"/>',
    calls: '<path d="M8 9h8M8 13h5"/><path d="M5 4h14v14H9l-4 3z"/>',
    agents: '<circle cx="9" cy="8" r="3"/><path d="M3 19c0-3 2-5 6-5s6 2 6 5M16 7h5M18.5 4.5v5"/>',
    issues: '<path d="M12 3 2 21h20L12 3zM12 9v5M12 18h.01"/>',
    status: '<path d="M12 3v18M3 12h18"/>',
    spend: '<path d="M12 3v18M16 7.5c0-1.4-1.8-2.5-4-2.5S8 6.1 8 7.5 9.8 10 12 10s4 1.1 4 2.5S14.2 15 12 15s-4-1.1-4-2.5"/>',
    leads: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M19 8v6M16 11h6"/>',
    cpl: '<circle cx="12" cy="12" r="8"/><path d="M9 12h6M12 9v6"/>',
    trend: '<path d="m4 16 5-5 4 3 7-8"/><path d="M15 6h5v5"/>',
  };
  return `<svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.overview}</svg>`;
}

function inline(text) {
  return esc(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}

function renderMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  const output = [];
  let index = 0;
  let paragraph = [];
  const flush = () => {
    if (paragraph.length) {
      output.push('<p>' + paragraph.map(inline).join('<br>') + '</p>');
      paragraph = [];
    }
  };
  while (index < lines.length) {
    const line = lines[index];
    if (/^\s*$/.test(line)) { flush(); index++; continue; }
    if (/^```/.test(line)) {
      flush();
      const block = [];
      index++;
      while (index < lines.length && !/^```/.test(lines[index])) block.push(lines[index++]);
      index++;
      output.push('<pre><code>' + esc(block.join('\n')) + '</code></pre>');
      continue;
    }
    if (line.trim().startsWith('|') && index + 1 < lines.length &&
        /^[\s|:\-]+$/.test(lines[index + 1]) && lines[index + 1].includes('-')) {
      flush();
      const header = line.trim().replace(/^\||\|$/g, '').split('|').map(cell => inline(cell.trim()));
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].trim().startsWith('|')) {
        rows.push(lines[index].trim().replace(/^\||\|$/g, '').split('|').map(cell => inline(cell.trim())));
        index++;
      }
      output.push('<div class="table-wrap"><table><thead><tr>' + header.map(cell => `<th>${cell}</th>`).join('') +
        '</tr></thead><tbody>' + rows.map(row => '<tr>' + row.map(cell => `<td>${cell}</td>`).join('') + '</tr>').join('') +
        '</tbody></table></div>');
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flush();
      const level = Math.min(heading[1].length + 2, 6);
      output.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      index++;
      continue;
    }
    const quote = line.match(/^>\s?(.*)$/);
    if (quote) { flush(); output.push(`<blockquote>${inline(quote[1])}</blockquote>`); index++; continue; }
    const unordered = line.match(/^\s*[-*+]\s+(.*)$/);
    if (unordered) {
      flush();
      output.push('<ul>');
      while (index < lines.length) {
        const match = lines[index].match(/^\s*[-*+]\s+(.*)$/);
        if (!match) break;
        output.push(`<li>${inline(match[1])}</li>`);
        index++;
      }
      output.push('</ul>');
      continue;
    }
    const ordered = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ordered) {
      flush();
      output.push('<ol>');
      while (index < lines.length) {
        const match = lines[index].match(/^\s*\d+\.\s+(.*)$/);
        if (!match) break;
        output.push(`<li>${inline(match[1])}</li>`);
        index++;
      }
      output.push('</ol>');
      continue;
    }
    paragraph.push(line);
    index++;
  }
  flush();
  return output.join('\n');
}

function statusBadge(status) {
  const definition = STATUS[status] || STATUS.unknown;
  return `<span class="status-badge ${definition.className}"><span class="status-dot" aria-hidden="true"></span>${definition.label}</span>`;
}

function parseReport(markdown) {
  const sections = [];
  let current = null;
  markdown.split(/\r?\n/).forEach(line => {
    const match = line.trim().match(/^【(.+)】$/);
    if (match) {
      current = {title: match[1], lines: []};
      sections.push(current);
    } else if (current) current.lines.push(line);
  });
  return sections;
}

function compactLongList(html, visibleCount = 4) {
  const template = document.createElement('template');
  template.innerHTML = html;
  const list = template.content.querySelector('ul, ol');
  if (!list || list.children.length <= visibleCount) return html;
  const hiddenItems = Array.from(list.children).slice(visibleCount);
  const extraList = document.createElement(list.tagName.toLowerCase());
  hiddenItems.forEach(item => extraList.appendChild(item));
  const details = document.createElement('details');
  details.className = 'report-more';
  const summary = document.createElement('summary');
  summary.textContent = `展开其余 ${hiddenItems.length} 项`;
  details.append(summary, extraList);
  list.after(details);
  return template.innerHTML;
}

function compactLongParagraphs(html, visibleChars = 150) {
  const template = document.createElement('template');
  template.innerHTML = html;
  template.content.querySelectorAll('p').forEach(paragraph => {
    const fullText = paragraph.textContent.trim().replace(/\s+/g, ' ');
    if (fullText.length <= visibleChars) return;
    let cutoff = visibleChars;
    const nextSentence = fullText.slice(visibleChars, visibleChars + 60).match(/[。！？；]/);
    if (nextSentence) cutoff += nextSentence.index + 1;
    else {
      const naturalBreak = fullText.slice(0, visibleChars).lastIndexOf('，');
      if (naturalBreak > visibleChars * 0.65) cutoff = naturalBreak + 1;
    }
    const summary = document.createElement('p');
    summary.className = 'report-summary';
    summary.textContent = fullText.slice(0, cutoff).trim() + '\u2026';
    const details = document.createElement('details');
    details.className = 'report-details';
    const detailsSummary = document.createElement('summary');
    detailsSummary.textContent = '\u5c55\u5f00\u5b8c\u6574\u4f9d\u636e';
    details.append(detailsSummary, paragraph.cloneNode(true));
    paragraph.replaceWith(summary, details);
  });
  return template.innerHTML;
}

function renderReport(markdown) {
  const sections = parseReport(markdown);
  if (!sections.length) {
    navEl.innerHTML = '';
    reportEl.innerHTML = `<article class="report-card overview"><div class="report-body">${compactLongParagraphs(renderMarkdown(markdown))}</div></article>`;
    return;
  }
  navEl.innerHTML = sections.map((section, index) =>
    `<a href="#section-${index}">${esc(SECTION_DISPLAY[section.title] || section.title)}</a>`).join('');
  reportEl.innerHTML = sections.map((section, index) => {
    const style = SECTION_STYLE[section.title] || {className: 'default', icon: 'overview'};
    const markdownBody = section.lines.join('\n').trim();
    const itemCount = (markdownBody.match(/^\s*[-*+]\s+/gm) || []).length;
    const count = itemCount ? `<span class="section-count">${itemCount} 项</span>` : '';
    return `<article id="section-${index}" class="report-card ${style.className}">
      <header class="report-card-header"><span class="section-icon">${icon(style.icon)}</span>
        <h2>${esc(SECTION_DISPLAY[section.title] || section.title)}</h2>${count}</header>
      <div class="report-body">${compactLongParagraphs(compactLongList(renderMarkdown(markdownBody))) || '<p class="empty-copy">暂无内容</p>'}</div>
    </article>`;
  }).join('');
}

function renderList(runs) {
  listEl.innerHTML = '';
  countEl.textContent = `${runs.length} 次`;
  if (!runs.length) {
    listEl.innerHTML = '<div class="empty-state"><strong>暂无运行</strong><span>完成一次诊断后会显示在这里。</span></div>';
    return;
  }
  runs.forEach(run => {
    const button = document.createElement('button');
    button.className = 'run-item';
    button.dataset.id = run.id;
    const date = run.report_date || (run.id.match(/\d{4}-\d{2}-\d{2}/) || [''])[0];
    const state = STATUS[run.status] || STATUS.unknown;
    button.innerHTML = `<span class="run-state ${state.className}" aria-hidden="true"></span>
      <span class="run-copy"><strong>${esc(date || '未知日期')}</strong>
      <small>${esc(run.model || '未记录模型')} · ${run.model_calls ?? '?'} 次调用</small></span>
      <span class="run-status">${state.label}</span>`;
    button.onclick = () => selectRun(run, button);
    listEl.appendChild(button);
  });
  selectRun(runs[0]);
}

function metricCard(label, value, note, iconName, state = '') {
  return `<article class="metric-card ${state}"><div class="metric-label">${icon(iconName)}<span>${esc(label)}</span></div>
    <strong class="metric-value">${esc(value)}</strong><span class="metric-note">${esc(note)}</span></article>`;
}

function numberValue(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function formatNumber(value, digits = 0) {
  const number = numberValue(value);
  if (number === null) return '\u2014';
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(number);
}

function formatCurrency(value) {
  const number = numberValue(value);
  return number === null ? '\u2014' : `\u00a5${formatNumber(number, 2)}`;
}

function formatRate(value) {
  const number = numberValue(value);
  if (number === null) return '\u2014';
  const percent = number * 100;
  return `${formatNumber(percent, Number.isInteger(percent) ? 0 : 1)}%`;
}

function reportMetric(report, names, isRate = false) {
  for (const name of names) {
    const match = report.match(new RegExp(`(?:${name})\\s*(?:[:：]|\\u4e3a)?\\s*([\\d,.]+)\\s*(%)?`, 'i'));
    if (!match) continue;
    const number = numberValue(match[1].replace(/,/g, ''));
    if (number === null) continue;
    if (!isRate) return number;
    return match[2] || number > 1 ? number / 100 : number;
  }
  return null;
}

function metricsFromReport(report) {
  const metrics = {
    spend: reportMetric(report, ['\\u6d88\\u8017', '\\u82b1\\u8d39', 'spend']),
    impressions: reportMetric(report, ['\\u5c55\\u793a', '\\u66dd\\u5149', 'impressions']),
    clicks: reportMetric(report, ['\\u70b9\\u51fb', 'clicks']),
    leads: reportMetric(report, ['\\u7ebf\\u7d22', '\\u7559\\u8d44', 'leads']),
    cpl: reportMetric(report, ['CPL']),
    ctr: reportMetric(report, ['CTR'], true),
    cvr: reportMetric(report, ['CVR'], true),
  };
  if (metrics.spend === null) return null;
  const range = report.match(/(\d+d)\s*[（(]\s*(\d{4}-\d{2}-\d{2}\s*[~～]\s*\d{4}-\d{2}-\d{2})/i);
  return {
    metrics,
    time_range: range ? `${range[1]} ${range[2]}` : '\u65e5\u62a5\u539f\u6587\u63d0\u53d6',
  };
}

function businessMetricCards(summary) {
  const metrics = summary && summary.metrics;
  if (!metrics || typeof metrics !== 'object' || numberValue(metrics.spend) === null) return null;
  const range = summary.time_range || '\u672c\u6b21\u5206\u6790\u7a97\u53e3';
  return [
    metricCard('\u6295\u653e\u6d88\u8017', formatCurrency(metrics.spend), range, 'spend'),
    metricCard('\u7ebf\u7d22', formatNumber(metrics.leads), '\u5e73\u53f0\u7559\u8d44', 'leads'),
    metricCard('CPL', formatCurrency(metrics.cpl), '\u7ebf\u7d22\u83b7\u53d6\u6210\u672c', 'cpl'),
    metricCard('CTR', formatRate(metrics.ctr), `\u70b9\u51fb ${formatNumber(metrics.clicks)}`, 'trend'),
  ].join('');
}

async function selectRun(run, button) {
  const id = typeof run === 'string' ? run : run.id;
  document.querySelectorAll('.run-item').forEach(element => element.classList.remove('active'));
  const selected = button || document.querySelector(`.run-item[data-id="${CSS.escape(id)}"]`);
  if (selected) selected.classList.add('active');
  reportEl.setAttribute('aria-busy', 'true');
  try {
    const [reportResponse, reviewResponse] = await Promise.all([
      fetch('/api/run/' + encodeURIComponent(id) + '/report'),
      fetch('/api/run/' + encodeURIComponent(id) + '/review'),
    ]);
    if (!reportResponse.ok) throw new Error('日报正文读取失败');
    const report = await reportResponse.text();
    const review = reviewResponse.ok ? await reviewResponse.json() : {};
    let summary = metricsFromReport(report);
    if (!summary) {
      const summaryResponse = await fetch('/api/run/' + encodeURIComponent(id) + '/summary');
      summary = summaryResponse.ok ? await summaryResponse.json() : {};
    }
    const status = review.operational_status || review.structural_status || 'unknown';
    const state = STATUS[status] || STATUS.unknown;
    const coverage = review.agent_coverage || {};
    const agentEntries = Object.entries(coverage);
    const agentCount = agentEntries.filter(([, covered]) => covered).length;
    const issueCount = (review.issues || []).length + (review.bounded_limit_errors || []).length;
    const date = (typeof run === 'object' && run.report_date) || (id.match(/\d{4}-\d{2}-\d{2}/) || [''])[0];
    const model = (typeof run === 'object' && run.model) || '未记录模型';
    placeholderEl.hidden = true;
    contentEl.hidden = false;
    metaEl.innerHTML = `<div class="report-heading"><div><p class="eyebrow">投放诊断日报</p>
      <h1>${esc(date || '未知日期')}</h1><p class="report-subtitle">${esc(model)} · ${esc(id)}</p></div>
      ${statusBadge(status)}</div>`;
    metricsEl.innerHTML = businessMetricCards(summary) || [
      metricCard('运行状态', state.label, status === 'pass' ? '本次结构与运行正常' : '查看下方提示后再决策', 'status', state.className),
      metricCard('模型调用', review.model_calls ?? '?', '本次分析调用次数', 'calls'),
      metricCard('Agent 覆盖', `${agentCount} / ${agentEntries.length || 5}`, '完成职责的 Agent', 'agents'),
      metricCard('待关注', issueCount, issueCount ? '存在需人工复核的问题' : '未记录结构问题', 'issues', issueCount ? 'partial' : 'pass'),
    ].join('');
    coverageEl.innerHTML = `<div class="coverage-heading"><div><p class="panel-kicker">协作链路</p><h2>Agent 覆盖</h2></div>
      <span>${agentCount} / ${agentEntries.length || 5} 已完成</span></div>
      <div class="agent-track">${agentEntries.map(([name, covered]) => `<div class="agent-step ${covered ? 'covered' : 'missing'}">
        <span class="agent-marker" aria-hidden="true"></span><strong>${esc(AGENT_LABELS[name] || name)}</strong>
        <small>${covered ? '已执行' : '未执行'}</small></div>`).join('')}</div>`;
    const issues = [...(review.issues || []), ...(review.bounded_limit_errors || [])];
    issuesEl.innerHTML = issues.length ? `<section class="notice-panel"><div class="notice-icon">${icon('issues')}</div>
      <div><h2>运行提示</h2><ul>${issues.map(issue => `<li>${esc(issue)}</li>`).join('')}</ul></div></section>` : '';
    renderReport(report);
  } catch (error) {
    placeholderEl.hidden = false;
    contentEl.hidden = true;
    placeholderEl.innerHTML = `<strong>日报读取失败</strong><span>${esc(error.message)}</span>`;
  } finally {
    reportEl.removeAttribute('aria-busy');
  }
}

async function load() {
  try {
    const response = await fetch('/api/runs');
    if (!response.ok) throw new Error('运行列表读取失败');
    renderList(await response.json());
  } catch (error) {
    listEl.innerHTML = `<div class="empty-state error"><strong>加载失败</strong><span>${esc(error.message)}</span></div>`;
    placeholderEl.innerHTML = '<strong>无法连接本地服务</strong><span>请重新打开投放诊断工作台。</span>';
  }
}

load();
