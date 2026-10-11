import {messages} from './i18n';

export type SlashCommand = {
  name: string;
  description: string;
};

export type SlashCommandMatch = SlashCommand & {
  matchedPrefix: string;
  unmatchedSuffix: string;
};

export function slashCommands(): SlashCommand[] {
  return [
    {name: '/compact', description: messages().slash.compact},
  ];
}

/** @deprecated Prefer slashCommands() so descriptions follow the active locale. */
export const SLASH_COMMANDS: SlashCommand[] = slashCommands();

export function matchingSlashCommands(input: string): SlashCommandMatch[] {
  if (!input.startsWith('/')) return [];
  const query = input.trimStart().split(/\s+/, 1)[0] ?? '';
  return slashCommands()
    .filter((command) => command.name.toLowerCase().startsWith(query.toLowerCase()))
    .map((command) => ({
      ...command,
      matchedPrefix: command.name.slice(0, query.length),
      unmatchedSuffix: command.name.slice(query.length),
    }));
}

export function shouldShowSlashCommands(input: string, busy: boolean) {
  return !busy && input.startsWith('/');
}
