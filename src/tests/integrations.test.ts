import assert from 'node:assert/strict';
import test from 'node:test';
import { GoogleDriveProjectMemory, loadProjectMemoryConfig } from '../integrations/googleDriveProjectMemory';
import { MoneyPrinterTurboClient } from '../integrations/moneyPrinterTurbo';
import { TelegramProjectCommands } from '../integrations/telegramCommands';

const config = {
  accessToken: 'test-token',
  allowedTelegramChatIds: new Set(['123']),
  fileIds: { status: 'status-id', progress: 'progress-id', decision: 'decision-id' },
};

test('fails closed when a required Drive ID is missing or duplicated', () => {
  assert.throws(() => loadProjectMemoryConfig({}), /TELEGRAM_ALLOWED_CHAT_IDS/);
  assert.throws(() => loadProjectMemoryConfig({
    TELEGRAM_ALLOWED_CHAT_IDS: '123', GOOGLE_DRIVE_ACCESS_TOKEN: 'token',
    GOOGLE_DRIVE_STATUS_FILE_ID: 'same', GOOGLE_DRIVE_PROGRESS_FILE_ID: 'same',
    GOOGLE_DRIVE_DECISION_FILE_ID: 'decision',
  }), /three distinct/);
});

test('rejects an unauthorized Telegram chat before any Drive request', async () => {
  let calls = 0;
  const memory = new GoogleDriveProjectMemory(config, async () => { calls++; return new Response(); });
  await assert.rejects(memory.read('999', 'status'), /not authorized/);
  assert.equal(calls, 0);
});

test('acceptance: /memory_check verifies exactly the three shared markdown files without mutation', async () => {
  const calls: Array<{ url: string; method: string }> = [];
  const names: Record<string, string> = { 'status-id': 'Status.md', 'progress-id': 'Progress.md', 'decision-id': 'Decision.md' };
  const request = async (url: string | URL | Request, init?: RequestInit) => {
    const value = String(url);
    calls.push({ url: value, method: init?.method || 'GET' });
    const id = Object.keys(names).find((candidate) => value.includes(candidate))!;
    return new Response(JSON.stringify({ id, name: names[id], capabilities: { canDownload: true } }), { status: 200 });
  };
  const memory = new GoogleDriveProjectMemory(config, request as typeof fetch);
  const video = new MoneyPrinterTurboClient({ baseUrl: 'https://video.example', apiKey: 'secret' }, async () => {
    throw new Error('video service must not be called by memory acceptance test');
  });
  const result = await new TelegramProjectCommands(memory, video).handle('123', '/memory_check');
  assert.equal(result?.text, '✅ Status.md\n✅ Progress.md\n✅ Decision.md');
  assert.equal(calls.length, 3);
  assert.ok(calls.every((call) => call.method === 'GET'));
});

test('video creation delegates one bounded Arabic portrait job', async () => {
  let body: any;
  let headers: HeadersInit | undefined;
  const client = new MoneyPrinterTurboClient({ baseUrl: 'https://video.example', apiKey: 'secret' }, async (_url, init) => {
    body = JSON.parse(String(init?.body));
    headers = init?.headers;
    return new Response(JSON.stringify({ data: { task_id: '12345678-abcd' } }), { status: 200 });
  });
  assert.equal(await client.createVideo('تمارين آمنة لآلام الرقبة'), '12345678-abcd');
  assert.equal(body.video_language, 'ar');
  assert.equal(body.video_aspect, '9:16');
  assert.equal(body.video_count, 1);
  assert.equal((headers as Record<string, string>)['x-api-key'], 'secret');
});
