export type MemoryDocument = 'status' | 'progress' | 'decision';

const expectedNames: Record<MemoryDocument, string> = {
  status: 'Status.md',
  progress: 'Progress.md',
  decision: 'Decision.md',
};

export interface ProjectMemoryConfig {
  accessToken: string;
  allowedTelegramChatIds: ReadonlySet<string>;
  fileIds: Record<MemoryDocument, string>;
}

export interface DriveFileMetadata {
  id: string;
  name: string;
  mimeType?: string;
  capabilities?: { canDownload?: boolean };
}

export interface MemoryCheck {
  document: MemoryDocument;
  id: string;
  expectedName: string;
  actualName: string;
  readable: boolean;
}

function required(env: NodeJS.ProcessEnv, name: string): string {
  const value = env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

export function loadProjectMemoryConfig(env: NodeJS.ProcessEnv = process.env): ProjectMemoryConfig {
  const chatIds = required(env, 'TELEGRAM_ALLOWED_CHAT_IDS')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
  const fileIds = {
    status: required(env, 'GOOGLE_DRIVE_STATUS_FILE_ID'),
    progress: required(env, 'GOOGLE_DRIVE_PROGRESS_FILE_ID'),
    decision: required(env, 'GOOGLE_DRIVE_DECISION_FILE_ID'),
  };
  if (new Set(Object.values(fileIds)).size !== 3) {
    throw new Error('Google Drive project-memory file IDs must be three distinct values');
  }
  return {
    accessToken: required(env, 'GOOGLE_DRIVE_ACCESS_TOKEN'),
    allowedTelegramChatIds: new Set(chatIds),
    fileIds,
  };
}

export class GoogleDriveProjectMemory {
  constructor(
    private readonly config: ProjectMemoryConfig,
    private readonly request: typeof fetch = fetch,
  ) {}

  private assertAuthorized(chatId: string): void {
    if (!this.config.allowedTelegramChatIds.has(chatId)) {
      throw new Error('Telegram chat is not authorized for project memory');
    }
  }

  private async driveGet(path: string): Promise<Response> {
    const response = await this.request(`https://www.googleapis.com/drive/v3/${path}`, {
      headers: { Authorization: `Bearer ${this.config.accessToken}` },
    });
    if (!response.ok) throw new Error(`Google Drive request failed (${response.status})`);
    return response;
  }

  async read(chatId: string, document: MemoryDocument): Promise<string> {
    this.assertAuthorized(chatId);
    const id = encodeURIComponent(this.config.fileIds[document]);
    return (await this.driveGet(`files/${id}?alt=media`)).text();
  }

  async verify(chatId: string): Promise<MemoryCheck[]> {
    this.assertAuthorized(chatId);
    return Promise.all((Object.keys(expectedNames) as MemoryDocument[]).map(async (document) => {
      const id = this.config.fileIds[document];
      const fields = encodeURIComponent('id,name,mimeType,capabilities(canDownload)');
      const metadata = await (await this.driveGet(`files/${encodeURIComponent(id)}?fields=${fields}`)).json() as DriveFileMetadata;
      return {
        document,
        id,
        expectedName: expectedNames[document],
        actualName: metadata.name,
        readable: metadata.id === id && metadata.name === expectedNames[document] && metadata.capabilities?.canDownload !== false,
      };
    }));
  }
}
