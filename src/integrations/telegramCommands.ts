import { GoogleDriveProjectMemory, MemoryDocument } from './googleDriveProjectMemory';
import { MoneyPrinterTurboClient } from './moneyPrinterTurbo';

export interface TelegramCommandResult {
  text: string;
}

export class TelegramProjectCommands {
  constructor(
    private readonly memory: GoogleDriveProjectMemory,
    private readonly video: MoneyPrinterTurboClient,
  ) {}

  async handle(chatId: string, input: string): Promise<TelegramCommandResult | null> {
    const [rawCommand, ...args] = input.trim().split(/\s+/);
    const command = rawCommand?.split('@')[0].toLowerCase();
    const memoryMap: Partial<Record<string, MemoryDocument>> = {
      '/status': 'status',
      '/progress': 'progress',
      '/decision': 'decision',
    };
    if (memoryMap[command]) return { text: await this.memory.read(chatId, memoryMap[command]!) };
    if (command === '/memory_check') {
      const checks = await this.memory.verify(chatId);
      return { text: checks.map((item) => `${item.readable ? '✅' : '❌'} ${item.expectedName}`).join('\n') };
    }
    if (command === '/video_create') {
      const taskId = await this.video.createVideo(args.join(' '));
      return { text: `Video task created: ${taskId}` };
    }
    if (command === '/video_status') {
      const task = await this.video.getTask(args[0] || '');
      return { text: `Video task ${task.task_id}: ${task.progress ?? 0}% (state ${task.state})` };
    }
    return null;
  }
}
