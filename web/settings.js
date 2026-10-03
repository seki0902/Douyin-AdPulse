'use strict';

const form = document.getElementById('model-form');
const fields = document.getElementById('model-fields');
const provider = document.getElementById('provider');
const model = document.getElementById('model');
const key = document.getElementById('api-key');
const message = document.getElementById('form-message');
const configStatus = document.getElementById('config-status');
const keyHelp = document.getElementById('key-help');
let token = '';
let savedProvider = '';
let hasSavedKey = false;
let settingsAvailable = true;

function showMessage(text, status) {
  message.textContent = text;
  message.className = 'form-message ' + status;
  message.hidden = false;
}

function updateKeyHint() {
  const retained = hasSavedKey && provider.value === savedProvider;
  key.placeholder = retained ? '已保存；留空保留原 Key' : '粘贴 API Key';
  keyHelp.textContent = retained ? '已配置此服务商的 Key。填写新 Key 可替换，留空则保留。' : 'Key 仅保存到本机，不会显示在日报中。';
}

function updateSavedState(value) {
  settingsAvailable = value.settings_available !== false;
  savedProvider = value.provider;
  hasSavedKey = value.key_configured;
  configStatus.textContent = settingsAvailable ? (hasSavedKey ? '已有本地配置' : '待配置') : '需要本地 Agent';
  document.getElementById('environment-note').hidden = !value.environment_override;
  updateKeyHint();
}

async function send(path, button) {
  if (!form.reportValidity()) return;
  const original = button.textContent;
  button.textContent = path.endsWith('test') ? '正在测试…' : '正在保存…';
  fields.disabled = true;
  form.setAttribute('aria-busy', 'true');
  message.hidden = true;
  try {
    const response = await fetch(path, {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Local-Token': token},
      body: JSON.stringify({provider: provider.value, model: model.value.trim(), api_key: key.value.trim()}),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || '请求失败，请重试。');
    if (path.endsWith('save')) {
      key.value = '';
      updateSavedState(result);
      showMessage('已保存。日报运行将使用此配置。', 'success');
    } else {
      showMessage(result.message, result.status === 'pass' ? 'success' : 'error');
    }
  } catch (error) {
    showMessage(error.message || '无法连接本地服务，请重新打开工作台。', 'error');
  } finally {
    fields.disabled = false;
    form.setAttribute('aria-busy', 'false');
    button.textContent = original;
  }
}

provider.addEventListener('change', () => {
  key.value = '';
  updateKeyHint();
  message.hidden = true;
});
form.addEventListener('submit', event => {
  event.preventDefault();
  send('/api/settings/save', document.getElementById('save-button'));
});
document.getElementById('test-button').addEventListener('click', event => send('/api/settings/test', event.currentTarget));

(async () => {
  try {
    const response = await fetch('/api/settings');
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || '无法读取配置。');
    token = result.token;
    provider.value = result.provider;
    model.value = result.model;
    updateSavedState(result);
    fields.disabled = !settingsAvailable;
    if (!settingsAvailable) showMessage(result.message || '模型设置需要本地 Agent 项目。', 'error');
  } catch (error) {
    configStatus.textContent = '读取失败';
    showMessage(error.message, 'error');
  } finally {
    form.setAttribute('aria-busy', 'false');
  }
})();
