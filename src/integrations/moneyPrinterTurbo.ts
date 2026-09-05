export interface MoneyPrinterConfig {
  baseUrl: string;
  apiKey: string;
}

export function loadMoneyPrinterConfig(env: NodeJS.ProcessEnv = process.env): MoneyPrinterConfig {
  const baseUrl = env.MONEYPRINTER_API_URL?.trim().replace(/\/$/, '');
  const apiKey = env.MONEYPRINTER_API_KEY?.trim();
  if (!baseUrl) throw new Error('Missing required environment variable: MONEYPRINTER_API_URL');
  if (!apiKey) throw new Error('Missing required environment variable: MONEYPRINTER_API_KEY');
  if (!baseUrl.startsWith('https://') && !/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(baseUrl)) {
    throw new Error('MONEYPRINTER_API_URL must use HTTPS except on localhost');
  }
  return { baseUrl, apiKey };
}

export class MoneyPrinterTurboClient {
  constructor(private readonly config: MoneyPrinterConfig, private readonly request: typeof fetch = fetch) {}

  private async call(path: string, init: RequestInit = {}): Promise<any> {
    const response = await this.request(`${this.config.baseUrl}/api/v1${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey,
        ...(init.headers || {}),
      },
    });
    if (!response.ok) throw new Error(`MoneyPrinterTurbo request failed (${response.status})`);
    return response.json();
  }

  async createVideo(subject: string): Promise<string> {
    const cleanSubject = subject.trim();
    if (cleanSubject.length < 5 || cleanSubject.length > 500) {
      throw new Error('Video subject must contain 5-500 characters');
    }
    const result = await this.call('/videos', {
      method: 'POST',
      body: JSON.stringify({
        video_subject: cleanSubject,
        video_language: 'ar',
        video_aspect: '9:16',
        video_count: 1,
      }),
    });
    const taskId = result?.data?.task_id;
    if (typeof taskId !== 'string' || !taskId) throw new Error('MoneyPrinterTurbo returned no task ID');
    return taskId;
  }

  async getTask(taskId: string): Promise<any> {
    if (!/^[a-zA-Z0-9-]{8,80}$/.test(taskId)) throw new Error('Invalid MoneyPrinterTurbo task ID');
    return (await this.call(`/tasks/${encodeURIComponent(taskId)}`)).data;
  }
}
